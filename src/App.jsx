import { useState, useEffect, useRef, useCallback } from "react";

// ─── WebSocket hook ────────────────────────────────────────────────────────
function useWebSocket(url) {
  const [events, setEvents] = useState([]);
  const [snapshot, setSnapshot] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => { setConnected(true); clearTimeout(reconnectTimer.current); };
    ws.onclose = () => {
      setConnected(false);
      reconnectTimer.current = setTimeout(connect, 3000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "snapshot") {
        setSnapshot(msg.data);
      } else if (msg.type === "event") {
        setEvents(prev => [...prev.slice(-200), msg.data]);
      }
    };
  }, [url]);

  useEffect(() => { connect(); return () => wsRef.current?.close(); }, [connect]);
  return { events, snapshot, connected };
}

// ─── API helper ───────────────────────────────────────────────────────────
const API = "http://localhost:8000/api";
async function apiFetch(path, opts = {}) {
  try {
    const r = await fetch(API + path, opts);
    return await r.json();
  } catch { return null; }
}

// ─── Sparkline ───────────────────────────────────────────────────────────
function Sparkline({ data, color = "#22d3ee", height = 32 }) {
  if (!data?.length) return null;
  const w = 120, h = height;
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

// ─── Status badge ────────────────────────────────────────────────────────
function Badge({ status }) {
  const colors = {
    running: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    paused:  "bg-amber-500/20 text-amber-400 border-amber-500/30",
    error:   "bg-red-500/20 text-red-400 border-red-500/30",
    stopped: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
  };
  return (
    <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${colors[status] || colors.stopped}`}>
      {status?.toUpperCase()}
    </span>
  );
}

// ─── Metric card ─────────────────────────────────────────────────────────
function MetricCard({ label, value, sub, color, spark }) {
  return (
    <div className="bg-[#0f1117] border border-zinc-800 rounded-lg p-4 flex flex-col gap-1 hover:border-zinc-600 transition-colors">
      <div className="text-[11px] text-zinc-500 uppercase tracking-widest font-mono">{label}</div>
      <div className={`text-2xl font-bold font-mono ${color || "text-white"}`}>{value}</div>
      {sub && <div className="text-xs text-zinc-500">{sub}</div>}
      {spark && <div className="mt-1"><Sparkline data={spark} color={color === "text-emerald-400" ? "#34d399" : color === "text-red-400" ? "#f87171" : "#94a3b8"} /></div>}
    </div>
  );
}

// ─── Panel ───────────────────────────────────────────────────────────────
function Panel({ title, children, className = "" }) {
  return (
    <div className={`bg-[#0f1117] border border-zinc-800 rounded-lg flex flex-col ${className}`}>
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center gap-2">
        <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
        <span className="text-xs font-mono text-zinc-400 uppercase tracking-widest">{title}</span>
      </div>
      <div className="flex-1 overflow-hidden">{children}</div>
    </div>
  );
}

// ─── Agent Monitor Panel ─────────────────────────────────────────────────
function AgentMonitor({ agents }) {
  return (
    <Panel title="Agent Monitor" className="h-full">
      <div className="p-3 space-y-2 overflow-y-auto max-h-80">
        {(agents || []).map(agent => (
          <div key={agent.agent_id} className="flex items-center justify-between bg-zinc-900/50 rounded px-3 py-2 border border-zinc-800/50">
            <div className="flex items-center gap-2 min-w-0">
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                agent.status === "running" ? "bg-emerald-400 shadow-[0_0_6px_#34d399]" :
                agent.status === "paused" ? "bg-amber-400" : "bg-red-400"
              }`} />
              <span className="text-xs font-mono text-zinc-300 truncate">{agent.name}</span>
            </div>
            <div className="flex items-center gap-3 flex-shrink-0">
              <span className="text-[10px] text-zinc-500 font-mono hidden sm:block">
                {agent.metrics?.events_processed || 0} evts
              </span>
              <span className="text-[10px] text-zinc-500 font-mono hidden sm:block">
                {agent.metrics?.avg_processing_ms?.toFixed(1) || 0}ms
              </span>
              <Badge status={agent.status} />
            </div>
          </div>
        ))}
        {(!agents?.length) && (
          <div className="text-center text-zinc-600 text-xs py-8 font-mono">Connecting to agents...</div>
        )}
      </div>
    </Panel>
  );
}

// ─── Trade Log ───────────────────────────────────────────────────────────
function TradeLog({ events }) {
  const relevant = events.filter(e =>
    ["order.filled", "order.rejected", "risk.breach", "risk.kill_switch",
     "strategy.signal", "sentiment.signal"].includes(e.event_type)
  ).slice(-40).reverse();

  const colors = {
    "order.filled": "text-emerald-400",
    "order.rejected": "text-red-400",
    "risk.breach": "text-amber-400",
    "risk.kill_switch": "text-red-300",
    "strategy.signal": "text-cyan-400",
    "sentiment.signal": "text-violet-400",
  };
  const icons = {
    "order.filled": "✓",
    "order.rejected": "✗",
    "risk.breach": "⚠",
    "risk.kill_switch": "🔴",
    "strategy.signal": "↑",
    "sentiment.signal": "◈",
  };

  return (
    <Panel title="Event Log" className="h-full">
      <div className="font-mono text-[11px] overflow-y-auto max-h-72">
        {relevant.map((e, i) => {
          const ts = new Date(e.timestamp * 1000).toLocaleTimeString("en-US", { hour12: false });
          const sym = e.payload?.symbol || "";
          const dir = e.payload?.direction || e.payload?.action || "";
          const conf = e.payload?.confidence ? ` ${(e.payload.confidence * 100).toFixed(0)}%` : "";
          return (
            <div key={i} className="flex gap-2 px-4 py-1.5 border-b border-zinc-900 hover:bg-zinc-900/40">
              <span className="text-zinc-600 flex-shrink-0">{ts}</span>
              <span className={`${colors[e.event_type] || "text-zinc-400"} flex-shrink-0`}>
                {icons[e.event_type] || "·"}
              </span>
              <span className={`${colors[e.event_type] || "text-zinc-400"} truncate`}>
                {sym && <span className="text-white">{sym} </span>}
                {dir && <span>{dir}</span>}
                {conf && <span className="text-zinc-400">{conf}</span>}
                {!sym && !dir && <span className="text-zinc-500">{e.event_type}</span>}
              </span>
            </div>
          );
        })}
        {!relevant.length && (
          <div className="text-center text-zinc-600 py-8">Waiting for events...</div>
        )}
      </div>
    </Panel>
  );
}

// ─── Positions Panel ──────────────────────────────────────────────────────
function PositionsPanel({ portfolio }) {
  const positions = portfolio?.positions || [];
  return (
    <Panel title="Open Positions" className="h-full">
      <div className="overflow-y-auto max-h-48">
        {positions.length === 0 ? (
          <div className="text-center text-zinc-600 text-xs py-8 font-mono">No open positions</div>
        ) : (
          <table className="w-full font-mono text-xs">
            <thead>
              <tr className="text-zinc-600 uppercase text-[10px] tracking-wider">
                <th className="px-4 py-2 text-left">Symbol</th>
                <th className="px-4 py-2 text-left">Side</th>
                <th className="px-4 py-2 text-right">Entry</th>
                <th className="px-4 py-2 text-right">Current</th>
                <th className="px-4 py-2 text-right">P&L</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos, i) => (
                <tr key={i} className="border-t border-zinc-900 hover:bg-zinc-900/40">
                  <td className="px-4 py-2 text-white">{pos.symbol}</td>
                  <td className={`px-4 py-2 ${pos.direction === "BUY" ? "text-emerald-400" : "text-red-400"}`}>
                    {pos.direction}
                  </td>
                  <td className="px-4 py-2 text-right text-zinc-400">${pos.entry_price?.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right text-zinc-300">${pos.current_price?.toFixed(2)}</td>
                  <td className={`px-4 py-2 text-right font-bold ${pos.unrealized_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {pos.unrealized_pnl >= 0 ? "+" : ""}${pos.unrealized_pnl?.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Panel>
  );
}

// ─── Risk Dashboard ───────────────────────────────────────────────────────
function RiskDashboard({ risk, regime }) {
  const params = risk?.parameters || {};
  const portfolio = risk?.portfolio || {};
  
  const drawdown = portfolio.drawdown_pct || 0;
  const dailyLoss = portfolio.daily_loss_pct || 0;
  const exposure = portfolio.exposure_pct || 0;
  const maxDD = (params.max_drawdown_pct || 0.15) * 100;
  const maxDaily = (params.max_daily_loss_pct || 0.05) * 100;
  const maxExp = (params.max_total_exposure_pct || 0.20) * 100;

  const regimeColors = {
    BULL: "text-emerald-400", BEAR: "text-red-400",
    SIDEWAYS: "text-amber-400", HIGH_VOLATILITY: "text-orange-400",
    CRISIS: "text-red-300", UNKNOWN: "text-zinc-500"
  };

  function RiskBar({ label, value, max, unit = "%" }) {
    const pct = Math.min(100, (value / max) * 100);
    const color = pct > 80 ? "bg-red-500" : pct > 60 ? "bg-amber-500" : "bg-emerald-500";
    return (
      <div className="space-y-1">
        <div className="flex justify-between text-[11px] font-mono">
          <span className="text-zinc-500">{label}</span>
          <span className="text-zinc-300">{value.toFixed(1)}{unit} / {max.toFixed(1)}{unit}</span>
        </div>
        <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
        </div>
      </div>
    );
  }

  return (
    <Panel title="Risk Dashboard">
      <div className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-xs text-zinc-500 font-mono">Market Regime</span>
          <span className={`text-sm font-bold font-mono ${regimeColors[regime] || "text-zinc-400"}`}>
            {regime || "UNKNOWN"}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-zinc-500 font-mono">VIX</span>
          <span className="text-sm font-mono text-zinc-300">{params.current_vix?.toFixed(1) || "—"}</span>
        </div>
        <div className="space-y-3 pt-2 border-t border-zinc-800">
          <RiskBar label="Drawdown" value={drawdown} max={maxDD} />
          <RiskBar label="Daily Loss" value={dailyLoss} max={maxDaily} />
          <RiskBar label="Exposure" value={exposure} max={maxExp} />
        </div>
      </div>
    </Panel>
  );
}

// ─── Controls Panel ────────────────────────────────────────────────────────
function ControlsPanel({ onKillSwitch, onResetKillSwitch }) {
  const [symbol, setSymbol] = useState("");
  const [shock, setShock] = useState(-10);
  const [showKillConfirm, setShowKillConfirm] = useState(false);

  return (
    <Panel title="Manual Controls">
      <div className="p-4 space-y-4">
        {/* Kill Switch */}
        <div className="space-y-2">
          <div className="text-[10px] text-zinc-600 font-mono uppercase tracking-wider">Emergency Controls</div>
          {!showKillConfirm ? (
            <button
              onClick={() => setShowKillConfirm(true)}
              className="w-full py-2 px-4 bg-red-900/30 border border-red-500/40 text-red-400 
                         rounded font-mono text-xs hover:bg-red-900/50 transition-all"
            >
              🔴 ACTIVATE KILL SWITCH
            </button>
          ) : (
            <div className="space-y-2">
              <div className="text-xs text-red-400 font-mono text-center">Close ALL positions?</div>
              <div className="flex gap-2">
                <button
                  onClick={() => { onKillSwitch(); setShowKillConfirm(false); }}
                  className="flex-1 py-1.5 bg-red-600 text-white rounded font-mono text-xs hover:bg-red-500"
                >
                  CONFIRM
                </button>
                <button
                  onClick={() => setShowKillConfirm(false)}
                  className="flex-1 py-1.5 bg-zinc-800 text-zinc-400 rounded font-mono text-xs hover:bg-zinc-700"
                >
                  CANCEL
                </button>
              </div>
            </div>
          )}
          <button
            onClick={onResetKillSwitch}
            className="w-full py-2 px-4 bg-zinc-900 border border-zinc-700 text-zinc-400
                       rounded font-mono text-xs hover:bg-zinc-800 transition-all"
          >
            ↺ Reset Kill Switch
          </button>
        </div>

        {/* Stress Test */}
        <div className="space-y-2 border-t border-zinc-800 pt-4">
          <div className="text-[10px] text-zinc-600 font-mono uppercase tracking-wider">Stress Test</div>
          <input
            value={symbol}
            onChange={e => setSymbol(e.target.value)}
            placeholder="Symbol (e.g. AAPL)"
            className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-1.5 
                       text-xs font-mono text-zinc-300 placeholder-zinc-600 focus:outline-none focus:border-cyan-500/50"
          />
          <div className="flex items-center gap-2">
            <input
              type="range" min={-50} max={50} value={shock}
              onChange={e => setShock(Number(e.target.value))}
              className="flex-1"
            />
            <span className={`text-xs font-mono w-12 text-right ${shock < 0 ? "text-red-400" : "text-emerald-400"}`}>
              {shock > 0 ? "+" : ""}{shock}%
            </span>
          </div>
          <button
            onClick={() => symbol && apiFetch(`/controls/inject-shock?symbol=${symbol}&shock_pct=${shock}`, { method: "POST" })}
            className="w-full py-2 bg-amber-900/30 border border-amber-500/30 text-amber-400
                       rounded font-mono text-xs hover:bg-amber-900/50 transition-all"
          >
            Inject Price Shock
          </button>
        </div>
      </div>
    </Panel>
  );
}

// ─── Sentiment Panel ──────────────────────────────────────────────────────
function SentimentPanel({ sentiment }) {
  const items = Object.entries(sentiment || {});
  return (
    <Panel title="Sentiment">
      <div className="p-3 space-y-2 overflow-y-auto max-h-60">
        {items.map(([sym, data]) => {
          const score = data.score || 0;
          const pct = Math.round((score + 1) / 2 * 100);
          return (
            <div key={sym} className="space-y-1">
              <div className="flex justify-between text-[11px] font-mono">
                <span className="text-zinc-300">{sym}</span>
                <span className={score >= 0.1 ? "text-emerald-400" : score <= -0.1 ? "text-red-400" : "text-zinc-500"}>
                  {data.direction} {(Math.abs(score) * 100).toFixed(0)}%
                </span>
              </div>
              <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    score >= 0.1 ? "bg-emerald-500" : score <= -0.1 ? "bg-red-500" : "bg-zinc-600"
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
        {!items.length && (
          <div className="text-center text-zinc-600 text-xs py-6 font-mono">Processing sentiment...</div>
        )}
      </div>
    </Panel>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────
export default function App() {
  const WS_URL = "ws://localhost:8000/ws";
  const { events, snapshot, connected } = useWebSocket(WS_URL);

  const [portfolio, setPortfolio] = useState(null);
  const [agents, setAgents] = useState([]);
  const [risk, setRisk] = useState(null);
  const [sentiment, setSentiment] = useState({});
  const [decisions, setDecisions] = useState([]);
  const [regime, setRegime] = useState("UNKNOWN");
  const [equitySpark, setEquitySpark] = useState([]);
  const [killActive, setKillActive] = useState(false);

  // Hydrate from snapshot
  useEffect(() => {
    if (!snapshot) return;
    if (snapshot.portfolio) setPortfolio(snapshot.portfolio);
    if (snapshot.agents) setAgents(snapshot.agents);
    if (snapshot.risk) setRisk({ parameters: snapshot.risk });
    if (snapshot.sentiment) setSentiment(snapshot.sentiment);
    if (snapshot.recent_decisions) setDecisions(snapshot.recent_decisions);
    if (snapshot.regime) setRegime(snapshot.regime);
  }, [snapshot]);

  // Poll REST endpoints every 2s for rich data
  useEffect(() => {
    const poll = async () => {
      const [port, agts, rsk, sent, dec] = await Promise.all([
        apiFetch("/portfolio"),
        apiFetch("/agents"),
        apiFetch("/risk"),
        apiFetch("/sentiment"),
        apiFetch("/decisions"),
      ]);
      if (port?.portfolio) {
        setPortfolio(port.portfolio);
        setEquitySpark(prev => [...prev.slice(-60), port.portfolio.total_value].filter(Boolean));
      }
      if (agts?.agents) setAgents(agts.agents);
      if (rsk) {
        setRisk(rsk);
        setRegime(rsk.regime || "UNKNOWN");
      }
      if (sent?.current_sentiment) setSentiment(sent.current_sentiment);
      if (dec?.recent_decisions) setDecisions(dec.recent_decisions);
    };
    poll();
    const t = setInterval(poll, 2000);
    return () => clearInterval(t);
  }, []);

  // Update agent statuses from events
  useEffect(() => {
    const lastEvent = events[events.length - 1];
    if (lastEvent?.event_type === "system.agent_status") {
      const d = lastEvent.payload;
      setAgents(prev => prev.map(a =>
        a.agent_id === d.agent_id ? { ...a, status: d.status, metrics: d.metrics } : a
      ));
    }
    if (lastEvent?.event_type === "market.regime.change") {
      setRegime(lastEvent.payload.regime);
    }
    if (lastEvent?.event_type === "risk.kill_switch") {
      setKillActive(true);
    }
  }, [events]);

  const handleKillSwitch = () => {
    apiFetch("/controls/kill-switch?authorized_by=dashboard_user", { method: "POST" });
    setKillActive(true);
  };
  const handleResetKillSwitch = () => {
    apiFetch("/controls/reset-kill-switch?authorized_by=dashboard_user", { method: "POST" });
    setKillActive(false);
  };

  const totalValue = portfolio?.total_value || 100000;
  const totalPnl = portfolio?.total_pnl || portfolio?.realized_pnl || 0;
  const unrealizedPnl = portfolio?.unrealized_pnl || 0;
  const drawdown = risk?.portfolio?.drawdown_pct || 0;
  const openPositions = portfolio?.open_positions || 0;
  const totalTrades = portfolio?.total_trades || 0;
  const totalReturn = portfolio?.total_return_pct || 0;

  return (
    <div className="min-h-screen bg-[#080a0f] text-white font-sans" style={{
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace"
    }}>
      {/* Kill switch banner */}
      {killActive && (
        <div className="bg-red-900/70 border-b border-red-500 px-6 py-2 text-center text-red-300 text-sm font-mono animate-pulse">
          🔴 KILL SWITCH ACTIVE — All positions being closed — Trading halted
        </div>
      )}

      {/* Header */}
      <header className="border-b border-zinc-800/60 px-6 py-4 flex items-center justify-between bg-[#0a0d13]">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-cyan-500/10 border border-cyan-500/30 rounded flex items-center justify-center">
              <span className="text-cyan-400 text-sm">⬡</span>
            </div>
            <div>
              <div className="text-sm font-bold tracking-wider text-white">NEXUS<span className="text-cyan-400">AI</span></div>
              <div className="text-[9px] text-zinc-600 tracking-widest uppercase">Multi-Agent Trading Platform</div>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-1 text-[10px] font-mono text-zinc-600 border-l border-zinc-800 pl-4">
            <span className="text-zinc-500">MODE:</span>
            <span className="text-amber-400 font-bold">PAPER</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Regime */}
          <div className="hidden sm:flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded px-3 py-1.5">
            <span className="text-[10px] text-zinc-600 font-mono">REGIME</span>
            <span className={`text-xs font-bold font-mono ${
              regime === "BULL" ? "text-emerald-400" : regime === "BEAR" ? "text-red-400" :
              regime === "CRISIS" ? "text-red-300" : "text-amber-400"
            }`}>{regime}</span>
          </div>
          {/* WS status */}
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400 shadow-[0_0_8px_#34d399]" : "bg-red-500"}`} />
            <span className="text-[10px] font-mono text-zinc-500">{connected ? "LIVE" : "DISCONNECTED"}</span>
          </div>
        </div>
      </header>

      {/* Main grid */}
      <main className="p-4 space-y-4">
        {/* Metrics row */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <MetricCard
            label="Portfolio Value"
            value={`$${totalValue.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`}
            color={totalReturn >= 0 ? "text-emerald-400" : "text-red-400"}
            spark={equitySpark}
          />
          <MetricCard
            label="Total P&L"
            value={`${totalPnl >= 0 ? "+" : ""}$${Math.abs(totalPnl).toFixed(0)}`}
            sub={`${totalReturn >= 0 ? "+" : ""}${totalReturn.toFixed(2)}%`}
            color={totalPnl >= 0 ? "text-emerald-400" : "text-red-400"}
          />
          <MetricCard
            label="Unrealized"
            value={`${unrealizedPnl >= 0 ? "+" : ""}$${Math.abs(unrealizedPnl).toFixed(0)}`}
            color={unrealizedPnl >= 0 ? "text-emerald-400" : "text-red-400"}
          />
          <MetricCard
            label="Drawdown"
            value={`${drawdown.toFixed(2)}%`}
            color={drawdown > 10 ? "text-red-400" : drawdown > 5 ? "text-amber-400" : "text-zinc-400"}
          />
          <MetricCard label="Open Positions" value={openPositions} color="text-cyan-400" />
          <MetricCard label="Total Trades" value={totalTrades} color="text-zinc-300" />
        </div>

        {/* Middle row: Agents + Log + Risk */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <AgentMonitor agents={agents} />
          <TradeLog events={events} />
          <div className="space-y-4">
            <RiskDashboard risk={risk} regime={regime} />
            <SentimentPanel sentiment={sentiment} />
          </div>
        </div>

        {/* Bottom row: Positions + Decisions + Controls */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <PositionsPanel portfolio={portfolio} />

          {/* Decision log */}
          <Panel title="Orchestrator Decisions">
            <div className="overflow-y-auto max-h-48 font-mono text-[11px]">
              {decisions.slice().reverse().slice(0, 20).map((d, i) => (
                <div key={i} className="flex gap-2 px-4 py-1.5 border-b border-zinc-900 hover:bg-zinc-900/40">
                  <span className={`flex-shrink-0 w-20 font-bold ${
                    d.action?.includes("BUY") ? "text-emerald-400" :
                    d.action?.includes("SELL") ? "text-red-400" :
                    d.action === "HOLD" ? "text-zinc-500" : "text-amber-400"
                  }`}>{d.action}</span>
                  <span className="text-zinc-300">{d.symbol}</span>
                  <span className="text-zinc-600 ml-auto">{(d.final_confidence * 100 || 0).toFixed(0)}%</span>
                </div>
              ))}
              {!decisions.length && (
                <div className="text-center text-zinc-600 py-8">Awaiting decisions...</div>
              )}
            </div>
          </Panel>

          <ControlsPanel onKillSwitch={handleKillSwitch} onResetKillSwitch={handleResetKillSwitch} />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800/40 px-6 py-3 flex justify-between text-[10px] font-mono text-zinc-700">
        <span>NEXUSAI v1.0.0 — Multi-Agent Hedge Fund Platform</span>
        <span>⚠ PAPER TRADING ONLY — Not financial advice</span>
      </footer>
    </div>
  );
}
