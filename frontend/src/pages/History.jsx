import React, { useEffect, useState } from "react";
import { Calendar, TrendingUp, BarChart2 } from "lucide-react";
import { fetchScanHistory } from "../utils/api";

const MOCK_HISTORY = [
  { scan_date: "2026-05-28", total_scanned: 192, total_breakouts: 24, nifty_trend: true, completed_at: "2026-05-28 08:49:12" },
  { scan_date: "2026-05-27", total_scanned: 192, total_breakouts: 18, nifty_trend: true, completed_at: "2026-05-27 08:48:55" },
  { scan_date: "2026-05-26", total_scanned: 192, total_breakouts: 31, nifty_trend: true, completed_at: "2026-05-26 08:49:44" },
  { scan_date: "2026-05-23", total_scanned: 192, total_breakouts: 12, nifty_trend: false, completed_at: "2026-05-23 08:50:01" },
  { scan_date: "2026-05-22", total_scanned: 192, total_breakouts: 9, nifty_trend: false, completed_at: "2026-05-22 08:48:30" },
  { scan_date: "2026-05-21", total_scanned: 192, total_breakouts: 27, nifty_trend: true, completed_at: "2026-05-21 08:49:00" },
  { scan_date: "2026-05-20", total_scanned: 192, total_breakouts: 33, nifty_trend: true, completed_at: "2026-05-20 08:49:11" },
];

export default function History() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchScanHistory()
      .then(setHistory)
      .catch(() => setHistory(MOCK_HISTORY))
      .finally(() => setLoading(false));
  }, []);

  const avgBreakouts = history.length
    ? (history.reduce((s, h) => s + h.total_breakouts, 0) / history.length).toFixed(1)
    : "—";

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Scan History</h1>
        <p className="text-gray-400 text-sm mt-0.5">Daily breakout scan results archive</p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="stat-card">
          <span className="text-xs text-gray-400 uppercase tracking-wider">Total Scans</span>
          <span className="text-3xl font-bold text-white mt-1">{history.length}</span>
        </div>
        <div className="stat-card">
          <span className="text-xs text-gray-400 uppercase tracking-wider">Avg Breakouts/Day</span>
          <span className="text-3xl font-bold text-blue-400 mt-1">{avgBreakouts}</span>
        </div>
        <div className="stat-card">
          <span className="text-xs text-gray-400 uppercase tracking-wider">Uptrend Days</span>
          <span className="text-3xl font-bold text-emerald-400 mt-1">
            {history.filter((h) => h.nifty_trend).length}
          </span>
        </div>
      </div>

      {/* Bar chart (simple CSS) */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-blue-400" /> Breakouts Per Day
        </h3>
        <div className="flex items-end gap-2 h-28">
          {history.slice().reverse().map((h) => {
            const max = Math.max(...history.map((x) => x.total_breakouts));
            const pct = max > 0 ? (h.total_breakouts / max) * 100 : 0;
            return (
              <div key={h.scan_date} className="flex-1 flex flex-col items-center gap-1 group">
                <span className="text-[9px] text-gray-500 opacity-0 group-hover:opacity-100 transition">
                  {h.total_breakouts}
                </span>
                <div
                  className={`w-full rounded-t transition-all ${h.nifty_trend ? "bg-blue-600" : "bg-gray-600"}`}
                  style={{ height: `${pct}%`, minHeight: 4 }}
                  title={`${h.scan_date}: ${h.total_breakouts} breakouts`}
                />
                <span className="text-[9px] text-gray-500 rotate-45 origin-left whitespace-nowrap">
                  {h.scan_date.slice(5)}
                </span>
              </div>
            );
          })}
        </div>
        <div className="flex gap-4 mt-5 text-xs text-gray-400">
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-blue-600 rounded" /> Nifty Uptrend</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-gray-600 rounded" /> Nifty Downtrend</span>
        </div>
      </div>

      {/* History table */}
      {loading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-900 border-b border-gray-800 text-xs text-gray-400">
                <th className="px-4 py-3 text-left">Date</th>
                <th className="px-4 py-3 text-left">Scanned</th>
                <th className="px-4 py-3 text-left">Breakouts</th>
                <th className="px-4 py-3 text-left">Nifty Trend</th>
                <th className="px-4 py-3 text-left">Completed At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {history.map((h) => (
                <tr key={h.scan_date} className="hover:bg-gray-800/40 transition">
                  <td className="px-4 py-3 flex items-center gap-2 text-white font-medium">
                    <Calendar className="w-3.5 h-3.5 text-gray-500" />
                    {h.scan_date}
                  </td>
                  <td className="px-4 py-3 text-gray-300 tabular-nums">{h.total_scanned}</td>
                  <td className="px-4 py-3">
                    <span className={`font-bold tabular-nums ${
                      h.total_breakouts >= 20 ? "text-emerald-400"
                      : h.total_breakouts >= 10 ? "text-yellow-400"
                      : "text-gray-300"
                    }`}>
                      {h.total_breakouts}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {h.nifty_trend ? (
                      <span className="flex items-center gap-1 text-emerald-400 text-xs font-medium">
                        <TrendingUp className="w-3.5 h-3.5" /> Uptrend
                      </span>
                    ) : (
                      <span className="text-red-400 text-xs font-medium">Downtrend</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs tabular-nums">{h.completed_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
