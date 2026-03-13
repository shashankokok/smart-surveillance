import cv2
from ultralytics import YOLO
import config

print("Loading model...")
model = YOLO(config.YOLO_MODEL)
print("Opening video...")
cap = cv2.VideoCapture('test_video.mp4')
ok, frame = cap.read()
if ok:
    print("Running inference...")
    results = model.predict(frame, conf=0.1, device=config.DEVICE, verbose=False)[0]
    print("Detections:")
    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        name = model.names[cls_id]
        print(f"Class: {cls_id} ({name}), Conf: {conf:.2f}")
else:
    print("Failed to read video")
cap.release()
