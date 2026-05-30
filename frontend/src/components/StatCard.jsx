import React from "react";
import clsx from "clsx";

export default function StatCard({ label, value, sub, color = "default", icon }) {
  const colorMap = {
    default: "text-white",
    green: "text-emerald-400",
    yellow: "text-yellow-400",
    blue: "text-blue-400",
    red: "text-red-400",
  };

  return (
    <div className="stat-card">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400 font-medium uppercase tracking-wider">{label}</span>
        {icon && <span className="text-lg">{icon}</span>}
      </div>
      <div className={clsx("text-3xl font-bold tabular-nums mt-1", colorMap[color])}>
        {value ?? "—"}
      </div>
      {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
    </div>
  );
}
