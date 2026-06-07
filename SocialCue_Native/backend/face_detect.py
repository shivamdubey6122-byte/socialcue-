"""
Standalone face detection on ESP32-CAM stream for SocialCue Native.
Run from SocialCue_Native folder:
  python backend/face_detect.py YOUR_IP
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
from deepface import DeepFace

from backend.database.mongo import get_settings

url = os.getenv("ESP32_URL", "http://10.81.203.182/")

if len(sys.argv) > 1:
    arg = sys.argv[1]
    if arg == "0":
        url = 0
    elif not arg.startswith("http://") and not arg.startswith("https://"):
        url = f"http://{arg}"
    else:
        url = arg
else:
    try:
        settings = get_settings()
        if settings and settings.get("esp32_stream_url"):
            url = settings["esp32_stream_url"]
    except Exception:
        pass

print(f"Connecting to video source: {url}")
print("Press 'q' in the window to quit.")

cap = cv2.VideoCapture(url)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera failed")
        break

    try:
        faces = DeepFace.extract_faces(
            img_path=frame,
            detector_backend="opencv",
            enforce_detection=False,
        )
        for face in faces:
            x = face["facial_area"]["x"]
            y = face["facial_area"]["y"]
            w = face["facial_area"]["w"]
            h = face["facial_area"]["h"]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    except Exception:
        pass

    cv2.imshow("Detection", frame)

    if cv2.waitKey(1) == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
