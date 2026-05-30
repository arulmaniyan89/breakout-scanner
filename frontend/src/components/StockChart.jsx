import React, { useEffect, useRef } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";

export default function StockChart({ symbol, exchange = "NSE" }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "#0f172a" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#334155" },
      timeScale: { borderColor: "#334155", timeVisible: true },
      width: containerRef.current.clientWidth,
      height: 320,
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    const volSeries = chart.addHistogramSeries({
      color: "#334155",
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    // Generate synthetic demo data
    const generateData = () => {
      const candles = [];
      const volumes = [];
      let price = 1000 + Math.random() * 2000;
      const now = Math.floor(Date.now() / 1000);
      const DAY = 86400;

      for (let i = 200; i >= 0; i--) {
        const time = now - i * DAY;
        const open = price;
        const change = (Math.random() - 0.48) * price * 0.03;
        const close = Math.max(open + change, 1);
        const high = Math.max(open, close) * (1 + Math.random() * 0.015);
        const low = Math.min(open, close) * (1 - Math.random() * 0.015);
        const volume = Math.floor(1000000 + Math.random() * 5000000);

        candles.push({ time, open, high, low, close });
        volumes.push({
          time,
          value: volume,
          color: close >= open ? "#10b98133" : "#ef444433",
        });
        price = close;
      }
      return { candles, volumes };
    };

    const { candles, volumes } = generateData();
    candleSeries.setData(candles);
    volSeries.setData(volumes);
    chart.timeScale().fitContent();

    chartRef.current = chart;

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [symbol]);

  return (
    <div className="rounded-xl border border-gray-800 overflow-hidden bg-[#0f172a]">
      <div className="px-4 py-2 border-b border-gray-800 text-xs text-gray-400 flex items-center justify-between">
        <span className="font-semibold text-white">{symbol} — Daily Chart (Demo)</span>
        <span className="text-gray-500">
          For live data: open{" "}
          <a
            href={`https://www.tradingview.com/chart/?symbol=${exchange}%3A${symbol}`}
            target="_blank"
            rel="noreferrer"
            className="text-blue-400 hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            TradingView ↗
          </a>
        </span>
      </div>
      <div ref={containerRef} />
    </div>
  );
}
