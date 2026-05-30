from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Text, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class BreakoutStrength(str, enum.Enum):
    STRONG = "STRONG"       # 4/4 criteria
    MODERATE = "MODERATE"   # 3/4 criteria
    WATCHLIST = "WATCHLIST" # 2/4 criteria


class Exchange(str, enum.Enum):
    NSE = "NSE"
    BSE = "BSE"


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id = Column(Integer, primary_key=True)
    scan_date = Column(Date, nullable=False, unique=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    total_scanned = Column(Integer, default=0)
    total_breakouts = Column(Integer, default=0)
    nifty_trend = Column(Boolean)  # True = uptrend (above 50 DMA)
    status = Column(String(20), default="running")  # running/completed/failed
    error_message = Column(Text)

    stocks = relationship("BreakoutResult", back_populates="scan_run")


class BreakoutResult(Base):
    __tablename__ = "breakout_results"

    id = Column(Integer, primary_key=True)
    scan_run_id = Column(Integer, ForeignKey("scan_runs.id"), nullable=False)
    scan_date = Column(Date, nullable=False, index=True)

    symbol = Column(String(20), nullable=False)
    name = Column(String(100))
    exchange = Column(SAEnum(Exchange), nullable=False)
    sector = Column(String(60))
    market_cap = Column(Float)  # in crores

    # Price data
    cmp = Column(Float)          # current market price
    prev_close = Column(Float)
    pct_change = Column(Float)
    high_52w = Column(Float)
    low_52w = Column(Float)
    volume = Column(Float)
    avg_volume_20d = Column(Float)
    volume_ratio = Column(Float)  # volume / avg_volume_20d

    # Technical indicators
    sma50 = Column(Float)
    sma200 = Column(Float)
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)

    # Breakout criteria flags
    price_breakout = Column(Boolean, default=False)  # above 52w high or 20d high
    volume_confirmed = Column(Boolean, default=False)
    momentum_ok = Column(Boolean, default=False)
    trend_ok = Column(Boolean, default=False)
    criteria_met = Column(Integer, default=0)  # 0-4

    breakout_type = Column(String(30))  # "52W_HIGH", "200DMA", "20D_HIGH"
    strength = Column(SAEnum(BreakoutStrength))
    strength_score = Column(Float)  # 0-100

    # Suggested levels
    entry_price = Column(Float)
    stop_loss = Column(Float)
    target_price = Column(Float)

    # Post-breakout tracking
    price_after_1d = Column(Float)
    price_after_5d = Column(Float)
    price_after_20d = Column(Float)
    pct_gain_1d = Column(Float)
    pct_gain_5d = Column(Float)
    pct_gain_20d = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    scan_run = relationship("ScanRun", back_populates="stocks")

    __table_args__ = (
        UniqueConstraint("scan_run_id", "symbol", name="uq_scan_symbol"),
    )


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    exchange = Column(SAEnum(Exchange))
    name = Column(String(100))
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)

    __table_args__ = (UniqueConstraint("symbol", name="uq_watchlist_symbol"),)


class AlertSubscription(Base):
    __tablename__ = "alert_subscriptions"

    id = Column(Integer, primary_key=True)
    email = Column(String(200))
    telegram_chat_id = Column(String(50))
    whatsapp_number = Column(String(20))
    min_strength = Column(SAEnum(BreakoutStrength), default=BreakoutStrength.MODERATE)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
