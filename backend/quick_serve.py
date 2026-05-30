"""
Standalone backend — no database required.
Fetches official NSE Bhavcopy data on startup and keeps results in memory.

Data source : NSE Bhavcopy archives (official, free, cached locally)
Fallback    : yfinance for Nifty trend + unknown company metadata

Usage:
    pip install -r requirements.txt
    python quick_serve.py
"""
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from data_fetcher import fetch_all_data, get_nifty_trend, get_company_info
from nse_bhavcopy import cache_stats
from scanner import run_scan, BreakoutStrength
from valuation.stock_data import fetch_stock
from valuation.scorer import evaluate as evaluate_stock

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

# ── Persistence ───────────────────────────────────────────────────────────────
RESULTS_FILE = Path(__file__).parent / "scan_results.json"


def _save_results() -> None:
    """Persist scan results to disk so backend restarts don't lose data."""
    try:
        payload = {
            "breakouts":     _state["breakouts"],
            "scan_date":     _state["scan_date"],
            "nifty_trend":   _state["nifty_trend"],
            "total_scanned": _state["total_scanned"],
            "saved_at":      datetime.utcnow().isoformat(),
        }
        with open(RESULTS_FILE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        logger.info("Saved %d breakouts → %s", len(_state["breakouts"]), RESULTS_FILE)
    except Exception as exc:
        logger.warning("Could not save results to disk: %s", exc)


def _load_results() -> bool:
    """Load persisted scan results from disk. Returns True on success."""
    if not RESULTS_FILE.exists():
        return False
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        _state["breakouts"]     = payload.get("breakouts", [])
        _state["scan_date"]     = payload.get("scan_date")
        _state["nifty_trend"]   = payload.get("nifty_trend")
        _state["total_scanned"] = payload.get("total_scanned", 0)
        _state["status"]        = "completed"
        saved_at = payload.get("saved_at", "")[:16].replace("T", " ")
        _state["status_detail"] = (
            f"Loaded {len(_state['breakouts'])} breakouts from last scan "
            f"({_state['scan_date']}, saved {saved_at} UTC) — click 'Run Scan Now' to refresh"
        )
        logger.info(
            "Loaded %d breakouts from disk (scan_date=%s)",
            len(_state["breakouts"]), _state["scan_date"],
        )
        return True
    except Exception as exc:
        logger.warning("Could not load results from disk: %s", exc)
        return False

app = FastAPI(title="Breakout Scanner (quick mode)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── In-memory state ──────────────────────────────────────────────────────────
_state = {
    "breakouts": [],          # list[dict]  — today's results
    "scan_date": None,        # str
    "nifty_trend": None,      # bool
    "total_scanned": 0,
    "status": "idle",         # idle / running / downloading / analysing / completed / failed
    "status_detail": "",      # human-readable progress message
    "dl_done": 0,             # bhavcopy files downloaded so far
    "dl_total": 0,            # total bhavcopy files to download
    "error": None,
    "watchlist": [],          # list[str]  — symbols
}


def _as_dict(analysis, name: str, sector: str, market_cap: float) -> dict:
    return {
        "id": hash(analysis.symbol) & 0x7FFFFFFF,
        "scan_date": str(date.today()),
        "symbol": analysis.symbol,
        "name": name,
        "exchange": analysis.exchange,
        "sector": sector,
        "market_cap": market_cap,
        "cmp": analysis.cmp,
        "prev_close": analysis.prev_close,
        "pct_change": analysis.pct_change,
        "high_52w": analysis.high_52w,
        "low_52w": analysis.low_52w,
        "volume": analysis.volume,
        "avg_volume_20d": analysis.avg_volume_20d,
        "volume_ratio": analysis.volume_ratio,
        "sma50": analysis.sma50,
        "sma200": analysis.sma200,
        "rsi": analysis.rsi,
        "macd": analysis.macd,
        "macd_signal": analysis.macd_signal,
        "macd_hist": analysis.macd_hist,
        "price_breakout": analysis.price_breakout,
        "volume_confirmed": analysis.volume_confirmed,
        "momentum_ok": analysis.momentum_ok,
        "trend_ok": analysis.trend_ok,
        "criteria_met": analysis.criteria_met,
        "breakout_type": analysis.breakout_type,
        "strength": analysis.strength.value if analysis.strength else None,
        "strength_score": analysis.strength_score,
        "entry_price": analysis.entry_price,
        "stop_loss": analysis.stop_loss,
        "target_price": analysis.target_price,
        "pct_gain_1d": None,
        "pct_gain_5d": None,
        "pct_gain_20d": None,
    }


def _run_scan_thread():
    logger.info("Starting NSE Bhavcopy scan…")
    _state["status"] = "downloading"
    _state["status_detail"] = "Checking Bhavcopy cache…"
    _state["error"] = None
    _state["dl_done"] = 0
    _state["dl_total"] = 0

    try:
        # ── Step 1: Nifty trend (quick yfinance call) ─────────────────────────
        _state["status_detail"] = "Fetching Nifty trend…"
        nifty_up = get_nifty_trend()
        _state["nifty_trend"] = nifty_up

        # ── Step 2: Download & compile Bhavcopy data ─────────────────────────
        def _progress(done: int, total: int) -> None:
            _state["dl_done"] = done
            _state["dl_total"] = total
            _state["status_detail"] = f"Downloading Bhavcopy files… {done}/{total}"
            if done % 20 == 0 or done == total:
                logger.info("Bhavcopy download progress: %d / %d", done, total)

        _state["status"] = "downloading"
        symbol_data, symbols = fetch_all_data(n_days=385, progress_cb=_progress)

        if not symbol_data:
            raise RuntimeError(
                "No data returned from Bhavcopy. "
                "Check internet connection or try again later."
            )

        _state["total_scanned"] = len(symbol_data)
        symbol_exchange_map = {s: ex for s, ex in symbols}
        logger.info("Compiled %d NSE symbols — running breakout analysis…", len(symbol_data))

        # ── Step 3: Run breakout scanner ──────────────────────────────────────
        _state["status"] = "analysing"
        _state["status_detail"] = f"Analysing {len(symbol_data)} NSE stocks…"

        results = run_scan(symbol_data, symbol_exchange_map, nifty_up)
        logger.info("Found %d breakout stocks", len(results))

        # ── Step 4: Enrich with company metadata ──────────────────────────────
        _state["status_detail"] = "Fetching company metadata…"
        enriched = []
        for r in results:
            info = get_company_info(r.symbol, r.exchange)
            enriched.append(
                _as_dict(r, info.get("name", r.symbol), info.get("sector"), info.get("market_cap"))
            )

        _state["breakouts"] = enriched
        _state["scan_date"] = str(date.today())
        _state["status"] = "completed"
        _state["status_detail"] = (
            f"Completed — {len(enriched)} pre-breakout setups from "
            f"{len(symbol_data)} NSE stocks"
        )
        logger.info("Scan complete — %d breakouts stored in memory", len(enriched))
        _save_results()   # ← persist to disk so restarts don't lose data

    except Exception as e:
        logger.error("Scan failed: %s", e, exc_info=True)
        _state["status"] = "failed"
        _state["status_detail"] = str(e)
        _state["error"] = str(e)


def _apply_filters(data: list, strength=None, exchange=None, sector=None) -> list:
    out = data
    if strength and strength.upper() != "ALL":
        out = [r for r in out if r.get("strength") == strength.upper()]
    if exchange and exchange.upper() != "ALL":
        out = [r for r in out if r.get("exchange") == exchange.upper()]
    if sector and sector.upper() not in ("ALL", ""):
        out = [r for r in out if (r.get("sector") or "").lower() == sector.lower()]
    return out


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": _state["status"]}


@app.get("/api/stats")
def stats():
    b = _state["breakouts"]
    return {
        "total": len(b),
        "strong": sum(1 for r in b if r.get("strength") == "STRONG"),
        "moderate": sum(1 for r in b if r.get("strength") == "MODERATE"),
        "watchlist": sum(1 for r in b if r.get("strength") == "WATCHLIST"),
        "nifty_trend": _state["nifty_trend"],
        "scan_date": _state["scan_date"],
    }


@app.get("/api/scan/status")
def scan_status():
    return {
        "status": _state["status"],
        "status_detail": _state["status_detail"],
        "last_scan": _state["scan_date"],
        "total_scanned": _state["total_scanned"],
        "total_breakouts": len(_state["breakouts"]),
        "nifty_trend": _state["nifty_trend"],
        "dl_done": _state["dl_done"],
        "dl_total": _state["dl_total"],
        "error": _state["error"],
    }


@app.get("/api/data/cache")
def data_cache_info():
    """Show the local Bhavcopy cache statistics."""
    return cache_stats()


@app.get("/api/breakouts/today")
def today(
    strength: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
):
    return _apply_filters(_state["breakouts"], strength, exchange, sector)


@app.get("/api/breakouts/yesterday")
def yesterday(
    strength: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
):
    # No persistence in quick mode — yesterday == today's results
    return _apply_filters(_state["breakouts"], strength, exchange)


@app.get("/api/breakouts/{symbol}")
def symbol_detail(symbol: str):
    match = [r for r in _state["breakouts"] if r["symbol"] == symbol.upper()]
    return match


@app.get("/api/history")
def history():
    if not _state["scan_date"]:
        return []
    return [{
        "scan_date": _state["scan_date"],
        "total_scanned": _state["total_scanned"],
        "total_breakouts": len(_state["breakouts"]),
        "nifty_trend": _state["nifty_trend"],
        "completed_at": datetime.utcnow().isoformat(),
    }]


@app.get("/api/watchlist")
def get_watchlist():
    wl = _state["watchlist"]
    result = []
    for sym in wl:
        match = next((r for r in _state["breakouts"] if r["symbol"] == sym), None)
        result.append({
            "id": hash(sym) & 0x7FFFFFFF,
            "symbol": sym,
            "exchange": match.get("exchange", "NSE") if match else "NSE",
            "name": match.get("name", sym) if match else sym,
            "notes": None,
            "added_at": datetime.utcnow().isoformat(),
            "latest_cmp": match.get("cmp") if match else None,
            "latest_pct_change": match.get("pct_change") if match else None,
            "latest_rsi": match.get("rsi") if match else None,
            "latest_strength": match.get("strength") if match else None,
        })
    return result


@app.post("/api/watchlist/add")
def add_watchlist(payload: dict):
    sym = payload.get("symbol", "").upper()
    if sym in _state["watchlist"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Already in watchlist")
    _state["watchlist"].append(sym)
    return {"symbol": sym, "status": "added"}


@app.delete("/api/watchlist/{symbol}")
def remove_watchlist(symbol: str):
    sym = symbol.upper()
    if sym in _state["watchlist"]:
        _state["watchlist"].remove(sym)
    return {"removed": sym}


@app.post("/api/scan/trigger")
def trigger_scan():
    if _state["status"] == "running":
        return {"status": "already running"}
    t = threading.Thread(target=_run_scan_thread, daemon=True)
    t.start()
    return {"status": "scan started"}


@app.post("/api/alerts/subscribe")
def subscribe(payload: dict):
    return {"status": "subscribed (quick mode — no persistence)"}


# ── Stock Evaluation endpoints ────────────────────────────────────────────────
# yfinance can hang indefinitely when Yahoo Finance rate-limits cloud IPs.
# We run it in a separate thread and enforce a hard 90-second timeout.
_eval_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="eval")

def _verdict_to_dict(verdict) -> dict:
    """Serialise a StockVerdict dataclass to a JSON-safe dict."""
    def _check(c):
        return {
            "name":      c.name,
            "value":     c.value,
            "benchmark": c.benchmark,
            "status":    c.status,
            "note":      c.note,
            "score":     c.score,
        }

    dcf = verdict.dcf
    return {
        "ticker":        verdict.ticker,
        "company_name":  verdict.company_name,
        "current_price": verdict.current_price,
        "currency":      verdict.currency,
        "sector":        verdict.sector,
        "industry":      verdict.industry,
        "overall_score": verdict.overall_score,
        "verdict":       verdict.verdict,
        "verdict_color": verdict.verdict_color,
        "category_scores": verdict.category_scores,
        "price_target_low":  verdict.price_target_low,
        "price_target_mid":  verdict.price_target_mid,
        "price_target_high": verdict.price_target_high,
        "upside_pct":    verdict.upside_pct,
        "dcf": {
            "intrinsic":        dcf.intrinsic,
            "bull":             dcf.bull,
            "bear":             dcf.bear,
            "margin_of_safety": dcf.margin_of_safety,
            "growth_rate_used": dcf.growth_rate_used,
            "method":           dcf.method,
        } if dcf else None,
        "checks": {
            cat: [_check(c) for c in chks]
            for cat, chks in (verdict.checks or {}).items()
        },
        "error": verdict.error,
    }


def _run_evaluate(sym: str, exchange: str, discount_rate: float, terminal_growth: float) -> dict:
    """Runs inside the thread-pool so we can enforce a timeout."""
    data    = fetch_stock(sym, exchange)
    verdict = evaluate_stock(sym if not hasattr(data, 'ticker') else data.ticker,
                             data,
                             discount_rate=discount_rate,
                             terminal_growth=terminal_growth)
    return _verdict_to_dict(verdict)


@app.get("/api/evaluate/{symbol}")
def evaluate_symbol(
    symbol: str,
    exchange: str = Query("NSE"),
    discount_rate: float = Query(0.10),
    terminal_growth: float = Query(0.03),
):
    """
    Run full fundamental evaluation for one stock.
    Takes ~10-30 seconds (yfinance fetches financials, history, analyst data).
    Results are cached in memory for 1 hour.
    Hard timeout: 90 seconds (Yahoo Finance may be slow from cloud servers).
    """
    sym = symbol.upper()
    try:
        future = _eval_pool.submit(_run_evaluate, sym, exchange.upper(), discount_rate, terminal_growth)
        return future.result(timeout=90)
    except FuturesTimeout:
        msg = (
            "Yahoo Finance did not respond within 90 seconds. "
            "This often happens on cloud servers. "
            "Please try again in 1–2 minutes — it usually works on the second attempt."
        )
        logger.warning("Evaluation timed out for %s", sym)
        return {"ticker": sym, "error": msg, "verdict": "N/A"}
    except Exception as e:
        logger.error("Evaluation failed for %s: %s", sym, e, exc_info=True)
        return {"ticker": sym, "error": str(e), "verdict": "N/A"}


@app.post("/api/evaluate/batch")
def evaluate_batch(payload: dict):
    """
    Evaluate multiple symbols. Body: {"symbols": ["RELIANCE","TCS"], "exchange": "NSE"}
    Runs sequentially — each call takes ~10-30s so keep lists short.
    """
    symbols  = payload.get("symbols", [])
    exchange = payload.get("exchange", "NSE").upper()
    discount_rate   = payload.get("discount_rate", 0.10)
    terminal_growth = payload.get("terminal_growth", 0.03)

    if len(symbols) > 20:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Maximum 20 symbols per batch request")

    results = []
    for sym in symbols:
        try:
            future = _eval_pool.submit(_run_evaluate, sym.upper(), exchange, discount_rate, terminal_growth)
            results.append(future.result(timeout=90))
        except FuturesTimeout:
            results.append({"ticker": sym.upper(), "error": "Timed out — Yahoo Finance slow from cloud server. Try again.", "verdict": "N/A"})
        except Exception as e:
            results.append({"ticker": sym.upper(), "error": str(e), "verdict": "N/A"})

    return results


# ── Sector endpoints ─────────────────────────────────────────────────────────

@app.get("/api/sectors/list")
def list_sectors():
    """All unique sectors with stock counts, sorted by count (Unknown last)."""
    counts: dict[str, int] = {}
    for r in _state["breakouts"]:
        sector = r.get("sector") or "Unknown"
        counts[sector] = counts.get(sector, 0) + 1

    result = [{"sector": s, "count": c} for s, c in counts.items()]
    result.sort(key=lambda x: (-x["count"] if x["sector"] != "Unknown" else 0))
    return result


@app.get("/api/sectors/stocks")
def sector_stocks(sector: str = Query(...)):
    """All breakout stocks for a given sector, sorted by strength score desc."""
    target = sector.lower().strip()
    matched = [
        r for r in _state["breakouts"]
        if (r.get("sector") or "Unknown").lower() == target
    ]
    matched.sort(key=lambda x: x.get("strength_score", 0), reverse=True)
    return matched


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    # Try to restore last scan from disk first (instant).
    # Only kick off a fresh scan when there is nothing cached.
    if not _load_results():
        logger.info("No cached results found — starting initial scan…")
        t = threading.Thread(target=_run_scan_thread, daemon=True)
        t.start()


# ── Serve built React frontend (production / Render.com) ─────────────────────
# When deployed, the Dockerfile copies frontend/dist → backend/static.
# FastAPI serves it at "/" so the whole app is one service on one port.
from fastapi.staticfiles import StaticFiles as _SF
_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/", _SF(directory=str(_static_dir), html=True), name="spa")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("quick_serve:app", host="0.0.0.0", port=port, reload=False)
