import React, { useState, useCallback, useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import {
  Search, Loader2, TrendingUp, TrendingDown, Minus,
  AlertTriangle, CheckCircle, XCircle, HelpCircle,
  ChevronDown, ChevronUp, ExternalLink,
} from "lucide-react";
import axios from "axios";

// ─── Constants ────────────────────────────────────────────────────────────────

const EXCHANGES = ["NSE", "BSE", "US"];

const CAT_META = {
  valuation:    { label: "Valuation",       icon: "📊", color: "blue",   weight: "30%" },
  fundamentals: { label: "Fundamentals",    icon: "💪", color: "emerald",weight: "35%" },
  risk:         { label: "Risk",            icon: "⚠️", color: "red",    weight: "20%" },
  future:       { label: "Future Potential",icon: "🚀", color: "purple", weight: "15%" },
};

const STATUS_COLORS = {
  green:  { bg: "bg-emerald-900/30", text: "text-emerald-400", border: "border-emerald-800", dot: "bg-emerald-500" },
  yellow: { bg: "bg-yellow-900/30",  text: "text-yellow-400",  border: "border-yellow-800",  dot: "bg-yellow-500" },
  red:    { bg: "bg-red-900/30",     text: "text-red-400",     border: "border-red-800",     dot: "bg-red-500"    },
  na:     { bg: "bg-gray-800/40",    text: "text-gray-500",    border: "border-gray-700",    dot: "bg-gray-600"   },
};

const VERDICT_STYLES = {
  BUY:   { bg: "bg-emerald-600", text: "text-white",    icon: TrendingUp,   label: "BUY"   },
  HOLD:  { bg: "bg-yellow-600",  text: "text-white",    icon: Minus,        label: "HOLD"  },
  AVOID: { bg: "bg-red-600",     text: "text-white",    icon: TrendingDown, label: "AVOID" },
  "N/A": { bg: "bg-gray-700",    text: "text-gray-300", icon: HelpCircle,   label: "N/A"   },
};

// ─── Breakout Context Panel ───────────────────────────────────────────────────

function BreakoutContextPanel({ data }) {
  const criteria = [
    { key: "price_breakout",   label: "Near Resistance",           short: "P" },
    { key: "volume_confirmed", label: "Volume Building",           short: "V" },
    { key: "momentum_ok",      label: "Momentum (RSI+MACD)",       short: "M" },
    { key: "trend_ok",         label: "Trend + Consolidation",     short: "T" },
    { key: "breakout_100d",    label: "Vol > Yesterday + 100D High", short: "E" },
  ];

  const strengthStyle = {
    STRONG:    "bg-emerald-600/30 border-emerald-700 text-emerald-300",
    MODERATE:  "bg-yellow-600/30  border-yellow-700  text-yellow-300",
    WATCHLIST: "bg-blue-700/30   border-blue-700    text-blue-300",
  }[data.strength] || "bg-gray-800 border-gray-700 text-gray-400";

  return (
    <div className="bg-gray-900 border border-blue-900 rounded-xl p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-blue-400">📈 Breakout Context</span>
        <span className="text-xs text-gray-500">· from latest NSE scan ({data.scan_date})</span>
        <span className={`ml-auto text-xs font-bold px-2.5 py-0.5 rounded-lg border ${strengthStyle}`}>
          {data.strength}  {data.strength_score?.toFixed(1)}
        </span>
      </div>

      {/* Key metrics grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="bg-gray-800 rounded-lg p-2.5">
          <div className="text-[11px] text-gray-500 mb-0.5">CMP</div>
          <div className="text-sm font-bold text-white">
            ₹{data.cmp?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </div>
          <div className={`text-[11px] font-semibold ${data.pct_change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {data.pct_change >= 0 ? "+" : ""}{data.pct_change?.toFixed(2)}%
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-2.5">
          <div className="text-[11px] text-gray-500 mb-0.5">RSI (14)</div>
          <div className={`text-sm font-bold ${
            data.rsi > 70 ? "text-red-400" : data.rsi > 55 ? "text-emerald-400" : "text-yellow-400"
          }`}>
            {data.rsi?.toFixed(1)}
          </div>
          <div className="text-[11px] text-gray-600">
            {data.rsi > 70 ? "Overbought" : data.rsi > 55 ? "Bullish zone" : "Neutral"}
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-2.5">
          <div className="text-[11px] text-gray-500 mb-0.5">Vol Ratio</div>
          <div className={`text-sm font-bold ${data.volume_ratio >= 2 ? "text-emerald-400" : "text-gray-300"}`}>
            {data.volume_ratio?.toFixed(2)}x
          </div>
          <div className="text-[11px] text-gray-600">vs 20-day avg</div>
        </div>

        <div className="bg-gray-800 rounded-lg p-2.5">
          <div className="text-[11px] text-gray-500 mb-0.5">52W High</div>
          <div className="text-sm font-bold text-gray-200">
            ₹{data.high_52w?.toLocaleString("en-IN")}
          </div>
          <div className="text-[11px] text-gray-600">
            {data.high_52w && data.cmp
              ? `${(((data.high_52w - data.cmp) / data.high_52w) * 100).toFixed(1)}% below`
              : "—"}
          </div>
        </div>
      </div>

      {/* MACD row */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: "MACD",      val: data.macd,        colored: true  },
          { label: "Signal",    val: data.macd_signal, colored: false },
          { label: "Histogram", val: data.macd_hist,   colored: true  },
        ].map(({ label, val, colored }) => (
          <div key={label} className="bg-gray-800 rounded-lg p-2.5">
            <div className="text-[11px] text-gray-500 mb-0.5">{label}</div>
            <div className={`text-xs font-mono font-bold ${
              colored ? (val >= 0 ? "text-emerald-400" : "text-red-400") : "text-gray-300"
            }`}>
              {val != null ? val.toFixed(3) : "—"}
            </div>
          </div>
        ))}
      </div>

      {/* Price levels + entry/SL/target */}
      <div className="flex flex-wrap gap-3 text-xs text-gray-500">
        <span>SMA50 <span className="text-gray-300 font-semibold ml-1">₹{data.sma50?.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span></span>
        {data.entry_price  && <span>Entry  <span className="text-emerald-400 font-semibold ml-1">₹{data.entry_price?.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span></span>}
        {data.stop_loss    && <span>Stop   <span className="text-red-400    font-semibold ml-1">₹{data.stop_loss?.toLocaleString("en-IN",    { maximumFractionDigits: 2 })}</span></span>}
        {data.target_price && <span>Target <span className="text-blue-400   font-semibold ml-1">₹{data.target_price?.toLocaleString("en-IN",  { maximumFractionDigits: 2 })}</span></span>}
      </div>

      {/* Criteria badges */}
      <div className="flex flex-wrap gap-1.5">
        {criteria.map(({ key, label, short }) => (
          <span
            key={key}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border ${
              data[key]
                ? "bg-emerald-900/40 border-emerald-700 text-emerald-300"
                : "bg-gray-800/60 border-gray-700 text-gray-500 line-through decoration-gray-600"
            }`}
          >
            <span className={`w-4 h-4 rounded text-[9px] flex items-center justify-center font-bold shrink-0 ${
              data[key] ? "bg-emerald-700 text-emerald-100" : "bg-gray-700 text-gray-500"
            }`}>
              {short}
            </span>
            {label}
          </span>
        ))}
        {data.breakout_type && (
          <span className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-blue-900/30 border border-blue-800 text-blue-300">
            {data.breakout_type}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Evaluation sub-components ────────────────────────────────────────────────

function ScoreBar({ score, color = "blue" }) {
  const colors = {
    blue:    "bg-blue-500",
    emerald: "bg-emerald-500",
    red:     "bg-red-400",
    purple:  "bg-purple-500",
    yellow:  "bg-yellow-500",
  };
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${colors[color]}`}
          style={{ width: `${Math.min(100, score || 0)}%` }}
        />
      </div>
      <span className="text-xs text-white font-semibold w-8 text-right">
        {score != null ? Math.round(score) : "—"}
      </span>
    </div>
  );
}

function StatusIcon({ status }) {
  if (status === "green")  return <CheckCircle  className="w-4 h-4 text-emerald-400 shrink-0" />;
  if (status === "red")    return <XCircle      className="w-4 h-4 text-red-400    shrink-0" />;
  if (status === "yellow") return <AlertTriangle className="w-4 h-4 text-yellow-400 shrink-0" />;
  return <HelpCircle className="w-4 h-4 text-gray-600 shrink-0" />;
}

function ChecksTable({ checks }) {
  if (!checks?.length) return <p className="text-xs text-gray-500">No checks available.</p>;
  return (
    <div className="space-y-1.5">
      {checks.map((c, i) => {
        const sc = STATUS_COLORS[c.status] || STATUS_COLORS.na;
        return (
          <div
            key={i}
            className={`flex items-start gap-2.5 px-3 py-2 rounded-lg border ${sc.bg} ${sc.border}`}
          >
            <StatusIcon status={c.status} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-white">{c.name}</span>
                {c.value && (
                  <span className={`text-xs font-mono font-bold ${sc.text}`}>{c.value}</span>
                )}
              </div>
              {c.note      && <p className="text-xs text-gray-400 mt-0.5">{c.note}</p>}
              {c.benchmark && <p className="text-[11px] text-gray-600 mt-0.5">{c.benchmark}</p>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function CategorySection({ catKey, checks, score }) {
  const [open, setOpen] = useState(true);
  const meta = CAT_META[catKey];
  if (!meta) return null;

  const colorMap = {
    blue:    "text-blue-400",
    emerald: "text-emerald-400",
    red:     "text-red-400",
    purple:  "text-purple-400",
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-800/50 transition text-left"
      >
        <span className="text-lg">{meta.icon}</span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-semibold ${colorMap[meta.color]}`}>{meta.label}</span>
            <span className="text-xs text-gray-500">· {meta.weight} weight</span>
          </div>
          <ScoreBar score={score} color={meta.color} />
        </div>
        <span className="text-xs text-gray-500 mr-2">
          {checks?.filter(c => c.status === "green").length ?? 0} / {checks?.length ?? 0} green
        </span>
        {open
          ? <ChevronUp   className="w-4 h-4 text-gray-500 shrink-0" />
          : <ChevronDown className="w-4 h-4 text-gray-500 shrink-0" />}
      </button>
      {open && (
        <div className="px-4 pb-4 border-t border-gray-800 pt-3">
          <ChecksTable checks={checks} />
        </div>
      )}
    </div>
  );
}

function PriceTargetBar({ current, low, mid, high }) {
  if (!mid) return null;
  const mn = Math.min(current ?? mid, low ?? mid) * 0.90;
  const mx = Math.max(current ?? mid, high ?? mid) * 1.10;
  const range = mx - mn;
  if (range <= 0) return null;
  const pct = (v) => ((v - mn) / range) * 100;

  return (
    <div className="relative h-6 w-full">
      <div className="absolute top-1/2 left-0 right-0 h-1 -translate-y-1/2 bg-gray-700 rounded" />
      {low && high && (
        <div
          className="absolute top-1/2 h-1 -translate-y-1/2 bg-blue-800/60 rounded"
          style={{ left: `${pct(low)}%`, width: `${pct(high) - pct(low)}%` }}
        />
      )}
      {mid && (
        <div className="absolute top-0 bottom-0 w-0.5 bg-blue-400"
          style={{ left: `${pct(mid)}%` }} />
      )}
      {current && (
        <div className="absolute top-0 bottom-0 w-1 bg-white rounded"
          style={{ left: `${pct(current)}%` }} />
      )}
    </div>
  );
}

function ResultCard({ result }) {
  const vs = VERDICT_STYLES[result.verdict] || VERDICT_STYLES["N/A"];
  const VIcon = vs.icon;
  const currency = result.currency || "₹";
  const upside = result.upside_pct;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-widest mb-0.5">
              {result.ticker}
            </div>
            <h2 className="text-xl font-bold text-white">
              {result.company_name || result.ticker}
            </h2>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              {result.sector && (
                <span className="text-xs text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
                  {result.sector}
                </span>
              )}
              {result.industry && result.industry !== result.sector && (
                <span className="text-xs text-gray-500">{result.industry}</span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            {result.current_price && (
              <div className="text-right">
                <div className="text-2xl font-bold text-white">
                  {currency}{result.current_price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                </div>
                {upside != null && (
                  <div className={`text-sm font-semibold ${upside >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {upside >= 0 ? "+" : ""}{(upside * 100).toFixed(1)}% upside
                  </div>
                )}
              </div>
            )}
            <div className={`flex items-center gap-2 px-4 py-3 rounded-xl ${vs.bg} ${vs.text}`}>
              <VIcon className="w-5 h-5" />
              <span className="text-lg font-bold">{vs.label}</span>
            </div>
          </div>
        </div>

        {/* Overall score */}
        <div className="mt-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-500">Overall Score</span>
            <span className="text-base font-bold text-white">{result.overall_score}/100</span>
          </div>
          <div className="h-2.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                result.overall_score >= 70 ? "bg-emerald-500"
                : result.overall_score >= 50 ? "bg-yellow-500"
                : "bg-red-500"
              }`}
              style={{ width: `${result.overall_score}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-600 mt-0.5">
            <span>0</span><span>AVOID &lt; 50</span><span>HOLD 50–70</span><span>BUY ≥ 70</span><span>100</span>
          </div>
        </div>
      </div>

      {/* Category scores */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Object.entries(CAT_META).map(([key, meta]) => {
          const score = result.category_scores?.[key] ?? null;
          const colorMap = {
            blue:    "border-blue-800",
            emerald: "border-emerald-800",
            red:     "border-red-800",
            purple:  "border-purple-800",
          };
          return (
            <div key={key} className={`bg-gray-900 border ${colorMap[meta.color]} rounded-xl p-3 text-center`}>
              <div className="text-xl mb-1">{meta.icon}</div>
              <div className="text-xs text-gray-400 mb-1">{meta.label}</div>
              <div className="text-2xl font-bold text-white">{score != null ? Math.round(score) : "—"}</div>
              <div className="text-xs text-gray-600">{meta.weight} weight</div>
            </div>
          );
        })}
      </div>

      {/* Price targets */}
      {result.price_target_mid && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="text-sm font-semibold text-white mb-3">Price Targets</div>
          <div className="grid grid-cols-3 gap-3 mb-3 text-center">
            {[
              { label: "Bear", val: result.price_target_low,  color: "text-red-400"     },
              { label: "Base", val: result.price_target_mid,  color: "text-blue-400"    },
              { label: "Bull", val: result.price_target_high, color: "text-emerald-400" },
            ].map(({ label, val, color }) => (
              <div key={label}>
                <div className="text-xs text-gray-500">{label}</div>
                <div className={`text-base font-bold ${color}`}>
                  {val ? `${currency}${val.toLocaleString("en-IN", { maximumFractionDigits: 0 })}` : "—"}
                </div>
              </div>
            ))}
          </div>
          <PriceTargetBar
            current={result.current_price}
            low={result.price_target_low}
            mid={result.price_target_mid}
            high={result.price_target_high}
          />
          <div className="flex justify-between text-xs text-gray-600 mt-1">
            <span>◻ current price</span>
            <span>▏ base target</span>
          </div>
          {result.dcf?.intrinsic && (
            <div className="mt-2 text-xs text-gray-500">
              DCF intrinsic ({result.dcf.method}): {currency}{result.dcf.intrinsic.toFixed(2)}
              {result.dcf.growth_rate_used != null && ` · growth rate used: ${(result.dcf.growth_rate_used * 100).toFixed(1)}%`}
            </div>
          )}
        </div>
      )}

      {/* Detailed checks per category */}
      <div className="space-y-3">
        {Object.keys(CAT_META).map((cat) => (
          <CategorySection
            key={cat}
            catKey={cat}
            checks={result.checks?.[cat]}
            score={result.category_scores?.[cat]}
          />
        ))}
      </div>

      {/* Verify links */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="text-xs text-gray-500 mb-2">Verify on external platforms</div>
        <div className="flex flex-wrap gap-2">
          {[
            { label: "NSE India",   href: `https://www.nseindia.com/get-quotes/equity?symbol=${result.ticker.replace(".NS","").replace(".BO","")}`, icon: "🏛" },
            { label: "Screener.in", href: `https://www.screener.in/company/${result.ticker.replace(".NS","").replace(".BO","")}/`, icon: "🔍" },
            { label: "TradingView", href: `https://www.tradingview.com/chart/?symbol=NSE%3A${result.ticker.replace(".NS","").replace(".BO","")}`, icon: "📊" },
          ].map(({ label, href, icon }) => (
            <a key={label} href={href} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700
                         text-xs text-gray-400 hover:text-white transition group">
              {icon} {label}
              <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100" />
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Evaluate() {
  const location = useLocation();

  // Breakout data passed from the BreakoutTable "Evaluate" button
  const breakoutContext = location.state?.breakoutData ?? null;

  const [symbol,   setSymbol]   = useState(breakoutContext?.symbol   || "");
  const [exchange, setExchange] = useState(breakoutContext?.exchange  || "NSE");
  const [loading,  setLoading]  = useState(false);
  const [result,   setResult]   = useState(null);
  const [error,    setError]    = useState(null);
  const [elapsed,  setElapsed]  = useState(null);

  const autoTriggered = useRef(false);

  const run = useCallback(async () => {
    const sym = symbol.trim().toUpperCase();
    if (!sym) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setElapsed(null);
    const t0 = Date.now();

    try {
      const res = await axios.get(`/api/evaluate/${sym}`, {
        params: { exchange },
        timeout: 120_000,
      });
      setResult(res.data);
      setElapsed(((Date.now() - t0) / 1000).toFixed(1));
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Evaluation failed");
    } finally {
      setLoading(false);
    }
  }, [symbol, exchange]);

  // Auto-trigger when navigated from BreakoutTable
  useEffect(() => {
    if (breakoutContext && !autoTriggered.current) {
      autoTriggered.current = true;
      run();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleKey = (e) => {
    if (e.key === "Enter") run();
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          🔬 Stock Evaluation
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Fundamental analysis across Valuation · Fundamentals · Risk · Future Potential.
          Returns a BUY / HOLD / AVOID verdict with a 0–100 score.
        </p>
      </div>

      {/* Score guide */}
      <div className="grid grid-cols-4 gap-2 text-center text-xs">
        {[
          { label: "Valuation",    desc: "P/E · PEG · P/B · EV/EBITDA · FCF · DCF · Historical P/E", weight: "30%", icon: "📊" },
          { label: "Fundamentals", desc: "Revenue · EPS · Margins · ROE · ROIC · D/E · FCF trend",   weight: "35%", icon: "💪" },
          { label: "Risk",         desc: "Debt trend · Earnings stability · Regulatory · Cyclicality", weight: "20%", icon: "⚠️" },
          { label: "Future",       desc: "Analyst targets · DCF range · Technical momentum",           weight: "15%", icon: "🚀" },
        ].map(({ label, desc, weight, icon }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-3">
            <div className="text-lg mb-1">{icon}</div>
            <div className="text-white font-semibold">{label}</div>
            <div className="text-gray-500 mt-1 leading-tight hidden sm:block">{desc}</div>
            <div className="text-blue-400 font-bold mt-1">{weight}</div>
          </div>
        ))}
      </div>

      {/* Breakout Context — shown when arriving from the Dashboard table */}
      {breakoutContext && (
        <BreakoutContextPanel data={breakoutContext} />
      )}

      {/* Search bar */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[160px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={symbol}
              onChange={e => setSymbol(e.target.value.toUpperCase())}
              onKeyDown={handleKey}
              placeholder="RELIANCE, TCS, INFY…"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm
                         text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
            {EXCHANGES.map(ex => (
              <button
                key={ex}
                onClick={() => setExchange(ex)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition
                  ${exchange === ex ? "bg-blue-600 text-white" : "text-gray-400 hover:text-gray-200"}`}
              >
                {ex}
              </button>
            ))}
          </div>

          <button
            onClick={run}
            disabled={loading || !symbol.trim()}
            className="flex items-center gap-2 px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500
                       disabled:opacity-50 disabled:cursor-not-allowed text-sm text-white font-semibold transition"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {loading ? "Analysing…" : "Evaluate"}
          </button>
        </div>

        {loading && (
          <div className="mt-3 space-y-1">
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
              {breakoutContext
                ? `Fetching fundamentals for ${symbol} — comparing with breakout signals…`
                : "Fetching financials, balance sheet, cashflow & analyst data from Yahoo Finance…"}
              {" "}This can take up to 60 seconds on cloud servers.
            </div>
            <div className="text-xs text-yellow-700">
              ⚠ If it times out, click Evaluate again — the second attempt is usually faster.
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-lg px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Result */}
      {result && !result.error && (
        <div>
          {elapsed && (
            <p className="text-xs text-gray-600 mb-3 text-right">
              Analysis completed in {elapsed}s · Data: Yahoo Finance
            </p>
          )}
          <ResultCard result={result} />
        </div>
      )}

      {result?.error && (
        <div className="bg-red-900/30 border border-red-800 rounded-xl p-4 space-y-3">
          <div className="flex items-start gap-2 text-sm text-red-300">
            <span className="text-lg shrink-0">⚠️</span>
            <div>
              <div className="font-semibold mb-0.5">Could not fetch data for {result.ticker}</div>
              <div className="text-xs text-red-400/80">
                {result.error?.includes("Yahoo Finance") || result.error?.includes("fetch data")
                  ? "Yahoo Finance is blocking this cloud server's IP. This is a known limitation of free hosting."
                  : result.error}
              </div>
            </div>
          </div>

          {/* Fallback links */}
          <div className="border-t border-red-800/50 pt-3">
            <div className="text-xs text-red-400 mb-2">
              View fundamentals directly on these platforms (free, no login needed):
            </div>
            <div className="flex flex-wrap gap-2">
              {(() => {
                const sym = result.ticker.replace(".NS","").replace(".BO","");
                return [
                  { label: "Screener.in",  href: `https://www.screener.in/company/${sym}/`, icon: "🔍", desc: "P/E, EPS, ROE, Balance Sheet" },
                  { label: "NSE India",    href: `https://www.nseindia.com/get-quotes/equity?symbol=${sym}`, icon: "🏛", desc: "Price, Market Cap" },
                  { label: "TradingView", href: `https://www.tradingview.com/chart/?symbol=NSE%3A${sym}`, icon: "📊", desc: "Charts, Technicals" },
                  { label: "Moneycontrol",href: `https://www.moneycontrol.com/india/stockpricequote/${sym.toLowerCase()}`, icon: "💹", desc: "News, Fundamentals" },
                ].map(({ label, href, icon, desc }) => (
                  <a key={label} href={href} target="_blank" rel="noopener noreferrer"
                    className="flex flex-col px-3 py-2 rounded-lg bg-gray-800 border border-gray-700
                               text-xs text-gray-400 hover:text-white hover:border-gray-500 transition">
                    <span>{icon} {label} ↗</span>
                    <span className="text-gray-600 mt-0.5">{desc}</span>
                  </a>
                ));
              })()}
            </div>
          </div>

          <div className="text-xs text-gray-600">
            💡 Tip: The Evaluate feature works fully when running the app locally on your computer.
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !result && !error && (
        <div className="text-center py-16 text-gray-600">
          <div className="text-4xl mb-3">🔬</div>
          {breakoutContext
            ? <p className="text-sm text-gray-500">Loading evaluation for <span className="text-white font-semibold">{symbol}</span>…</p>
            : <>
                <p className="text-sm">Enter a stock symbol above and click Evaluate</p>
                <p className="text-xs mt-1">Works for NSE, BSE, and US stocks (NYSE / NASDAQ)</p>
              </>
          }
        </div>
      )}
    </div>
  );
}
