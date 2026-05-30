import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  timeout: 30000,
});

export const fetchTodayBreakouts = (params = {}) =>
  api.get("/breakouts/today", { params }).then((r) => r.data);

export const fetchYesterdayBreakouts = (params = {}) =>
  api.get("/breakouts/yesterday", { params }).then((r) => r.data);

export const fetchSymbolHistory = (symbol) =>
  api.get(`/breakouts/${symbol}`).then((r) => r.data);

export const fetchScanHistory = () =>
  api.get("/history").then((r) => r.data);

export const fetchStats = () =>
  api.get("/stats").then((r) => r.data);

export const fetchScanStatus = () =>
  api.get("/scan/status").then((r) => r.data);

export const triggerScan = () =>
  api.post("/scan/trigger").then((r) => r.data);

export const fetchWatchlist = () =>
  api.get("/watchlist").then((r) => r.data);

export const addToWatchlist = (symbol, exchange, name, notes) =>
  api.post("/watchlist/add", { symbol, exchange, name, notes }).then((r) => r.data);

export const removeFromWatchlist = (symbol) =>
  api.delete(`/watchlist/${symbol}`).then((r) => r.data);

export const subscribeAlerts = (payload) =>
  api.post("/alerts/subscribe", payload).then((r) => r.data);

export default api;
