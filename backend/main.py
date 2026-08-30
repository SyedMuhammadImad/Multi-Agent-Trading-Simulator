"""
FastAPI Application — REST + WebSocket API layer.

Exposes:
- /ws — Real-time event stream via WebSocket
- /api/portfolio — Portfolio state and metrics
- /api/agents — Agent health and status
- /api/signals — Recent trading signals
- /api/orders — Order history
- /api/risk — Risk parameters and current exposure
- /api/controls — Manual overrides (pause/resume/kill)

Security note: In production, add:
- JWT authentication on all endpoints
- Rate limiting (slowapi)
- CORS whitelist (not *)
- TLS/HTTPS
- API key rotation
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env before anything else
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# Import all system components
from core.event_bus import EventType, get_event_bus
from core.orchestrator import MasterOrchestrator
from core.database import (init_db, save_trade, save_equity_snapshot,
    save_agent_weights, load_agent_weights, get_trade_history, get_performance_stats)
from agents.strategy_agent import StrategyAgent
from agents.risk_agent import RiskManagementAgent, RiskParameters
from agents.execution_agent import ExecutionAgent, TradingMode
from agents.sentiment_agent import SentimentAgent
from agents.portfolio_regime_agents import PortfolioManagerAgent, RegimeDetectionAgent
from agents.advanced_agents import ComplianceAgent, BacktestingAgent, LearningAgent
from data.pipeline import MarketDataPipeline

logger = logging.getLogger(__name__)

# ─── System singleton ─────────────────────────────────────────────────────────
class TradingSystem:
    orchestrator: Optional[MasterOrchestrator] = None
    strategy_agent: Optional[StrategyAgent] = None
    risk_agent: Optional[RiskManagementAgent] = None
    execution_agent: Optional[ExecutionAgent] = None
    sentiment_agent: Optional[SentimentAgent] = None
    portfolio_manager: Optional[PortfolioManagerAgent] = None
    regime_agent: Optional[RegimeDetectionAgent] = None
    compliance_agent: Optional[ComplianceAgent] = None
    backtest_agent: Optional[BacktestingAgent] = None
    learning_agent: Optional[LearningAgent] = None
    data_pipeline: Optional[MarketDataPipeline] = None
    initialized: bool = False

system = TradingSystem()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the entire trading system on startup."""
    logger.info("Initializing trading system...")
    
    # Initialize all agents
    system.orchestrator = MasterOrchestrator()
    system.strategy_agent = StrategyAgent()
    system.risk_agent = RiskManagementAgent(initial_capital=100_000.0)
    system.execution_agent = ExecutionAgent(mode=TradingMode.PAPER)
    system.sentiment_agent = SentimentAgent()
    system.portfolio_manager = PortfolioManagerAgent(initial_capital=100_000.0)
    system.regime_agent = RegimeDetectionAgent()
    system.data_pipeline = MarketDataPipeline()
    system.compliance_agent = ComplianceAgent()
    system.backtest_agent = BacktestingAgent()
    system.learning_agent = LearningAgent(orchestrator=system.orchestrator)

    # Initialize database
    await init_db()

    # Load persisted agent weights (survive restarts)
    saved_weights = await load_agent_weights()
    if saved_weights:
        for agent_id, weight in saved_weights.items():
            system.orchestrator.update_agent_weight(agent_id, weight)
        logger.info(f"Restored agent weights: {saved_weights}")

    # Start all agents
    agents = [
        system.orchestrator,
        system.strategy_agent,
        system.risk_agent,
        system.execution_agent,
        system.sentiment_agent,
        system.portfolio_manager,
        system.regime_agent,
    ]
    
    for agent in agents:
        await agent.start()

    # Start event bus and data pipeline concurrently
    bus = get_event_bus()
    asyncio.create_task(bus.start())
    asyncio.create_task(system.data_pipeline.start())
    
    # Hook database persistence to event bus
    bus = get_event_bus()

    async def _persist_closed_trade(event):
        try:
            trade = event.payload.get("trade", {})
            if trade:
                await save_trade(trade)
                await save_equity_snapshot(
                    system.risk_agent.portfolio_state.get("total_capital", 100000),
                    daily_pnl=system.risk_agent.portfolio_state.get("daily_pnl", 0)
                )
                # Persist updated agent weights after each trade
                if system.orchestrator:
                    await save_agent_weights(system.orchestrator.agent_weights)
        except Exception as e:
            logger.error(f"DB persistence error: {e}")

    from core.event_bus import Event as _Event
    bus.subscribe(EventType.POSITION_CLOSED, _persist_closed_trade)

    system.initialized = True
    logger.info("✅ Trading system fully initialized — all agents running")

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down trading system...")
    await system.data_pipeline.stop()
    for agent in agents:
        await agent.stop()
    await bus.stop()
    logger.info("Trading system shutdown complete")


# ─── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Hedge Fund Trading Platform",
    description="Multi-agent paper-trading simulation. Not production ready.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── WebSocket connection manager ────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self._connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info(f"WS client connected | total: {len(self._connections)}")

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.remove(ws)
        logger.info(f"WS client disconnected | remaining: {len(self._connections)}")

    async def broadcast(self, message: dict) -> None:
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


ws_manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time event stream.
    Clients receive all events from the event bus in real-time.
    """
    await ws_manager.connect(websocket)
    bus = get_event_bus()
    
    try:
        # Initial state snapshot
        if system.initialized:
            await websocket.send_json({
                "type": "snapshot",
                "data": await _get_full_snapshot(),
                "timestamp": time.time(),
            })

        # Stream events from broadcast queue
        while True:
            try:
                event_data = await asyncio.wait_for(
                    bus._broadcast_queue.get(), timeout=1.0
                )
                await websocket.send_json({
                    "type": "event",
                    "data": event_data,
                    "timestamp": time.time(),
                })
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await websocket.send_json({"type": "heartbeat", "timestamp": time.time()})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


# ─── REST API endpoints ───────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy" if system.initialized else "initializing",
        "timestamp": time.time(),
        "ws_connections": ws_manager.connection_count,
        "pipeline_stats": system.data_pipeline.stats if system.data_pipeline else {},
        "bus_stats": get_event_bus().stats,
    }


@app.get("/api/portfolio")
async def get_portfolio():
    if not system.portfolio_manager:
        raise HTTPException(503, "System not initialized")
    return {
        "portfolio": system.portfolio_manager.portfolio_summary,
        "metrics": system.portfolio_manager.performance_metrics,
        "risk_state": system.risk_agent.portfolio_state if system.risk_agent else {},
    }


@app.get("/api/agents")
async def get_agents():
    agents = []
    for agent in _get_all_agents():
        agents.append(agent.health_check())
    return {"agents": agents, "count": len(agents)}


@app.get("/api/signals")
async def get_signals():
    bus = get_event_bus()
    return {
        "strategy_signals": bus.get_history(EventType.STRATEGY_SIGNAL, limit=20),
        "sentiment_signals": bus.get_history(EventType.SENTIMENT_SIGNAL, limit=10),
        "risk_assessments": bus.get_history(EventType.RISK_ASSESSMENT, limit=10),
    }


@app.get("/api/orders")
async def get_orders():
    if not system.execution_agent:
        raise HTTPException(503, "System not initialized")
    return {
        "open_orders": system.execution_agent.open_orders,
        "order_history": system.execution_agent.order_history,
        "mode": system.execution_agent.trading_mode,
    }


@app.get("/api/risk")
async def get_risk():
    if not system.risk_agent:
        raise HTTPException(503, "System not initialized")
    return {
        "portfolio": system.risk_agent.portfolio_state,
        "parameters": system.risk_agent.risk_parameters,
        "agent_weights": system.orchestrator.agent_weights if system.orchestrator else {},
        "kill_switch_active": system.orchestrator.kill_switch_active if system.orchestrator else False,
        "regime": system.regime_agent.current_regime if system.regime_agent else "UNKNOWN",
    }


@app.get("/api/sentiment")
async def get_sentiment():
    if not system.sentiment_agent:
        raise HTTPException(503, "System not initialized")
    return {
        "current_sentiment": system.sentiment_agent.current_sentiment,
        "recent_news": system.sentiment_agent.recent_news,
    }


@app.get("/api/decisions")
async def get_decisions():
    if not system.orchestrator:
        raise HTTPException(503, "System not initialized")
    return {
        "recent_decisions": system.orchestrator.recent_decisions,
        "agent_weights": system.orchestrator.agent_weights,
    }


# ─── Control endpoints ────────────────────────────────────────────────────────

class AgentControlRequest(BaseModel):
    agent_id: str
    action: str  # pause | resume | restart


class RiskUpdateRequest(BaseModel):
    max_portfolio_risk_pct: Optional[float] = None
    max_daily_loss_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    max_total_exposure_pct: Optional[float] = None


class SymbolWatchlistRequest(BaseModel):
    symbol: str
    action: str  # add | remove


class TestSignalRequest(BaseModel):
    symbol: str
    direction: str  # BUY | SELL
    price: float
    confidence: float = 0.9


@app.post("/api/controls/agent")
async def control_agent(request: AgentControlRequest):
    agent = _find_agent(request.agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {request.agent_id} not found")

    if request.action == "pause":
        agent.pause()
        return {"status": "paused", "agent_id": request.agent_id}
    elif request.action == "resume":
        agent.resume()
        return {"status": "resumed", "agent_id": request.agent_id}
    else:
        raise HTTPException(400, f"Unknown action: {request.action}")


@app.post("/api/controls/kill-switch")
async def activate_kill_switch(authorized_by: str = "manual"):
    """
    Emergency kill switch — closes all positions and stops trading.
    IRREVERSIBLE until manually reset.
    """
    bus = get_event_bus()
    from core.event_bus import Event
    await bus.publish(Event(
        event_type=EventType.KILL_SWITCH_ACTIVATED,
        source_agent="manual_override",
        payload={"reason": f"Manual kill switch by {authorized_by}", "timestamp": time.time()},
        priority=1,
    ))
    logger.critical(f"MANUAL KILL SWITCH activated by {authorized_by}")
    return {"status": "kill_switch_activated", "authorized_by": authorized_by}


@app.post("/api/controls/reset-kill-switch")
async def reset_kill_switch(authorized_by: str = "manual"):
    if system.orchestrator:
        system.orchestrator.deactivate_kill_switch(authorized_by)
    if system.risk_agent:
        system.risk_agent.deactivate_kill_switch()
    return {"status": "kill_switch_reset", "authorized_by": authorized_by}


@app.post("/api/controls/risk")
async def update_risk_parameters(request: RiskUpdateRequest):
    if not system.risk_agent:
        raise HTTPException(503, "System not initialized")
    
    params = system.risk_agent.params
    if request.max_portfolio_risk_pct is not None:
        params.max_portfolio_risk_pct = request.max_portfolio_risk_pct
    if request.max_daily_loss_pct is not None:
        params.max_daily_loss_pct = request.max_daily_loss_pct
    if request.max_drawdown_pct is not None:
        params.max_drawdown_pct = request.max_drawdown_pct
    if request.max_total_exposure_pct is not None:
        params.max_total_exposure_pct = request.max_total_exposure_pct

    return {"status": "updated", "parameters": system.risk_agent.risk_parameters}


@app.post("/api/controls/watchlist")
async def update_watchlist(request: SymbolWatchlistRequest):
    if not system.strategy_agent:
        raise HTTPException(503, "System not initialized")
    
    symbol = request.symbol.upper()
    if request.action == "add":
        system.strategy_agent.add_to_watchlist(symbol)
        system.sentiment_agent.add_symbol(symbol)
        return {"status": "added", "symbol": symbol, "watchlist": system.strategy_agent.watchlist}
    elif request.action == "remove":
        system.strategy_agent.remove_from_watchlist(symbol)
        return {"status": "removed", "symbol": symbol, "watchlist": system.strategy_agent.watchlist}
    else:
        raise HTTPException(400, "action must be 'add' or 'remove'")


@app.post("/api/controls/inject-shock")
async def inject_price_shock(symbol: str, shock_pct: float):
    """Stress test: inject a price shock for a symbol."""
    if not system.data_pipeline:
        raise HTTPException(503, "System not initialized")
    system.data_pipeline.inject_price_shock(symbol, shock_pct / 100)
    return {"status": "shock_injected", "symbol": symbol, "shock_pct": shock_pct}


@app.post("/api/controls/inject-test-signals")
async def inject_test_signals(request: TestSignalRequest):
    """Stress test: inject agreeing strategy and sentiment signals."""
    symbol = request.symbol.upper()
    direction = request.direction.upper()
    if direction not in {"BUY", "SELL"}:
        raise HTTPException(400, "direction must be BUY or SELL")
    if request.price <= 0:
        raise HTTPException(400, "price must be positive")

    confidence = max(0.0, min(1.0, request.confidence))
    base_payload = {
        "symbol": symbol,
        "direction": direction,
        "confidence": confidence,
        "price": request.price,
        "ttl_seconds": 120.0,
    }

    bus = get_event_bus()
    from core.event_bus import Event
    await bus.publish(Event(
        event_type=EventType.STRATEGY_SIGNAL,
        source_agent="strategy_agent",
        payload={
            **base_payload,
            "reasoning": "Injected paired test strategy signal",
            "strategy_count": 1,
            "indicators": {"price": request.price, "rsi": 50.0},
        },
        priority=2,
    ))
    await bus.publish(Event(
        event_type=EventType.SENTIMENT_SIGNAL,
        source_agent="sentiment_agent",
        payload={
            **base_payload,
            "reasoning": "Injected paired test sentiment signal",
            "sentiment_data": {"symbol": symbol, "direction": direction},
        },
        priority=2,
    ))
    return {
        "status": "test_signals_injected",
        "symbol": symbol,
        "direction": direction,
        "price": request.price,
    }


@app.get("/api/history")
async def get_trade_history_endpoint(limit: int = 50, symbol: str = None):
    trades = await get_trade_history(limit=limit, symbol=symbol)
    return {"trades": trades, "count": len(trades)}


@app.get("/api/stats")
async def get_performance_stats_endpoint():
    stats = await get_performance_stats()
    return {"performance": stats, "sentiment_nlp": system.sentiment_agent.nlp_status if system.sentiment_agent else {}}


@app.post("/api/backtest")
async def run_backtest(strategy: str = "trend_following", symbol: str = "AAPL", days: int = 252):
    if not system.backtest_agent:
        raise HTTPException(503, "Backtest agent not initialized")
    result = await system.backtest_agent.run_backtest(strategy, symbol, days)
    if result:
        return result.to_dict()
    raise HTTPException(500, "Backtest failed")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_all_agents():
    return [
        a for a in [
            system.orchestrator,
            system.strategy_agent,
            system.risk_agent,
            system.execution_agent,
            system.sentiment_agent,
            system.portfolio_manager,
            system.regime_agent,
        ] if a is not None
    ]


def _find_agent(agent_id: str):
    for agent in _get_all_agents():
        if agent.agent_id == agent_id:
            return agent
    return None


async def _get_full_snapshot() -> dict:
    """Full system state for initial WebSocket connection."""
    return {
        "portfolio": system.portfolio_manager.portfolio_summary if system.portfolio_manager else {},
        "agents": [a.health_check() for a in _get_all_agents()],
        "risk": system.risk_agent.risk_parameters if system.risk_agent else {},
        "regime": system.regime_agent.current_regime if system.regime_agent else "UNKNOWN",
        "sentiment": system.sentiment_agent.current_sentiment if system.sentiment_agent else {},
        "recent_decisions": system.orchestrator.recent_decisions[:10] if system.orchestrator else [],
        "pipeline_stats": system.data_pipeline.stats if system.data_pipeline else {},
    }


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
