# ─── detector.py ──────────────────────────────────────────────────────────────
"""
Thread-safe shared YOLO detector — one model instance shared across all cameras.
FP16 inference + cuDNN benchmark for maximum GPU throughput.
"""

import threading
import numpy as np
import torch
from ultralytics import YOLO
import config

# ── cuDNN performance flags ───────────────────────────────────────────────────
if config.DEVICE == "cuda":
    torch.backends.cudnn.benchmark    = True
    torch.backends.cudnn.deterministic = False


class SharedDetector:
    """
    Singleton YOLO detector shared by all camera pipelines.
    A threading.Lock ensures only one inference runs at a time on the GPU.
    """
    _instance = None
    _lock      = threading.Lock()

    @classmethod
    def get(cls) -> "SharedDetector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.model  = YOLO(config.YOLO_MODEL)
        self.device = config.DEVICE
        self.half   = (config.DEVICE == "cuda")
        self._infer_lock = threading.Lock()   # serialise concurrent calls

        if self.half:
            self.model.model.half()
            print(f"[Detector] Model={config.YOLO_MODEL}  Device=CUDA  Precision=FP16  (shared)")
        else:
            print(f"[Detector] Model={config.YOLO_MODEL}  Device=CPU  Precision=FP32  (shared)")

        # Warm-up
        try:
            dummy = np.zeros((480, 640, 3), dtype=np.uint8)
            self.model.predict(dummy, conf=0.9, device=config.DEVICE,
                               half=self.half, verbose=False)
            print("[Detector] GPU warm-up complete.")
        except Exception as e:
            print(f"[Detector] Warm-up skipped: {e}")

    def detect(self, frame):
        """
        Thread-safe inference on a BGR frame.
        Returns (persons, bags, weapons) lists.
        """
        WEAPON_LABELS = {43: "Knife", 76: "Scissors"}
        with self._infer_lock:
            with torch.no_grad():
                results = self.model.predict(
                    frame,
                    conf=config.YOLO_CONF,
                    iou=config.YOLO_IOU,
                    classes=config.YOLO_CLASSES,
                    device=self.device,
                    half=self.half,
                    verbose=False,
                )[0]

        persons, bags, weapons = [], [], []
        for box in results.boxes:
            cls  = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            if (x2 - x1) < 20 or (y2 - y1) < 40:
                continue
            entry = {"bbox": [x1, y1, x2, y2], "conf": conf, "cls": cls}
            if cls == config.CLS_PERSON:
                persons.append(entry)
            elif cls in config.CLS_BAGS:
                bags.append(entry)
            elif cls in config.CLS_WEAPONS:
                entry["label"] = WEAPON_LABELS.get(cls, "Weapon")
                weapons.append(entry)

        return persons, bags, weapons


# Backwards-compat alias for anything that imports `Detector`
Detector = SharedDetector
