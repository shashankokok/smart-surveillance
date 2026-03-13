# ─── tracker.py ───────────────────────────────────────────────────────────────
"""DeepSORT tracking wrapper — robust fallback if embedder fails."""

from deep_sort_realtime.deepsort_tracker import DeepSort
import config


class Tracker:
    def __init__(self):
        # Try embedding-based tracker first, fall back to IoU-only if it fails
        use_gpu = config.DEVICE == "cuda"
        try:
            self.tracker = DeepSort(
                max_age=config.MAX_AGE,
                n_init=config.N_INIT,
                embedder="mobilenet",
                embedder_gpu=use_gpu,   # ← use GPU for re-ID embeddings
                half=use_gpu,           # ← FP16 embedder on GPU
                nms_max_overlap=1.0,
            )
            print(f"[Tracker] DeepSORT + MobileNet embedder  GPU={use_gpu}")
        except Exception as e:
            print(f"[Tracker] Embedder failed ({e}), falling back to nn_budget=None")
            self.tracker = DeepSort(
                max_age=config.MAX_AGE,
                n_init=config.N_INIT,
                embedder=None,
                embedder_gpu=False,
                nms_max_overlap=1.0,
            )

    def update(self, persons, frame):
        """
        Args:
            persons: list of {bbox:[x1,y1,x2,y2], conf:float}
            frame:   BGR numpy array

        Returns:
            tracks: list of {track_id, bbox:[x1,y1,x2,y2], centroid:(cx,cy)}
        """
        if not persons:
            # Still call update so tracker ages existing tracks
            try:
                self.tracker.update_tracks([], frame=frame)
            except Exception:
                pass
            return []

        raw = []
        for p in persons:
            x1, y1, x2, y2 = p["bbox"]
            w = max(x2 - x1, 1)
            h = max(y2 - y1, 1)
            raw.append(([x1, y1, w, h], p["conf"], "person"))

        try:
            track_objs = self.tracker.update_tracks(raw, frame=frame)
        except Exception as e:
            print(f"[Tracker] update_tracks error: {e}")
            # Degrade gracefully: return detections as pseudo-tracks
            return [
                {
                    "track_id": i,
                    "bbox":     p["bbox"],
                    "centroid": (
                        (p["bbox"][0] + p["bbox"][2]) // 2,
                        (p["bbox"][1] + p["bbox"][3]) // 2,
                    ),
                }
                for i, p in enumerate(persons)
            ]

        tracks = []
        for t in track_objs:
            if not t.is_confirmed():
                continue
            try:
                x1, y1, x2, y2 = map(int, t.to_ltrb())
            except Exception:
                continue
            # Clamp to valid range
            x1, y1 = max(x1, 0), max(y1, 0)
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            tracks.append({
                "track_id": t.track_id,
                "bbox":     [x1, y1, x2, y2],
                "centroid": (cx, cy),
            })

        return tracks
