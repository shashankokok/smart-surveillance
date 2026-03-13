# ─── utils.py ─────────────────────────────────────────────────────────────────
"""Drawing helpers and frame-encoding utilities."""

import cv2
import numpy as np
import base64
import config

# Severity → BGR colour
SEV_BGR = {
    "CRITICAL": (0,   0, 220),
    "HIGH":     (0,  50, 220),
    "MEDIUM":   (0, 140, 255),
    "LOW":      (0, 220, 255),
}

TRACK_PALETTE = [
    (255,  99,  71),  # tomato
    (100, 149, 237),  # cornflower
    ( 60, 179, 113),  # medium-sea-green
    (255, 165,   0),  # orange
    (147, 112, 219),  # medium-purple
    (  0, 206, 209),  # dark-turquoise
    (255, 105, 180),  # hot-pink
    (173, 255,  47),  # green-yellow
    (255, 215,   0),  # gold
    (135, 206, 235),  # sky-blue
]


def _track_color(tid):
    try:
        idx = int(tid)
    except (ValueError, TypeError):
        idx = hash(str(tid))
    return TRACK_PALETTE[idx % len(TRACK_PALETTE)]


def _label_bg(frame, x1, y1, text, color, font_scale=0.55, thickness=1):
    """Draw a filled pill-label above the bounding box."""
    (tw, th), baseline = cv2.getTextSize(
        text, cv2.FONT_HERSHEY_DUPLEX, font_scale, thickness)
    pad = 4
    rx1, ry1 = x1, max(0, y1 - th - pad * 2)
    rx2, ry2 = x1 + tw + pad * 2, y1
    cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), color, -1)
    cv2.putText(frame, text, (rx1 + pad, ry2 - pad),
                cv2.FONT_HERSHEY_DUPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)


def draw_tracks(frame, tracks, active_alerts):
    """
    Suspicious persons by type:
      RUNNING / any other alert → orange box  (high-speed)
      LOITERING / ZONE INTRUSION → red box
      WEAPON nearby alert → deep-red box
    Normal persons → small centroid dot only.
    """
    # Build map: track_id → list of alert rules affecting them
    alert_rules: dict = {}
    for a in active_alerts:
        tid = a.get("track_id")
        if tid is not None:
            alert_rules.setdefault(tid, []).append(a.get("rule", 0))

    for t in tracks:
        tid      = t["track_id"]
        x1,y1,x2,y2 = t["bbox"]
        cx, cy   = t["centroid"]
        conf     = t.get("conf", None)
        color    = _track_color(tid)
        rules    = alert_rules.get(tid, [])

        if rules:
            conf_str = f"  {int(conf*100)}%" if conf is not None else ""
            if 5 in rules:        # RUNNING
                box_color = (0, 140, 255)   # orange
                label     = f"RUNNING  ID-{tid}{conf_str}"
            elif 1 in rules:     # LOITERING
                box_color = (0, 0, 220)     # red
                label     = f"LOITERING  ID-{tid}{conf_str}"
            elif 3 in rules:     # ZONE INTRUSION
                box_color = (0, 0, 220)     # red
                label     = f"INTRUSION  ID-{tid}{conf_str}"
            else:
                box_color = (0, 0, 220)
                label     = f"SUSPICIOUS  ID-{tid}{conf_str}"

            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 3)
            _label_bg(frame, x1, y1, label, box_color, font_scale=0.58, thickness=2)
            cv2.circle(frame, (cx, cy), 8, box_color, 2)
            cv2.circle(frame, (cx, cy), 4, (255, 200, 80), -1)
        else:
            # Normal — tiny dot only
            cv2.circle(frame, (cx, cy), 5, color, -1)
            cv2.circle(frame, (cx, cy), 5, (255, 255, 255), 1)

    return frame


def draw_bags(frame, bags):
    """Orange rounded boxes with class-name labels for detected bags."""
    CLASS_NAMES = {24: "BACKPACK", 26: "HANDBAG", 28: "SUITCASE"}
    for bag in bags:
        x1, y1, x2, y2 = bag["bbox"]
        conf = bag.get("conf", None)
        name = CLASS_NAMES.get(bag.get("cls", 26), "BAG")
        conf_str = f"  {int(conf*100)}%" if conf is not None else ""
        label = f"{name}{conf_str}"
        color = (0, 140, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        _label_bg(frame, x1, y1, label, color)
    return frame


def draw_weapons(frame, weapons):
    """Bright red pulsing-style boxes for detected weapons."""
    for w in weapons:
        x1, y1, x2, y2 = w["bbox"]
        conf     = w.get("conf", None)
        conf_str = f"  {int(conf*100)}%" if conf is not None else ""
        label    = f"!WEAPON: {w['label'].upper()}{conf_str}"
        color    = (0, 0, 255)
        # Thick outer glow
        cv2.rectangle(frame, (x1-2, y1-2), (x2+2, y2+2), (0, 0, 128), 1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
        _label_bg(frame, x1, y1, label, color, font_scale=0.6, thickness=2)
    return frame


def draw_alert_overlay(frame, active_alerts):
    """Translucent top banner showing the highest-severity active alert."""
    if not active_alerts:
        return frame
    priority = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    top   = min(active_alerts, key=lambda a: priority.get(a["severity"], 9))
    color = SEV_BGR.get(top["severity"], (0, 0, 200))
    h, w  = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 56), color, -1)
    cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)
    rule_icons = {
        1: "LOITERING",
        2: "ABANDONED BAG",
        3: "ZONE INTRUSION",
        4: "WEAPON DETECTED",
        5: "RUNNING",
    }
    type_str = rule_icons.get(top.get("rule", 0), top["type"])
    banner   = f"  ALERT [{top['severity']}]: {type_str}  |  {top['message']}"
    cv2.putText(frame, banner, (8, 38),
                cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
    return frame


def draw_cam_label(frame, label: str):
    """Camera name badge in top-right corner."""
    h, w = frame.shape[:2]
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.55, 1)
    pad = 5
    rx1, ry1 = w - tw - pad * 2 - 4, 4
    rx2, ry2 = w - 4, th + pad * 2
    overlay = frame.copy()
    cv2.rectangle(overlay, (rx1, ry1), (rx2, ry2), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    cv2.putText(frame, label, (rx1 + pad, ry2 - pad),
                cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 220, 255), 1, cv2.LINE_AA)
    return frame


def draw_stats(frame, tracks, fps: float):
    """Bottom HUD bar — people count, FPS, and GPU/CPU indicator."""
    h, w = frame.shape[:2]
    device_lbl = f"GPU" if config.DEVICE == "cuda" else "CPU"
    text = f"  People: {len(tracks)}   FPS: {fps:.1f}   [{device_lbl}]"
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 0.60, 1)
    bar_top = h - th - 16
    # Semi-transparent black bar
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, bar_top), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.50, frame, 0.50, 0, frame)
    cv2.putText(frame, text, (4, h - 8),
                cv2.FONT_HERSHEY_DUPLEX, 0.60, (180, 255, 180), 1, cv2.LINE_AA)
    return frame


def draw_zones(frame, zones):
    """Semi-transparent red polygons for restricted zones."""
    for zone in zones:
        if len(zone) < 3:
            continue
        pts = np.array(zone, dtype=np.int32).reshape((-1, 1, 2))
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], (30, 0, 180))
        cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
        cv2.polylines(frame, [pts], True, (0, 0, 255), 2)
        cx = int(np.mean([p[0] for p in zone]))
        cy = int(np.mean([p[1] for p in zone]))
        cv2.putText(frame, "RESTRICTED ZONE", (cx - 70, cy),
                    cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 0, 255), 1, cv2.LINE_AA)
    return frame


def frame_to_jpeg_b64(frame, quality: int = 85) -> str:
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def snapshot_b64(frame, quality: int = 65) -> str:
    small = cv2.resize(frame, (320, 180))
    return frame_to_jpeg_b64(small, quality)
