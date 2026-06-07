"""
Quick ESP32-CAM stream test — same URL as your working browser feed.
Run from SocialCue_Native folder:
  python test_camera.py
"""
import cv2

ESP32_URL = "http://10.81.203.182/"

print(f"Connecting to: {ESP32_URL}")
cap = cv2.VideoCapture(ESP32_URL)

if not cap.isOpened():
    print("Failed to open stream. Check WiFi, ESP32 power, and URL.")
    exit(1)

print("Stream OK. Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to get frame")
        break

    cv2.imshow("ESP32-CAM Stream", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("Done.")
