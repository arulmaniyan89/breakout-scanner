"""
Notification dispatch: Email (SMTP), Telegram Bot, WhatsApp (Twilio).
"""
import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ─── Email ────────────────────────────────────────────────────────────────────

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)


def _build_email_html(breakouts: list[dict]) -> str:
    rows = ""
    emoji_map = {"STRONG": "🟢", "MODERATE": "🟡", "WATCHLIST": "🔵"}
    for b in breakouts[:10]:
        emoji = emoji_map.get(b.get("strength", ""), "")
        rows += f"""
        <tr>
          <td style="padding:6px 12px">{emoji} {b['name']}</td>
          <td style="padding:6px 12px">{b['symbol']}</td>
          <td style="padding:6px 12px">{b['exchange']}</td>
          <td style="padding:6px 12px">₹{b['cmp']:.2f}</td>
          <td style="padding:6px 12px;color:{'green' if b['pct_change'] >= 0 else 'red'}">
            {b['pct_change']:+.2f}%
          </td>
          <td style="padding:6px 12px">{b['volume_ratio']:.1f}x</td>
          <td style="padding:6px 12px">{b['rsi']:.1f}</td>
          <td style="padding:6px 12px">{b.get('breakout_type','')}</td>
        </tr>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif">
      <h2 style="color:#1a56db">📈 Breakout Scanner — Today's Top Picks</h2>
      <table border="1" cellspacing="0" cellpadding="0"
             style="border-collapse:collapse;font-size:13px">
        <thead style="background:#1a56db;color:white">
          <tr>
            <th style="padding:8px 12px">Stock</th>
            <th style="padding:8px 12px">Symbol</th>
            <th style="padding:8px 12px">Exchange</th>
            <th style="padding:8px 12px">CMP</th>
            <th style="padding:8px 12px">% Change</th>
            <th style="padding:8px 12px">Vol Ratio</th>
            <th style="padding:8px 12px">RSI</th>
            <th style="padding:8px 12px">Type</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="color:#666;font-size:11px;margin-top:16px">
        Data sourced via Yahoo Finance. ~15 min delay. Not investment advice.
      </p>
    </body></html>"""


def send_email_digest(breakouts: list[dict], recipients: list[str]):
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("SMTP credentials not configured; skipping email")
        return
    if not recipients:
        return

    html = _build_email_html(breakouts)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🟢 Breakout Scanner — {len(breakouts)} stocks found today"
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        logger.info("Email digest sent to %d recipients", len(recipients))
    except Exception as e:
        logger.error("Email send failed: %s", e)


# ─── Telegram ─────────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _breakouts_to_telegram_text(breakouts: list[dict]) -> str:
    emoji_map = {"STRONG": "🟢", "MODERATE": "🟡", "WATCHLIST": "🔵"}
    lines = ["📈 *Breakout Scanner — Today's Picks*\n"]
    for b in breakouts[:15]:
        e = emoji_map.get(b.get("strength", ""), "")
        lines.append(
            f"{e} *{b['symbol']}* ({b['exchange']}) — ₹{b['cmp']:.2f} "
            f"({b['pct_change']:+.2f}%) | Vol {b['volume_ratio']:.1f}x | RSI {b['rsi']:.1f}"
        )
    lines.append("\n_Data via Yahoo Finance. Not investment advice._")
    return "\n".join(lines)


def send_telegram_message(chat_id: str, text: str):
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram token not configured")
        return
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error("Telegram send failed to %s: %s", chat_id, e)


def broadcast_telegram(breakouts: list[dict], chat_ids: list[str]):
    text = _breakouts_to_telegram_text(breakouts)
    for chat_id in chat_ids:
        send_telegram_message(chat_id, text)


def handle_telegram_webhook(update: dict, db_breakouts_fn) -> Optional[str]:
    """Process incoming Telegram update and return reply text."""
    message = update.get("message") or update.get("channel_post", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    text = message.get("text", "").strip().lower()

    if text in ("/breakouts", "/start"):
        breakouts = db_breakouts_fn()
        if not breakouts:
            return chat_id, "No breakouts found for today yet. Try after 8:45 AM IST."
        return chat_id, _breakouts_to_telegram_text(breakouts)
    if text == "/help":
        return chat_id, (
            "📈 *Breakout Scanner Bot*\n\n"
            "/breakouts — today's breakout stocks\n"
            "/help — this message"
        )
    return None, None


# ─── WhatsApp (Twilio) ────────────────────────────────────────────────────────

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")


def send_whatsapp(breakouts: list[dict], to_numbers: list[str]):
    if not TWILIO_SID or not TWILIO_TOKEN:
        logger.warning("Twilio credentials not configured; skipping WhatsApp")
        return
    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        body = _breakouts_to_telegram_text(breakouts).replace("*", "").replace("_", "")
        for number in to_numbers:
            client.messages.create(
                body=body,
                from_=TWILIO_FROM,
                to=f"whatsapp:{number}",
            )
        logger.info("WhatsApp sent to %d numbers", len(to_numbers))
    except ImportError:
        logger.warning("twilio package not installed; skipping WhatsApp")
    except Exception as e:
        logger.error("WhatsApp send failed: %s", e)
