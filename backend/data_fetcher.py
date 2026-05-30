"""
Data layer for the Breakout Scanner.

Primary OHLCV source : NSE Bhavcopy (official daily CSV from NSE archives)
Fallback / metadata  : yfinance (Nifty trend + company names/sectors)

Why Bhavcopy over yfinance?
  - Official NSE source — same data shown on nseindia.com
  - Covers all ~1800 NSE equity stocks (not just our hardcoded list)
  - No rate-limiting / bot-detection issues
  - Cached locally — subsequent runs are near-instant
  - Transparent: each daily file is a plain CSV you can inspect
"""
import logging
from typing import Optional

import pandas as pd
import yfinance as yf

from nse_bhavcopy import build_all_ohlcv, symbols_list

logger = logging.getLogger(__name__)

NIFTY_INDEX = "^NSEI"


# ─── Static company metadata ─────────────────────────────────────────────────
# Name + sector for the most common NSE stocks.
# For symbols not listed here we fall back to yfinance info (cached in memory).
# Sector names match the FilterBar.jsx SECTORS list where possible.

NSE_COMPANY_INFO: dict[str, tuple[str, str]] = {
    # (Company Name, Sector)
    "RELIANCE":    ("Reliance Industries Ltd",                     "Energy"),
    "TCS":         ("Tata Consultancy Services Ltd",               "Information Technology"),
    "HDFCBANK":    ("HDFC Bank Ltd",                              "Financial Services"),
    "INFY":        ("Infosys Ltd",                                "Information Technology"),
    "ICICIBANK":   ("ICICI Bank Ltd",                             "Financial Services"),
    "HINDUNILVR":  ("Hindustan Unilever Ltd",                     "FMCG"),
    "ITC":         ("ITC Ltd",                                    "FMCG"),
    "SBIN":        ("State Bank of India",                        "Financial Services"),
    "BHARTIARTL":  ("Bharti Airtel Ltd",                          "Telecommunication"),
    "KOTAKBANK":   ("Kotak Mahindra Bank Ltd",                    "Financial Services"),
    "LT":          ("Larsen & Toubro Ltd",                        "Capital Goods"),
    "AXISBANK":    ("Axis Bank Ltd",                              "Financial Services"),
    "ASIANPAINT":  ("Asian Paints Ltd",                           "Consumer Discretionary"),
    "MARUTI":      ("Maruti Suzuki India Ltd",                    "Automobile"),
    "TITAN":       ("Titan Company Ltd",                          "Consumer Discretionary"),
    "SUNPHARMA":   ("Sun Pharmaceutical Industries Ltd",          "Pharmaceuticals"),
    "BAJFINANCE":  ("Bajaj Finance Ltd",                          "Financial Services"),
    "HCLTECH":     ("HCL Technologies Ltd",                       "Information Technology"),
    "WIPRO":       ("Wipro Ltd",                                  "Information Technology"),
    "ULTRACEMCO":  ("UltraTech Cement Ltd",                       "Cement & Construction"),
    "NESTLEIND":   ("Nestle India Ltd",                           "FMCG"),
    "POWERGRID":   ("Power Grid Corporation of India Ltd",        "Power"),
    "NTPC":        ("NTPC Ltd",                                   "Power"),
    "TECHM":       ("Tech Mahindra Ltd",                          "Information Technology"),
    "DRREDDY":     ("Dr. Reddy's Laboratories Ltd",               "Pharmaceuticals"),
    "CIPLA":       ("Cipla Ltd",                                  "Pharmaceuticals"),
    "BAJAJFINSV":  ("Bajaj Finserv Ltd",                          "Financial Services"),
    "DIVISLAB":    ("Divi's Laboratories Ltd",                    "Pharmaceuticals"),
    "BRITANNIA":   ("Britannia Industries Ltd",                   "FMCG"),
    "GRASIM":      ("Grasim Industries Ltd",                      "Diversified"),
    "ADANIPORTS":  ("Adani Ports and SEZ Ltd",                    "Infrastructure"),
    "HINDALCO":    ("Hindalco Industries Ltd",                    "Metals & Mining"),
    "JSWSTEEL":    ("JSW Steel Ltd",                              "Metals & Mining"),
    "COALINDIA":   ("Coal India Ltd",                             "Metals & Mining"),
    "TATACONSUM":  ("Tata Consumer Products Ltd",                 "FMCG"),
    "TATASTEEL":   ("Tata Steel Ltd",                             "Metals & Mining"),
    "BPCL":        ("Bharat Petroleum Corporation Ltd",           "Energy"),
    "ONGC":        ("Oil & Natural Gas Corporation Ltd",          "Energy"),
    "IOC":         ("Indian Oil Corporation Ltd",                 "Energy"),
    "HDFCLIFE":    ("HDFC Life Insurance Company Ltd",            "Financial Services"),
    "SBILIFE":     ("SBI Life Insurance Company Ltd",             "Financial Services"),
    "APOLLOHOSP":  ("Apollo Hospitals Enterprise Ltd",            "Healthcare"),
    "PIDILITIND":  ("Pidilite Industries Ltd",                    "Chemicals"),
    "DMART":       ("Avenue Supermarts Ltd",                      "Retail"),
    "DABUR":       ("Dabur India Ltd",                            "FMCG"),
    "HAVELLS":     ("Havells India Ltd",                          "Consumer Electronics"),
    "MARICO":      ("Marico Ltd",                                 "FMCG"),
    "COLPAL":      ("Colgate-Palmolive (India) Ltd",              "FMCG"),
    "GODREJCP":    ("Godrej Consumer Products Ltd",               "FMCG"),
    "TATAPOWER":   ("Tata Power Company Ltd",                     "Power"),
    "IRCTC":       ("Indian Railway Catering & Tourism Corp Ltd", "Services"),
    "HAL":         ("Hindustan Aeronautics Ltd",                  "Defence & Aerospace"),
    "BEL":         ("Bharat Electronics Ltd",                     "Defence & Aerospace"),
    "BHEL":        ("Bharat Heavy Electricals Ltd",               "Capital Goods"),
    "SAIL":        ("Steel Authority of India Ltd",               "Metals & Mining"),
    "TATAMOTORS":  ("Tata Motors Ltd",                            "Automobile"),
    "M&M":         ("Mahindra & Mahindra Ltd",                    "Automobile"),
    "BAJAJ-AUTO":  ("Bajaj Auto Ltd",                             "Automobile"),
    "EICHERMOT":   ("Eicher Motors Ltd",                          "Automobile"),
    "HEROMOTOCO":  ("Hero MotoCorp Ltd",                          "Automobile"),
    "TVSMOTOR":    ("TVS Motor Company Ltd",                      "Automobile"),
    "ASHOKLEY":    ("Ashok Leyland Ltd",                          "Automobile"),
    "ESCORTS":     ("Escorts Kubota Ltd",                         "Automobile"),
    "MOTHERSON":   ("Samvardhana Motherson International Ltd",    "Automobile"),
    "BALKRISIND":  ("Balkrishna Industries Ltd",                  "Automobile"),
    "BOSCHLTD":    ("Bosch Ltd",                                  "Automobile"),
    "AMBUJACEM":   ("Ambuja Cements Ltd",                         "Cement & Construction"),
    "ACC":         ("ACC Ltd",                                    "Cement & Construction"),
    "SHREECEM":    ("Shree Cement Ltd",                           "Cement & Construction"),
    "RAMCOCEM":    ("The Ramco Cements Ltd",                      "Cement & Construction"),
    "INDUSINDBK":  ("IndusInd Bank Ltd",                          "Financial Services"),
    "FEDERALBNK":  ("The Federal Bank Ltd",                       "Financial Services"),
    "BANDHANBNK":  ("Bandhan Bank Ltd",                           "Financial Services"),
    "IDFCFIRSTB":  ("IDFC First Bank Ltd",                        "Financial Services"),
    "AUBANK":      ("AU Small Finance Bank Ltd",                  "Financial Services"),
    "MUTHOOTFIN":  ("Muthoot Finance Ltd",                        "Financial Services"),
    "CHOLAFIN":    ("Cholamandalam Investment and Finance Co Ltd","Financial Services"),
    "MANAPPURAM":  ("Manappuram Finance Ltd",                     "Financial Services"),
    "LICHSGFIN":   ("LIC Housing Finance Ltd",                    "Financial Services"),
    "RECLTD":      ("REC Ltd",                                    "Financial Services"),
    "PFC":         ("Power Finance Corporation Ltd",              "Financial Services"),
    "IRFC":        ("Indian Railway Finance Corporation Ltd",     "Financial Services"),
    "HUDCO":       ("Housing & Urban Development Corporation Ltd","Financial Services"),
    "HINDZINC":    ("Hindustan Zinc Ltd",                         "Metals & Mining"),
    "VEDL":        ("Vedanta Ltd",                                "Metals & Mining"),
    "NATIONALUM":  ("National Aluminium Company Ltd",             "Metals & Mining"),
    "NMDC":        ("NMDC Ltd",                                   "Metals & Mining"),
    "MOIL":        ("MOIL Ltd",                                   "Metals & Mining"),
    "TATACHEM":    ("Tata Chemicals Ltd",                         "Chemicals"),
    "SRF":         ("SRF Ltd",                                    "Chemicals"),
    "AUROPHARMA":  ("Aurobindo Pharma Ltd",                       "Pharmaceuticals"),
    "TORNTPHARM":  ("Torrent Pharmaceuticals Ltd",                "Pharmaceuticals"),
    "ALKEM":       ("Alkem Laboratories Ltd",                     "Pharmaceuticals"),
    "IPCALAB":     ("Ipca Laboratories Ltd",                      "Pharmaceuticals"),
    "GLENMARK":    ("Glenmark Pharmaceuticals Ltd",               "Pharmaceuticals"),
    "BIOCON":      ("Biocon Ltd",                                 "Pharmaceuticals"),
    "LAURUSLABS":  ("Laurus Labs Ltd",                            "Pharmaceuticals"),
    "GRANULES":    ("Granules India Ltd",                         "Pharmaceuticals"),
    "ABBOTINDIA":  ("Abbott India Ltd",                           "Pharmaceuticals"),
    "PFIZER":      ("Pfizer Ltd",                                 "Pharmaceuticals"),
    "ZYDUSLIFE":   ("Zydus Lifesciences Ltd",                     "Pharmaceuticals"),
    "LUPIN":       ("Lupin Ltd",                                  "Pharmaceuticals"),
    "GLAXO":       ("GlaxoSmithKline Pharmaceuticals Ltd",        "Pharmaceuticals"),
    "STRIDES":     ("Strides Pharma Science Ltd",                 "Pharmaceuticals"),
    "INDIAMART":   ("IndiaMart InterMESH Ltd",                    "Information Technology"),
    "JUSTDIAL":    ("Just Dial Ltd",                              "Information Technology"),
    "NAUKRI":      ("Info Edge (India) Ltd",                      "Information Technology"),
    "MPHASIS":     ("Mphasis Ltd",                                "Information Technology"),
    "LTTS":        ("L&T Technology Services Ltd",                "Information Technology"),
    "COFORGE":     ("Coforge Ltd",                                "Information Technology"),
    "PERSISTENT":  ("Persistent Systems Ltd",                     "Information Technology"),
    "KPITTECH":    ("KPIT Technologies Ltd",                      "Information Technology"),
    "TATAELXSI":   ("Tata Elxsi Ltd",                             "Information Technology"),
    "CYIENT":      ("Cyient Ltd",                                 "Information Technology"),
    "LTIM":        ("LTIMindtree Ltd",                            "Information Technology"),
    "BIRLASOFT":   ("Birlasoft Ltd",                              "Information Technology"),
    "HEXAWARE":    ("Hexaware Technologies Ltd",                  "Information Technology"),
    "TRENT":       ("Trent Ltd",                                  "Retail"),
    "VMART":       ("V-Mart Retail Ltd",                          "Retail"),
    "DELHIVERY":   ("Delhivery Ltd",                              "Logistics"),
    "CONCOR":      ("Container Corporation of India Ltd",         "Logistics"),
    "BLUEDART":    ("Blue Dart Express Ltd",                      "Logistics"),
    "VOLTAS":      ("Voltas Ltd",                                 "Consumer Electronics"),
    "BLUESTARCO":  ("Blue Star Ltd",                              "Consumer Electronics"),
    "WHIRLPOOL":   ("Whirlpool of India Ltd",                     "Consumer Electronics"),
    "CROMPTON":    ("Crompton Greaves Consumer Electricals Ltd",  "Consumer Electronics"),
    "ORIENTELEC":  ("Orient Electric Ltd",                        "Consumer Electronics"),
    "AMBER":       ("Amber Enterprises India Ltd",                "Consumer Electronics"),
    "DIXON":       ("Dixon Technologies (India) Ltd",             "Consumer Electronics"),
    "VGUARD":      ("V-Guard Industries Ltd",                     "Consumer Electronics"),
    "CUMMINSIND":  ("Cummins India Ltd",                          "Capital Goods"),
    "THERMAX":     ("Thermax Ltd",                                "Capital Goods"),
    "SIEMENS":     ("Siemens Ltd",                                "Capital Goods"),
    "ABB":         ("ABB India Ltd",                              "Capital Goods"),
    "KEI":         ("KEI Industries Ltd",                         "Capital Goods"),
    "ASTRAL":      ("Astral Ltd",                                 "Capital Goods"),
    "SUPREMEIND":  ("Supreme Industries Ltd",                     "Capital Goods"),
    "BHEL":        ("Bharat Heavy Electricals Ltd",               "Capital Goods"),
    "KEC":         ("KEC International Ltd",                      "Capital Goods"),
    "KALPATPOWR":  ("Kalpataru Projects International Ltd",       "Capital Goods"),
    "TORNTPOWER":  ("Torrent Power Ltd",                          "Power"),
    "CESC":        ("CESC Ltd",                                   "Power"),
    "ADANIGREEN":  ("Adani Green Energy Ltd",                     "Power"),
    "ADANIPOWER":  ("Adani Power Ltd",                            "Power"),
    "OBEROIRLTY":  ("Oberoi Realty Ltd",                          "Real Estate"),
    "PRESTIGE":    ("Prestige Estates Projects Ltd",              "Real Estate"),
    "GODREJPROP":  ("Godrej Properties Ltd",                      "Real Estate"),
    "DLF":         ("DLF Ltd",                                    "Real Estate"),
    "BRIGADE":     ("Brigade Enterprises Ltd",                    "Real Estate"),
    "PHOENIXLTD":  ("The Phoenix Mills Ltd",                      "Real Estate"),
    "SOBHA":       ("Sobha Ltd",                                  "Real Estate"),
    "ICICIPRULI":  ("ICICI Prudential Life Insurance Co Ltd",     "Financial Services"),
    "HDFCAMC":    ("HDFC Asset Management Company Ltd",          "Financial Services"),
    "ICICIGI":     ("ICICI Lombard General Insurance Co Ltd",     "Financial Services"),
    "ANGELONE":    ("Angel One Ltd",                              "Financial Services"),
    "BSE":         ("BSE Ltd",                                    "Financial Services"),
    "MCX":         ("Multi Commodity Exchange of India Ltd",      "Financial Services"),
    "CDSL":        ("Central Depository Services (India) Ltd",    "Financial Services"),
    "PAGEIND":     ("Page Industries Ltd",                        "Textiles"),
    "JUBLFOOD":    ("Jubilant Foodworks Ltd",                     "Consumer Discretionary"),
    "DEVYANI":     ("Devyani International Ltd",                  "Consumer Discretionary"),
    "WESTLIFE":    ("Westlife Foodworld Ltd",                     "Consumer Discretionary"),
    "ZOMATO":      ("Zomato Ltd",                                 "Consumer Discretionary"),
    "IRCON":       ("IRCON International Ltd",                    "Infrastructure"),
    "GMRINFRA":    ("GMR Airports Infrastructure Ltd",            "Infrastructure"),
    "APOLLOTYRE":  ("Apollo Tyres Ltd",                           "Automobile"),
    "MRF":         ("MRF Ltd",                                    "Automobile"),
    "CEATLTD":     ("CEAT Ltd",                                   "Automobile"),
    "ATUL":        ("Atul Ltd",                                   "Chemicals"),
    "NAVINFLUOR":  ("Navin Fluorine International Ltd",           "Chemicals"),
    "ALKYLAMINE":  ("Alkyl Amines Chemicals Ltd",                 "Chemicals"),
    "FINEORG":     ("Fine Organic Industries Ltd",                "Chemicals"),
    "DEEPAKNITRITE":("Deepak Nitrite Ltd",                        "Chemicals"),
    "NOCIL":       ("NOCIL Ltd",                                  "Chemicals"),
    "FINOLEX":     ("Finolex Cables Ltd",                         "Capital Goods"),
    "MAHINDCIE":   ("Mahindra CIE Automotive Ltd",                "Automobile"),
    "BERGERPAINTS":("Berger Paints India Ltd",                    "Consumer Discretionary"),
    "ADANIENT":    ("Adani Enterprises Ltd",                      "Diversified"),
    "PAYTM":       ("One 97 Communications Ltd",                  "Financial Services"),
    "NYKAA":       ("FSN E-Commerce Ventures Ltd",                "Retail"),
    "POLICYBZR":   ("PB Fintech Ltd",                             "Financial Services"),
    "LINDEINDIA":  ("Linde India Ltd",                            "Chemicals"),
    "SAPPHIRE":    ("Sapphire Foods India Ltd",                   "Consumer Discretionary"),
    "BAJAJHLDNG":  ("Bajaj Holdings & Investment Ltd",            "Financial Services"),
    "CHOLAHLDNG":  ("Cholamandalam Financial Holdings Ltd",       "Financial Services"),
    "SUNDRMFAST":  ("Sundram Fasteners Ltd",                      "Automobile"),
    "MATRIMONY":   ("Matrimony.com Ltd",                          "Consumer Discretionary"),
    "SHOPERSTOP":  ("Shoppers Stop Ltd",                          "Retail"),
    "RELAXO":      ("Relaxo Footwears Ltd",                       "Consumer Discretionary"),
    "ABBOTINDIA":  ("Abbott India Ltd",                           "Pharmaceuticals"),
    "SANOFI":      ("Sanofi India Ltd",                           "Pharmaceuticals"),
    "MANJUSHREE":  ("Manjushree Technopack Ltd",                  "Packaging"),
    "IIFL":        ("IIFL Finance Ltd",                           "Financial Services"),
}

# In-memory cache for yfinance metadata fallback (so each symbol is only
# queried once per process lifetime)
_info_cache: dict[str, dict] = {}


# ─── Company info ─────────────────────────────────────────────────────────────

def get_company_info(symbol: str, exchange: str = "NSE", use_yfinance: bool = False) -> dict:
    """
    Return name, sector, market_cap for a symbol.

    Priority:
      1. Static NSE_COMPANY_INFO dict  (instant, ~200 major stocks)
      2. In-memory yfinance cache      (if already fetched this session)
      3. yfinance fetch                (only when use_yfinance=True — slow, avoid in bulk)
      4. Symbol name as fallback       (always succeeds)
    """
    if symbol in NSE_COMPANY_INFO:
        name, sector = NSE_COMPANY_INFO[symbol]
        return {"name": name, "sector": sector, "market_cap": 0}

    if symbol in _info_cache:
        return _info_cache[symbol]

    if use_yfinance:
        info = _yf_ticker_info(symbol, exchange)
        _info_cache[symbol] = info
        return info

    # Fast fallback — no network call, just use the symbol as the name
    return {"name": symbol, "sector": "Unknown", "market_cap": 0}


def _yf_ticker_info(symbol: str, exchange: str = "NSE") -> dict:
    suffix = ".NS" if exchange == "NSE" else ".BO"
    try:
        ticker = yf.Ticker(f"{symbol}{suffix}")
        info = ticker.info
        return {
            "name": info.get("longName") or info.get("shortName", symbol),
            "sector": info.get("sector", "Unknown"),
            "market_cap": (info.get("marketCap") or 0) / 1e7,
        }
    except Exception:
        return {"name": symbol, "sector": "Unknown", "market_cap": 0}


# ─── Nifty trend (still uses yfinance — index not in bhavcopy) ────────────────

def get_nifty_trend(sma_window: int = 50) -> bool:
    """Return True if Nifty 50 is above its 50-day SMA (uptrend)."""
    try:
        ticker = yf.Ticker(NIFTY_INDEX)
        df = ticker.history(period="3mo", interval="1d", auto_adjust=True)
        if df.empty or len(df) < sma_window:
            return True      # default to True if data unavailable
        df.index = pd.to_datetime(df.index).tz_localize(None)
        close = df["Close"]
        sma = close.rolling(sma_window).mean().iloc[-1]
        result = float(close.iloc[-1]) > float(sma)
        logger.info(
            "Nifty trend check: CMP=%.1f, SMA50=%.1f → %s",
            float(close.iloc[-1]), float(sma),
            "UPTREND" if result else "DOWNTREND",
        )
        return result
    except Exception as e:
        logger.warning("Nifty trend check failed: %s — defaulting to True", e)
        return True


# ─── Main entry point ─────────────────────────────────────────────────────────

def fetch_all_data(
    n_days: int = 385,
    progress_cb=None,
) -> tuple[dict[str, pd.DataFrame], list[tuple[str, str]]]:
    """
    Download + compile all NSE OHLCV data via Bhavcopy.

    Returns
    -------
    symbol_data : dict[symbol → OHLCV DataFrame]
    symbols     : list of (symbol, 'NSE') tuples
    """
    symbol_data = build_all_ohlcv(n_days=n_days, progress_cb=progress_cb)
    syms = symbols_list(symbol_data)
    return symbol_data, syms


# ─── Legacy compat (kept so scanner.py imports don't break) ──────────────────

def fetch_ticker_info(symbol: str, exchange: str = "NSE") -> dict:
    """Alias kept for backward compatibility with quick_serve.py."""
    return get_company_info(symbol, exchange)
