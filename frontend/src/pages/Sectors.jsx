import React, { useState, useEffect, useMemo } from "react";
import { Building2, Download, ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react";
import axios from "axios";
import clsx from "clsx";

// ─── Export helpers ───────────────────────────────────────────────────────────

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportCSV(stocks, sector) {
  // Tickers only — one per line, no header
  const content = stocks.map((s) => s.symbol).join("\n");
  downloadBlob(
    new Blob([content], { type: "text/plain;charset=utf-8" }),
    `${sector.replace(/\s+/g, "_")}_tickers.csv`
  );
}

function exportExcel(stocks, sector) {
  // SpreadsheetML XML — Excel opens it natively, no npm library needed
  // Single column, no header row, just ticker values
  const rows = stocks
    .map((s) => `    <Row><Cell><Data ss:Type="String">${s.symbol}</Data></Cell></Row>`)
    .join("\n");
  const xml = `<?xml version="1.0"?><?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
          xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
  <Worksheet ss:Name="Tickers">
    <Table>
${rows}
    </Table>
  </Worksheet>
</Workbook>`;
  downloadBlob(
    new Blob([xml], { type: "application/vnd.ms-excel" }),
    `${sector.replace(/\s+/g, "_")}_tickers.xls`
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StrengthBadge({ strength }) {
  if (strength === "STRONG")    return <span className="badge-strong">🟢 Strong</span>;
  if (strength === "MODERATE")  return <span className="badge-moderate">🟡 Moderate</span>;
  if (strength === "WATCHLIST") return <span className="badge-watchlist">🔵 Watch</span>;
  return <span className="text-gray-600 text-xs">—</span>;
}

const SORT_COLS = [
  { key: "symbol",       label: "Symbol",     sortable: true  },
  { key: "name",         label: "Company",    sortable: false },
  { key: "cmp",          label: "CMP (₹)",   sortable: true  },
  { key: "pct_change",   label: "% Change",   sortable: true  },
  { key: "rsi",          label: "RSI",        sortable: true  },
  { key: "volume_ratio", label: "Vol Ratio",  sortable: true  },
  { key: "strength",     label: "Strength",   sortable: false },
];

function SortIcon({ col, sort }) {
  if (!col.sortable) return null;
  if (sort.key !== col.key) return <ArrowUpDown className="w-3 h-3 opacity-30" />;
  return sort.dir === "asc"
    ? <ArrowUp className="w-3 h-3" />
    : <ArrowDown className="w-3 h-3" />;
}

// ─── Sector button ─────────────────────────────────────────────────────────────

const SECTOR_COLORS = {
  "Technology":           "border-blue-700 text-blue-300   hover:border-blue-500",
  "Financial Services":   "border-emerald-700 text-emerald-300 hover:border-emerald-500",
  "Energy":               "border-orange-700 text-orange-300 hover:border-orange-500",
  "Healthcare":           "border-rose-700 text-rose-300   hover:border-rose-500",
  "Consumer Goods":       "border-yellow-700 text-yellow-300 hover:border-yellow-500",
  "Consumer Cyclical":    "border-yellow-700 text-yellow-300 hover:border-yellow-500",
  "Industrials":          "border-purple-700 text-purple-300 hover:border-purple-500",
  "Materials":            "border-teal-700 text-teal-300   hover:border-teal-500",
  "Communication Services":"border-pink-700 text-pink-300  hover:border-pink-500",
  "Real Estate":          "border-amber-700 text-amber-300 hover:border-amber-500",
  "Utilities":            "border-cyan-700 text-cyan-300   hover:border-cyan-500",
};

function sectorColor(sector, isSelected) {
  if (isSelected) return "bg-blue-600 border-blue-500 text-white";
  const base = SECTOR_COLORS[sector] || "border-gray-700 text-gray-400 hover:border-gray-500";
  return `bg-gray-900/60 ${base}`;
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Sectors() {
  const [sectors,        setSectors]        = useState([]);
  const [selected,       setSelected]       = useState(null);
  const [stocks,         setStocks]         = useState([]);
  const [loadingSectors, setLoadingSectors] = useState(true);
  const [loadingStocks,  setLoadingStocks]  = useState(false);
  const [sort,           setSort]           = useState({ key: "strength_score", dir: "desc" });

  // Load sector list once on mount
  useEffect(() => {
    axios.get("/api/sectors/list")
      .then((r) => setSectors(r.data))
      .catch(() => setSectors([]))
      .finally(() => setLoadingSectors(false));
  }, []);

  // Load stocks whenever a sector is chosen
  useEffect(() => {
    if (!selected) return;
    setLoadingStocks(true);
    setStocks([]);
    axios
      .get("/api/sectors/stocks", { params: { sector: selected } })
      .then((r) => setStocks(r.data))
      .catch(() => setStocks([]))
      .finally(() => setLoadingStocks(false));
  }, [selected]);

  const toggleSort = (key) =>
    setSort((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key, dir: "desc" }
    );

  const sorted = useMemo(() => {
    if (!stocks.length) return [];
    return [...stocks].sort((a, b) => {
      const va = a[sort.key] ?? -Infinity;
      const vb = b[sort.key] ?? -Infinity;
      if (typeof va === "string") return sort.dir === "asc" ? va.localeCompare(vb) : vb.localeCompare(va);
      return sort.dir === "asc" ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
    });
  }, [stocks, sort.key, sort.dir]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Building2 className="w-6 h-6 text-blue-400" />
          Sector Explorer
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Browse today's pre-breakout stocks grouped by sector.
          Select any sector to view all matching stocks and export their tickers.
        </p>
      </div>

      {/* ── Sector grid ────────────────────────────────────────────────────── */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Choose a Sector
          {!loadingSectors && sectors.length > 0 && (
            <span className="ml-2 normal-case font-normal text-gray-600">
              · {sectors.length} sectors · {sectors.reduce((s, x) => s + x.count, 0)} stocks total
            </span>
          )}
        </div>

        {loadingSectors ? (
          <div className="flex flex-wrap gap-2">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-9 w-28 bg-gray-800 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : sectors.length === 0 ? (
          <p className="text-sm text-gray-500">
            No scan data yet. Click <strong className="text-white">Run Scan Now</strong> on the Dashboard.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {sectors.map(({ sector, count }) => {
              const isSelected = selected === sector;
              return (
                <button
                  key={sector}
                  onClick={() => setSelected(sector)}
                  className={clsx(
                    "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border transition",
                    sectorColor(sector, isSelected)
                  )}
                >
                  <span>{sector}</span>
                  <span className={clsx(
                    "text-xs rounded-full px-1.5 py-0.5 font-bold",
                    isSelected ? "bg-white/20 text-white" : "bg-gray-800 text-gray-500"
                  )}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Stocks table ────────────────────────────────────────────────────── */}
      {selected && (
        <div className="space-y-3">

          {/* Sub-header row with export buttons */}
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <h2 className="text-base font-semibold text-white">{selected}</h2>
              <span className="text-sm text-gray-400">
                {loadingStocks ? "Loading…" : (() => {
                  const bo = sorted.filter(s => s.is_breakout).length;
                  return `${sorted.length} stock${sorted.length !== 1 ? "s" : ""}${bo > 0 ? ` · ${bo} breakout${bo !== 1 ? "s" : ""}` : ""}`;
                })()}
              </span>
            </div>

            {!loadingStocks && sorted.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-600">Export tickers:</span>
                <button
                  onClick={() => exportCSV(sorted, selected)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800
                             border border-gray-700 text-xs font-semibold text-gray-300
                             hover:text-white hover:border-gray-500 transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  CSV
                </button>
                <button
                  onClick={() => exportExcel(sorted, selected)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                             bg-emerald-900/30 border border-emerald-800
                             text-xs font-semibold text-emerald-400
                             hover:text-emerald-300 hover:border-emerald-600 transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  Excel
                </button>
              </div>
            )}
          </div>

          {/* Loading skeleton */}
          {loadingStocks && (
            <div className="space-y-2">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-12 bg-gray-800 rounded-lg animate-pulse" />
              ))}
            </div>
          )}

          {/* Table */}
          {!loadingStocks && sorted.length > 0 && (
            <div className="overflow-x-auto rounded-xl border border-gray-800">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 bg-gray-900/80">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 w-10">#</th>
                    {SORT_COLS.map((col) => (
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
                          <SortIcon col={col} sort={sort} />
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {sorted.map((row, idx) => (
                    <tr
                      key={row.id || row.symbol}
                      className="hover:bg-gray-800/40 transition-colors"
                    >
                      {/* Row number */}
                      <td className="px-4 py-3 text-xs text-gray-600 tabular-nums">{idx + 1}</td>

                      {/* Symbol */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="font-semibold text-white">{row.symbol}</span>
                          {row.is_breakout && (
                            <span className="text-[10px] bg-blue-900/50 text-blue-300 border border-blue-800/60 rounded px-1.5 py-0.5 font-semibold leading-none">
                              Breakout
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Company name */}
                      <td className="px-4 py-3">
                        <span className="text-xs text-gray-400 truncate block max-w-[200px]">
                          {row.name || "—"}
                        </span>
                      </td>

                      {/* CMP */}
                      <td className="px-4 py-3 tabular-nums font-medium text-white">
                        ₹{row.cmp?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </td>

                      {/* % Change */}
                      <td className={clsx(
                        "px-4 py-3 tabular-nums font-semibold",
                        row.pct_change >= 0 ? "text-emerald-400" : "text-red-400"
                      )}>
                        {row.pct_change >= 0 ? "+" : ""}{row.pct_change?.toFixed(2)}%
                      </td>

                      {/* RSI */}
                      <td className="px-4 py-3">
                        <span className={clsx(
                          "tabular-nums font-semibold",
                          row.rsi > 70 ? "text-red-400"
                            : row.rsi > 55 ? "text-emerald-400"
                            : "text-gray-400"
                        )}>
                          {row.rsi?.toFixed(1)}
                        </span>
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

                      {/* Strength */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <StrengthBadge strength={row.strength} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Empty state */}
          {!loadingStocks && sorted.length === 0 && (
            <div className="text-center py-14 text-gray-500">
              <p className="text-3xl mb-2">📭</p>
              <p className="text-sm">No pre-breakout stocks found in <strong className="text-gray-400">{selected}</strong></p>
              <p className="text-xs mt-1 text-gray-600">
                Try another sector, or run a fresh scan on the Dashboard
              </p>
            </div>
          )}
        </div>
      )}

      {/* Placeholder when nothing is selected yet */}
      {!selected && !loadingSectors && sectors.length > 0 && (
        <div className="text-center py-16 text-gray-600">
          <div className="text-5xl mb-3">🏢</div>
          <p className="text-sm">Select a sector above to view its stocks</p>
          <p className="text-xs mt-1">You can then export all tickers as CSV or Excel</p>
        </div>
      )}

    </div>
  );
}
