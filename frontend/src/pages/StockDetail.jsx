import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, BookmarkPlus, TrendingUp, Target, ShieldAlert } from "lucide-react";
import toast from "react-hot-toast";

import StockChart from "../components/StockChart";
import { fetchSymbolHistory, addToWatchlist } from "../utils/api";
import { MOCK_BREAKOUTS } from "../utils/mock";

function InfoRow({ label, value, color }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-800 last:border-0">
      <span className="text-gray-400 text-sm">{label}</span>
      <span className={`text-sm font-semibold ${color || "text-white"}`}>{value ?? "—"}</span>
    </div>
  );
}

function CriteriaPill({ label, met }) {
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
      ${met ? "bg-emerald-900/40 border border-emerald-700 text-emerald-300"
             : "bg-gray-800 border border-gray-700 text-gray-400"}`}>
      <span>{met ? "✓" : "✗"}</span>
      {label}
    </div>
  );
}

export default function StockDetail() {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [stock, setStock] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    // Try API, fall back to mock
    fetchSymbolHistory(symbol)
      .then((rows) => {
        if (rows.length) {
          setHistory(rows);
          setStock(rows[0]);
        } else {
          const mock = MOCK_BREAKOUTS.find((b) => b.symbol === symbol) || MOCK_BREAKOUTS[0];
          setStock({ ...mock, symbol });
          setHistory([{ ...mock, symbol }]);
        }
      })
      .catch(() => {
        const mock = MOCK_BREAKOUTS.find((b) => b.symbol === symbol) || MOCK_BREAKOUTS[0];
        setStock({ ...mock, symbol });
        setHistory([{ ...mock, symbol }]);
      })
      .finally(() => setLoading(false));
  }, [symbol]);

  const handleWatchlist = async () => {
    try {
      await addToWatchlist(symbol, stock?.exchange || "NSE", stock?.name);
      toast.success(`${symbol} added to watchlist`);
    } catch (e) {
      if (e.response?.status === 409) toast.error("Already in watchlist");
      else toast.error("Could not add (backend offline?)");
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-10">
        <div className="h-8 w-48 bg-gray-800 rounded animate-pulse mb-6" />
        <div className="h-80 bg-gray-800 rounded-xl animate-pulse" />
      </div>
    );
  }

  const s = stock;
  const riskReward = s ? ((s.target_price - s.entry_price) / (s.entry_price - s.stop_loss)).toFixed(1) : null;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Back + header */}
      <div className="flex items-center gap-4 flex-wrap">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-gray-400 hover:text-white transition text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="flex-1 flex items-center gap-3 flex-wrap">
          <h1 className="text-2xl font-bold text-white">{symbol}</h1>
          <span className="text-gray-400 text-sm">{s?.name}</span>
          <span className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-400">
            {s?.exchange}
          </span>
          {s?.strength === "STRONG" && <span className="badge-strong">🟢 Strong Breakout</span>}
          {s?.strength === "MODERATE" && <span className="badge-moderate">🟡 Moderate Breakout</span>}
          {s?.strength === "WATCHLIST" && <span className="badge-watchlist">🔵 Watch List</span>}
        </div>
        <button
          onClick={handleWatchlist}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 border border-gray-700
                     text-sm text-gray-300 hover:text-yellow-400 transition"
        >
          <BookmarkPlus className="w-4 h-4" /> Add to Watchlist
        </button>
      </div>

      {/* Price header */}
      <div className="flex items-baseline gap-3 flex-wrap">
        <span className="text-4xl font-bold text-white tabular-nums">
          ₹{s?.cmp?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
        </span>
        <span className={`text-xl font-semibold tabular-nums ${s?.pct_change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
          {s?.pct_change >= 0 ? "+" : ""}{s?.pct_change?.toFixed(2)}%
        </span>
        <span className="text-sm text-gray-400">as of {s?.scan_date}</span>
      </div>

      {/* Chart */}
      <StockChart symbol={symbol} exchange={s?.exchange} />

      {/* Main grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Trade levels */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-1">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Suggested Levels
          </h3>
          <div className="flex items-center gap-2 py-2 border-b border-gray-800">
            <TrendingUp className="w-4 h-4 text-blue-400" />
            <span className="text-gray-400 text-sm flex-1">Entry</span>
            <span className="text-white font-semibold">₹{s?.entry_price?.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-2 py-2 border-b border-gray-800">
            <ShieldAlert className="w-4 h-4 text-red-400" />
            <span className="text-gray-400 text-sm flex-1">Stop Loss</span>
            <span className="text-red-400 font-semibold">₹{s?.stop_loss?.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-2 py-2 border-b border-gray-800">
            <Target className="w-4 h-4 text-emerald-400" />
            <span className="text-gray-400 text-sm flex-1">Target</span>
            <span className="text-emerald-400 font-semibold">₹{s?.target_price?.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-2 py-2">
            <span className="text-gray-400 text-sm flex-1">Risk:Reward</span>
            <span className="text-yellow-400 font-bold">1 : {riskReward}</span>
          </div>
        </div>

        {/* Technical indicators */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Technical Indicators
          </h3>
          <InfoRow label="RSI (14)" value={s?.rsi?.toFixed(1)}
            color={s?.rsi > 70 ? "text-red-400" : s?.rsi > 55 ? "text-emerald-400" : "text-gray-300"} />
          <InfoRow label="MACD" value={s?.macd?.toFixed(3)} color={s?.macd > 0 ? "text-emerald-400" : "text-red-400"} />
          <InfoRow label="MACD Signal" value={s?.macd_signal?.toFixed(3)} />
          <InfoRow label="SMA 50" value={`₹${s?.sma50?.toFixed(2)}`}
            color={s?.cmp > s?.sma50 ? "text-emerald-400" : "text-red-400"} />
          <InfoRow label="SMA 200" value={`₹${s?.sma200?.toFixed(2)}`}
            color={s?.cmp > s?.sma200 ? "text-emerald-400" : "text-red-400"} />
          <InfoRow label="Volume" value={`${(s?.volume / 1e6)?.toFixed(2)}M`} />
          <InfoRow label="Avg Volume (20d)" value={`${(s?.avg_volume_20d / 1e6)?.toFixed(2)}M`} />
          <InfoRow label="Volume Ratio" value={`${s?.volume_ratio?.toFixed(2)}x`}
            color={s?.volume_ratio >= 2 ? "text-emerald-400" : "text-gray-300"} />
        </div>

        {/* Price stats */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Price Statistics
          </h3>
          <InfoRow label="52W High" value={`₹${s?.high_52w?.toLocaleString("en-IN")}`} color="text-emerald-400" />
          <InfoRow label="52W Low" value={`₹${s?.low_52w?.toLocaleString("en-IN")}`} color="text-red-400" />
          <InfoRow label="Prev Close" value={`₹${s?.prev_close?.toLocaleString("en-IN")}`} />
          <InfoRow label="Breakout Type" value={s?.breakout_type || "—"} />
          <InfoRow label="Strength Score" value={`${s?.strength_score?.toFixed(1)} / 100`}
            color="text-yellow-400" />
          <InfoRow label="Criteria Met" value={`${s?.criteria_met} / 4`} />
          <InfoRow label="Sector" value={s?.sector} />
          <InfoRow label="Market Cap"
            value={s?.market_cap ? `₹${(s.market_cap / 100).toFixed(0)}Cr` : "—"} />
        </div>
      </div>

      {/* Breakout criteria checklist */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-white mb-3">Breakout Criteria Checklist</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <CriteriaPill label="Price Breakout" met={s?.price_breakout} />
          <CriteriaPill label="Volume ≥ 2x Avg" met={s?.volume_confirmed} />
          <CriteriaPill label="RSI 55–75 + MACD" met={s?.momentum_ok} />
          <CriteriaPill label="Trend Filter (Nifty)" met={s?.trend_ok} />
        </div>
      </div>

      {/* Historical appearances */}
      {history.length > 1 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-white mb-3">
            Historical Breakout Appearances ({history.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 text-xs border-b border-gray-800">
                  <th className="py-2 pr-4 text-left">Date</th>
                  <th className="py-2 pr-4 text-left">CMP</th>
                  <th className="py-2 pr-4 text-left">Strength</th>
                  <th className="py-2 pr-4 text-left">Score</th>
                  <th className="py-2 pr-4 text-left">+1D</th>
                  <th className="py-2 pr-4 text-left">+5D</th>
                  <th className="py-2 text-left">+20D</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {history.map((h) => (
                  <tr key={h.id}>
                    <td className="py-2 pr-4 text-gray-300">{h.scan_date}</td>
                    <td className="py-2 pr-4 text-white tabular-nums">₹{h.cmp?.toFixed(2)}</td>
                    <td className="py-2 pr-4">
                      {h.strength === "STRONG" && <span className="badge-strong">🟢</span>}
                      {h.strength === "MODERATE" && <span className="badge-moderate">🟡</span>}
                      {h.strength === "WATCHLIST" && <span className="badge-watchlist">🔵</span>}
                    </td>
                    <td className="py-2 pr-4 text-yellow-400">{h.strength_score?.toFixed(1)}</td>
                    <td className={`py-2 pr-4 tabular-nums ${h.pct_gain_1d > 0 ? "text-emerald-400" : h.pct_gain_1d < 0 ? "text-red-400" : "text-gray-500"}`}>
                      {h.pct_gain_1d != null ? `${h.pct_gain_1d > 0 ? "+" : ""}${h.pct_gain_1d?.toFixed(2)}%` : "—"}
                    </td>
                    <td className={`py-2 pr-4 tabular-nums ${h.pct_gain_5d > 0 ? "text-emerald-400" : h.pct_gain_5d < 0 ? "text-red-400" : "text-gray-500"}`}>
                      {h.pct_gain_5d != null ? `${h.pct_gain_5d > 0 ? "+" : ""}${h.pct_gain_5d?.toFixed(2)}%` : "—"}
                    </td>
                    <td className={`py-2 tabular-nums ${h.pct_gain_20d > 0 ? "text-emerald-400" : h.pct_gain_20d < 0 ? "text-red-400" : "text-gray-500"}`}>
                      {h.pct_gain_20d != null ? `${h.pct_gain_20d > 0 ? "+" : ""}${h.pct_gain_20d?.toFixed(2)}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
