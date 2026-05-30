"""
nse_sector_fetcher.py

Downloads NSE official index constituent CSV files to build a comprehensive
symbol → sector mapping for ALL NSE-listed stocks.

NSE publishes free CSV files at:
  https://archives.nseindia.com/content/indices/ind_nifty500list.csv
  (and similar files for every sector index and broad market index)

Each CSV has columns:  Company Name, Industry, Symbol, Series, ISIN Code

By combining the Nifty 500, Midcap 150, Smallcap 250, Microcap 250 and all
sector-specific indices we can classify 1,000–1,500 NSE stocks with official
NSE industry labels.  Results are cached on disk (refreshed weekly).
"""
import csv
import io
import json
import logging
import threading
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

CACHE_FILE    = Path(__file__).parent / "nse_sector_cache.json"
CACHE_MAX_AGE = 7 * 86400   # 7 days in seconds

# ── NSE Industry string → display sector name ─────────────────────────────────
INDUSTRY_TO_SECTOR: dict[str, str] = {
    # Financial Services
    "FINANCIAL SERVICES":                    "Financial Services",
    "BANKS":                                 "Financial Services",
    "INSURANCE":                             "Financial Services",
    "FINANCIAL SERVICES-OTHERS":             "Financial Services",
    "CAPITAL MARKETS":                       "Financial Services",
    "HOUSING FINANCE COMPANY":               "Financial Services",
    "NBFC":                                  "Financial Services",
    "MICROFINANCE INSTITUTIONS":             "Financial Services",
    # Information Technology
    "IT":                                    "Information Technology",
    "INFORMATION TECHNOLOGY":                "Information Technology",
    "COMPUTERS - SOFTWARE":                  "Information Technology",
    "SOFTWARE":                              "Information Technology",
    "IT - HARDWARE":                         "Information Technology",
    "INFORMATION TECHNOLOGY - OTHER":        "Information Technology",
    # Pharmaceuticals
    "PHARMA":                                "Pharmaceuticals",
    "PHARMACEUTICALS":                       "Pharmaceuticals",
    "PHARMACEUTICALS & BIOTECHNOLOGY":       "Pharmaceuticals",
    "BIOTECHNOLOGY":                         "Pharmaceuticals",
    # Healthcare
    "HOSPITAL & DIAGNOSTIC CENTRES":         "Healthcare",
    "HEALTHCARE SERVICES":                   "Healthcare",
    "HEALTH CARE":                           "Healthcare",
    "HEALTHCARE":                            "Healthcare",
    # Automobile
    "AUTOMOBILE":                            "Automobile",
    "AUTO COMPONENTS":                       "Automobile",
    "AUTOMOBILE AND AUTO COMPONENTS":        "Automobile",
    "AUTOMOBILES":                           "Automobile",
    # FMCG
    "CONSUMER GOODS":                        "FMCG",
    "FMCG":                                  "FMCG",
    "FAST MOVING CONSUMER GOODS":            "FMCG",
    "FOOD & BEVERAGES":                      "FMCG",
    "AGRICULTURE":                           "FMCG",
    "FOOD PRODUCTS":                         "FMCG",
    "BEVERAGES":                             "FMCG",
    "SUGAR":                                 "FMCG",
    # Metals & Mining
    "METALS & MINING":                       "Metals & Mining",
    "METALS":                                "Metals & Mining",
    "MINING":                                "Metals & Mining",
    "IRON & STEEL":                          "Metals & Mining",
    "ALUMINIUM":                             "Metals & Mining",
    "STEEL":                                 "Metals & Mining",
    "NON FERROUS METALS":                    "Metals & Mining",
    "FERROUS METALS":                        "Metals & Mining",
    # Media & Entertainment
    "MEDIA & ENTERTAINMENT":                 "Media & Entertainment",
    "MEDIA":                                 "Media & Entertainment",
    "ENTERTAINMENT":                         "Media & Entertainment",
    "PRINTING & PUBLICATION":                "Media & Entertainment",
    # Real Estate
    "REALTY":                                "Real Estate",
    "REAL ESTATE":                           "Real Estate",
    # Capital Goods / Engineering
    "CONSTRUCTION":                          "Capital Goods",
    "ENGINEERING":                           "Capital Goods",
    "CAPITAL GOODS":                         "Capital Goods",
    "INDUSTRIAL MANUFACTURING":              "Capital Goods",
    "INDUSTRIAL PRODUCTS":                   "Capital Goods",
    # Defence
    "DEFENCE":                               "Defence & Aerospace",
    "AEROSPACE & DEFENCE":                   "Defence & Aerospace",
    # Cement & Construction
    "CONSTRUCTION MATERIALS":               "Cement & Construction",
    "CEMENT":                                "Cement & Construction",
    "CEMENT & CONSTRUCTION MATERIALS":      "Cement & Construction",
    # Energy
    "ENERGY":                                "Energy",
    "OIL & GAS":                             "Energy",
    "OIL AND GAS":                           "Energy",
    "RENEWABLE ENERGY":                      "Energy",
    # Power
    "POWER":                                 "Power",
    "UTILITIES":                             "Power",
    # Chemicals
    "CHEMICALS":                             "Chemicals",
    "SPECIALTY CHEMICALS":                   "Chemicals",
    "FERTILISERS & PESTICIDES":              "Chemicals",
    "AGROCHEMICALS":                         "Chemicals",
    "PETROCHEMICALS":                        "Chemicals",
    "COMMODITY CHEMICALS":                   "Chemicals",
    # Telecommunication
    "TELECOM":                               "Telecommunication",
    "TELECOMMUNICATION":                     "Telecommunication",
    # Textiles
    "TEXTILES":                              "Textiles",
    "TEXTILE":                               "Textiles",
    "TEXTILE PRODUCTS":                      "Textiles",
    "APPARELS & ACCESSORIES":               "Textiles",
    "YARN":                                  "Textiles",
    # Consumer Electronics
    "CONSUMER DURABLES":                     "Consumer Electronics",
    "HOUSEHOLD APPLIANCES":                  "Consumer Electronics",
    "CONSUMER ELECTRONICS":                  "Consumer Electronics",
    # Retail
    "RETAIL":                                "Retail",
    "GEMS JEWELLERY AND WATCHES":            "Retail",
    "TRADING":                               "Retail",
    "FOOTWEAR":                              "Retail",
    # Logistics
    "LOGISTICS":                             "Logistics",
    "TRANSPORTATION":                        "Logistics",
    "PORTS":                                 "Logistics",
    "SHIPPING":                              "Logistics",
    "RAILWAYS":                              "Logistics",
    # Consumer Discretionary
    "CONSUMER DISCRETIONARY":               "Consumer Discretionary",
    "HOTEL":                                 "Consumer Discretionary",
    "RESTAURANTS":                           "Consumer Discretionary",
    "LEISURE & ENTERTAINMENT":               "Consumer Discretionary",
    "TRAVEL & TOURISM":                      "Consumer Discretionary",
    # Services
    "SERVICES":                              "Services",
    "EDUCATIONAL SERVICES":                  "Services",
    "INFRASTRUCTURE INVESTMENT TRUSTS":      "Services",
    # Diversified
    "DIVERSIFIED":                           "Diversified",
    "CONGLOMERATE":                          "Diversified",
    "FOREST MATERIALS":                      "Diversified",
    "PAPER & FOREST PRODUCTS":               "Diversified",
    # Miscellaneous Capital Goods
    "GLASS":                                 "Capital Goods",
    "PACKAGING":                             "Capital Goods",
    "RUBBER":                                "Capital Goods",
    "PLASTICS":                              "Capital Goods",
    "CERAMICS":                              "Capital Goods",
}

# ── Index CSV files to try (broadest / most important first) ──────────────────
# NSE archives: https://archives.nseindia.com/content/indices/<name>.csv
INDEX_FILES = [
    # Broad market indices (most coverage, include Industry column)
    "ind_nifty500list",
    "ind_niftymidcap150list",
    "ind_niftysmallcap250list",
    "ind_niftymicrocap250list",
    "ind_niftylargemidcap250list",
    "ind_niftyTotalMarketList",        # covers ~1750 eligible NSE stocks
    "ind_nifty1000list",               # top 1000 if available
    # Sector indices (capture additional stocks not in broad lists)
    "ind_niftybanklist",
    "ind_niftyfinancialserviceslist",
    "ind_niftyitlist",
    "ind_niftypharmalist",
    "ind_niftyautolist",
    "ind_niftyfmcglist",
    "ind_niftymetallist",
    "ind_niftyrealtylist",
    "ind_niftyenergylist",
    "ind_niftyinfrastructurelist",
    "ind_niftyhealthcarelist",
    "ind_niftymedialist",
    "ind_niftycommoditieslist",
    "ind_niftyoilandgaslist",
    "ind_niftycpse",
    "ind_niftypsubanklist",
    "ind_niftydefencelist",
    "ind_niftytransportationlist",
    "ind_niftyhousfinancialslist",
]

_BASE_URL = "https://archives.nseindia.com/content/indices/{}.csv"
_HEADERS  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer":         "https://www.nseindia.com/",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept":          "text/html,application/xhtml+xml,*/*",
}
_TIMEOUT = 15

_lock    = threading.Lock()


def _parse_index_csv(text: str) -> dict[str, str]:
    """
    Parse an NSE index constituent CSV.
    Expected columns: Company Name, Industry, Symbol, Series, ISIN Code
    Returns dict[symbol → sector].
    """
    result: dict[str, str] = {}
    try:
        reader = csv.reader(io.StringIO(text.strip()))
        for i, row in enumerate(reader):
            if i == 0:
                continue                # skip header row
            if len(row) < 3:
                continue
            industry = row[1].strip().upper()
            symbol   = row[2].strip()
            if not symbol or not industry:
                continue
            sector = INDUSTRY_TO_SECTOR.get(industry)
            if sector:
                result[symbol] = sector
    except Exception as exc:
        logger.debug("CSV parse error: %s", exc)
    return result


def _fetch_one(index_name: str) -> dict[str, str]:
    """Download and parse one NSE index CSV.  Returns {} on any failure."""
    url = _BASE_URL.format(index_name.strip())
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        if resp.status_code == 200 and len(resp.text) > 100:
            data = _parse_index_csv(resp.text)
            if data:
                logger.info("  %-45s → %d symbols", index_name, len(data))
            return data
        logger.debug("  %-45s → HTTP %d (skipped)", index_name, resp.status_code)
    except Exception as exc:
        logger.debug("  %-45s → failed: %s", index_name, exc)
    return {}


def build_sector_map(force_refresh: bool = False) -> dict[str, str]:
    """
    Build a comprehensive symbol→sector map by downloading NSE index CSV files.

    Strategy:
      1. Return cached result if it exists and is < 7 days old.
      2. Download INDEX_FILES (broad → sector-specific) combining all results.
         First classification wins (broad indices take priority).
      3. Cache the result to disk.

    Returns dict[symbol → sector_name].  Empty dict on total failure.
    """
    with _lock:
        # 1. Try cache
        if not force_refresh and CACHE_FILE.exists():
            try:
                age = time.time() - CACHE_FILE.stat().st_mtime
                if age < CACHE_MAX_AGE:
                    with open(CACHE_FILE, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    logger.info(
                        "NSE sector map loaded from cache: %d symbols in %d sectors",
                        len(data), len(set(data.values())),
                    )
                    return data
            except Exception:
                pass

        # 2. Download
        logger.info("Downloading NSE sector map from archives.nseindia.com …")
        sector_map: dict[str, str] = {}

        for idx in INDEX_FILES:
            partial = _fetch_one(idx)
            for sym, sec in partial.items():
                if sym not in sector_map:   # first match wins
                    sector_map[sym] = sec

        logger.info(
            "NSE sector map complete: %d symbols across %d sectors",
            len(sector_map), len(set(sector_map.values())) if sector_map else 0,
        )

        # 3. Save to cache
        if sector_map:
            try:
                CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(CACHE_FILE, "w", encoding="utf-8") as fh:
                    json.dump(sector_map, fh)
            except Exception as exc:
                logger.warning("Could not save sector cache: %s", exc)
        else:
            logger.warning(
                "NSE sector map: no data downloaded — "
                "all index CSV files were inaccessible. "
                "Falling back to static NSE_COMPANY_INFO."
            )

        return sector_map
