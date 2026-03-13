# Smart Surveillance System — Hackathon Pitch

**Domain:** Artificial Intelligence  
**Tagline:** *Real-time suspicious activity detection using AI-powered object detection and behavior analysis.*

---

## 1. The Problem (30 seconds)

Traditional CCTV systems record video but **don’t understand** what’s happening. Security staff must watch many feeds and still miss:

- Someone loitering in a sensitive area  
- Crowds building up (stampede risk)  
- Abandoned bags (security threat)  
- People entering restricted zones  
- Unusual movement (e.g. running)

Manual monitoring doesn’t scale and is easy to miss in real time.

---

## 2. Our Solution (30 seconds)

We built a **Smart Surveillance System** that:

1. **Detects** people, bags, and objects in the video using **YOLOv11** (state-of-the-art object detection).  
2. **Tracks** them over time with **DeepSORT** so each person has a stable ID across frames.  
3. **Analyzes behavior** with rule-based logic: loitering, crowd surge, abandoned objects, zone breach, running.  
4. **Alerts** in real time with sound, on-screen overlay, and a live log—all on a **single dashboard** that works with webcam, video files, or RTSP/IP cameras.

So instead of “just recording,” the system **interprets** the scene and **notifies** when something suspicious happens.

---

## 3. Key Features (for judges)

| Feature | What it does |
|--------|----------------|
| **5 detection rules** | Loitering, crowd surge, running, abandoned bag, restricted-zone breach (+ weapon detection from YOLO) |
| **Multi-camera** | Add multiple feeds (webcam, MP4, RTSP); each has its own tracking and alerts |
| **Live dashboard** | MJPEG stream with bounding boxes, track IDs, FPS, and an alert sidebar |
| **Configurable** | All thresholds (e.g. “loiter after 10 s”, “crowd = 5 people”) adjustable from the UI without code |
| **Alert management** | Deduplication, severity (HIGH/MEDIUM/LOW), sound, export log as CSV |
| **GPU support** | Uses CUDA when available for higher FPS |

---

## 4. How It Works (architecture in one slide)

```
Video (webcam / file / RTSP)
        ↓
   [OpenCV] read frames
        ↓
   [YOLOv11] detect persons, bags, weapons
        ↓
   [DeepSORT] track IDs across frames
        ↓
   [Behavior Engine] apply rules (loiter, crowd, abandon, zone, running)
        ↓
   [Alert Manager] dedupe → log → sound
        ↓
   [Flask] stream annotated video + REST API → Dashboard
```

**In one sentence:** We run YOLO on every few frames, track detections with DeepSORT, run a small rules engine on track history, and stream the annotated video plus alerts to a web dashboard.

---

## 5. Tech Stack

| Layer | Technology |
|-------|------------|
| Detection | YOLOv11 (Ultralytics), PyTorch |
| Tracking | DeepSORT (deep_sort_realtime) |
| Video I/O | OpenCV |
| Backend | Flask (REST API + MJPEG streaming) |
| Frontend | HTML/CSS/JS, dark-mode dashboard |
| Optional | CUDA for GPU acceleration |

---

## 6. How to Demo (suggested flow)

1. **Start:** “We’re solving the problem of passive CCTV—our system understands the scene and alerts in real time.”  
2. **Show dashboard:** Open `http://localhost:5000`, add a camera (e.g. source `0` for webcam).  
3. **Show feed:** Point at the live stream with bounding boxes and track IDs.  
4. **Trigger an alert:** e.g. stay still for 10+ seconds (loitering), or show a bag and walk away (abandoned object).  
5. **Show alerts:** Point to the Live Alerts panel and optional sound.  
6. **Show configurability:** Open Settings, move a slider (e.g. loiter time), explain that operators can tune without touching code.  
7. **Optional:** Add a second camera or switch to an RTSP/MP4 source to show multi-camera.

**One-liner for the intro:**  
*“We built a surveillance system that doesn’t just record—it detects people and bags, tracks them over time, and alerts when someone is loitering, when a bag is left alone, when too many people gather, or when someone enters a restricted zone.”*

---

## 7. Future / Extensions (if asked)

- Deploy on edge devices (Jetson, etc.) for on-prem use  
- Cloud backup of alerts and snapshots  
- More behaviors (e.g. fall detection, queue length)  
- Mobile app for alert push notifications  

---

## Quick Reference — Detection Rules

| Rule | Condition | Typical use |
|------|-----------|-------------|
| Loitering | Person stays within ~80 px for > 10 s | Suspicious lingering |
| Crowd surge | ≥ 5 people in frame | Overcrowding / stampede risk |
| Running | Speed above threshold (px/s) | Unusual movement |
| Abandoned object | Bag/luggage with no person nearby for > 8 s | Unattended baggage |
| Zone breach | Person centroid inside drawn polygon | Restricted area access |
| Weapon | YOLO class (knife, etc.) | Immediate threat |

Use this doc for your slide deck, verbal pitch, or judge Q&A.
