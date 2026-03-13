# ─── app.py ───────────────────────────────────────────────────────────────────
"""Flask application — Multi-Camera Smart Surveillance Dashboard."""

import os, json, time, threading
from flask import Flask, Response, render_template, request, jsonify, send_file

import config
from surveillance import SurveillancePipeline
from detector    import SharedDetector

app = Flask(__name__)

# ── Shared YOLO model (loaded once at startup) ────────────────────────────────
_detector = SharedDetector.get()

# ── Camera registry ───────────────────────────────────────────────────────────
_cameras: dict[str, SurveillancePipeline] = {}
_cam_lock = threading.Lock()

def _get_cam(cam_id: str) -> SurveillancePipeline | None:
    with _cam_lock:
        return _cameras.get(cam_id)

def _add_camera(cam_id: str, source, label: str) -> SurveillancePipeline:
    with _cam_lock:
        if cam_id in _cameras:
            _cameras[cam_id].stop()
        pipe = SurveillancePipeline(cam_id=cam_id, label=label)
        _cameras[cam_id] = pipe
    pipe.start(source=source, shared_detector=_detector)
    return pipe

def _remove_camera(cam_id: str) -> bool:
    with _cam_lock:
        pipe = _cameras.pop(cam_id, None)
    if pipe:
        pipe.stop()
        return True
    return False


# ── MJPEG stream generators ───────────────────────────────────────────────────
def _gen_stream(cam_id: str):
    while True:
        pipe = _get_cam(cam_id)
        if pipe:
            frame = pipe.get_jpeg()
            if frame:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
                continue
        time.sleep(0.04)


@app.route("/video_feed/<cam_id>")
def video_feed(cam_id):
    return Response(_gen_stream(cam_id),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

# Legacy single-camera route (keeps old dashboard compatible)
@app.route("/video_feed")
def video_feed_default():
    return video_feed("default")

@app.route("/favicon.ico")
def favicon():
    return "", 204

# ── Pages ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("dashboard.html")

# ── Multi-camera API ──────────────────────────────────────────────────────────
@app.route("/api/cameras", methods=["GET"])
def api_cameras_list():
    with _cam_lock:
        cams = list(_cameras.values())
    return jsonify([c.get_stats() for c in cams])

@app.route("/api/cameras/add", methods=["POST"])
def api_cameras_add():
    data   = request.get_json(silent=True) or {}
    cam_id = data.get("id",     f"cam{len(_cameras)+1}")
    source = data.get("source", config.DEFAULT_SOURCE)
    label  = data.get("label",  f"Camera {cam_id}")
    _add_camera(cam_id, source, label)
    return jsonify({"status": "added", "id": cam_id, "label": label})

@app.route("/api/cameras/remove", methods=["POST"])
def api_cameras_remove():
    data   = request.get_json(silent=True) or {}
    cam_id = data.get("id", "")
    ok = _remove_camera(cam_id)
    return jsonify({"status": "removed" if ok else "not_found", "id": cam_id})

@app.route("/api/cameras/<cam_id>/stats")
def api_cam_stats(cam_id):
    pipe = _get_cam(cam_id)
    if not pipe:
        return jsonify({"error": "not found"}), 404
    return jsonify(pipe.get_stats())

@app.route("/api/cameras/<cam_id>/alerts")
def api_cam_alerts(cam_id):
    pipe = _get_cam(cam_id)
    if not pipe:
        return jsonify([])
    n = int(request.args.get("n", 50))
    clean = [{k: v for k, v in h.items() if k != "snapshot"}
             for h in pipe.alerts.get_history(n)]
    return jsonify(clean)

# ── Legacy single-camera control endpoints (backward-compat) ──────────────────
@app.route("/api/start", methods=["POST"])
def api_start():
    data   = request.get_json(silent=True) or {}
    source = data.get("source", config.DEFAULT_SOURCE)
    label  = data.get("label",  "Default Camera")
    _add_camera("default", source, label)
    return jsonify({"status": "started", "source": str(source)})

@app.route("/api/stop", methods=["POST"])
def api_stop():
    _remove_camera("default")
    return jsonify({"status": "stopped"})

@app.route("/api/stats")
def api_stats():
    pipe = _get_cam("default")
    if not pipe:
        return jsonify({"running": False, "person_count": 0, "fps": 0, "error": ""})
    return jsonify(pipe.get_stats())

@app.route("/api/alerts")
def api_alerts():
    pipe = _get_cam("default")
    if not pipe:
        return jsonify([])
    n = int(request.args.get("n", 50))
    clean = [{k: v for k, v in h.items() if k != "snapshot"}
             for h in pipe.alerts.get_history(n)]
    return jsonify(clean)

@app.route("/api/alerts/clear", methods=["POST"])
def api_clear():
    pipe = _get_cam("default")
    if pipe:
        pipe.alerts.clear()
    return jsonify({"status": "cleared"})

# ── Global aggregated alerts (all cameras) ────────────────────────────────────
@app.route("/api/alerts/all")
def api_alerts_all():
    n = int(request.args.get("n", 100))
    all_alerts = []
    with _cam_lock:
        pipes = list(_cameras.values())
    for p in pipes:
        for h in p.alerts.get_history(n):
            entry = {k: v for k, v in h.items() if k != "snapshot"}
            all_alerts.append(entry)
    all_alerts.sort(key=lambda a: a.get("time_str", ""), reverse=True)
    return jsonify(all_alerts[:n])

# ── Snapshot ──────────────────────────────────────────────────────────────────
@app.route("/api/snapshot/<int:idx>")
def api_snapshot(idx):
    import base64
    pipe = _get_cam("default")
    if not pipe:
        return "", 404
    history = pipe.alerts.get_history(100)
    if idx < len(history) and "snapshot" in history[idx]:
        data = base64.b64decode(history[idx]["snapshot"])
        return Response(data, mimetype="image/jpeg")
    return "", 404

# ── Zone management ───────────────────────────────────────────────────────────
@app.route("/api/zones", methods=["GET"])
def api_zones_get():
    return jsonify(config.RESTRICTED_ZONES)

@app.route("/api/zones", methods=["POST"])
def api_zones_set():
    data = request.get_json(silent=True) or []
    config.RESTRICTED_ZONES = data
    return jsonify({"status": "ok", "count": len(data)})

@app.route("/api/zones/clear", methods=["POST"])
def api_zones_clear():
    config.RESTRICTED_ZONES = []
    return jsonify({"status": "cleared"})

# ── Config ────────────────────────────────────────────────────────────────────
@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "GET":
        return jsonify({
            "loiter_seconds":    config.LOITER_SECONDS,
            "loiter_radius_px":  config.LOITER_RADIUS_PX,
            "abandon_seconds":   config.ABANDON_SECONDS,
            "yolo_conf":         config.YOLO_CONF,
            "running_px_per_sec": config.RUNNING_PX_PER_SEC,
            "alert_sound":       config.ALERT_SOUND,
        })
    data = request.get_json(silent=True) or {}
    if "loiter_seconds"    in data: config.LOITER_SECONDS    = float(data["loiter_seconds"])
    if "loiter_radius_px"  in data: config.LOITER_RADIUS_PX  = float(data["loiter_radius_px"])
    if "abandon_seconds"   in data: config.ABANDON_SECONDS   = float(data["abandon_seconds"])
    if "yolo_conf"         in data: config.YOLO_CONF         = float(data["yolo_conf"])
    if "running_px_per_sec" in data: config.RUNNING_PX_PER_SEC = float(data["running_px_per_sec"])
    if "alert_sound"       in data: config.ALERT_SOUND       = bool(data["alert_sound"])
    return jsonify({"status": "updated"})

# ── Notifications (email / webhook) ──────────────────────────────────────────
@app.route("/api/notifications", methods=["GET", "POST"])
def api_notifications():
    if request.method == "GET":
        return jsonify({
            "notify_enabled":        getattr(config, "NOTIFY_ENABLED", True),
            "notify_alert_types":    getattr(config, "NOTIFY_ALERT_TYPES", ["LOITERING", "WEAPON DETECTED"]),
            "notify_email_enabled":  getattr(config, "NOTIFY_EMAIL_ENABLED", False),
            "notify_smtp_host":      getattr(config, "NOTIFY_SMTP_HOST", "smtp.gmail.com"),
            "notify_smtp_port":      getattr(config, "NOTIFY_SMTP_PORT", 587),
            "notify_smtp_user":      getattr(config, "NOTIFY_SMTP_USER", ""),
            "notify_smtp_password":  "",   # never expose password to frontend
            "notify_email_to":       getattr(config, "NOTIFY_EMAIL_TO", ""),
            "notify_webhook_enabled": getattr(config, "NOTIFY_WEBHOOK_ENABLED", False),
            "notify_webhook_url":    getattr(config, "NOTIFY_WEBHOOK_URL", ""),
        })
    data = request.get_json(silent=True) or {}
    if "notify_enabled"         in data: config.NOTIFY_ENABLED         = bool(data["notify_enabled"])
    if "notify_alert_types"     in data: config.NOTIFY_ALERT_TYPES     = list(data["notify_alert_types"]) if isinstance(data["notify_alert_types"], list) else config.NOTIFY_ALERT_TYPES
    if "notify_email_enabled"    in data: config.NOTIFY_EMAIL_ENABLED    = bool(data["notify_email_enabled"])
    if "notify_smtp_host"       in data: config.NOTIFY_SMTP_HOST        = str(data["notify_smtp_host"] or "smtp.gmail.com")
    if "notify_smtp_port"       in data: config.NOTIFY_SMTP_PORT        = int(data["notify_smtp_port"] or 587)
    if "notify_smtp_user"       in data: config.NOTIFY_SMTP_USER       = str(data.get("notify_smtp_user", "") or "")
    if "notify_smtp_password"   in data: config.NOTIFY_SMTP_PASSWORD   = str(data.get("notify_smtp_password", "") or "")
    if "notify_email_to"        in data: config.NOTIFY_EMAIL_TO        = str(data.get("notify_email_to", "") or "")
    if "notify_webhook_enabled"  in data: config.NOTIFY_WEBHOOK_ENABLED = bool(data["notify_webhook_enabled"])
    if "notify_webhook_url"      in data: config.NOTIFY_WEBHOOK_URL     = str(data.get("notify_webhook_url", "") or "")
    return jsonify({"status": "updated"})

# ── Export log ────────────────────────────────────────────────────────────────
@app.route("/api/log/export")
def api_log_export():
    import io, csv
    all_alerts = []
    with _cam_lock:
        pipes = list(_cameras.values())
    for p in pipes:
        all_alerts.extend(p.alerts.get_history(500))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["cam_id","label","time_str","type","severity","rule","message","track_id"])
    w.writeheader()
    for h in all_alerts:
        w.writerow({k: h.get(k, "") for k in w.fieldnames})
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=alert_log.csv"})

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════╗")
    print("║   Smart Surveillance System — CodeFiesta 6.0    ║")
    print(f"║   Dashboard → http://localhost:{config.FLASK_PORT}             ║")
    print("╚══════════════════════════════════════════════════╝")
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False, threaded=True)
