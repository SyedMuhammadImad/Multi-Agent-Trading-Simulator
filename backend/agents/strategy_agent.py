"""
Strategy Agent — Identifies trading opportunities.
Supports: Trend Following, Mean Reversion, Breakout, RSI divergence.

This agent consumes market data and emits directional signals.
It does NOT make trade decisions — that's the orchestrator's job.

In production: swap the mock calculations with real TA-Lib calls
and your trained ML model inference.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

from core.base_agent import BaseAgent
from core.event_bus import Event, EventType

logger = logging.getLogger(__name__)


class StrategyType(str, Enum):
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    RSI_DIVERGENCE = "rsi_divergence"


@dataclass
class TechnicalIndicators:
    symbol: str
    price: float
    sma_20: float
    sma_50: float
    sma_200: float
    rsi_14: float
    macd_line: float
    macd_signal: float
    bb_upper: float
    bb_lower: float
    bb_mid: float
    volume: float
    avg_volume: float
    atr_14: float  # Average True Range — volatility measure

    @property
    def price_vs_sma20(self) -> float:
        return (self.price - self.sma_20) / self.sma_20

    @property
    def price_vs_sma50(self) -> float:
        return (self.price - self.sma_50) / self.sma_50

    @property
    def macd_histogram(self) -> float:
        return self.macd_line - self.macd_signal

    @property
    def bb_position(self) -> float:
        """0 = at lower band, 1 = at upper band"""
        band_width = self.bb_upper - self.bb_lower
        if band_width == 0:
            return 0.5
        return (self.price - self.bb_lower) / band_width

    @property
    def is_golden_cross(self) -> bool:
        return self.sma_50 > self.sma_200

    @property
    def volume_ratio(self) -> float:
        return self.volume / max(self.avg_volume, 1)


class StrategyAgent(BaseAgent):
    """
    Multi-strategy signal generator.
    
    Each strategy runs independently and votes.
    Final signal aggregates all active strategy votes.
    """

    def __init__(self, active_strategies: Optional[List[StrategyType]] = None):
        super().__init__("strategy_agent", "Strategy Agent")
        self.active_strategies = active_strategies or [
            StrategyType.TREND_FOLLOWING,
            StrategyType.MEAN_REVERSION,
            StrategyType.BREAKOUT,
            StrategyType.RSI_DIVERGENCE,
        ]
        self._indicators_cache: Dict[str, TechnicalIndicators] = {}
        self._signal_history: List[dict] = []
        self._watchlist: List[str] = ["AAPL", "MSFT", "BTC-USD", "ETH-USD", "EUR-USD"]

    async def initialize(self) -> None:
        self.bus.subscribe(EventType.MARKET_DATA_UPDATE, self.handle_event)
        logger.info(f"Strategy Agent initialized | strategies: {[s.value for s in self.active_strategies]}")

    async def process_event(self, event: Event) -> None:
        if event.event_type != EventType.MARKET_DATA_UPDATE:
            return

        payload = event.payload
        symbol = payload.get("symbol")
        if not symbol or symbol not in self._watchlist:
            return

        # Build indicator snapshot from incoming data
        indicators = self._build_indicators(symbol, payload)
        if not indicators:
            return

        self._indicators_cache[symbol] = indicators

        # Run all active strategies
        strategy_signals = []
        for strategy in self.active_strategies:
            result = self._run_strategy(strategy, indicators)
            if result:
                strategy_signals.append(result)

        if not strategy_signals:
            return

        # Aggregate strategy votes into one signal
        final_signal = self._aggregate_strategy_signals(symbol, strategy_signals)
        if final_signal:
            await self._emit_signal(symbol, final_signal, indicators)

    def _build_indicators(self, symbol: str, payload: dict) -> Optional[TechnicalIndicators]:
        """
        Build TechnicalIndicators from market data payload.
        In production: use real OHLCV data + TA-Lib calculations.
        """
        try:
            price = float(payload.get("price", 0))
            if price <= 0:
                return None

            # In production these come from real calculations over OHLCV history
            # Here we use the payload data with realistic fallbacks
            return TechnicalIndicators(
                symbol=symbol,
                price=price,
                sma_20=payload.get("sma_20", price * (1 + random.gauss(0, 0.02))),
                sma_50=payload.get("sma_50", price * (1 + random.gauss(0, 0.03))),
                sma_200=payload.get("sma_200", price * (1 + random.gauss(0, 0.05))),
                rsi_14=payload.get("rsi", 50.0),
                macd_line=payload.get("macd_line", random.gauss(0, 0.5)),
                macd_signal=payload.get("macd_signal", random.gauss(0, 0.5)),
                bb_upper=payload.get("bb_upper", price * 1.02),
                bb_lower=payload.get("bb_lower", price * 0.98),
                bb_mid=payload.get("bb_mid", price),
                volume=payload.get("volume", 1_000_000),
                avg_volume=payload.get("avg_volume", 900_000),
                atr_14=payload.get("atr", price * 0.015),
            )
        except Exception as e:
            logger.error(f"Failed to build indicators for {symbol}: {e}")
            return None

    def _run_strategy(
        self, strategy: StrategyType, ind: TechnicalIndicators
    ) -> Optional[Tuple[str, float, str]]:
        """
        Returns (direction, confidence, reasoning) or None if no signal.
        
        Each strategy has clear, testable rules.
        If you can't articulate the rule, don't trade it.
        """
        if strategy == StrategyType.TREND_FOLLOWING:
            return self._trend_following(ind)
        elif strategy == StrategyType.MEAN_REVERSION:
            return self._mean_reversion(ind)
        elif strategy == StrategyType.BREAKOUT:
            return self._breakout(ind)
        elif strategy == StrategyType.RSI_DIVERGENCE:
            return self._rsi_divergence(ind)
        return None

    def _trend_following(self, ind: TechnicalIndicators) -> Optional[Tuple[str, float, str]]:
        """
        Rules:
        - BUY: Price > SMA20 > SMA50, Golden cross, Volume confirmation
        - SELL: Price < SMA20 < SMA50, Death cross, Volume confirmation
        """
        is_uptrend = (
            ind.price > ind.sma_20 and
            ind.sma_20 > ind.sma_50 and
            ind.is_golden_cross and
            ind.macd_histogram > 0
        )
        is_downtrend = (
            ind.price < ind.sma_20 and
            ind.sma_20 < ind.sma_50 and
            not ind.is_golden_cross and
            ind.macd_histogram < 0
        )
        volume_confirmed = ind.volume_ratio > 1.2

        if is_uptrend and volume_confirmed:
            confidence = min(0.85, 0.5 + abs(ind.price_vs_sma20) * 5)
            return ("BUY", confidence, "Trend following: uptrend confirmed with volume")
        elif is_downtrend and volume_confirmed:
            confidence = min(0.85, 0.5 + abs(ind.price_vs_sma20) * 5)
            return ("SELL", confidence, "Trend following: downtrend confirmed with volume")

        return None

    def _mean_reversion(self, ind: TechnicalIndicators) -> Optional[Tuple[str, float, str]]:
        """
        Rules:
        - BUY: Price at/below lower BB, RSI oversold (<30)
        - SELL: Price at/above upper BB, RSI overbought (>70)
        """
        oversold = ind.rsi_14 < 32 and ind.bb_position < 0.15
        overbought = ind.rsi_14 > 68 and ind.bb_position > 0.85

        if oversold:
            # Confidence scales with how extreme the oversold condition is
            rsi_excess = (32 - ind.rsi_14) / 32
            bb_excess = (0.15 - ind.bb_position) / 0.15
            confidence = min(0.80, 0.45 + (rsi_excess + bb_excess) * 0.3)
            return ("BUY", confidence, f"Mean reversion: RSI={ind.rsi_14:.1f}, BB={ind.bb_position:.2f} oversold")
        elif overbought:
            rsi_excess = (ind.rsi_14 - 68) / 32
            bb_excess = (ind.bb_position - 0.85) / 0.15
            confidence = min(0.80, 0.45 + (rsi_excess + bb_excess) * 0.3)
            return ("SELL", confidence, f"Mean reversion: RSI={ind.rsi_14:.1f}, BB={ind.bb_position:.2f} overbought")

        return None

    def _breakout(self, ind: TechnicalIndicators) -> Optional[Tuple[str, float, str]]:
        """
        Rules:
        - BUY: Price breaks above upper BB with high volume (3x surge expected)
        - SELL: Price breaks below lower BB with high volume
        
        Note: Breakouts need sequential data in production. 
        Here we approximate with BB + volume.
        """
        high_volume_breakout = ind.volume_ratio > 2.0
        upside_breakout = ind.price > ind.bb_upper and high_volume_breakout
        downside_breakout = ind.price < ind.bb_lower and high_volume_breakout

        if upside_breakout:
            confidence = min(0.75, 0.45 + (ind.volume_ratio - 2.0) * 0.1)
            return ("BUY", confidence, f"Breakout: above BB with {ind.volume_ratio:.1f}x volume")
        elif downside_breakout:
            confidence = min(0.75, 0.45 + (ind.volume_ratio - 2.0) * 0.1)
            return ("SELL", confidence, f"Breakout: below BB with {ind.volume_ratio:.1f}x volume")

        return None

    def _rsi_divergence(self, ind: TechnicalIndicators) -> Optional[Tuple[str, float, str]]:
        """
        RSI neutral zone entry — when RSI crosses 50 with momentum.
        Simple but effective as a confirmation signal.
        """
        bullish_cross = 48 < ind.rsi_14 < 55 and ind.macd_histogram > 0
        bearish_cross = 45 < ind.rsi_14 < 52 and ind.macd_histogram < 0

        if bullish_cross:
            return ("BUY", 0.45, f"RSI momentum cross up: {ind.rsi_14:.1f}")
        elif bearish_cross:
            return ("SELL", 0.45, f"RSI momentum cross down: {ind.rsi_14:.1f}")

        return None

    def _aggregate_strategy_signals(
        self, symbol: str, signals: List[Tuple[str, float, str]]
    ) -> Optional[dict]:
        """
        Combine multiple strategy signals into one.
        Direction must have majority agreement; confidence averages.
        """
        buy_signals = [(conf, reason) for dir, conf, reason in signals if dir == "BUY"]
        sell_signals = [(conf, reason) for dir, conf, reason in signals if dir == "SELL"]

        if not buy_signals and not sell_signals:
            return None

        # Direction by majority
        if len(buy_signals) > len(sell_signals):
            direction = "BUY"
            relevant = buy_signals
        elif len(sell_signals) > len(buy_signals):
            direction = "SELL"
            relevant = sell_signals
        else:
            # Tie — compare average confidence
            buy_conf = sum(c for c, _ in buy_signals) / len(buy_signals)
            sell_conf = sum(c for c, _ in sell_signals) / len(sell_signals)
            if buy_conf > sell_conf:
                direction = "BUY"
                relevant = buy_signals
            else:
                direction = "SELL"
                relevant = sell_signals

        avg_confidence = sum(c for c, _ in relevant) / len(relevant)
        # Bonus confidence for consensus
        if len(relevant) == len(signals):  # All strategies agree
            avg_confidence = min(0.95, avg_confidence * 1.15)

        combined_reasoning = " | ".join(r for _, r in relevant)

        return {
            "direction": direction,
            "confidence": round(avg_confidence, 4),
            "reasoning": combined_reasoning,
            "strategy_count": len(relevant),
        }

    async def _emit_signal(
        self, symbol: str, signal: dict, ind: TechnicalIndicators
    ) -> None:
        self.metrics.signals_generated += 1
        payload = {
            "symbol": symbol,
            "direction": signal["direction"],
            "confidence": signal["confidence"],
            "reasoning": signal["reasoning"],
            "strategy_count": signal["strategy_count"],
            "price": ind.price,
            "indicators": {
                "price": ind.price,
                "rsi": ind.rsi_14,
                "sma_20": ind.sma_20,
                "macd_histogram": ind.macd_histogram,
                "bb_position": ind.bb_position,
                "volume_ratio": ind.volume_ratio,
            },
            "ttl_seconds": 120.0,
        }
        await self.publish(EventType.STRATEGY_SIGNAL, payload, priority=3)
        
        logger.info(
            f"Strategy signal: {symbol} {signal['direction']} "
            f"({signal['confidence']:.0%}) — {signal['reasoning'][:80]}"
        )
        self._signal_history.append({"timestamp": time.time(), **payload})
        if len(self._signal_history) > 500:
            self._signal_history = self._signal_history[-500:]

    def add_to_watchlist(self, symbol: str) -> None:
        if symbol not in self._watchlist:
            self._watchlist.append(symbol)
            logger.info(f"Added {symbol} to strategy watchlist")

    def remove_from_watchlist(self, symbol: str) -> None:
        self._watchlist = [s for s in self._watchlist if s != symbol]

    @property
    def watchlist(self) -> List[str]:
        return self._watchlist.copy()

    @property
    def recent_signals(self) -> List[dict]:
        return self._signal_history[-20:]
