"""
APScheduler setup: runs the breakout scan at 8:45 AM IST every day.
"""
import logging
from datetime import datetime, date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")
_scheduler: BackgroundScheduler = None


def run_breakout_scan():
    """
    Entry point called by the scheduler. Imports lazily to avoid circular deps.
    """
    logger.info("Starting scheduled breakout scan at %s", datetime.now(IST))
    try:
        from database import SessionLocal
        from models import ScanRun, BreakoutResult, Exchange, AlertSubscription
        from data_fetcher import (
            get_all_symbols, batch_fetch_ohlcv, get_nifty_trend, fetch_ticker_info
        )
        from scanner import run_scan
        from notifier import send_email_digest, broadcast_telegram, send_whatsapp

        db = SessionLocal()
        today = date.today()

        # Avoid duplicate runs on the same day
        existing = db.query(ScanRun).filter(ScanRun.scan_date == today).first()
        if existing and existing.status == "completed":
            logger.info("Scan already completed for %s", today)
            db.close()
            return

        # Create/update scan run record
        if existing:
            scan_run = existing
        else:
            scan_run = ScanRun(scan_date=today)
            db.add(scan_run)
            db.commit()
            db.refresh(scan_run)

        scan_run.status = "running"
        scan_run.started_at = datetime.utcnow()
        db.commit()

        # Nifty trend filter
        nifty_uptrend = get_nifty_trend()
        scan_run.nifty_trend = nifty_uptrend
        db.commit()

        # Fetch data
        symbols = get_all_symbols()
        symbol_exchange_map = {s: ex for s, ex in symbols}
        logger.info("Fetching data for %d symbols…", len(symbols))
        data = batch_fetch_ohlcv(symbols)

        scan_run.total_scanned = len(data)
        db.commit()

        # Run scanner
        results = run_scan(data, symbol_exchange_map, nifty_uptrend)
        logger.info("Found %d breakout stocks", len(results))

        # Persist results
        db.query(BreakoutResult).filter(BreakoutResult.scan_run_id == scan_run.id).delete()
        for r in results:
            info = fetch_ticker_info(r.symbol, r.exchange)
            br = BreakoutResult(
                scan_run_id=scan_run.id,
                scan_date=today,
                symbol=r.symbol,
                name=info.get("name", r.symbol),
                exchange=Exchange(r.exchange),
                sector=info.get("sector"),
                market_cap=info.get("market_cap"),
                cmp=r.cmp,
                prev_close=r.prev_close,
                pct_change=r.pct_change,
                high_52w=r.high_52w,
                low_52w=r.low_52w,
                volume=r.volume,
                avg_volume_20d=r.avg_volume_20d,
                volume_ratio=r.volume_ratio,
                sma50=r.sma50,
                sma200=r.sma200,
                rsi=r.rsi,
                macd=r.macd,
                macd_signal=r.macd_signal,
                macd_hist=r.macd_hist,
                price_breakout=r.price_breakout,
                volume_confirmed=r.volume_confirmed,
                momentum_ok=r.momentum_ok,
                trend_ok=r.trend_ok,
                criteria_met=r.criteria_met,
                breakout_type=r.breakout_type,
                strength=r.strength,
                strength_score=r.strength_score,
                entry_price=r.entry_price,
                stop_loss=r.stop_loss,
                target_price=r.target_price,
            )
            db.add(br)

        scan_run.total_breakouts = len(results)
        scan_run.completed_at = datetime.utcnow()
        scan_run.status = "completed"
        db.commit()
        logger.info("Scan committed to DB")

        # Build notification payload
        payload = [
            {
                "symbol": r.symbol,
                "name": r.symbol,  # name fetched above; re-query if needed
                "exchange": r.exchange,
                "cmp": r.cmp,
                "pct_change": r.pct_change,
                "volume_ratio": r.volume_ratio,
                "rsi": r.rsi,
                "breakout_type": r.breakout_type,
                "strength": r.strength.value if r.strength else "",
            }
            for r in results
        ]

        # Get subscribers
        subs = db.query(AlertSubscription).filter(AlertSubscription.active == True).all()
        emails = [s.email for s in subs if s.email]
        tg_ids = [s.telegram_chat_id for s in subs if s.telegram_chat_id]
        wa_nums = [s.whatsapp_number for s in subs if s.whatsapp_number]

        if payload:
            send_email_digest(payload, emails)
            broadcast_telegram(payload, tg_ids)
            send_whatsapp(payload, wa_nums)

        db.close()

    except Exception as e:
        logger.error("Breakout scan failed: %s", e, exc_info=True)
        try:
            scan_run.status = "failed"
            scan_run.error_message = str(e)
            db.commit()
            db.close()
        except Exception:
            pass


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler(timezone=IST)
    # Run at 8:45 AM IST every weekday (Mon-Fri)
    _scheduler.add_job(
        run_breakout_scan,
        CronTrigger(hour=8, minute=45, day_of_week="mon-fri", timezone=IST),
        id="daily_breakout_scan",
        replace_existing=True,
        misfire_grace_time=600,  # allow up to 10 min late start
    )
    _scheduler.start()
    logger.info("Scheduler started — daily scan at 08:45 IST (Mon–Fri)")
    return _scheduler


def stop_scheduler():
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()


def trigger_scan_now():
    """Manually trigger a scan (for testing / on-demand)."""
    import threading
    t = threading.Thread(target=run_breakout_scan, daemon=True)
    t.start()
    return t
