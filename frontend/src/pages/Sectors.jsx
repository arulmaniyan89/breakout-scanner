import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  Building2, Download, Search, RefreshCw,
  ArrowUp, ArrowDown, ArrowUpDown, Copy, CheckCheck, ChevronDown,
} from "lucide-react";
import axios from "axios";
import clsx from "clsx";

// ─── Export helpers ───────────────────────────────────────────────────────────

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a   = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Tickers only — one per line, no header (for pasting into screeners / eval apps) */
function exportTickersCSV(stocks, label) {
  downloadBlob(
    new Blob([stocks.map((s) => s.symbol).join("\n")], { type: "text/plain;charset=utf-8" }),
    `${label.replace(/\s+/g, "_")}_tickers.csv`
  );
}

/** Tickers only — Excel (SpreadsheetML, no library needed) */
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

/** Full CSV — Symbol, Company Name, ISIN (with header) */
function exportFullCSV(stocks, label) {
  const header = "Symbol,Company Name,ISIN";
  const rows   = stocks.map(
    (s) => `${s.symbol},"${(s.name || "").replace(/"/g, '""')}",${s.isin || ""}`
  );
  downloadBlob(
    new Blob([[header, ...rows].join("\n")], { type: "text/csv;charset=utf-8" }),
    `${label.replace(/\s+/g, "_")}_full.csv`
  );
}

// ─── Copy-to-clipboard button ─────────────────────────────────────────────────

function CopyButton({ stocks }) {
  const [done, setDone] = useState(false);
  const handle = () => {
    navigator.clipboard.writeText(stocks.map((s) => s.symbol).join(",")).then(() => {
      setDone(true);
      setTimeout(() => setDone(false), 2000);
    });
  };
  return (
    <button
      onClick={handle}
      title="Copy comma-separated tickers to clipboard"
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800
                 border border-gray-700 text-xs font-semibold text-gray-300
                 hover:text-white hover:border-gray-500 transition"
    >
      {done
        ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" />
        : <Copy className="w-3.5 h-3.5" />}
      {done ? "Copied!" : "Copy Tickers"}
    </button>
  );
}

// ─── Sortable table header ────────────────────────────────────────────────────

const COLS = [
  { key: "symbol", label: "Symbol",       sortable: true  },
  { key: "name",   label: "Company Name", sortable: true  },
  { key: "isin",   label: "ISIN",         sortable: false },
];

function SortTh({ col, sort, onSort }) {
  const active = sort.key === col.key;
  return (
    <th
      onClick={() => col.sortable && onSort(col.key)}
      className={clsx(
        "px-4 py-3 text-left text-xs font-semibold text-gray-400 whitespace-nowrap select-none",
        col.sortable && "cursor-pointer hover:text-gray-200 transition"
      )}
    >
      <span className="inline-flex items-center gap-1">
        {col.label}
        {col.sortable && (
          active
            ? sort.dir === "asc"
              ? <ArrowUp className="w-3 h-3" />
              : <ArrowDown className="w-3 h-3" />
            : <ArrowUpDown className="w-3 h-3 opacity-30" />
        )}
      </span>
    </th>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Sectors() {
  const [sectors,        setSectors]       = useState([]);
  const [totalStocks,    setTotalStocks]   = useState(0);
  const [selected,       setSelected]      = useState("");
  const [stocks,         setStocks]        = useState([]);
  const [search,         setSearch]        = useState("");
  const [loadingSectors, setLoadingSectors] = useState(true);
  const [loadingStocks,  setLoadingStocks]  = useState(false);
  const [sort,           setSort]          = useState({ key: "symbol", dir: "asc" });
  const [refreshing,     setRefreshing]    = useState(false);
  const [dataSource,     setDataSource]    = useState("");

  // ── Load sector list from NSE Universe ────────────────────────────────────
  const loadSectors = useCallback(() => {
    setLoadingSectors(true);
    axios.get("/api/universe/sectors")
      .then((r) => {
        setSectors(r.data.sectors || []);
        setTotalStocks(r.data.total_stocks || 0);
        setDataSource("NSE EQUITY_L (all listed stocks)");
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
    setSearch("");
    axios.get("/api/universe/stocks", { params: { sector: selected } })
      .then((r) => setStocks(r.data))
      .catch(() => setStocks([]))
      .finally(() => setLoadingStocks(false));
  }, [selected]);

  // ── Sort + client-side search ──────────────────────────────────────────────
  const displayed = useMemo(() => {
    let list = stocks;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(
        (s) => s.symbol.toLowerCase().includes(q) || (s.name || "").toLowerCase().includes(q)
      );
    }
    return [...list].sort((a, b) => {
      const va = (a[sort.key] ?? "").toString().toLowerCase();
      const vb = (b[sort.key] ?? "").toString().toLowerCase();
      return sort.dir === "asc" ? va.localeCompare(vb) : vb.localeCompare(va);
    });
  }, [stocks, search, sort.key, sort.dir]);

  const toggleSort = (key) =>
    setSort((p) => p.key === key
      ? { key, dir: p.dir === "asc" ? "desc" : "asc" }
      : { key, dir: "asc" }
    );

  const handleRefresh = () => {
    setRefreshing(true);
    axios.post("/api/universe/refresh")
      .then(() => setTimeout(() => { loadSectors(); setRefreshing(false); }, 3500))
      .catch(() => setRefreshing(false));
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Building2 className="w-6 h-6 text-blue-400" />
            Sector Explorer
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Browse all NSE-listed stocks by sector. Select a sector and export tickers.
          </p>
          {totalStocks > 0 && (
            <p className="text-xs text-gray-500 mt-1">
              Source: <span className="text-blue-300">{dataSource}</span>
              {" · "}<span className="text-white font-semibold">{totalStocks.toLocaleString()}</span> total stocks
              {" · "}<span className="text-white font-semibold">{sectors.length}</span> sectors
            </p>
          )}
        </div>

        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800
                     border border-gray-700 text-xs font-semibold text-gray-400
                     hover:text-white hover:border-gray-500 disabled:opacity-50 transition"
        >
          <RefreshCw className={clsx("w-3.5 h-3.5", refreshing && "animate-spin")} />
          {refreshing ? "Refreshing…" : "Refresh from NSE"}
        </button>
      </div>

      {/* ── Sector dropdown ─────────────────────────────────────────────────── */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Choose a Sector
        </p>

        {loadingSectors ? (
          <div className="h-11 w-72 bg-gray-800 rounded-lg animate-pulse" />
        ) : sectors.length === 0 ? (
          <p className="text-sm text-gray-500">
            No sector data yet — this loads automatically on first visit (~10 s).
            <br />
            If it keeps showing empty, click <strong className="text-white">Refresh from NSE</strong>.
          </p>
        ) : (
          <div className="relative inline-block w-full sm:w-96">
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              className="w-full appearance-none bg-gray-800 border border-gray-700 text-white
                         rounded-lg px-4 py-2.5 pr-10 text-sm font-medium
                         focus:outline-none focus:border-blue-500 cursor-pointer
                         hover:border-gray-500 transition"
            >
              <option value="">— Select a sector —</option>
              {sectors.map(({ sector, count }) => (
                <option key={sector} value={sector}>
                  {sector}  ({count} stocks)
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          </div>
        )}
      </div>

      {/* ── Stock table ─────────────────────────────────────────────────────── */}
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
                    }`}
              </span>
            </div>

            {/* Export buttons */}
            {!loadingStocks && displayed.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-gray-600">Export:</span>

                <CopyButton stocks={displayed} />

                <button
                  onClick={() => exportTickersCSV(displayed, selected)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800
                             border border-gray-700 text-xs font-semibold text-gray-300
                             hover:text-white hover:border-gray-500 transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  Tickers CSV
                </button>

                <button
                  onClick={() => exportTickersExcel(displayed, selected)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                             bg-emerald-900/30 border border-emerald-800
                             text-xs font-semibold text-emerald-400
                             hover:text-emerald-300 hover:border-emerald-600 transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  Tickers Excel
                </button>

                <button
                  onClick={() => exportFullCSV(displayed, selected)}
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

          {/* Search within sector */}
          {!loadingStocks && stocks.length > 0 && (
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={`Search ${selected}…`}
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
                      <SortTh key={col.key} col={col} sort={sort} onSort={toggleSort} />
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
                        <span className="text-gray-300 text-xs truncate block">{row.name || "—"}</span>
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
                  : `No stocks found in "${selected}"`}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Placeholder — nothing selected yet */}
      {!selected && !loadingSectors && sectors.length > 0 && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-10 text-center space-y-3">
          <div className="text-5xl">🏢</div>
          <p className="text-sm text-gray-300 font-medium">
            Select a sector from the dropdown above
          </p>
          <p className="text-xs text-gray-500">
            All NSE-listed stocks for the chosen sector will appear here.
            <br />
            Export tickers as <strong className="text-gray-400">CSV</strong> or{" "}
            <strong className="text-gray-400">Excel</strong>, or grab the{" "}
            <strong className="text-gray-400">Full CSV</strong> (Symbol + Name + ISIN)
            to seed your evaluation app.
          </p>
        </div>
      )}

    </div>
  );
}
