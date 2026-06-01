"""
Core breakout detection logic.
Computes technical indicators and applies the 4-criteria breakout model.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd

from models import BreakoutStrength

logger = logging.getLogger(__name__)

# ─── Indicator helpers ────────────────────────────────────────────────────────

def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    return series.ewm(span=window, adjust=False).mean()


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(close: pd.Series, fast=12, slow=26, signal=9):
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_indicators(df: pd.DataFrame) -> dict:
    """Compute all required indicators from OHLCV dataframe."""
    close = df["close"]
    volume = df["volume"]

    ind = {}
    ind["sma50"] = sma(close, 50)
    ind["sma200"] = sma(close, 200)
    ind["rsi"] = compute_rsi(close, 14)
    ind["macd"], ind["macd_signal"], ind["macd_hist"] = compute_macd(close)
    ind["avg_vol_20"] = sma(volume, 20)
    ind["avg_vol_3"] = sma(volume, 3)    # recent 3-day volume avg
    ind["avg_vol_10"] = sma(volume, 10)  # prior 10-day volume avg
    ind["high_20d"] = df["high"].rolling(20, min_periods=10).max()
    ind["high_10d"] = df["high"].rolling(10, min_periods=5).max()
    ind["high_100d"] = df["high"].rolling(100, min_periods=80).max().shift(1)  # yesterday's 100d high
    ind["high_52w"] = df["high"].rolling(252, min_periods=200).max()
    ind["low_52w"] = df["low"].rolling(252, min_periods=200).min()
    # 10-day price range as % of close — measures consolidation tightness
    ind["range_10d_pct"] = (
        df["high"].rolling(10, min_periods=5).max() -
        df["low"].rolling(10, min_periods=5).min()
    ) / close * 100
    return ind


# ─── Breakout criteria ────────────────────────────────────────────────────────

@dataclass
class BreakoutAnalysis:
    symbol: str
    exchange: str

    cmp: float = 0.0
    prev_close: float = 0.0
    pct_change: float = 0.0
    high_52w: float = 0.0
    low_52w: float = 0.0
    volume: float = 0.0
    avg_volume_20d: float = 0.0
    volume_ratio: float = 0.0

    sma50: float = 0.0
    sma200: float = 0.0
    rsi: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0

    high_100d: float = 0.0

    price_breakout: bool = False
    volume_confirmed: bool = False
    momentum_ok: bool = False
    trend_ok: bool = False
    breakout_100d: bool = False   # vol > yesterday AND close > 100-day high
    criteria_met: int = 0

    breakout_type: str = ""
    strength: Optional[BreakoutStrength] = None
    strength_score: float = 0.0

    entry_price: float = 0.0
    stop_loss: float = 0.0
    target_price: float = 0.0


def analyse_stock(
    symbol: str,
    exchange: str,
    df: pd.DataFrame,
    nifty_uptrend: bool = True,
) -> Optional[BreakoutAnalysis]:
    """
    Run all 4 breakout criteria on the stock's OHLCV data.
    Returns BreakoutAnalysis if the stock qualifies (criteria_met >= 2), else None.
    """
    if df is None or len(df) < 200:
        return None

    ind = compute_indicators(df)

    # Use last completed candle (index -1 = today's; -2 = yesterday's confirmed)
    # We run at 8:45 AM before market open, so last closed bar is yesterday's.
    idx = -1
    if df["close"].iloc[idx] is None or np.isnan(df["close"].iloc[idx]):
        return None

    cmp = float(df["close"].iloc[idx])
    prev_close = float(df["close"].iloc[-2]) if len(df) >= 2 else cmp

    def safe(series, i=idx):
        v = series.iloc[i]
        return float(v) if (v is not None and not np.isnan(v)) else None

    s50 = safe(ind["sma50"])
    s200 = safe(ind["sma200"])
    rsi_val = safe(ind["rsi"])
    macd_val = safe(ind["macd"])
    macd_sig = safe(ind["macd_signal"])
    macd_hist_val = safe(ind["macd_hist"])
    avg_vol = safe(ind["avg_vol_20"])
    h20 = safe(ind["high_20d"])
    h52 = safe(ind["high_52w"])
    l52 = safe(ind["low_52w"])
    vol = float(df["volume"].iloc[idx])

    avg_vol3 = safe(ind["avg_vol_3"])
    avg_vol10 = safe(ind["avg_vol_10"])
    range_10d = safe(ind["range_10d_pct"])
    rsi_5d_ago = safe(ind["rsi"], -6)  # RSI 5 sessions ago
    h100 = safe(ind["high_100d"])      # yesterday's 100-session high

    if any(v is None for v in [s50, rsi_val, avg_vol, h52]):
        return None
    if avg_vol == 0 or prev_close == 0:
        return None

    volume_ratio = vol / avg_vol

    a = BreakoutAnalysis(
        symbol=symbol,
        exchange=exchange,
        cmp=cmp,
        prev_close=prev_close,
        pct_change=round((cmp - prev_close) / prev_close * 100, 2),
        high_52w=h52,
        low_52w=l52 or 0.0,
        volume=vol,
        avg_volume_20d=avg_vol,
        volume_ratio=round(volume_ratio, 2),
        sma50=s50,
        sma200=s200 or 0.0,
        rsi=round(rsi_val, 2),
        macd=round(macd_val, 4),
        macd_signal=round(macd_sig, 4),
        macd_hist=round(macd_hist_val, 4),
    )

    # ── Criterion A: Near Resistance (pre-breakout zone) ─────────────────────
    # Stock is within 3% BELOW a key resistance level — coiling for a move
    near_52w = h52 and (h52 * 0.97) <= cmp < h52   # within 3% below 52W high
    near_20d = h20 and (h20 * 0.97) <= cmp          # within 3% below 20D high
    near_200dma = s200 and (s200 * 0.97) <= cmp < s200 * 1.02  # near 200 DMA

    # Also accept if already just above (fresh breakout today)
    just_above_52w = h52 and cmp >= h52
    just_above_20d = h20 and cmp >= h20

    resistance_labels = []
    if near_52w or just_above_52w:   resistance_labels.append("NEAR_52W_HIGH")
    if near_200dma:                   resistance_labels.append("NEAR_200DMA")
    if near_20d or just_above_20d:   resistance_labels.append("NEAR_20D_HIGH")

    a.price_breakout = len(resistance_labels) > 0
    a.breakout_type = resistance_labels[0] if resistance_labels else ""

    # ── Criterion B: Volume Building ─────────────────────────────────────────
    # Recent 3-day avg volume is rising vs prior 10-day avg (accumulation underway)
    vol_building = (
        (avg_vol3 and avg_vol10 and avg_vol3 >= avg_vol10 * 1.15) or  # 15% higher recently
        volume_ratio >= 1.5                                              # or today's vol spike
    )
    a.volume_confirmed = bool(vol_building)

    # ── Criterion C: Momentum Building ───────────────────────────────────────
    rsi_ok = 45 <= rsi_val <= 72
    rsi_rising = rsi_5d_ago is not None and rsi_val > rsi_5d_ago  # RSI trending up
    macd_positive = macd_hist_val > 0
    macd_improving = safe(ind["macd_hist"], -3) is not None and macd_hist_val > safe(ind["macd_hist"], -3)
    a.momentum_ok = rsi_ok and rsi_rising and (macd_positive or macd_improving)

    # ── Criterion D: Trend Intact + Consolidating ────────────────────────────
    above_50dma = cmp > s50
    # Price has been consolidating — 10-day range < 8% of price (tight coil)
    consolidating = range_10d is not None and range_10d < 8.0
    a.trend_ok = above_50dma and consolidating

    # ── Criterion E: Volume expanding + Close breaking 100-day high ──────────
    # Today's volume must exceed yesterday's volume AND
    # today's close must be above the highest close of the prior 100 sessions
    prev_vol_val = float(df["volume"].iloc[-2]) if len(df) >= 2 else vol
    vol_gt_yesterday = vol > prev_vol_val
    close_above_100d = h100 is not None and cmp > h100
    a.breakout_100d = bool(vol_gt_yesterday and close_above_100d)
    a.high_100d = h100 or 0.0

    # ── Score ────────────────────────────────────────────────────────────────
    criteria = [a.price_breakout, a.volume_confirmed, a.momentum_ok, a.trend_ok, a.breakout_100d]
    a.criteria_met = sum(criteria)

    if a.criteria_met < 2:
        return None  # Need at least 2 signals to be a valid pre-breakout setup

    # Strength classification (5 criteria total — 4+ = STRONG)
    if a.criteria_met >= 4:
        a.strength = BreakoutStrength.STRONG
        a.strength_score = 90 + min(10, (volume_ratio - 2) * 2)
    elif a.criteria_met == 3:
        a.strength = BreakoutStrength.MODERATE
        a.strength_score = 60 + min(25, (volume_ratio - 1) * 5)
    elif a.criteria_met == 2:
        a.strength = BreakoutStrength.WATCHLIST
        a.strength_score = 30 + min(25, (volume_ratio - 1) * 5)
    else:  # 1 criterion — watchlist with lower score
        a.strength = BreakoutStrength.WATCHLIST
        a.strength_score = 10 + min(20, (volume_ratio - 1) * 5)

    a.strength_score = round(min(100, a.strength_score), 1)

    # ── Suggested levels ─────────────────────────────────────────────────────
    # Entry: just above the nearest resistance (anticipate the break)
    resistance = h52 if "52W" in a.breakout_type else (h20 or cmp * 1.01)
    a.entry_price = round(resistance * 1.005, 2)  # 0.5% above resistance
    a.stop_loss = round(cmp * 0.96, 2)            # 4% below current price
    a.target_price = round(a.entry_price + 2 * (a.entry_price - a.stop_loss), 2)  # 1:2 R:R

    return a


# ─── Full scan orchestration ─────────────────────────────────────────────────

def run_scan(
    symbols_data: dict[str, pd.DataFrame],
    symbol_exchange_map: dict[str, str],
    nifty_uptrend: bool = True,
) -> list[BreakoutAnalysis]:
    """
    Run breakout analysis on all provided stock data.
    symbols_data: {symbol: ohlcv_dataframe}
    symbol_exchange_map: {symbol: "NSE" or "BSE"}
    Returns sorted list of BreakoutAnalysis objects (strong first).
    """
    results = []
    for symbol, df in symbols_data.items():
        exchange = symbol_exchange_map.get(symbol, "NSE")
        try:
            analysis = analyse_stock(symbol, exchange, df, nifty_uptrend)
            if analysis:
                results.append(analysis)
        except Exception as e:
            logger.warning("Error analysing %s: %s", symbol, e)

    # Sort: Strong > Moderate > Watchlist, then by strength_score desc
    order = {BreakoutStrength.STRONG: 0, BreakoutStrength.MODERATE: 1, BreakoutStrength.WATCHLIST: 2}
    results.sort(key=lambda x: (order.get(x.strength, 3), -x.strength_score))
    return results
