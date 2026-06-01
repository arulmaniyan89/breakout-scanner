import React from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import clsx from "clsx";

const EXCHANGES = ["ALL", "NSE", "BSE"];
const STRENGTHS = ["ALL", "STRONG", "MODERATE", "WATCHLIST"];
const SECTORS = [
  "ALL", "Information Technology", "Financial Services", "Energy",
  "Automobile", "Pharmaceuticals", "Consumer Discretionary",
  "Consumer Electronics", "FMCG",
];

const CRITERIA = [
  { key: "price_breakout",   label: "Price Breakout",   icon: "📈", color: "emerald" },
  { key: "volume_confirmed", label: "Volume",           icon: "📊", color: "blue"    },
  { key: "momentum_ok",      label: "Momentum",         icon: "⚡", color: "yellow"  },
  { key: "trend_ok",         label: "Trend",            icon: "🔺", color: "purple"  },
  { key: "breakout_100d",    label: "Vol↑ + 100D High", icon: "🚀", color: "orange"  },
];

const activeColors = {
  emerald: "bg-emerald-600 text-white border-emerald-500",
  blue:    "bg-blue-600 text-white border-blue-500",
  yellow:  "bg-yellow-600 text-white border-yellow-500",
  purple:  "bg-purple-600 text-white border-purple-500",
  orange:  "bg-orange-600 text-white border-orange-500",
};
const inactiveColors = {
  emerald: "text-emerald-400 border-emerald-800 hover:bg-emerald-900/40",
  blue:    "text-blue-400 border-blue-800 hover:bg-blue-900/40",
  yellow:  "text-yellow-400 border-yellow-800 hover:bg-yellow-900/40",
  purple:  "text-purple-400 border-purple-800 hover:bg-purple-900/40",
  orange:  "text-orange-400 border-orange-800 hover:bg-orange-900/40",
};

export default function FilterBar({ filters, onChange }) {
  const set = (key, value) => onChange({ ...filters, [key]: value });

  const toggleCriteria = (key) => {
    const current = filters.criteria || [];
    const next = current.includes(key)
      ? current.filter((k) => k !== key)
      : [...current, key];
    onChange({ ...filters, criteria: next });
  };

  const activeCriteria = filters.criteria || [];

  return (
    <div className="flex flex-col gap-3 bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
      {/* Row 1: search + exchange + strength + sector */}
      <div className="flex flex-wrap gap-3 items-center">
        {/* Search */}
        <div className="relative flex-1 min-w-[180px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search symbol or name…"
            value={filters.search || ""}
            onChange={(e) => set("search", e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm
                       text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
          />
        </div>

        {/* Exchange */}
        <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
          {EXCHANGES.map((ex) => (
            <button
              key={ex}
              onClick={() => set("exchange", ex)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition
                ${(filters.exchange || "ALL") === ex
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-gray-200"}`}
            >
              {ex}
            </button>
          ))}
        </div>

        {/* Strength */}
        <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
          {STRENGTHS.map((s) => {
            const active = (filters.strength || "ALL") === s;
            const colorMap = {
              STRONG:    active ? "bg-emerald-600 text-white" : "text-emerald-400 hover:text-emerald-200",
              MODERATE:  active ? "bg-yellow-600 text-white"  : "text-yellow-400 hover:text-yellow-200",
              WATCHLIST: active ? "bg-blue-600 text-white"    : "text-blue-400 hover:text-blue-200",
              ALL:       active ? "bg-gray-600 text-white"    : "text-gray-400 hover:text-gray-200",
            };
            return (
              <button
                key={s}
                onClick={() => set("strength", s)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${colorMap[s]}`}
              >
                {s === "ALL" ? "All" : s === "STRONG" ? "🟢 Strong" : s === "MODERATE" ? "🟡 Moderate" : "🔵 Watch"}
              </button>
            );
          })}
        </div>

        {/* Sector */}
        <div className="relative">
          <SlidersHorizontal className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
          <select
            value={filters.sector || "ALL"}
            onChange={(e) => set("sector", e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg pl-8 pr-8 py-2 text-xs text-gray-300
                       focus:outline-none focus:border-blue-500 transition appearance-none cursor-pointer"
          >
            {SECTORS.map((s) => (
              <option key={s} value={s}>{s === "ALL" ? "All Sectors" : s}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Row 2: Criteria toggles */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-gray-500 font-medium mr-1">Criteria:</span>
        {CRITERIA.map(({ key, label, icon, color }) => {
          const isActive = activeCriteria.includes(key);
          return (
            <button
              key={key}
              onClick={() => toggleCriteria(key)}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition",
                isActive ? activeColors[color] : `bg-gray-800/60 ${inactiveColors[color]}`
              )}
            >
              <span>{icon}</span>
              {label}
              {isActive && <span className="ml-0.5 opacity-70">✓</span>}
            </button>
          );
        })}

        {/* Clear criteria */}
        {activeCriteria.length > 0 && (
          <button
            onClick={() => onChange({ ...filters, criteria: [] })}
            className="px-2 py-1.5 rounded-lg text-xs text-gray-500 hover:text-gray-300 transition"
          >
            Clear ×
          </button>
        )}

        {/* Live count indicator */}
        {activeCriteria.length > 0 && (
          <span className="ml-auto text-xs text-gray-500">
            Showing stocks where{" "}
            <span className="text-white font-semibold">
              {activeCriteria.length === 1 ? "this criterion" : `all ${activeCriteria.length} criteria`}
            </span>{" "}
            {activeCriteria.length === 1 ? "is" : "are"} met
          </span>
        )}
      </div>
    </div>
  );
}
