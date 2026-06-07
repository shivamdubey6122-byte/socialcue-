import cv2
import sys

# Replace with your actual ESP32 IP address (e.g. "http://192.168.1.100")
# Alternatively, pass it as a command line argument: python backend/camera_stream.py <IP>
ESP32_URL = "http://10.81.203.182" 

if len(sys.argv) > 1:
    arg = sys.argv[1]
    if arg == "0":
        ESP32_URL = 0
    else:
        if not arg.startswith("http://") and not arg.startswith("https://"):
            ESP32_URL = f"http://{arg}"
        else:
            ESP32_URL = arg

# Standard ESP32-CAM stream urls:
# - http://<IP>:81/stream (MJPEG Stream)
# - http://<IP>/stream
# - http://<IP>/capture (Still snapshot)
if isinstance(ESP32_URL, str) and not ESP32_URL.endswith("/stream") and ":" not in ESP32_URL[7:]:
    # Defaulting to standard ESP32-CAM port 81 stream if just a raw IP is given
    print("Tip: If the base URL fails, try appending :81/stream or /stream to your IP.")

print(f"Connecting to video source: {ESP32_URL}")
print("Press 'q' in the window to quit.")

cap = cv2.VideoCapture(ESP32_URL)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera connection failed. Verify IP, power, and that no other client is reading the stream.")
        break

    cv2.imshow("SocialCue Camera", frame)

    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Camera stream closed.")
