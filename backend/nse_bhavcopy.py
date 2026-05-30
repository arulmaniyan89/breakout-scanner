"""
NSE Bhavcopy downloader and OHLCV compiler.

Downloads official daily Equity Bhavcopy files from NSE archives:
  https://nsearchives.nseindia.com/content/historical/EQUITIES/YYYY/MON/cmDDMONYYYYbhav.csv.zip

Each file covers all ~1800 NSE-listed equity stocks for one trading day.
Files are cached in bhavcopy_cache/ — only new dates are downloaded on
subsequent runs (warm start is near-instant).

Data quality:
  - Official NSE source (same data shown on NSE website)
  - Unadjusted prices (standard for Indian technical analysis)
  - EQ series only (excludes futures, options, SME board)
  - Zero-price rows and non-numeric values are dropped
"""
import io
import logging
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ─── Paths & constants ────────────────────────────────────────────────────────

CACHE_DIR = Path(__file__).parent / "bhavcopy_cache"
CACHE_DIR.mkdir(exist_ok=True)

# New NSE archive URL (as of 2025).  Date format: DDMMYYYY
# Example: https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_23052025.csv
BHAV_BASE = "https://nsearchives.nseindia.com/products/content"

# Browser-like headers — NSE archives check the User-Agent
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nseindia.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _bhav_url(dt: date) -> str:
    """Format: sec_bhavdata_full_DDMMYYYY.csv"""
    return f"{BHAV_BASE}/sec_bhavdata_full_{dt.day:02d}{dt.month:02d}{dt.year}.csv"


def _cache_path(dt: date) -> Path:
    return CACHE_DIR / f"{dt.isoformat()}.csv"


def _candidate_dates(n_days: int) -> list[date]:
    """Return up to n_days most-recent weekdays (newest first)."""
    today = date.today()
    out: list[date] = []
    d = today - timedelta(days=1)
    while len(out) < n_days and (today - d).days < 600:
        if d.weekday() < 5:          # Mon–Fri
            out.append(d)
        d -= timedelta(days=1)
    return out


def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    return s


# ─── Single-day download ──────────────────────────────────────────────────────

def _download_one(dt: date, session: requests.Session) -> Optional[pd.DataFrame]:
    """
    Download and parse one day's bhavcopy (plain CSV, no zip).

    URL format: sec_bhavdata_full_DDMMYYYY.csv
    Columns:    SYMBOL, SERIES, OPEN_PRICE, HIGH_PRICE, LOW_PRICE,
                CLOSE_PRICE, TTL_TRD_QNTY  (plus others we ignore)

    Returns DataFrame[symbol, open, high, low, close, volume, date]
    filtered to EQ series only, or None for holidays / download failures.
    An empty sentinel file is written for holidays to avoid re-fetching.
    """
    cache = _cache_path(dt)

    # ── Serve from cache ─────────────────────────────────────────────────────
    if cache.exists():
        if cache.stat().st_size == 0:
            return None  # holiday / no-trading-day marker
        try:
            return pd.read_csv(cache, dtype={"symbol": str})
        except Exception:
            cache.unlink(missing_ok=True)  # corrupted — re-download

    # ── Download from NSE ────────────────────────────────────────────────────
    url = _bhav_url(dt)
    try:
        resp = session.get(url, timeout=20)
        if resp.status_code == 404:
            cache.write_text("")           # holiday / no-trading-day marker
            return None
        resp.raise_for_status()

        # Plain CSV (no zip) — strip leading/trailing spaces from column names
        raw = pd.read_csv(io.StringIO(resp.text), dtype=str)
        raw.columns = [c.strip() for c in raw.columns]

        # Validate expected columns
        required = {"SYMBOL", "SERIES", "OPEN_PRICE", "HIGH_PRICE",
                    "LOW_PRICE", "CLOSE_PRICE", "TTL_TRD_QNTY"}
        if not required.issubset(set(raw.columns)):
            logger.warning(
                "Unexpected columns in bhavcopy %s: %s", dt, raw.columns.tolist()
            )
            cache.write_text("")
            return None

        # Filter to main board equity series
        eq = raw[raw["SERIES"].str.strip() == "EQ"][
            ["SYMBOL", "OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE",
             "CLOSE_PRICE", "TTL_TRD_QNTY"]
        ].copy()
        eq.columns = ["symbol", "open", "high", "low", "close", "volume"]
        eq["date"] = dt.isoformat()

        # Coerce numerics, drop bad/zero rows
        for col in ["open", "high", "low", "close", "volume"]:
            eq[col] = pd.to_numeric(eq[col], errors="coerce")
        eq = eq.dropna(subset=["open", "high", "low", "close"])
        eq = eq[eq["close"] > 0]
        eq = eq.reset_index(drop=True)

        eq.to_csv(cache, index=False)
        logger.debug("Downloaded bhavcopy %s — %d EQ rows", dt, len(eq))
        return eq

    except requests.exceptions.Timeout:
        logger.warning("Timeout downloading bhavcopy %s", dt)
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("Connection error downloading bhavcopy %s", dt)
        return None
    except Exception as e:
        logger.warning("Failed bhavcopy %s: %s", dt, e)
        return None


# ─── Main public API ──────────────────────────────────────────────────────────

def build_all_ohlcv(
    n_days: int = 385,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> dict[str, pd.DataFrame]:
    """
    Build per-symbol OHLCV DataFrames from NSE Bhavcopy archives.

    Parameters
    ----------
    n_days : int
        Calendar look-back window.  385 days ≈ 255 trading days
        (enough for 200-day SMA + some buffer).
    progress_cb : callable(downloaded_so_far, total_to_download)
        Called after each file is downloaded; useful for progress bars.

    Returns
    -------
    dict[symbol → pd.DataFrame]
        Each value has columns [open, high, low, close, volume] with a
        DatetimeIndex sorted ascending.  Only symbols with ≥ 50 rows
        are returned (scanner's own 200-row gate filters further).
    """
    dates = _candidate_dates(n_days)

    cached_dates  = [d for d in dates if _cache_path(d).exists()]
    missing_dates = [d for d in dates if not _cache_path(d).exists()]

    logger.info(
        "Bhavcopy build: %d candidate dates | %d cached | %d to download",
        len(dates), len(cached_dates), len(missing_dates),
    )

    session = _make_session()
    frames: list[pd.DataFrame] = []

    # Load already-cached days
    for d in cached_dates:
        p = _cache_path(d)
        if p.stat().st_size == 0:
            continue                          # holiday marker
        try:
            frames.append(pd.read_csv(p, dtype={"symbol": str}))
        except Exception:
            pass

    # Download missing days (newest first so recent data lands fast)
    total_missing = len(missing_dates)
    for i, d in enumerate(sorted(missing_dates, reverse=True)):
        df = _download_one(d, session)
        if df is not None and not df.empty:
            frames.append(df)
        if progress_cb:
            progress_cb(i + 1, total_missing)
        if total_missing > 0:
            time.sleep(0.12)                  # ~8 req/sec — polite rate limit

    if not frames:
        logger.error("No bhavcopy data available — check internet connection")
        return {}

    # ── Compile all days into per-symbol DataFrames ───────────────────────────
    all_data = pd.concat(frames, ignore_index=True)
    all_data["date"] = pd.to_datetime(all_data["date"])
    all_data = all_data.sort_values("date")

    symbol_data: dict[str, pd.DataFrame] = {}
    skipped = 0

    for symbol, group in all_data.groupby("symbol"):
        g = (
            group
            .set_index("date")[["open", "high", "low", "close", "volume"]]
            .copy()
        )
        g = g[~g.index.duplicated(keep="last")]  # remove duplicate date rows
        g = g.sort_index()
        g = g[g["close"] > 0].dropna(subset=["close"])  # sanity filter

        if len(g) < 50:                       # minimum history
            skipped += 1
            continue

        symbol_data[str(symbol)] = g

    logger.info(
        "Compiled OHLCV for %d NSE symbols (%d skipped — insufficient history)",
        len(symbol_data), skipped,
    )
    return symbol_data


def symbols_list(symbol_data: dict) -> list[tuple[str, str]]:
    """Return sorted list of (symbol, 'NSE') pairs from compiled data."""
    return [(s, "NSE") for s in sorted(symbol_data.keys())]


def cache_stats() -> dict:
    """Return stats about the local bhavcopy cache."""
    files = list(CACHE_DIR.glob("*.csv"))
    non_empty = [f for f in files if f.stat().st_size > 0]
    holidays  = [f for f in files if f.stat().st_size == 0]
    oldest = min((f.stem for f in non_empty), default="—")
    newest = max((f.stem for f in non_empty), default="—")
    return {
        "cached_days": len(non_empty),
        "holiday_markers": len(holidays),
        "oldest": oldest,
        "newest": newest,
        "cache_dir": str(CACHE_DIR),
    }
