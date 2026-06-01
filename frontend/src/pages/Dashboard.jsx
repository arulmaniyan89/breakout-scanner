import React, { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { RefreshCw, TrendingUp, TrendingDown, Zap, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

import { useBreakouts, useStats } from "../hooks/useBreakouts";
import BreakoutTable from "../components/BreakoutTable";
import FilterBar from "../components/FilterBar";
import StatCard from "../components/StatCard";
import { addToWatchlist, triggerScan, fetchScanStatus } from "../utils/api";

// ─── Scan progress helpers ────────────────────────────────────────────────────

const SCAN_STEPS = [
  { key: "nifty",    label: "Nifty Trend"   },
  { key: "download", label: "Download Data"  },
  { key: "analyse",  label: "Analyse Stocks" },
  { key: "done",     label: "Done"           },
];

function stepIndex(status) {
  if (status === "downloading") return 1;
  if (status === "analysing")   return 2;
  if (status === "completed")   return 3;
  return 0; // starting / idle
}

function progressPct(s) {
  if (!s) return 5;
  if (s.status === "downloading") {
    const done  = s.dl_done  || 0;
    const total = s.dl_total || 1;
    return Math.max(5, Math.round((done / total) * 70));
  }
  if (s.status === "analysing")  return 82;
  if (s.status === "completed")  return 100;
  return 5;
}

function ScanProgressBar({ scanStatus: s }) {
  const pct    = progressPct(s);
  const step   = stepIndex(s?.status);
  const failed = s?.status === "failed";

  return (
    <div className="bg-gray-900/80 border border-blue-900/60 rounded-xl px-5 py-4 space-y-3 animate-in fade-in duration-300">

      {/* Title */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-blue-300">
          <Loader2 className="w-4 h-4 animate-spin shrink-0" />
          Scanning NSE stocks…
        </div>
        <span className="text-xs text-gray-500 tabular-nums">{pct}%</span>
      </div>

      {/* Step indicators */}
      <div className="flex items-center">
        {SCAN_STEPS.map((st, i) => {
          const done    = i < step;
          const active  = i === step;
          const pending = i > step;
          return (
            <React.Fragment key={st.key}>
              <div className={clsx(
                "flex items-center gap-1.5 text-xs font-medium whitespace-nowrap",
                done    && "text-emerald-400",
                active  && "text-blue-300",
                pending && "text-gray-600",
              )}>
                {/* Circle */}
                <span className={clsx(
                  "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold border shrink-0",
                  done    && "bg-emerald-800 border-emerald-600 text-emerald-200",
                  active  && "bg-blue-700   border-blue-400   text-white animate-pulse",
                  pending && "bg-gray-800   border-gray-700   text-gray-600",
                )}>
                  {done ? "✓" : i + 1}
                </span>
                <span className="hidden sm:inline">{st.label}</span>
              </div>

              {/* Connector line */}
              {i < SCAN_STEPS.length - 1 && (
                <div className={clsx(
                  "flex-1 h-px mx-1.5 min-w-[8px]",
                  i < step ? "bg-emerald-700" : "bg-gray-700"
                )} />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={clsx(
            "h-full rounded-full transition-all duration-700 ease-out",
            failed       ? "bg-red-500"
            : pct === 100 ? "bg-emerald-500"
            : "bg-blue-500"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Detail text */}
      {s?.status_detail && !failed && (
        <p className="text-xs text-gray-400 leading-snug">{s.status_detail}</p>
      )}
      {failed && s?.error && (
        <p className="text-xs text-red-400">{s.error}</p>
      )}
    </div>
  );
}

// ─── Filter helpers ───────────────────────────────────────────────────────────

const CRITERIA_KEYS = {
  price_breakout:   "price_breakout",
  volume_confirmed: "volume_confirmed",
  momentum_ok:      "momentum_ok",
  trend_ok:         "trend_ok",
  breakout_100d:    "breakout_100d",
};

function applyFilters(data, filters) {
  return data.filter((row) => {
    if (filters.search) {
      const q = filters.search.toLowerCase();
      if (!row.symbol.toLowerCase().includes(q) && !row.name?.toLowerCase().includes(q)) return false;
    }
    if (filters.exchange && filters.exchange !== "ALL") {
      if (row.exchange !== filters.exchange) return false;
    }
    if (filters.strength && filters.strength !== "ALL") {
      if (row.strength !== filters.strength) return false;
    }
    if (filters.sector && filters.sector !== "ALL") {
      if (row.sector !== filters.sector) return false;
    }
    if (filters.criteria?.length) {
      for (const key of filters.criteria) {
        if (!row[CRITERIA_KEYS[key]]) return false;
      }
    }
    return true;
  });
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

const TABS = [
  { id: "today",     label: "Today's Breakouts" },
  { id: "yesterday", label: "Yesterday"          },
];

export default function Dashboard() {
  const [tab,     setTab]     = useState("today");
  const [filters, setFilters] = useState({ exchange: "ALL", strength: "ALL", sector: "ALL", search: "" });
  const { data, loading, error, reload } = useBreakouts(tab, filters);
  const { stats, scanStatus }            = useStats();

  // ── Scan progress polling ──────────────────────────────────────────────────
  const [liveStatus, setLiveStatus] = useState(null);  // null = not scanning
  const pollTimer = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearTimeout(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  const poll = useCallback(async () => {
    try {
      const s = await fetchScanStatus();
      setLiveStatus(s);

      if (s.status === "completed") {
        stopPolling();
        setTimeout(() => {
          setLiveStatus(null);   // hide bar after short pause
          reload();              // refresh breakout table
        }, 1200);
        toast.success(`✅ Scan complete — ${s.total_breakouts} breakouts found`);
      } else if (s.status === "failed") {
        stopPolling();
        setTimeout(() => setLiveStatus(null), 4000);
        toast.error(`Scan failed: ${s.error || "unknown error"}`);
      } else {
        // still running → poll again in 2s
        pollTimer.current = setTimeout(poll, 2000);
      }
    } catch {
      // network hiccup — retry in 3s
      pollTimer.current = setTimeout(poll, 3000);
    }
  }, [reload, stopPolling]);

  const startPolling = useCallback(() => {
    stopPolling();
    // small delay so backend has time to set status to "downloading"
    pollTimer.current = setTimeout(poll, 800);
  }, [poll, stopPolling]);

  // cleanup on unmount
  useEffect(() => () => stopPolling(), [stopPolling]);

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleWatchlist = async (row) => {
    try {
      await addToWatchlist(row.symbol, row.exchange, row.name);
      toast.success(`${row.symbol} added to watchlist`);
    } catch (e) {
      if (e.response?.status === 409) toast.error("Already in watchlist");
      else toast.error("Failed to add");
    }
  };

  const handleTriggerScan = async () => {
    try {
      await triggerScan();
      setLiveStatus({ status: "downloading", status_detail: "Starting scan…", dl_done: 0, dl_total: 0 });
      startPolling();
    } catch {
      toast.error("Could not trigger scan (backend offline?)");
    }
  };

  const filtered = useMemo(() => applyFilters(data, filters), [data, filters]);
  const isScanning = liveStatus !== null && !["completed", "failed"].includes(liveStatus?.status);

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            Pre-Breakout Setups
            {stats?.nifty_trend === true && (
              <span className="flex items-center gap-1 text-sm font-normal text-emerald-400 bg-emerald-900/30 border border-emerald-800 rounded-full px-2 py-0.5">
                <TrendingUp className="w-3.5 h-3.5" /> Nifty Uptrend
              </span>
            )}
            {stats?.nifty_trend === false && (
              <span className="flex items-center gap-1 text-sm font-normal text-red-400 bg-red-900/30 border border-red-800 rounded-full px-2 py-0.5">
                <TrendingDown className="w-3.5 h-3.5" /> Nifty Downtrend
              </span>
            )}
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            {scanStatus?.last_scan
              ? `Last scan: ${scanStatus.last_scan} · ${scanStatus.total_scanned} stocks analysed`
              : "Scheduled daily at 8:45 AM IST"}
          </p>
        </div>

        <div className="flex flex-col items-end gap-2">
          <div className="flex gap-2">
            <button
              onClick={reload}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 border border-gray-700
                         text-sm text-gray-300 hover:text-white transition"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
            <button
              onClick={handleTriggerScan}
              disabled={isScanning}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500
                         disabled:opacity-60 disabled:cursor-not-allowed
                         text-sm text-white font-semibold transition"
            >
              {isScanning
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <Zap className="w-4 h-4" />}
              {isScanning ? "Scanning…" : "Run Scan Now"}
            </button>
          </div>
        </div>
      </div>

      {/* ── Scan progress bar (shown only while scanning) ── */}
      {liveStatus && (
        <ScanProgressBar scanStatus={liveStatus} />
      )}

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Total Breakouts" value={stats?.total} icon="📊" color="default"
          sub={stats?.scan_date} />
        <StatCard label="Strong"     value={stats?.strong}    icon="🟢" color="green"  sub="All 4 criteria" />
        <StatCard label="Moderate"   value={stats?.moderate}  icon="🟡" color="yellow" sub="3 of 4 criteria" />
        <StatCard label="Watch List" value={stats?.watchlist} icon="🔵" color="blue"   sub="2 of 4 criteria" />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-xl p-1 w-fit">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition
              ${tab === t.id
                ? "bg-blue-600 text-white shadow"
                : "text-gray-400 hover:text-gray-200"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Filters */}
      <FilterBar filters={filters} onChange={setFilters} />

      {/* Error banner */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-lg px-4 py-3 text-sm text-red-300">
          Backend unavailable — showing demo data. Error: {error}
        </div>
      )}

      {/* Results count */}
      {!loading && (
        <div className="text-sm text-gray-400">
          Showing <span className="text-white font-semibold">{filtered.length}</span> breakout stocks
          {filtered.length !== data.length && ` (filtered from ${data.length})`}
        </div>
      )}

      {/* Table */}
      <BreakoutTable data={filtered} loading={loading} onWatchlist={handleWatchlist} />
    </div>
  );
}
