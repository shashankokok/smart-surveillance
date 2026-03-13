import cv2

cap = cv2.VideoCapture('test_video.mp4')
print('Opened:', cap.isOpened())
print('Frames:', cap.get(cv2.CAP_PROP_FRAME_COUNT))

ok, frame = cap.read()
if ok:
    print("Frame read successfully. Shape:", frame.shape)
    ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print('Encoded:', ret, 'Bytes:', len(buf.tobytes()))
    with open('test.jpg', 'wb') as f:
        f.write(buf.tobytes())
    print("test.jpg saved.")
else:
    print("Failed to read frame")

cap.release()
