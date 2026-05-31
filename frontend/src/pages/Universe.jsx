import React, { useState, useEffect, useMemo, useCallback } from "react";
import { Globe, Download, Search, RefreshCw, ArrowUp, ArrowDown, ArrowUpDown, Copy, CheckCheck } from "lucide-react";
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

/** Tickers only — one per line, no header */
function exportTickersCSV(stocks, label) {
  const content = stocks.map((s) => s.symbol).join("\n");
  downloadBlob(
    new Blob([content], { type: "text/plain;charset=utf-8" }),
    `${label.replace(/\s+/g, "_")}_tickers.csv`
  );
}

/** Tickers + Name + Sector + ISIN — with header */
function exportFullCSV(stocks, label) {
  const header  = "Symbol,Company Name,Sector,ISIN";
  const rows    = stocks.map((s) =>
    `${s.symbol},"${(s.name || "").replace(/"/g, '""')}",${s.sector || "Unknown"},${s.isin || ""}`
  );
  downloadBlob(
    new Blob([[header, ...rows].join("\n")], { type: "text/csv;charset=utf-8" }),
    `${label.replace(/\s+/g, "_")}_stocks.csv`
  );
}

/** Tickers only — Excel (SpreadsheetML, no header) */
function exportTickersExcel(stocks, label) {
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
    `${label.replace(/\s+/g, "_")}_tickers.xls`
  );
}

// ─── Sector colour pills ──────────────────────────────────────────────────────

const SECTOR_COLORS = {
  "Financial Services":    "border-emerald-700 text-emerald-300 hover:border-emerald-500",
  "Information Technology":"border-blue-700 text-blue-300 hover:border-blue-500",
  "Pharmaceuticals":       "border-pink-700 text-pink-300 hover:border-pink-500",
  "Healthcare":            "border-rose-700 text-rose-300 hover:border-rose-500",
  "Automobile":            "border-yellow-700 text-yellow-300 hover:border-yellow-500",
  "FMCG":                  "border-lime-700 text-lime-300 hover:border-lime-500",
  "Metals & Mining":       "border-stone-600 text-stone-300 hover:border-stone-400",
  "Energy":                "border-orange-700 text-orange-300 hover:border-orange-500",
  "Power":                 "border-amber-700 text-amber-300 hover:border-amber-500",
  "Capital Goods":         "border-purple-700 text-purple-300 hover:border-purple-500",
  "Cement & Construction": "border-teal-700 text-teal-300 hover:border-teal-500",
  "Chemicals":             "border-cyan-700 text-cyan-300 hover:border-cyan-500",
  "Real Estate":           "border-amber-700 text-amber-300 hover:border-amber-500",
  "Telecommunication":     "border-indigo-700 text-indigo-300 hover:border-indigo-500",
  "Textiles":              "border-fuchsia-700 text-fuchsia-300 hover:border-fuchsia-500",
  "Retail":                "border-violet-700 text-violet-300 hover:border-violet-500",
  "Media & Entertainment": "border-red-700 text-red-300 hover:border-red-500",
  "Consumer Electronics":  "border-sky-700 text-sky-300 hover:border-sky-500",
  "Consumer Discretionary":"border-orange-700 text-orange-300 hover:border-orange-500",
  "Defence & Aerospace":   "border-green-700 text-green-300 hover:border-green-500",
  "Logistics":             "border-slate-600 text-slate-300 hover:border-slate-400",
  "Diversified":           "border-gray-600 text-gray-400 hover:border-gray-400",
  "Services":              "border-blue-600 text-blue-300 hover:border-blue-400",
};

function sectorColor(sector, isSelected) {
  if (isSelected) return "bg-blue-600 border-blue-500 text-white";
  const base = SECTOR_COLORS[sector] || "border-gray-700 text-gray-400 hover:border-gray-500";
  return `bg-gray-900/60 ${base}`;
}

// ─── Sort icon ────────────────────────────────────────────────────────────────

const COLS = [
  { key: "symbol", label: "Symbol",       sortable: true  },
  { key: "name",   label: "Company Name", sortable: false },
  { key: "sector", label: "Sector",       sortable: true  },
  { key: "isin",   label: "ISIN",         sortable: false },
];

function SortIcon({ col, sort }) {
  if (!col.sortable) return null;
  if (sort.key !== col.key) return <ArrowUpDown className="w-3 h-3 opacity-30" />;
  return sort.dir === "asc"
    ? <ArrowUp className="w-3 h-3" />
    : <ArrowDown className="w-3 h-3" />;
}

// ─── Copy-to-clipboard button ─────────────────────────────────────────────────

function CopyButton({ stocks }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    const text = stocks.map((s) => s.symbol).join(",");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <button
      onClick={copy}
      title="Copy comma-separated tickers to clipboard"
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800
                 border border-gray-700 text-xs font-semibold text-gray-300
                 hover:text-white hover:border-gray-500 transition"
    >
      {copied ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? "Copied!" : "Copy Tickers"}
    </button>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Universe() {
  const [sectors,        setSectors]        = useState([]);
  const [totalStocks,    setTotalStocks]    = useState(0);
  const [classifiedStocks, setClassified]  = useState(0);
  const [selected,       setSelected]       = useState(null);
  const [stocks,         setStocks]         = useState([]);
  const [search,         setSearch]         = useState("");
  const [loadingSectors, setLoadingSectors] = useState(true);
  const [loadingStocks,  setLoadingStocks]  = useState(false);
  const [sort,           setSort]           = useState({ key: "symbol", dir: "asc" });
  const [refreshing,     setRefreshing]     = useState(false);

  // ── Load sector list ───────────────────────────────────────────────────────
  const loadSectors = useCallback(() => {
    setLoadingSectors(true);
    axios.get("/api/universe/sectors")
      .then((r) => {
        setSectors(r.data.sectors || []);
        setTotalStocks(r.data.total_stocks || 0);
        setClassified(r.data.classified_stocks || 0);
      })
      .catch(() => setSectors([]))
      .finally(() => setLoadingSectors(false));
  }, []);

  useEffect(() => { loadSectors(); }, [loadSectors]);

  // ── Load stocks when sector changes ───────────────────────────────────────
  useEffect(() => {
    if (!selected) { setStocks([]); return; }
    setLoadingStocks(true);
    setStocks([]);
    axios.get("/api/universe/stocks", { params: { sector: selected } })
      .then((r) => setStocks(r.data))
      .catch(() => setStocks([]))
      .finally(() => setLoadingStocks(false));
  }, [selected]);

  // ── Sort + search ──────────────────────────────────────────────────────────
  const displayed = useMemo(() => {
    let list = stocks;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(
        (s) => s.symbol.toLowerCase().includes(q) || s.name?.toLowerCase().includes(q)
      );
    }
    return [...list].sort((a, b) => {
      const va = (a[sort.key] ?? "").toString().toLowerCase();
      const vb = (b[sort.key] ?? "").toString().toLowerCase();
      return sort.dir === "asc" ? va.localeCompare(vb) : vb.localeCompare(va);
    });
  }, [stocks, search, sort.key, sort.dir]);

  const toggleSort = (key) =>
    setSort((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key, dir: "asc" }
    );

  const handleRefresh = () => {
    setRefreshing(true);
    axios.post("/api/universe/refresh")
      .then(() => setTimeout(() => { loadSectors(); setRefreshing(false); }, 3000))
      .catch(() => setRefreshing(false));
  };

  const exportLabel = selected || "NSE_All";

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Globe className="w-6 h-6 text-blue-400" />
            NSE Stock Universe
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            All NSE-listed equity stocks, grouped by sector.
            Select a sector and export tickers to seed your evaluation app.
          </p>
          {totalStocks > 0 && (
            <p className="text-xs text-gray-500 mt-1">
              <span className="text-white font-semibold">{totalStocks.toLocaleString()}</span> total stocks
              {" · "}
              <span className="text-blue-300 font-semibold">{classifiedStocks.toLocaleString()}</span> with known sector
              {" · "}
              <span className="text-gray-500">{(totalStocks - classifiedStocks).toLocaleString()} unclassified</span>
            </p>
          )}
        </div>

        {/* Top-level export + refresh */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800
                       border border-gray-700 text-xs font-semibold text-gray-400
                       hover:text-white hover:border-gray-500 disabled:opacity-50 transition"
          >
            <RefreshCw className={clsx("w-3.5 h-3.5", refreshing && "animate-spin")} />
            {refreshing ? "Refreshing…" : "Refresh Data"}
          </button>
        </div>
      </div>

      {/* Sector grid */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Choose a Sector
          {!loadingSectors && sectors.length > 0 && (
            <span className="ml-2 normal-case font-normal text-gray-600">
              · {sectors.length} sectors
            </span>
          )}
        </div>

        {loadingSectors ? (
          <div className="flex flex-wrap gap-2">
            {[...Array(12)].map((_, i) => (
              <div key={i} className="h-9 w-32 bg-gray-800 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : sectors.length === 0 ? (
          <div className="text-sm text-gray-500 space-y-1">
            <p>No sector data yet. This loads automatically on first visit (~10 s).</p>
            <p>If it keeps showing empty, click <strong className="text-white">Refresh Data</strong> above.</p>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {sectors.map(({ sector, count }) => {
              const isSelected = selected === sector;
              return (
                <button
                  key={sector}
                  onClick={() => { setSelected(sector); setSearch(""); }}
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

      {/* Stock table */}
      {selected && (
        <div className="space-y-3">

          {/* Sub-header */}
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <h2 className="text-base font-semibold text-white">{selected}</h2>
              <span className="text-sm text-gray-400">
                {loadingStocks
                  ? "Loading…"
                  : `${displayed.length} stock${displayed.length !== 1 ? "s" : ""}${
                      search && displayed.length !== stocks.length
                        ? ` (filtered from ${stocks.length})`
                        : ""
                    }`
                }
              </span>
            </div>

            {!loadingStocks && displayed.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-gray-600">Export tickers:</span>

                <CopyButton stocks={displayed} />

                <button
                  onClick={() => exportTickersCSV(displayed, exportLabel)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800
                             border border-gray-700 text-xs font-semibold text-gray-300
                             hover:text-white hover:border-gray-500 transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  CSV
                </button>

                <button
                  onClick={() => exportTickersExcel(displayed, exportLabel)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                             bg-emerald-900/30 border border-emerald-800
                             text-xs font-semibold text-emerald-400
                             hover:text-emerald-300 hover:border-emerald-600 transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  Excel
                </button>

                <button
                  onClick={() => exportFullCSV(displayed, exportLabel)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                             bg-blue-900/30 border border-blue-800
                             text-xs font-semibold text-blue-400
                             hover:text-blue-300 hover:border-blue-600 transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  Full CSV
                </button>
              </div>
            )}
          </div>

          {/* Search */}
          {!loadingStocks && stocks.length > 0 && (
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={`Search in ${selected}…`}
                className="w-full sm:w-80 pl-9 pr-4 py-2 bg-gray-900 border border-gray-700
                           rounded-lg text-sm text-white placeholder-gray-500
                           focus:outline-none focus:border-blue-600 transition"
              />
            </div>
          )}

          {/* Loading skeleton */}
          {loadingStocks && (
            <div className="space-y-2">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="h-11 bg-gray-800/60 rounded-lg animate-pulse" />
              ))}
            </div>
          )}

          {/* Table */}
          {!loadingStocks && displayed.length > 0 && (
            <div className="overflow-x-auto rounded-xl border border-gray-800">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 bg-gray-900/80">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 w-10">#</th>
                    {COLS.map((col) => (
                      <th
                        key={col.key}
                        onClick={() => col.sortable && toggleSort(col.key)}
                        className={clsx(
                          "px-4 py-3 text-left text-xs font-semibold text-gray-400 whitespace-nowrap select-none",
                          col.sortable && "cursor-pointer hover:text-gray-200 transition"
                        )}
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
                  {displayed.map((row, idx) => (
                    <tr key={row.symbol} className="hover:bg-gray-800/40 transition-colors">
                      <td className="px-4 py-2.5 text-xs text-gray-600 tabular-nums">{idx + 1}</td>

                      {/* Symbol */}
                      <td className="px-4 py-2.5">
                        <span className="font-mono font-semibold text-white tracking-wide">
                          {row.symbol}
                        </span>
                      </td>

                      {/* Company Name */}
                      <td className="px-4 py-2.5 max-w-xs">
                        <span className="text-gray-300 text-xs truncate block">
                          {row.name || "—"}
                        </span>
                      </td>

                      {/* Sector */}
                      <td className="px-4 py-2.5">
                        <span className="text-xs text-gray-400">{row.sector || "—"}</span>
                      </td>

                      {/* ISIN */}
                      <td className="px-4 py-2.5">
                        <span className="font-mono text-xs text-gray-500 tracking-wider">
                          {row.isin || "—"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Empty */}
          {!loadingStocks && displayed.length === 0 && (
            <div className="text-center py-14 text-gray-500">
              <p className="text-3xl mb-2">📭</p>
              <p className="text-sm">
                {search
                  ? `No stocks match "${search}" in ${selected}`
                  : `No stocks found in ${selected}`}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Placeholder */}
      {!selected && !loadingSectors && sectors.length > 0 && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-8 text-center space-y-4">
          <div className="text-5xl">🏗️</div>
          <div>
            <p className="text-sm text-gray-300 font-medium">Select a sector above to view its stocks</p>
            <p className="text-xs text-gray-500 mt-1">
              Then export tickers as <strong className="text-gray-400">CSV</strong>,{" "}
              <strong className="text-gray-400">Excel</strong>, or{" "}
              <strong className="text-gray-400">Full CSV</strong> (with name + ISIN) to seed your evaluation app
            </p>
          </div>
          <div className="flex items-center justify-center gap-6 pt-2 text-xs text-gray-600">
            <span>📋 Tickers CSV — one symbol per line</span>
            <span>📊 Tickers Excel — ready for most screeners</span>
            <span>📁 Full CSV — Symbol + Name + Sector + ISIN</span>
          </div>
        </div>
      )}

    </div>
  );
}
