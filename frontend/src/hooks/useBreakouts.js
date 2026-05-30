import { useState, useEffect, useCallback } from "react";
import {
  fetchTodayBreakouts,
  fetchYesterdayBreakouts,
  fetchStats,
  fetchScanStatus,
} from "../utils/api";
import { MOCK_BREAKOUTS, MOCK_STATS, MOCK_SCAN_STATUS } from "../utils/mock";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

export function useBreakouts(tab = "today", filters = {}) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (USE_MOCK) {
        await new Promise((r) => setTimeout(r, 400)); // simulate latency
        setData(MOCK_BREAKOUTS);
      } else {
        const fn = tab === "today" ? fetchTodayBreakouts : fetchYesterdayBreakouts;
        const result = await fn(filters);
        setData(result);
      }
    } catch (e) {
      setError(e.message);
      setData(MOCK_BREAKOUTS); // fall back to mock
    } finally {
      setLoading(false);
    }
  }, [tab, JSON.stringify(filters)]);

  useEffect(() => {
    load();
  }, [load]);

  return { data, loading, error, reload: load };
}

export function useStats() {
  const [stats, setStats] = useState(null);
  const [scanStatus, setScanStatus] = useState(null);

  useEffect(() => {
    if (USE_MOCK) {
      setStats(MOCK_STATS);
      setScanStatus(MOCK_SCAN_STATUS);
      return;
    }
    Promise.all([fetchStats(), fetchScanStatus()])
      .then(([s, sc]) => {
        setStats(s);
        setScanStatus(sc);
      })
      .catch(() => {
        setStats(MOCK_STATS);
        setScanStatus(MOCK_SCAN_STATUS);
      });
  }, []);

  return { stats, scanStatus };
}
