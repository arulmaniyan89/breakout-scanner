import React from "react";
import { NavLink } from "react-router-dom";
import { TrendingUp, BookMarked, History, Bell, FlaskConical, Building2, BookOpen } from "lucide-react";
import clsx from "clsx";

const links = [
  { to: "/",            label: "Dashboard",    icon: TrendingUp   },
  { to: "/watchlist",   label: "Watchlist",    icon: BookMarked   },
  { to: "/history",     label: "History",      icon: History      },
  { to: "/alerts",      label: "Alerts",       icon: Bell         },
  { to: "/evaluate",    label: "Evaluate",     icon: FlaskConical },
  { to: "/sectors",     label: "Sectors",      icon: Building2    },
  { to: "/methodology", label: "How It Works", icon: BookOpen     },
];

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 bg-gray-950/90 backdrop-blur border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center h-14 gap-6">
        {/* Logo */}
        <div className="flex items-center gap-2 font-bold text-white text-base shrink-0">
          <span className="text-xl">📈</span>
          <span>Breakout Scanner</span>
          <span className="text-[10px] text-blue-400 border border-blue-800 rounded px-1.5 py-0.5 ml-1">
            NSE · BSE
          </span>
        </div>

        {/* Links */}
        <div className="flex items-center gap-1 ml-4">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition",
                  isActive
                    ? "bg-blue-900/40 text-blue-300"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
                )
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </div>

        {/* Right: live badge */}
        <div className="ml-auto flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs text-gray-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Live · ~15 min delay
          </span>
        </div>
      </div>
    </nav>
  );
}
