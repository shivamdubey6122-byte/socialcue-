from deepface import DeepFace
import cv2
import sys

# Replace with your actual ESP32 IP address
# Alternatively, pass it as a command line argument: python backend/face_detect.py <IP>
url = "http://10.0.0.1" 

if len(sys.argv) > 1:
    arg = sys.argv[1]
    if arg == "0":
        url = 0
    else:
        if not arg.startswith("http://") and not arg.startswith("https://"):
            url = f"http://{arg}"
        else:
            url = arg

print(f"Connecting to video source: {url}")
print("Running DeepFace detector. Press 'q' in the window to quit.")

cap = cv2.VideoCapture(url)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera feed failed.")
        break

    try:
        # Extract faces from the current frame
        faces = DeepFace.extract_faces(
            img_path=frame,
            detector_backend='opencv',
            enforce_detection=False
        )

        for face in faces:
            # DeepFace returns face area
            x = face['facial_area']['x']
            y = face['facial_area']['y']
            w = face['facial_area']['w']
            h = face['facial_area']['h']

            # Draw green rectangle around detected face
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )
    except Exception as e:
        # Prevent temporary deepface parsing errors from crashing stream
        pass

    cv2.imshow("Detection", frame)

    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Face detection closed.")
