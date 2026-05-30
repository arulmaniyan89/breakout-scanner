import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Trash2, ExternalLink, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";
import { fetchWatchlist, removeFromWatchlist } from "../utils/api";

const MOCK_WL = [
  { id: 1, symbol: "RELIANCE", exchange: "NSE", name: "Reliance Industries Ltd",
    latest_cmp: 2987.45, latest_pct_change: 2.66, latest_rsi: 62.4, latest_strength: "STRONG" },
  { id: 2, symbol: "ZOMATO", exchange: "NSE", name: "Zomato Ltd",
    latest_cmp: 298.4, latest_pct_change: 4.70, latest_rsi: 70.1, latest_strength: "STRONG" },
];

export default function Watchlist() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    fetchWatchlist()
      .then(setItems)
      .catch(() => setItems(MOCK_WL))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleRemove = async (symbol) => {
    try {
      await removeFromWatchlist(symbol);
      setItems((prev) => prev.filter((i) => i.symbol !== symbol));
      toast.success(`${symbol} removed`);
    } catch {
      // Optimistically remove from demo state anyway
      setItems((prev) => prev.filter((i) => i.symbol !== symbol));
      toast.success(`${symbol} removed`);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">My Watchlist</h1>
          <p className="text-gray-400 text-sm mt-0.5">{items.length} stocks tracked</p>
        </div>
        <button onClick={load}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-300 hover:text-white transition">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-14 bg-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <p className="text-3xl mb-3">📋</p>
          <p className="text-lg font-medium mb-1">Your watchlist is empty</p>
          <p className="text-sm">Click the bookmark icon on any breakout stock to add it here.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-900 border-b border-gray-800 text-xs text-gray-400">
                <th className="px-4 py-3 text-left">Stock</th>
                <th className="px-4 py-3 text-left">CMP</th>
                <th className="px-4 py-3 text-left">% Change</th>
                <th className="px-4 py-3 text-left">RSI</th>
                <th className="px-4 py-3 text-left">Strength</th>
                <th className="px-4 py-3 text-left">Exchange</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {items.map((item) => (
                <tr key={item.id}
                  className="hover:bg-gray-800/60 transition cursor-pointer"
                  onClick={() => navigate(`/stock/${item.symbol}`)}>
                  <td className="px-4 py-3">
                    <div className="font-semibold text-white">{item.symbol}</div>
                    <div className="text-xs text-gray-400">{item.name}</div>
                  </td>
                  <td className="px-4 py-3 tabular-nums text-white font-medium">
                    {item.latest_cmp ? `₹${item.latest_cmp.toLocaleString("en-IN")}` : "—"}
                  </td>
                  <td className={`px-4 py-3 tabular-nums font-semibold
                    ${item.latest_pct_change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {item.latest_pct_change != null
                      ? `${item.latest_pct_change >= 0 ? "+" : ""}${item.latest_pct_change.toFixed(2)}%`
                      : "—"}
                  </td>
                  <td className="px-4 py-3 tabular-nums text-gray-300">
                    {item.latest_rsi?.toFixed(1) ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    {item.latest_strength === "STRONG" && <span className="badge-strong">🟢 Strong</span>}
                    {item.latest_strength === "MODERATE" && <span className="badge-moderate">🟡 Moderate</span>}
                    {item.latest_strength === "WATCHLIST" && <span className="badge-watchlist">🔵 Watch</span>}
                    {!item.latest_strength && <span className="text-gray-500 text-xs">No scan data</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{item.exchange}</td>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <div className="flex gap-1">
                      <button
                        onClick={() => navigate(`/stock/${item.symbol}`)}
                        className="p-1.5 rounded text-gray-400 hover:text-blue-400 hover:bg-blue-900/20 transition"
                        title="View details">
                        <ExternalLink className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleRemove(item.symbol)}
                        className="p-1.5 rounded text-gray-400 hover:text-red-400 hover:bg-red-900/20 transition"
                        title="Remove">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
