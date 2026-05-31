"""
nse_universe.py

Downloads the complete NSE equity master file (EQUITY_L.csv) and combines
it with the sector map from nse_sector_fetcher to produce a full universe
of all NSE-listed stocks — completely independent of the breakout scanner.

Data sources
------------
  EQUITY_L.csv  — NSE archives (all ~1,800+ EQ-series stocks with ISIN)
  Sector map    — nse_sector_fetcher.build_sector_map() (NSE index CSVs)
  Static info   — data_fetcher.NSE_COMPANY_INFO (~360 stocks, name + sector)

Cache
-----
  Stored at backend/nse_universe_cache.json, refreshed every 24 hours.
"""

import csv
import io
import json
import logging
import time
import threading
from pathlib import Path

import requests

logger      = logging.getLogger(__name__)
CACHE_FILE  = Path(__file__).parent / "nse_universe_cache.json"
CACHE_MAX   = 24 * 3600   # 24 hours

_EQUITY_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
_HEADERS    = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer":         "https://www.nseindia.com/",
    "Accept-Language": "en-US,en;q=0.9",
}

_lock           = threading.Lock()
_universe_cache: list[dict] | None = None


def _download_equity_list() -> list[dict]:
    """
    Download EQUITY_L.csv from NSE archives.
    Returns list of {symbol, name, isin} for EQ-series stocks only.
    """
    logger.info("Downloading EQUITY_L.csv from NSE archives…")
    resp = requests.get(_EQUITY_URL, headers=_HEADERS, timeout=20)
    resp.raise_for_status()

    # Columns: SYMBOL, NAME OF COMPANY, SERIES, DATE OF LISTING,
    #          PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE
    stocks = []
    reader = csv.reader(io.StringIO(resp.text.strip()))
    for i, row in enumerate(reader):
        if i == 0:
            continue                    # header
        if len(row) < 7:
            continue
        symbol = row[0].strip()
        name   = row[1].strip()
        series = row[2].strip().upper()
        isin   = row[6].strip()
        if series != "EQ" or not symbol:
            continue                    # skip BE, SM, ETFs, etc.
        stocks.append({"symbol": symbol, "name": name, "isin": isin})

    logger.info("EQUITY_L.csv: %d EQ-series stocks parsed", len(stocks))
    return stocks


def fetch_universe(force_refresh: bool = False) -> list[dict]:
    """
    Return the full NSE stock universe as a sorted list of dicts:
      {symbol, name, isin, sector}

    Uses disk cache; re-downloads after 24 hours.
    Thread-safe.
    """
    global _universe_cache

    # Fast path — in-memory cache
    if not force_refresh and _universe_cache is not None:
        return _universe_cache

    with _lock:
        # Double-checked locking
        if not force_refresh and _universe_cache is not None:
            return _universe_cache

        # Try disk cache
        if not force_refresh and CACHE_FILE.exists():
            try:
                age = time.time() - CACHE_FILE.stat().st_mtime
                if age < CACHE_MAX:
                    with open(CACHE_FILE, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    _universe_cache = data
                    logger.info("NSE universe: loaded %d stocks from disk cache", len(data))
                    return data
            except Exception:
                pass

        # Build fresh
        try:
            raw = _download_equity_list()
        except Exception as exc:
            logger.error("EQUITY_L.csv download failed: %s", exc)
            # Return stale cache if any
            if CACHE_FILE.exists():
                try:
                    with open(CACHE_FILE, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    _universe_cache = data
                    logger.warning("Using stale universe cache (%d stocks)", len(data))
                    return data
                except Exception:
                    pass
            _universe_cache = []
            return []

        # Load sector maps
        try:
            from nse_sector_fetcher import build_sector_map
            sector_map = build_sector_map()
        except Exception as exc:
            logger.warning("Sector map unavailable: %s", exc)
            sector_map = {}

        try:
            from data_fetcher import NSE_COMPANY_INFO
        except Exception:
            NSE_COMPANY_INFO = {}

        # Enrich each stock with sector
        result = []
        for s in raw:
            sym = s["symbol"]
            if sym in NSE_COMPANY_INFO:
                full_name, sector = NSE_COMPANY_INFO[sym]
            else:
                full_name = s["name"]
                sector    = sector_map.get(sym, "Unknown")
            result.append({
                "symbol": sym,
                "name":   full_name,
                "isin":   s["isin"],
                "sector": sector,
            })

        # Sort alphabetically
        result.sort(key=lambda x: x["symbol"])

        # Save to disk
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as fh:
                json.dump(result, fh)
        except Exception as exc:
            logger.warning("Could not save universe cache: %s", exc)

        known = sum(1 for r in result if r["sector"] != "Unknown")
        logger.info(
            "NSE universe built: %d total stocks, %d with known sector",
            len(result), known,
        )
        _universe_cache = result
        return result
