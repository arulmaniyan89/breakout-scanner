import pandas as pd
import numpy as np


def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI using Wilder's EMA (exponential moving average)."""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_sma(prices: pd.Series, window: int) -> pd.Series:
    return prices.rolling(window=window).mean()


def get_technical_signals(history: pd.DataFrame) -> dict:
    """
    Returns a dict with:
      rsi_current, sma50, sma200, price_vs_50ma, price_vs_200ma,
      golden_cross, death_cross, status ("green"|"yellow"|"red"|"na")
    """
    if history is None or history.empty or len(history) < 50:
        return {"status": "na"}

    close = history["Close"].dropna()
    if len(close) < 50:
        return {"status": "na"}

    rsi_series = compute_rsi(close)
    sma50 = compute_sma(close, 50)
    sma200 = compute_sma(close, 200)

    rsi_cur = float(rsi_series.iloc[-1]) if not rsi_series.empty else None
    price = float(close.iloc[-1])
    sma50_cur = float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else None
    sma200_cur = float(sma200.iloc[-1]) if len(close) >= 200 and not pd.isna(sma200.iloc[-1]) else None

    golden_cross = False
    death_cross = False
    if sma50_cur and sma200_cur:
        # Check if 50MA crossed above 200MA in last 20 days
        recent_sma50 = sma50.iloc[-20:]
        recent_sma200 = sma200.iloc[-20:].reindex(recent_sma50.index)
        diff = recent_sma50 - recent_sma200
        if diff.iloc[-1] > 0 and (diff < 0).any():
            golden_cross = True
        elif diff.iloc[-1] < 0 and (diff > 0).any():
            death_cross = True

    # Determine overall technical status
    signals_positive = 0
    signals_total = 0

    if rsi_cur is not None:
        signals_total += 1
        if rsi_cur < 70:   # not overbought
            signals_positive += 1

    if sma50_cur is not None:
        signals_total += 1
        if price > sma50_cur:
            signals_positive += 1

    if sma200_cur is not None:
        signals_total += 1
        if price > sma200_cur:
            signals_positive += 1

    if signals_total == 0:
        status = "na"
    elif signals_positive / signals_total >= 0.67:
        status = "green"
    elif signals_positive / signals_total >= 0.33:
        status = "yellow"
    else:
        status = "red"

    return {
        "rsi_current": rsi_cur,
        "sma50": sma50_cur,
        "sma200": sma200_cur,
        "price": price,
        "price_vs_50ma_pct": ((price / sma50_cur) - 1) if sma50_cur else None,
        "price_vs_200ma_pct": ((price / sma200_cur) - 1) if sma200_cur else None,
        "golden_cross": golden_cross,
        "death_cross": death_cross,
        "status": status,
        "rsi_series": rsi_series,
        "sma50_series": sma50,
        "sma200_series": sma200,
    }
