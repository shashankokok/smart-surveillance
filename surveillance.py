# ─── surveillance.py ──────────────────────────────────────────────────────────
"""Per-camera pipeline — detect → track → analyse → annotate → stream."""

import threading
import time
import os
import traceback
import cv2
import torch
import config
import utils
from alerting import AlertManager


# ── YouTube URL resolver ───────────────────────────────────────────────────────
_YT_PATTERNS = ("youtube.com/watch", "youtu.be/", "youtube.com/live")

def _is_youtube(src: str) -> bool:
    return isinstance(src, str) and any(p in src for p in _YT_PATTERNS)

def _resolve_youtube(url: str) -> str:
    try:
        import yt_dlp
        ydl_opts = {"format": "best[ext=mp4]/best", "quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info   = ydl.extract_info(url, download=False)
            direct = info.get("url") or info.get("manifest_url", "")
            print(f"[YouTube] Resolved → {direct[:80]}…")
            return direct
    except ImportError:
        print("[YouTube] yt-dlp not installed")
        return url
    except Exception as e:
        print(f"[YouTube] Resolution failed: {e}")
        return url


class SurveillancePipeline:
    """One instance per camera.  Accepts a shared detector instance."""

    def __init__(self, cam_id: str = "default", label: str = "Camera"):
        self.cam_id  = cam_id
        self.label   = label
        self.alerts  = AlertManager()

        self._source  = config.DEFAULT_SOURCE
        self._cap     = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock   = threading.Lock()
        self._frame: bytes | None = None
        self._stats  = {
            "cam_id":       cam_id,
            "label":        label,
            "person_count": 0,
            "fps":          0.0,
            "source":       str(self._source),
            "running":      False,
            "error":        "",
        }
        os.makedirs(config.SNAPSHOT_DIR, exist_ok=True)

    # ── public controls ───────────────────────────────────────────────────────
    def start(self, source=None, shared_detector=None):
        if self._running:
            self.stop()
        if source is not None:
            try:
                self._source = int(source)
            except (ValueError, TypeError):
                self._source = source
        self._shared_detector = shared_detector
        self._stats["error"]   = ""
        self._running          = True
        self._thread           = threading.Thread(
            target=self._loop, daemon=True,
            name=f"pipeline-{self.cam_id}")
        self._thread.start()
        self._stats["running"] = True
        self._stats["source"]  = str(self._source)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        if self._cap:
            self._cap.release()
            self._cap = None
        self._stats["running"] = False
        with self._lock:
            self._frame = None

    def get_jpeg(self) -> bytes | None:
        with self._lock:
            return self._frame

    def get_stats(self) -> dict:
        s = dict(self._stats)
        s["alert_count"] = len(self.alerts.history)
        return s

    # ── internal loop ─────────────────────────────────────────────────────────
    def _loop(self):
        from tracker  import Tracker
        from behavior import BehaviorAnalyzer

        # Use shared detector (passed at start) or fall back to building one
        detector = self._shared_detector
        if detector is None:
            from detector import SharedDetector
            detector = SharedDetector.get()

        try:
            tracker  = Tracker()
            behavior = BehaviorAnalyzer()
        except Exception as e:
            self._stats["error"] = str(e)
            self._running = False
            traceback.print_exc()
            return

        print(f"[Pipeline:{self.cam_id}] Opening source: {self._source}")
        open_source = self._source
        if _is_youtube(str(self._source)):
            self._stats["error"] = "Resolving YouTube URL…"
            open_source = _resolve_youtube(str(self._source))
            self._stats["error"] = ""

        for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
            if isinstance(open_source, int):
                self._cap = cv2.VideoCapture(open_source, backend)
            else:
                self._cap = cv2.VideoCapture(open_source)
            if self._cap.isOpened():
                break
            self._cap.release()

        if not self._cap or not self._cap.isOpened():
            err = f"Cannot open source: {self._source}"
            self._stats["error"] = err
            self._running = False
            print(f"[Pipeline:{self.cam_id}] ERROR: {err}")
            return

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print(f"[Pipeline:{self.cam_id}] Started ✓")

        fps       = 0.0
        t_prev    = time.time()
        frame_idx = 0
        last_persons, last_bags, last_weapons = [], [], []
        tracks, new_alerts = [], []

        while self._running:
            try:
                ok, frame = self._cap.read()
                if not ok:
                    if isinstance(self._source, str):
                        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    else:
                        time.sleep(0.05)
                    continue

                frame_idx += 1

                # ── Detect every 2nd frame ────────────────────────────────────
                if frame_idx % 2 == 0:
                    try:
                        last_persons, last_bags, last_weapons = detector.detect(frame)
                    except Exception as e:
                        print(f"[Pipeline:{self.cam_id}] Detect error: {e}")

                persons, bags, weapons = last_persons, last_bags, last_weapons

                # ── Track ─────────────────────────────────────────────────────
                try:
                    tracks = tracker.update(persons, frame)
                except Exception as e:
                    print(f"[Pipeline:{self.cam_id}] Tracker error: {e}")
                    tracks = []

                # ── Behaviour ─────────────────────────────────────────────────
                try:
                    new_alerts = behavior.analyze(tracks, bags, weapons, frame.shape)
                except Exception as e:
                    print(f"[Pipeline:{self.cam_id}] Behavior error: {e}")
                    new_alerts = []

                # ── Alerts → snapshots ────────────────────────────────────────
                if new_alerts:
                    snap_b64 = utils.snapshot_b64(frame)
                    for a in new_alerts:
                        a["cam_id"] = self.cam_id
                        a["label"]  = self.label
                        self.alerts.push(a, frame_snapshot=snap_b64)
                    if config.SAVE_SNAPSHOTS:
                        ts  = time.strftime("%Y%m%d_%H%M%S")
                        tag = new_alerts[0]["type"].replace(" ", "_")
                        fn  = os.path.join(config.SNAPSHOT_DIR,
                                           f"{self.cam_id}_{tag}_{ts}.jpg")
                        cv2.imwrite(fn, frame)

                # ── Annotate ──────────────────────────────────────────────────
                try:
                    frame = utils.draw_zones(frame, config.RESTRICTED_ZONES)
                    frame = utils.draw_bags(frame, bags)
                    frame = utils.draw_weapons(frame, weapons)
                    frame = utils.draw_tracks(frame, tracks, new_alerts)
                    frame = utils.draw_alert_overlay(frame, new_alerts)
                    frame = utils.draw_cam_label(frame, self.label)
                    frame = utils.draw_stats(frame, tracks, fps)
                except Exception as e:
                    print(f"[Pipeline:{self.cam_id}] Annotate error: {e}")

                # ── Encode ────────────────────────────────────────────────────
                ret, buf = cv2.imencode(".jpg", frame,
                                        [cv2.IMWRITE_JPEG_QUALITY, config.JPEG_QUALITY])
                if ret:
                    with self._lock:
                        self._frame = bytes(buf)

                # ── FPS ───────────────────────────────────────────────────────
                now    = time.time()
                dt     = max(now - t_prev, 1e-6)
                fps    = 0.85 * fps + 0.15 / dt
                t_prev = now
                self._stats["person_count"] = len(tracks)
                self._stats["fps"]          = round(fps, 1)

            except Exception as e:
                print(f"[Pipeline:{self.cam_id}] Loop error: {e}")
                traceback.print_exc()
                time.sleep(1)

        if self._cap:
            self._cap.release()
        print(f"[Pipeline:{self.cam_id}] Stopped.")
