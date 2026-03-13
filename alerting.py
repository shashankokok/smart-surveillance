# ─── alerting.py ──────────────────────────────────────────────────────────────
"""Alert manager — stores history, plays sound, deduplicates, sends notifications."""

import threading
import time
from collections import deque
import config

try:
    from notifications import trigger_notifications
except ImportError:
    def trigger_notifications(*args, **kwargs):
        pass

MAX_HISTORY = 200

# Severity → colour for UI
SEV_COLOR = {
    "HIGH":   "#FF4136",
    "MEDIUM": "#FF851B",
    "LOW":    "#FFDC00",
}


class AlertManager:
    def __init__(self):
        self.history = deque(maxlen=MAX_HISTORY)   # list of dicts
        self._lock   = threading.Lock()
        self._last_beep = 0

    def push(self, alert, frame_snapshot=None):
        """
        Deduplicate: don't re-push same alert type+id within 5 seconds.
        """
        now = time.time()
        key = (alert["type"], alert.get("track_id"))

        with self._lock:
            # Check dedupe
            for prev in reversed(list(self.history)):
                if (prev["type"], prev.get("track_id")) == key:
                    if now - prev["ts"] < 5:
                        return   # duplicate within 5s — skip
                    break

            entry = {**alert, "ts": now, "time_str": time.strftime("%H:%M:%S")}
            if frame_snapshot is not None:
                entry["snapshot"] = frame_snapshot   # base64 JPEG
            self.history.appendleft(entry)

        # Notifications (email / webhook) for LOITERING, WEAPON DETECTED, etc.
        try:
            trigger_notifications(entry, frame_snapshot)
        except Exception:
            pass

        # Beep (Windows only) — throttle to 1s
        if config.ALERT_SOUND and now - self._last_beep > 1:
            self._last_beep = now
            threading.Thread(target=self._beep, args=(alert["severity"],), daemon=True).start()

    def get_history(self, n=50):
        with self._lock:
            return list(self.history)[:n]

    def clear(self):
        with self._lock:
            self.history.clear()

    @staticmethod
    def _beep(severity):
        try:
            import winsound
            freq = 1200 if severity == "HIGH" else 800
            winsound.Beep(freq, 200)
        except Exception:
            pass
