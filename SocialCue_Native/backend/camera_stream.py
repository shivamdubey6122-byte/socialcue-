"""
Standalone ESP32-CAM stream viewer for SocialCue Native.
Run from SocialCue_Native folder:
  python backend/camera_stream.py
  python backend/camera_stream.py 192.168.1.100
  python backend/camera_stream.py http://192.168.1.100:81/stream
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2

from backend.database.mongo import get_settings

ESP32_URL = os.getenv("ESP32_URL", "http://10.81.203.182/")

if len(sys.argv) > 1:
    arg = sys.argv[1]
    if arg == "0":
        ESP32_URL = 0
    elif not arg.startswith("http://") and not arg.startswith("https://"):
        ESP32_URL = f"http://{arg}"
    else:
        ESP32_URL = arg
else:
    try:
        settings = get_settings()
        if settings and settings.get("esp32_stream_url"):
            ESP32_URL = settings["esp32_stream_url"]
    except Exception:
        pass

print(f"Connecting to video source: {ESP32_URL}")
print("Press 'q' in the window to quit.")

cap = cv2.VideoCapture(ESP32_URL)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera failed. Check ESP32 IP, power, and stream URL.")
        break

    cv2.imshow("SocialCue Camera", frame)

    if cv2.waitKey(1) == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("Camera stream closed.")
