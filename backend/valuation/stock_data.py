"""
Thin yfinance wrapper for fundamental evaluation.
No Streamlit dependency — uses a simple in-process dict cache (TTL 1 hour).

Cloud note: Yahoo Finance sometimes blocks cloud server IPs.
We use curl_cffi with Chrome impersonation to maximise success rate.
"""
import time
import logging
import pandas as pd
import yfinance as yf

from valuation.eval_config import INDIAN_SUFFIXES

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, "StockData"]] = {}   # ticker → (fetched_at, obj)
_CACHE_TTL = 3600  # 1 hour


def _make_yf_session():
    """
    Return the best available HTTP session for yfinance.
    curl_cffi with Chrome impersonation bypasses Yahoo Finance bot-detection
    better than plain requests, especially from cloud servers.
    """
    try:
        from curl_cffi import requests as cffi_req
        session = cffi_req.Session(impersonate="chrome120")
        logger.debug("yfinance session: curl_cffi / chrome120")
        return session
    except Exception as exc:
        logger.warning("curl_cffi unavailable (%s) — falling back to requests with browser UA", exc)

    try:
        import requests as std_req
        s = std_req.Session()
        s.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        })
        return s
    except Exception:
        return None


def _ticker_with_suffix(symbol: str, exchange: str) -> str:
    """Return Yahoo Finance ticker string for a given symbol + exchange."""
    symbol = symbol.upper().strip()
    if exchange.upper() == "NSE":
        return f"{symbol}.NS"
    elif exchange.upper() == "BSE":
        return f"{symbol}.BO"
    else:
        return symbol  # US stocks — no suffix


class StockData:
    """Thin wrapper around yf.Ticker. Lazy-loads and caches each data type."""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        session = _make_yf_session()
        self._yf = yf.Ticker(self.ticker, session=session) if session else yf.Ticker(self.ticker)
        self._info: dict | None = None
        self._financials: dict | None = None
        self._history: pd.DataFrame | None = None
        self._analyst: dict | None = None

    def get_info(self) -> dict:
        if self._info is None:
            self._info = self._fetch_info()
        return self._info

    def get_financials(self) -> dict:
        if self._financials is None:
            self._financials = self._fetch_financials()
        return self._financials

    def get_history(self, period: str = "5y") -> pd.DataFrame:
        if self._history is None:
            self._history = self._fetch_history(period)
        return self._history

    def get_analyst_targets(self) -> dict:
        if self._analyst is None:
            self._analyst = self._fetch_analyst()
        return self._analyst

    def _fetch_info(self) -> dict:
        try:
            info = self._yf.info or {}
            if not info:
                logger.warning("yfinance returned empty info for %s — Yahoo Finance may be blocking this server's IP", self.ticker)
            else:
                logger.info("yfinance info OK for %s (%d keys)", self.ticker, len(info))
            return info
        except Exception as e:
            logger.warning("yfinance info fetch failed for %s: %s", self.ticker, e)
            return {}

    def _fetch_financials(self) -> dict:
        result = {"income_stmt": None, "balance_sheet": None, "cashflow": None}
        try:
            result["income_stmt"] = self._yf.financials
        except Exception:
            pass
        try:
            result["balance_sheet"] = self._yf.balance_sheet
        except Exception:
            pass
        try:
            result["cashflow"] = self._yf.cashflow
        except Exception:
            pass
        return result

    def _fetch_history(self, period: str) -> pd.DataFrame:
        try:
            df = self._yf.history(period=period)
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def _fetch_analyst(self) -> dict:
        info = self.get_info()
        return {
            "recommendationMean": info.get("recommendationMean"),
            "targetMeanPrice":    info.get("targetMeanPrice"),
            "targetHighPrice":    info.get("targetHighPrice"),
            "targetLowPrice":     info.get("targetLowPrice"),
            "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
        }


def fetch_stock(symbol: str, exchange: str = "NSE") -> StockData:
    """
    Fetch (or return cached) StockData for a symbol.
    Cache is per Yahoo ticker string, TTL = 1 hour.
    """
    ticker = _ticker_with_suffix(symbol, exchange)
    now = time.time()

    if ticker in _CACHE:
        fetched_at, cached = _CACHE[ticker]
        if now - fetched_at < _CACHE_TTL:
            return cached

    logger.info("Fetching fundamental data for %s…", ticker)
    sd = StockData(ticker)
    sd.get_info()
    sd.get_financials()
    sd.get_history("5y")
    sd.get_analyst_targets()

    _CACHE[ticker] = (now, sd)
    return sd


def clear_cache():
    """Evict all cached entries."""
    _CACHE.clear()
