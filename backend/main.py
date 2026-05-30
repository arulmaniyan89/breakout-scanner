"""
FastAPI application — Breakout Stock Scanner
"""
import logging
import os
from datetime import date, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, init_db
from models import (
    ScanRun, BreakoutResult, Watchlist, AlertSubscription,
    BreakoutStrength, Exchange,
)
from scheduler import start_scheduler, stop_scheduler, trigger_scan_now
from notifier import handle_telegram_webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Breakout Stock Scanner",
    description="NSE/BSE daily breakout screener",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()
    # Run a scan immediately if no completed scan exists for today
    from database import SessionLocal
    db = SessionLocal()
    today_scan = db.query(ScanRun).filter(
        ScanRun.scan_date == date.today(),
        ScanRun.status == "completed",
    ).first()
    db.close()
    if not today_scan:
        logger.info("No scan for today — triggering startup scan")
        trigger_scan_now()


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


# ─── Schema ───────────────────────────────────────────────────────────────────

class BreakoutResultOut(BaseModel):
    id: int
    scan_date: date
    symbol: str
    name: Optional[str]
    exchange: str
    sector: Optional[str]
    market_cap: Optional[float]
    cmp: Optional[float]
    prev_close: Optional[float]
    pct_change: Optional[float]
    high_52w: Optional[float]
    low_52w: Optional[float]
    volume: Optional[float]
    avg_volume_20d: Optional[float]
    volume_ratio: Optional[float]
    sma50: Optional[float]
    sma200: Optional[float]
    rsi: Optional[float]
    macd: Optional[float]
    macd_signal: Optional[float]
    macd_hist: Optional[float]
    price_breakout: Optional[bool]
    volume_confirmed: Optional[bool]
    momentum_ok: Optional[bool]
    trend_ok: Optional[bool]
    criteria_met: Optional[int]
    breakout_type: Optional[str]
    strength: Optional[str]
    strength_score: Optional[float]
    entry_price: Optional[float]
    stop_loss: Optional[float]
    target_price: Optional[float]
    pct_gain_1d: Optional[float]
    pct_gain_5d: Optional[float]
    pct_gain_20d: Optional[float]

    class Config:
        from_attributes = True


class WatchlistIn(BaseModel):
    symbol: str
    exchange: str = "NSE"
    name: Optional[str] = None
    notes: Optional[str] = None


class AlertSubscribeIn(BaseModel):
    email: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    whatsapp_number: Optional[str] = None
    min_strength: str = "MODERATE"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_scan_for_date(scan_date: date, db: Session) -> Optional[ScanRun]:
    return db.query(ScanRun).filter(
        ScanRun.scan_date == scan_date,
        ScanRun.status == "completed",
    ).first()


def _breakouts_query(scan_run_id: int, db: Session, strength: str = None,
                     exchange: str = None, sector: str = None):
    q = db.query(BreakoutResult).filter(BreakoutResult.scan_run_id == scan_run_id)
    if strength:
        q = q.filter(BreakoutResult.strength == strength.upper())
    if exchange:
        q = q.filter(BreakoutResult.exchange == exchange.upper())
    if sector:
        q = q.filter(BreakoutResult.sector.ilike(f"%{sector}%"))
    return q.order_by(BreakoutResult.strength_score.desc()).all()


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/breakouts/today", response_model=list[BreakoutResultOut])
def get_today_breakouts(
    strength: Optional[str] = None,
    exchange: Optional[str] = None,
    sector: Optional[str] = None,
    db: Session = Depends(get_db),
):
    scan = _get_scan_for_date(date.today(), db)
    if not scan:
        # Check yesterday (market may not have opened yet)
        scan = _get_scan_for_date(date.today() - timedelta(days=1), db)
    if not scan:
        return []
    return _breakouts_query(scan.id, db, strength, exchange, sector)


@app.get("/api/breakouts/yesterday", response_model=list[BreakoutResultOut])
def get_yesterday_breakouts(
    strength: Optional[str] = None,
    exchange: Optional[str] = None,
    db: Session = Depends(get_db),
):
    yesterday = date.today() - timedelta(days=1)
    scan = _get_scan_for_date(yesterday, db)
    if not scan:
        scan = _get_scan_for_date(yesterday - timedelta(days=1), db)
    if not scan:
        return []
    return _breakouts_query(scan.id, db, strength, exchange)


@app.get("/api/breakouts/{symbol}", response_model=list[BreakoutResultOut])
def get_symbol_history(
    symbol: str,
    limit: int = 30,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(BreakoutResult)
        .filter(BreakoutResult.symbol == symbol.upper())
        .order_by(BreakoutResult.scan_date.desc())
        .limit(limit)
        .all()
    )
    return rows


@app.get("/api/history")
def get_scan_history(limit: int = 30, db: Session = Depends(get_db)):
    runs = (
        db.query(ScanRun)
        .filter(ScanRun.status == "completed")
        .order_by(ScanRun.scan_date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "scan_date": str(r.scan_date),
            "total_scanned": r.total_scanned,
            "total_breakouts": r.total_breakouts,
            "nifty_trend": r.nifty_trend,
            "completed_at": str(r.completed_at) if r.completed_at else None,
        }
        for r in runs
    ]


@app.post("/api/watchlist/add")
def add_to_watchlist(payload: WatchlistIn, db: Session = Depends(get_db)):
    existing = db.query(Watchlist).filter(
        Watchlist.symbol == payload.symbol.upper()
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Symbol already in watchlist")
    item = Watchlist(
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        name=payload.name,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "symbol": item.symbol, "exchange": item.exchange}


@app.delete("/api/watchlist/{symbol}")
def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    item = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Symbol not found in watchlist")
    db.delete(item)
    db.commit()
    return {"removed": symbol.upper()}


@app.get("/api/watchlist")
def get_watchlist(db: Session = Depends(get_db)):
    items = db.query(Watchlist).order_by(Watchlist.added_at.desc()).all()
    # Enrich with latest breakout data
    result = []
    for w in items:
        latest = (
            db.query(BreakoutResult)
            .filter(BreakoutResult.symbol == w.symbol)
            .order_by(BreakoutResult.scan_date.desc())
            .first()
        )
        result.append({
            "id": w.id,
            "symbol": w.symbol,
            "exchange": str(w.exchange.value) if w.exchange else "",
            "name": w.name or (latest.name if latest else w.symbol),
            "notes": w.notes,
            "added_at": str(w.added_at),
            "latest_cmp": latest.cmp if latest else None,
            "latest_pct_change": latest.pct_change if latest else None,
            "latest_rsi": latest.rsi if latest else None,
            "latest_strength": latest.strength.value if latest and latest.strength else None,
        })
    return result


@app.post("/api/alerts/subscribe")
def subscribe_alerts(payload: AlertSubscribeIn, db: Session = Depends(get_db)):
    if not any([payload.email, payload.telegram_chat_id, payload.whatsapp_number]):
        raise HTTPException(status_code=400, detail="At least one contact method required")

    sub = AlertSubscription(
        email=payload.email,
        telegram_chat_id=payload.telegram_chat_id,
        whatsapp_number=payload.whatsapp_number,
        min_strength=BreakoutStrength(payload.min_strength.upper()),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {"id": sub.id, "status": "subscribed"}


@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    update = await request.json()

    def get_today_breakouts_fn():
        scan = _get_scan_for_date(date.today(), db)
        if not scan:
            return []
        return [
            {
                "symbol": b.symbol,
                "name": b.name or b.symbol,
                "exchange": b.exchange.value if b.exchange else "",
                "cmp": b.cmp or 0,
                "pct_change": b.pct_change or 0,
                "volume_ratio": b.volume_ratio or 0,
                "rsi": b.rsi or 0,
                "breakout_type": b.breakout_type or "",
                "strength": b.strength.value if b.strength else "",
            }
            for b in _breakouts_query(scan.id, db)
        ]

    chat_id, reply = handle_telegram_webhook(update, get_today_breakouts_fn)
    if chat_id and reply:
        from notifier import send_telegram_message
        send_telegram_message(chat_id, reply)
    return {"ok": True}


@app.post("/api/scan/trigger")
def trigger_scan(background_tasks: BackgroundTasks):
    """Manually trigger a scan (protected in production — add auth)."""
    trigger_scan_now()
    return {"status": "scan started"}


@app.get("/api/scan/status")
def scan_status(db: Session = Depends(get_db)):
    latest = (
        db.query(ScanRun)
        .order_by(ScanRun.scan_date.desc())
        .first()
    )
    if not latest:
        return {"status": "no_scans", "last_scan": None}
    return {
        "status": latest.status,
        "last_scan": str(latest.scan_date),
        "total_scanned": latest.total_scanned,
        "total_breakouts": latest.total_breakouts,
        "nifty_trend": latest.nifty_trend,
        "completed_at": str(latest.completed_at) if latest.completed_at else None,
    }


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Summary stats for the dashboard header."""
    today_scan = _get_scan_for_date(date.today(), db)
    if not today_scan:
        today_scan = (
            db.query(ScanRun)
            .filter(ScanRun.status == "completed")
            .order_by(ScanRun.scan_date.desc())
            .first()
        )
    if not today_scan:
        return {"total": 0, "strong": 0, "moderate": 0, "watchlist": 0, "nifty_trend": None}

    results = db.query(BreakoutResult).filter(
        BreakoutResult.scan_run_id == today_scan.id
    ).all()

    return {
        "total": len(results),
        "strong": sum(1 for r in results if r.strength == BreakoutStrength.STRONG),
        "moderate": sum(1 for r in results if r.strength == BreakoutStrength.MODERATE),
        "watchlist": sum(1 for r in results if r.strength == BreakoutStrength.WATCHLIST),
        "nifty_trend": today_scan.nifty_trend,
        "scan_date": str(today_scan.scan_date),
    }
