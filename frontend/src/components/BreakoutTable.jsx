import React, { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpDown, ArrowUp, ArrowDown, BookmarkPlus, ExternalLink, FlaskConical } from "lucide-react";
import clsx from "clsx";

const COLUMNS = [
  { key: "name", label: "Stock", sortable: false },
  { key: "cmp", label: "CMP (₹)", sortable: true },
  { key: "pct_change", label: "% Change", sortable: true },
  { key: "volume_ratio", label: "Vol Ratio", sortable: true },
  { key: "rsi", label: "RSI", sortable: true },
  { key: "high_52w", label: "52W High", sortable: true },
  { key: "breakout_type", label: "Type", sortable: false },
  { key: "strength_score", label: "Score", sortable: true },
  { key: "strength", label: "Strength", sortable: false },
  { key: "actions", label: "", sortable: false },
];

function StrengthBadge({ strength }) {
  if (strength === "STRONG")
    return <span className="badge-strong">🟢 Strong</span>;
  if (strength === "MODERATE")
    return <span className="badge-moderate">🟡 Moderate</span>;
  return <span className="badge-watchlist">🔵 Watch</span>;
}

function CriteriaIndicators({ row }) {
  const dots = [
    { key: "price_breakout", label: "P" },
    { key: "volume_confirmed", label: "V" },
    { key: "momentum_ok", label: "M" },
    { key: "trend_ok", label: "T" },
    { key: "breakout_100d", label: "E" },
  ];
  return (
    <div className="flex gap-0.5 mt-0.5">
      {dots.map(({ key, label }) => (
        <span
          key={key}
          title={key.replace("_", " ")}
          className={clsx(
            "w-4 h-4 rounded-sm text-[9px] font-bold flex items-center justify-center",
            row[key] ? "bg-emerald-700 text-emerald-200" : "bg-gray-700 text-gray-500"
          )}
        >
          {label}
        </span>
      ))}
    </div>
  );
}

function ScoreBar({ score }) {
  const color = score >= 85 ? "bg-emerald-500" : score >= 60 ? "bg-yellow-500" : "bg-blue-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs text-gray-300 tabular-nums">{score?.toFixed(1)}</span>
    </div>
  );
}

export default function BreakoutTable({ data, loading, onWatchlist }) {
  const navigate = useNavigate();
  const [sort, setSort] = useState({ key: "strength_score", dir: "desc" });

  const toggleSort = (key) => {
    setSort((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key, dir: "desc" }
    );
  };

  const sorted = useMemo(() => {
    if (!data) return [];
    return [...data].sort((a, b) => {
      const va = a[sort.key] ?? -Infinity;
      const vb = b[sort.key] ?? -Infinity;
      return sort.dir === "asc" ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
    });
  }, [data, sort.key, sort.dir]);

  if (loading) {
    return (
      <div className="flex flex-col gap-2">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-12 bg-gray-800 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (!sorted.length) {
    return (
      <div className="text-center py-16 text-gray-500">
        <p className="text-2xl mb-2">📭</p>
        <p>No breakouts found matching current filters.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 bg-gray-900/80">
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                className={clsx(
                  "px-4 py-3 text-left text-xs font-semibold text-gray-400 whitespace-nowrap select-none",
                  col.sortable && "cursor-pointer hover:text-gray-200 transition"
                )}
                onClick={() => col.sortable && toggleSort(col.key)}
              >
                <span className="inline-flex items-center gap-1">
                  {col.label}
                  {col.sortable && (
                    sort.key === col.key ? (
                      sort.dir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowUpDown className="w-3 h-3 opacity-30" />
                    )
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800/60">
          {sorted.map((row) => (
            <tr
              key={row.id}
              className="table-row-hover"
              onClick={() => navigate(`/stock/${row.symbol}`)}
            >
              {/* Stock name + symbol */}
              <td className="px-4 py-3">
                <div className="font-semibold text-white">{row.symbol}</div>
                <div className="text-xs text-gray-400 truncate max-w-[160px]">{row.name}</div>
                <CriteriaIndicators row={row} />
              </td>

              {/* CMP */}
              <td className="px-4 py-3 tabular-nums font-medium text-white">
                ₹{row.cmp?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </td>

              {/* % Change */}
              <td className={clsx("px-4 py-3 tabular-nums font-semibold",
                row.pct_change >= 0 ? "text-emerald-400" : "text-red-400"
              )}>
                {row.pct_change >= 0 ? "+" : ""}{row.pct_change?.toFixed(2)}%
              </td>

              {/* Volume Ratio */}
              <td className="px-4 py-3">
                <span className={clsx(
                  "font-semibold tabular-nums",
                  row.volume_ratio >= 2 ? "text-emerald-400" : "text-gray-300"
                )}>
                  {row.volume_ratio?.toFixed(2)}x
                </span>
              </td>

              {/* RSI */}
              <td className="px-4 py-3">
                <span className={clsx(
                  "tabular-nums font-semibold",
                  row.rsi > 70 ? "text-red-400" : row.rsi > 55 ? "text-emerald-400" : "text-gray-400"
                )}>
                  {row.rsi?.toFixed(1)}
                </span>
              </td>

              {/* 52W High */}
              <td className="px-4 py-3 tabular-nums text-gray-300 text-xs">
                ₹{row.high_52w?.toLocaleString("en-IN")}
              </td>

              {/* Breakout type */}
              <td className="px-4 py-3">
                <span className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-0.5 text-gray-300">
                  {row.breakout_type || "—"}
                </span>
              </td>

              {/* Score */}
              <td className="px-4 py-3">
                <ScoreBar score={row.strength_score} />
              </td>

              {/* Strength badge */}
              <td className="px-4 py-3 whitespace-nowrap">
                <StrengthBadge strength={row.strength} />
              </td>

              {/* Actions */}
              <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                <div className="flex gap-2">
                  <button
                    title="Add to watchlist"
                    onClick={() => onWatchlist && onWatchlist(row)}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-yellow-400 hover:bg-yellow-900/20 transition"
                  >
                    <BookmarkPlus className="w-4 h-4" />
                  </button>
                  <button
                    title="Evaluate fundamentals"
                    onClick={() => navigate("/evaluate", { state: { breakoutData: row } })}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-purple-400 hover:bg-purple-900/20 transition"
                  >
                    <FlaskConical className="w-4 h-4" />
                  </button>
                  <button
                    title="View details"
                    onClick={() => navigate(`/stock/${row.symbol}`)}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-blue-400 hover:bg-blue-900/20 transition"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
