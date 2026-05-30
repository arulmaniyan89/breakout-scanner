import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: parseInt(process.env.PORT || "3000"),
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on("error", (_err, req, res) => {
            // Backend offline — return empty-but-valid JSON so the UI stays clean
            const empty = req.url?.includes("/stats")
              ? '{"total":0,"strong":0,"moderate":0,"watchlist":0,"nifty_trend":null,"scan_date":null}'
              : req.url?.includes("/status")
              ? '{"status":"offline","last_scan":null}'
              : "[]";
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(empty);
          });
        },
      },
    },
  },
});
