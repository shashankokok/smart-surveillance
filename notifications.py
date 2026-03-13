# ─── notifications.py ──────────────────────────────────────────────────────────
"""Send notifications (email, webhook) when configured alert types fire."""

import json
import smtplib
import ssl
import threading
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import base64
import urllib.request
import urllib.error

import config


def _should_notify(alert: dict) -> bool:
    """True if this alert type is in the notify list."""
    if not getattr(config, "NOTIFY_ENABLED", False):
        return False
    types = getattr(config, "NOTIFY_ALERT_TYPES", ["LOITERING", "WEAPON DETECTED"])
    return alert.get("type") in types


def send_email(alert: dict, frame_snapshot_b64: str | None = None) -> None:
    """Send alert via SMTP. Runs in thread; logs errors only."""
    if not getattr(config, "NOTIFY_EMAIL_ENABLED", False):
        return
    host = getattr(config, "NOTIFY_SMTP_HOST", "") or "smtp.gmail.com"
    port = int(getattr(config, "NOTIFY_SMTP_PORT", 587))
    user = (getattr(config, "NOTIFY_SMTP_USER", "") or "").strip()
    password = (getattr(config, "NOTIFY_SMTP_PASSWORD", "") or "").strip()
    to_str = (getattr(config, "NOTIFY_EMAIL_TO", "") or "").strip()
    if not user or not password or not to_str:
        return
    to_list = [e.strip() for e in to_str.split(",") if e.strip()]

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Surveillance] {alert.get('type', 'Alert')} — {alert.get('label', 'Camera')}"
        msg["From"] = user
        msg["To"] = ", ".join(to_list)

        body = (
            f"Alert: {alert.get('type', 'Alert')}\n"
            f"Camera: {alert.get('label', 'N/A')} ({alert.get('cam_id', '')})\n"
            f"Time: {alert.get('time_str', '')}\n"
            f"Severity: {alert.get('severity', '')}\n"
            f"Message: {alert.get('message', '')}\n"
        )
        msg.attach(MIMEText(body, "plain"))

        if frame_snapshot_b64:
            try:
                img_data = base64.b64decode(frame_snapshot_b64)
                img = MIMEImage(img_data, _subtype="jpeg")
                img.add_header("Content-Disposition", "attachment", filename="snapshot.jpg")
                msg.attach(img)
            except Exception:
                pass

        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=ctx)
            server.login(user, password)
            server.sendmail(user, to_list, msg.as_string())
    except Exception as e:
        print(f"[Notifications] Email failed: {e}")


def send_webhook(alert: dict, frame_snapshot_b64: str | None = None) -> None:
    """POST alert JSON to webhook URL (Slack, Discord, Telegram bot, etc.)."""
    url = (getattr(config, "NOTIFY_WEBHOOK_URL", "") or "").strip()
    if not getattr(config, "NOTIFY_WEBHOOK_ENABLED", False) or not url:
        return

    payload = {
        "alert_type": alert.get("type"),
        "camera_id": alert.get("cam_id"),
        "camera_label": alert.get("label"),
        "time": alert.get("time_str"),
        "severity": alert.get("severity"),
        "message": alert.get("message"),
        "track_id": alert.get("track_id"),
    }
    if frame_snapshot_b64:
        payload["snapshot_b64"] = frame_snapshot_b64

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
    except urllib.error.HTTPError as e:
        print(f"[Notifications] Webhook HTTP error: {e.code} {e.reason}")
    except Exception as e:
        print(f"[Notifications] Webhook failed: {e}")


# Throttle: don't send same alert type to email/webhook more than once per N seconds
_last_sent: dict[str, float] = {}
_throttle_seconds = 60


def trigger_notifications(alert: dict, frame_snapshot_b64: str | None = None) -> None:
    """If alert type is in NOTIFY_ALERT_TYPES, send email and/or webhook in background."""
    if not _should_notify(alert):
        return
    key = f"{alert.get('type')}:{alert.get('cam_id', '')}"
    now = time.time()
    if _last_sent.get(key, 0) + _throttle_seconds > now:
        return
    _last_sent[key] = now

    def _run():
        send_email(alert, frame_snapshot_b64)
        send_webhook(alert, frame_snapshot_b64)

    threading.Thread(target=_run, daemon=True).start()
