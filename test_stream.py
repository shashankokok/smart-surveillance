import urllib.request
import time
req = urllib.request.Request('http://localhost:5000/api/start', data=b'{"source":"test_video.mp4"}', headers={'Content-Type': 'application/json'})
print("Starting stream:", urllib.request.urlopen(req).read().decode())
time.sleep(2)
print("Fetching frames...")
stream = urllib.request.urlopen('http://localhost:5000/video_feed')
print('Stream connected!')
print(stream.read(1024))
