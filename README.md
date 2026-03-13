# 🎯 Smart Surveillance System — CodeFiesta 6.0

> **Domain:** Artificial Intelligence  
> **Problem 5:** Smart Surveillance System for Suspicious Activity Detection Using Object Detection

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the system
python app.py

# 3. Open dashboard
# http://localhost:5000
```

---

## 🗂 Project Structure

```
├── app.py            # Flask web server + REST API
├── surveillance.py   # Core pipeline (detect → track → analyse → annotate)
├── detector.py       # YOLOv11 object detection (Ultralytics + PyTorch)
├── tracker.py        # DeepSORT multi-object tracking
├── behavior.py       # Suspicious activity rules engine
├── alerting.py       # Alert manager (dedup + sound + history)
├── utils.py          # Drawing helpers, frame encoding
├── config.py         # All thresholds and settings
├── templates/
│   └── dashboard.html  # Dark-mode Flask dashboard
└── requirements.txt
```

---

## 🔍 Detection Capabilities

| # | Activity | How Detected |
|---|---|---|
| 1 | **Loitering** | Person stays within 80px radius for > 10 seconds |
| 2 | **Crowd Surge** | ≥ 5 persons in frame simultaneously |
| 3 | **Running / Sudden Movement** | Centroid velocity > 30 px/frame |
| 4 | **Abandoned Object** | Bag/luggage alone for > 8 seconds |
| 5 | **Restricted Zone Breach** | Person enters annotated polygon zone |

---

## ⚙️ Configuration (`config.py`)

| Parameter | Default | Description |
|---|---|---|
| `YOLO_MODEL` | `yolo11n.pt` | YOLO model (auto-downloaded) |
| `YOLO_CONF` | `0.45` | Detection confidence threshold |
| `LOITER_SECONDS` | `10` | Seconds before loitering alert |
| `CROWD_THRESHOLD` | `5` | People count for crowd alert |
| `ABANDON_SECONDS` | `8` | Seconds for abandoned object alert |
| `SPEED_THRESHOLD` | `30` | Pixels/frame for running alert |

All thresholds are **adjustable live** from the web dashboard.

---

## 🖥 Using GPU (NVIDIA CUDA)

The app uses **GPU automatically** when PyTorch has CUDA. If the console shows `Device=CPU`, install PyTorch with CUDA:

1. **Check your CUDA version** (NVIDIA driver): run `nvidia-smi` in a terminal.
2. **Install PyTorch with CUDA** (pick one; replace `cu121` with your CUDA version, e.g. `cu118`):
   ```bash
   # CUDA 12.1
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   # CUDA 11.8
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```
3. Restart the app. You should see `Device=CUDA  Precision=FP16` in the console.
4. **Force device** (optional): in `config.py`, set `DEVICE_OVERRIDE = "cuda"` or `"cpu"`.

---

## 🛠 Technology Stack

| Component | Technology |
|---|---|
| Object Detection | YOLOv11 (Ultralytics) + PyTorch |
| Object Tracking | DeepSORT (deep_sort_realtime) |
| Video Processing | OpenCV |
| Web Dashboard | Flask + MJPEG streaming |
| Alert Sound | `winsound` (Windows) |

---

## 🌐 Dashboard Features

- **Live MJPEG Video Feed** — annotated with bounding boxes and track IDs
- **Real-time Stats** — person count, FPS, total alerts
- **Alert Log** — colour-coded by severity (HIGH/MEDIUM/LOW)
- **Toast Notifications** — pops on every new alert
- **Configurable Thresholds** — live sliders for all detection rules
- **Video Source Switcher** — webcam, MP4, or RTSP URL

---

## 📧 Notifications (Email / Webhook)

When **Loitering** or **Weapon detected** (or other configured alert types) fire, the app can:

- **Email** — Send an alert message (and optional snapshot) via SMTP.  
  Configure in **Settings → Notifications**: SMTP host (e.g. `smtp.gmail.com`), port (587), your email, **app password** (for Gmail use an [App Password](https://support.google.com/accounts/answer/185833)), and recipient(s).
- **Webhook** — POST a JSON payload to any URL (Slack incoming webhook, Discord webhook, Telegram bot, etc.).  
  Enable "Send to webhook URL" and set the URL in Settings.

By default only **LOITERING** and **WEAPON DETECTED** trigger notifications; this is configurable in `config.py` (`NOTIFY_ALERT_TYPES`). Notifications are throttled to at most one per alert type per camera per minute.

---

## 📽 Supported Video Sources

```python
# Webcam
source = 0

# Video file
source = "path/to/video.mp4"

# RTSP stream
source = "rtsp://192.168.1.100:554/stream"
```
