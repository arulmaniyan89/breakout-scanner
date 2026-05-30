import React, { useState, useMemo } from "react";
import { RefreshCw, TrendingUp, TrendingDown, Zap } from "lucide-react";
import toast from "react-hot-toast";

import { useBreakouts, useStats } from "../hooks/useBreakouts";
import BreakoutTable from "../components/BreakoutTable";
import FilterBar from "../components/FilterBar";
import StatCard from "../components/StatCard";
import { addToWatchlist, triggerScan } from "../utils/api";

const TABS = [
  { id: "today", label: "Today's Breakouts" },
  { id: "yesterday", label: "Yesterday" },
];

const CRITERIA_KEYS = {
  price_breakout:   "price_breakout",
  volume_confirmed: "volume_confirmed",
  momentum_ok:      "momentum_ok",
  trend_ok:         "trend_ok",
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
    // Each toggled criterion must be true on the row
    if (filters.criteria?.length) {
      for (const key of filters.criteria) {
        if (!row[CRITERIA_KEYS[key]]) return false;
      }
    }
    return true;
  });
}

export default function Dashboard() {
  const [tab, setTab] = useState("today");
  const [filters, setFilters] = useState({ exchange: "ALL", strength: "ALL", sector: "ALL", search: "" });
  const { data, loading, error, reload } = useBreakouts(tab, filters);
  const { stats, scanStatus } = useStats();

  const filtered = useMemo(() => applyFilters(data, filters), [data, filters]);

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
      toast.success("Scan triggered — check back in a few minutes");
    } catch {
      toast.error("Could not trigger scan (backend offline?)");
    }
  };

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
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500
                       text-sm text-white font-semibold transition"
          >
            <Zap className="w-4 h-4" />
            Run Scan Now
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Total Breakouts" value={stats?.total} icon="📊" color="default"
          sub={stats?.scan_date} />
        <StatCard label="Strong" value={stats?.strong} icon="🟢" color="green"
          sub="All 4 criteria" />
        <StatCard label="Moderate" value={stats?.moderate} icon="🟡" color="yellow"
          sub="3 of 4 criteria" />
        <StatCard label="Watch List" value={stats?.watchlist} icon="🔵" color="blue"
          sub="2 of 4 criteria" />
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
