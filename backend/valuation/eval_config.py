SCORING_WEIGHTS = {
    "valuation": 0.30,
    "fundamentals": 0.35,
    "risk": 0.20,
    "future": 0.15,
}

DCF_DISCOUNT_RATE = 0.10
DCF_TERMINAL_GROWTH = 0.03
DCF_GROWTH_MIN = 0.03
DCF_GROWTH_MAX = 0.30
DCF_MARGIN_OF_SAFETY = 0.80

INDIAN_SUFFIXES = [".NS", ".BO"]

# Sector P/E benchmarks — US market
US_SECTOR_PE = {
    "Technology": 28,
    "Healthcare": 22,
    "Financial Services": 14,
    "Consumer Cyclical": 18,
    "Consumer Defensive": 20,
    "Industrials": 20,
    "Basic Materials": 15,
    "Energy": 12,
    "Utilities": 16,
    "Real Estate": 30,
    "Communication Services": 22,
    "Unknown": 20,
}

# Sector P/E benchmarks — Indian market (NSE/BSE generally trade at higher multiples)
IN_SECTOR_PE = {
    "Technology": 35,
    "Healthcare": 30,
    "Financial Services": 18,
    "Consumer Cyclical": 28,
    "Consumer Defensive": 35,
    "Industrials": 28,
    "Basic Materials": 20,
    "Energy": 15,
    "Utilities": 20,
    "Real Estate": 40,
    "Communication Services": 25,
    "Unknown": 25,
}

# Cyclicality by sector: True = cyclical (sensitive to recession)
SECTOR_CYCLICALITY = {
    "Technology": False,
    "Healthcare": False,
    "Financial Services": True,
    "Consumer Cyclical": True,
    "Consumer Defensive": False,
    "Industrials": True,
    "Basic Materials": True,
    "Energy": True,
    "Utilities": False,
    "Real Estate": True,
    "Communication Services": False,
    "Unknown": False,
}

# Sectors with elevated regulatory risk
HIGH_REGULATORY_SECTORS = {"Healthcare", "Financial Services", "Energy", "Utilities", "Communication Services"}

# Valuation thresholds
PE_BAND = 0.15         # ±15% of sector avg = yellow; beyond = green/red
PEG_GREEN = 1.0
PEG_YELLOW = 2.0
PB_GREEN = 2.0
PB_YELLOW = 4.0
EV_EBITDA_GREEN = 10
EV_EBITDA_YELLOW = 20
FCF_YIELD_GREEN = 0.05
FCF_YIELD_YELLOW = 0.02
DCF_BAND = 0.20        # ±20% of intrinsic = yellow
HIST_PE_BAND = 0.10    # ±10% of own 5yr avg

# Fundamental thresholds
GROSS_MARGIN_GREEN = 0.40
GROSS_MARGIN_YELLOW = 0.20
OP_MARGIN_GREEN = 0.15
OP_MARGIN_YELLOW = 0.05
NET_MARGIN_GREEN = 0.10
NET_MARGIN_YELLOW = 0.03
ROE_GREEN = 0.15
ROE_YELLOW = 0.08
ROIC_WACC_PROXY = 0.10  # assume 10% WACC when not computable
DE_GREEN = 0.50
DE_YELLOW = 1.50
INTEREST_COVERAGE_GREEN = 5.0
INTEREST_COVERAGE_YELLOW = 2.0
CASH_DEBT_GREEN = 1.0
CASH_DEBT_YELLOW = 0.30
REVENUE_GROWTH_GREEN = 0.10
REVENUE_GROWTH_YELLOW = 0.0
EPS_GROWTH_GREEN = 0.10
EPS_GROWTH_YELLOW = 0.0

# Risk thresholds
EARNINGS_CV_GREEN = 0.25  # coefficient of variation
EARNINGS_CV_YELLOW = 0.50
DEBT_CAGR_RATIO_GREEN = 1.5  # debt CAGR / revenue CAGR
DEBT_CAGR_RATIO_YELLOW = 2.0

# Future / technicals
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
ANALYST_CONSENSUS_GREEN = 2.5  # 1=Strong Buy … 5=Strong Sell
ANALYST_CONSENSUS_YELLOW = 3.5

# Scoring verdict thresholds
VERDICT_BUY_SCORE = 70
VERDICT_HOLD_SCORE = 50
VERDICT_BUY_MIN_RISK = 0.60  # risk category score must be at least this for BUY
