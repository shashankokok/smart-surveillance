from ultralytics import YOLO

model = YOLO("yolo11n.pt")
print("Model classes mapping:")
print(model.names)
