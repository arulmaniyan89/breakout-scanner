import math
from valuation.eval_config import INDIAN_SUFFIXES


def safe_get(d, key, default=None):
    """Return d[key] if present and not NaN/None, else default."""
    if d is None:
        return default
    val = d.get(key, default)
    if val is None:
        return default
    try:
        if math.isnan(val):
            return default
    except (TypeError, ValueError):
        pass
    return val


def is_indian_stock(ticker: str) -> bool:
    upper = ticker.upper()
    return any(upper.endswith(s) for s in INDIAN_SUFFIXES)


def get_currency_symbol(ticker: str) -> str:
    return "₹" if is_indian_stock(ticker) else "$"


def format_currency(value, ticker: str) -> str:
    if value is None:
        return "N/A"
    symbol = get_currency_symbol(ticker)
    try:
        if abs(value) >= 1_000_000_000_000:
            return f"{symbol}{value/1_000_000_000_000:.2f}T"
        if abs(value) >= 1_000_000_000:
            return f"{symbol}{value/1_000_000_000:.2f}B"
        if abs(value) >= 1_000_000:
            return f"{symbol}{value/1_000_000:.2f}M"
        return f"{symbol}{value:,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def format_price(value, ticker: str) -> str:
    if value is None:
        return "N/A"
    symbol = get_currency_symbol(ticker)
    try:
        return f"{symbol}{value:,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def format_pct(value) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{value * 100:.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def format_multiple(value, suffix="x") -> str:
    if value is None:
        return "N/A"
    try:
        return f"{value:.2f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"


def format_number(value, decimals=2) -> str:
    if value is None:
        return "N/A"
    try:
        if math.isnan(value):
            return "N/A"
        return f"{value:,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def cagr(start, end, years) -> float | None:
    """Compound Annual Growth Rate. Returns None on invalid inputs."""
    if start is None or end is None or years is None or years <= 0:
        return None
    try:
        if start <= 0:
            return None
        return (end / start) ** (1 / years) - 1
    except (TypeError, ValueError, ZeroDivisionError):
        return None
