import cv2
import numpy as np
import base64
import os
from deepface import DeepFace

from backend.database.mongo import get_user

# Native path to known faces
KNOWN_FACES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'known_faces'))
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

def decode_image(base64_str: str) -> np.ndarray:
    """Decodes a base64 image string into an OpenCV image."""
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    img_data = base64.b64decode(base64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def analyze_scene_native(base64_image: str) -> list:
    """
    Analyzes an image natively using DeepFace.
    Extracts multiple faces, predicts emotion, age, gender, and recognizes known faces.
    """
    try:
        img = decode_image(base64_image)
        if img is None:
            return []
    except Exception as e:
        print(f"Failed to decode image: {e}")
        return []

    # Temporary save for DeepFace processing
    temp_path = "temp_native_frame.jpg"
    cv2.imwrite(temp_path, img)

    results = []
    
    try:
        try:
            # Extract faces natively with enforce_detection=True to return early and save latency when no face is present
            face_objs = DeepFace.extract_faces(img_path=temp_path, enforce_detection=True, align=True)
            if not face_objs:
                return []

            if isinstance(face_objs, dict):
                face_objs = [face_objs]
        except Exception as e:
            # This is raised when no faces are detected in enforce_detection=True mode. We return immediately.
            return []

        # Analyze attributes natively (Emotion, Age, Gender)
        try:
            analyses = DeepFace.analyze(
                img_path=temp_path, 
                actions=['emotion', 'age', 'gender'], 
                enforce_detection=False,
                silent=True
            )
            if isinstance(analyses, dict):
                analyses = [analyses]
        except Exception as e:
            print(f"Native DeepFace analysis failed: {e}")
            analyses = []

        # Recognize identities natively
        try:
            if len(os.listdir(KNOWN_FACES_DIR)) > 0:
                identities = DeepFace.find(
                    img_path=temp_path, 
                    db_path=KNOWN_FACES_DIR, 
                    enforce_detection=False, 
                    silent=True
                )
            else:
                identities = []
        except Exception as e:
            print(f"Native Recognition failed: {e}")
            identities = []

        # Construct final payload
        for i, face_obj in enumerate(face_objs):
            facial_area = face_obj.get("facial_area", {})
            face_data = {
                "box": {
                    "x": facial_area.get("x", 0),
                    "y": facial_area.get("y", 0),
                    "w": facial_area.get("w", 0),
                    "h": facial_area.get("h", 0)
                },
                "name": "Unknown",
                "relation": "Unknown",
                "emotion": "neutral",
                "age": 0,
                "gender": "Unknown",
                "confidence": 0.0
            }
            
            if i < len(analyses):
                a = analyses[i]
                face_data["emotion"] = a.get("dominant_emotion", "neutral")
                face_data["age"] = a.get("age", 0)
                g = a.get("dominant_gender", a.get("gender", "Unknown"))
                face_data["gender"] = max(g, key=g.get) if isinstance(g, dict) else str(g)

            if i < len(identities) and len(identities[i]) > 0:
                matched_img_path = identities[i].iloc[0]['identity']
                filename = os.path.basename(matched_img_path)
                face_data["name"] = os.path.splitext(filename)[0].capitalize()
                if 'distance' in identities[i].columns:
                    face_data["confidence"] = float(1.0 - identities[i].iloc[0]['distance'])

            # Fetch the relation mapping from MongoDB
            if face_data["name"] != "Unknown":
                user_data = get_user(face_data["name"])
                if user_data:
                    face_data["relation"] = user_data.get("relation", "Unknown")

            results.append(face_data)
        return results
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
