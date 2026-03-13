# ─── config.py ────────────────────────────────────────────────────────────────
# Central configuration — Smart Surveillance System
import torch
# ── YOLO ──────────────────────────────────────────────────────────────────────
YOLO_MODEL   = "yolo11n.pt"         # auto-downloaded on first run
YOLO_CONF    = 0.20              # lower threshold for better CCTV recall
YOLO_IOU     = 0.40              # tighter IOU for cleaner overlapping boxes
# GPU: set to "cuda" to use GPU, "cpu" to force CPU. None = auto-detect.
DEVICE_OVERRIDE = None
if DEVICE_OVERRIDE is not None:
    DEVICE = DEVICE_OVERRIDE
elif torch.cuda.is_available():
    DEVICE = "cuda"
else:
    DEVICE = "cpu"

# COCO classes to detect
CLS_PERSON   = 0
CLS_BAGS     = {24, 26, 28}         # backpack, handbag, suitcase
CLS_WEAPONS  = {43, 76}             # knife(43), scissors(76-proxy)
YOLO_CLASSES = [0, 24, 26, 28, 43, 76]

# ── TRACKER ───────────────────────────────────────────────────────────────────
MAX_AGE      = 40              # keep track alive longer for re-identification
N_INIT       = 2               # confirm track after 2 frames

# ── BEHAVIOUR THRESHOLDS ─────────────────────────────────────────────────────
LOITER_SECONDS      = 10            # seconds stationary → loitter alert
LOITER_RADIUS_PX    = 80            # movement within this radius = "stationary"
ABANDON_SECONDS     = 8             # seconds bag alone → abandoned alert
ABANDON_RADIUS_PX   = 120           # proximity to count person as "near" bag
RUNNING_PX_PER_SEC  = 120           # pixel/sec speed above which = "running"

# ── RESTRICTED ZONES ─────────────────────────────────────────────────────────
# List of polygons — each polygon is a list of [x, y] in pixel coords.
# Updated live from the Flask UI zone-editor.
RESTRICTED_ZONES = []

# ── SNAPSHOTS ────────────────────────────────────────────────────────────────
SNAPSHOT_DIR    = "snapshots"       # folder to save alert snapshots
SAVE_SNAPSHOTS  = True

# ── VIDEO SOURCE ──────────────────────────────────────────────────────────────
DEFAULT_SOURCE  = 0   # 0 = webcam; or "path/to/video.mp4" or "rtsp://..."

# ── ALERT SOUND ──────────────────────────────────────────────────────────────
ALERT_SOUND     = True

# ── NOTIFICATIONS (email / webhook for loitering & weapon alerts) ─────────────
NOTIFY_ENABLED       = True
NOTIFY_ALERT_TYPES   = ["LOITERING", "WEAPON DETECTED"]   # which alert types trigger email/webhook
NOTIFY_EMAIL_ENABLED = False
NOTIFY_SMTP_HOST     = "smtp.gmail.com"
NOTIFY_SMTP_PORT     = 587
NOTIFY_SMTP_USER     = ""           # your email
NOTIFY_SMTP_PASSWORD = ""           # app password (not regular password)
NOTIFY_EMAIL_TO      = ""           # comma-separated recipients
NOTIFY_WEBHOOK_ENABLED = False
NOTIFY_WEBHOOK_URL   = ""          # e.g. Slack incoming webhook, Discord webhook, or custom POST URL

# ── FLASK ─────────────────────────────────────────────────────────────────────
FLASK_HOST      = "0.0.0.0"
FLASK_PORT      = 5000
STREAM_FPS      = 25
JPEG_QUALITY    = 85
