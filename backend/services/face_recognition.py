import cv2
import os
import json
import time
from deepface import DeepFace
from backend.utils.speaker import speak
from backend.utils.hardware_client import send_result_to_hardware, set_esp32_ip

# Absolute paths for database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWN_FACES_DIR = os.path.join(BASE_DIR, 'database', 'known_faces')
RELATIONS_FILE = os.path.join(BASE_DIR, 'database', 'relations.json')

# Cache
_relations_cache = None
_recognition_cache = {} # Map crop hash/signature to name (optional, DeepFace is fast enough if skipping frames)
COOLDOWN_SECONDS = 5.0
last_seen = {}

def load_relations():
    global _relations_cache
    if _relations_cache is not None:
        return _relations_cache
    try:
        if os.path.exists(RELATIONS_FILE):
            with open(RELATIONS_FILE, 'r') as f:
                data = json.load(f)
                _relations_cache = {k.lower(): v for k, v in data.items()}
                return _relations_cache
    except Exception as e:
        print(f"Error loading relations: {e}")
    _relations_cache = {}
    return _relations_cache

def save_relations(relations):
    global _relations_cache
    try:
        os.makedirs(os.path.dirname(RELATIONS_FILE), exist_ok=True)
        with open(RELATIONS_FILE, 'w') as f:
            json.dump(relations, f, indent=4)
        _relations_cache = relations
    except Exception as e:
        print(f"Error saving relations: {e}")

def recognize_face(face_crop):
    """Uses DeepFace to compare face_crop against known_faces directory."""
    if not os.path.exists(KNOWN_FACES_DIR) or not os.listdir(KNOWN_FACES_DIR):
        return "Unknown"

    temp_img_path = "temp_detect_frame.jpg"
    try:
        cv2.imwrite(temp_img_path, face_crop)
        
        # DeepFace find returns a list of pandas dataframes
        dfs = DeepFace.find(
            img_path=temp_img_path, 
            db_path=KNOWN_FACES_DIR, 
            enforce_detection=False, 
            silent=True
        )
        
        if dfs and len(dfs) > 0 and not dfs[0].empty:
            matched_img_path = dfs[0].iloc[0]['identity']
            filename = os.path.basename(matched_img_path)
            name = os.path.splitext(filename)[0].capitalize()
            return name
            
        return "Unknown"
    except ValueError:
        return "Unknown"
    except Exception as e:
        print(f"DeepFace recognition error: {e}")
        return "Unknown"
    finally:
        if os.path.exists(temp_img_path):
            try:
                os.remove(temp_img_path)
            except:
                pass

def register_new_person(face_crop, frame):
    """Handles the terminal registration flow for an unknown person."""
    speak("Unknown person detected.")
    
    # Notify the hardware client immediately that an unknown face was detected
    send_result_to_hardware("Unknown", "Unknown", "unknown")
    
    # Show frozen frame while registering
    cv2.putText(frame, "Registration Mode - See Terminal", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.imshow("SocialCue - Face Recognition", frame)
    cv2.waitKey(1)
    
    print("\n--- Unknown Person Detected ---")
    name = input("Enter name: ").strip()
    if not name:
        print("Registration cancelled.")
        return None
        
    relation = input("Enter relation: ").strip()
    
    # Save Image
    os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
    filename = f"{name.lower()}.jpg"
    filepath = os.path.join(KNOWN_FACES_DIR, filename)
    cv2.imwrite(filepath, face_crop)
    
    # Update relations
    relations = load_relations()
    relations[name.lower()] = relation
    save_relations(relations)
    
    # Save to MongoDB
    try:
        from backend.database.mongo import add_user
        add_user(name, relation, filepath)
        print("[Database] Saved registration to MongoDB successfully.")
    except Exception as e:
        print(f"[Database] Error writing registration to MongoDB: {e}")
    
    formatted_name = name.capitalize()
    speak(f"Registration successful. Name is {formatted_name}. Relation is {relation}.")
    
    # Proactively send the registration details to the hardware OLED/Speaker
    send_result_to_hardware(formatted_name, relation, "known")
    
    # Force rebuild of DeepFace representations cache
    representations_path = os.path.join(KNOWN_FACES_DIR, "representations_vgg_face.pkl")
    if os.path.exists(representations_path):
        os.remove(representations_path)
        
    print("Resuming camera feed...\n")
    return formatted_name

def start_camera(stream_source=None):
    """Main camera loop with face detection, recognition, and UI overlay."""
    print("Initializing camera and Face Detector...")
    
    # Resolve stream source (webcam or ESP32 URL)
    if stream_source is None:
        import os
        stream_source = os.getenv("ESP32_URL", 0)
        try:
            if str(stream_source).isdigit():
                stream_source = int(stream_source)
        except:
            pass

    # Initialize Hardware client IP
    esp32_ip = "10.0.0.1"
    try:
        from backend.database.mongo import get_settings
        settings = get_settings()
        esp32_ip = settings.get("esp32_ip", "10.0.0.1")
    except Exception:
        pass

    # Auto-extract IP from camera stream URL if applicable
    if isinstance(stream_source, str) and stream_source.startswith("http"):
        from urllib.parse import urlparse
        try:
            parsed = urlparse(stream_source)
            if parsed.hostname:
                esp32_ip = parsed.hostname
        except:
            pass

    try:
        set_esp32_ip(esp32_ip)
    except Exception:
        pass

    cap = cv2.VideoCapture(stream_source)
    
    if not cap.isOpened():
        print(f"Error: Could not open the video source: {stream_source}")
        speak("Camera error.")
        return
        
    # Use standard Haar cascades for fast face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    print(f"System ready. Source: {stream_source}. Press 'q' in the video window to quit.")
    
    FRAME_SKIP = 10  # Only run deepface every 10 frames
    frame_count = 0
    current_faces_display = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
            
            if frame_count % FRAME_SKIP == 0:
                current_faces_display.clear()
                relations = load_relations()
                
                # Handle multiple people one by one
                for (x, y, w, h) in faces:
                    # Crop face with a slight margin
                    margin = 20
                    y1, y2 = max(0, y - margin), min(frame.shape[0], y + h + margin)
                    x1, x2 = max(0, x - margin), min(frame.shape[1], x + w + margin)
                    face_crop = frame[y1:y2, x1:x2]
                    
                    if face_crop.size == 0:
                        continue
                        
                    name = recognize_face(face_crop)
                    
                    if name == "Unknown":
                        # Freeze and start registration
                        new_name = register_new_person(face_crop, frame.copy())
                        if new_name:
                            name = new_name
                            relations = load_relations()
                            
                    if name and name != "Unknown":
                        relation = relations.get(name.lower(), "Unknown")
                        current_time = time.time()
                        
                        # Cooldown logic
                        if current_time - last_seen.get(name, 0) > COOLDOWN_SECONDS:
                            speak(f"Known person detected. Name {name}. Relation {relation}.")
                            last_seen[name] = current_time
                            print(f"Known person detected.\nName {name}.\nRelation {relation}.\n")
                            # Send known person result to ESP32 OLED / Speaker
                            send_result_to_hardware(name, relation, "known")
                            
                        # Save text to draw on skipped frames
                        current_faces_display.append({
                            "box": (x, y, w, h), 
                            "text": f"{name} ({relation})"
                        })

            # Draw boxes (either from active detection or cached from skipped frame)
            for (x, y, w, h) in faces:
                closest_text = "Scanning..."
                for display in current_faces_display:
                    bx, by, bw, bh = display["box"]
                    # Simple distance check to associate text with current bounding box
                    if abs(x - bx) < 50 and abs(y - by) < 50:
                        closest_text = display["text"]
                        break
                        
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, closest_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("SocialCue - Face Recognition", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except Exception as e:
        print(f"System runtime error: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

def get_video_stream(stream_source=None):
    """
    Generator function for Flask streaming.
    Captures frames, runs face detection/recognition, and yields processed frames for frontend rendering.
    """
    import os
    if stream_source is None:
        stream_source = os.getenv("ESP32_URL", 0)
        try:
            if str(stream_source).isdigit():
                stream_source = int(stream_source)
        except:
            pass

    # Resolve settings and target IP
    esp32_ip = "10.0.0.1"
    try:
        from backend.database.mongo import get_settings
        settings = get_settings()
        esp32_ip = settings.get("esp32_ip", "10.0.0.1")
    except Exception:
        pass

    # Auto-extract IP from camera stream URL if applicable
    if isinstance(stream_source, str) and stream_source.startswith("http"):
        from urllib.parse import urlparse
        try:
            parsed = urlparse(stream_source)
            if parsed.hostname:
                esp32_ip = parsed.hostname
        except:
            pass

    try:
        set_esp32_ip(esp32_ip)
    except Exception:
        pass

    cap = cv2.VideoCapture(stream_source)
    if not cap.isOpened():
        print(f"[Stream Generator] Error: Could not open source: {stream_source}")
        return

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    FRAME_SKIP = 10
    frame_count = 0
    current_faces_display = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
            
            if frame_count % FRAME_SKIP == 0:
                current_faces_display.clear()
                relations = load_relations()
                
                for (x, y, w, h) in faces:
                    margin = 20
                    y1, y2 = max(0, y - margin), min(frame.shape[0], y + h + margin)
                    x1, x2 = max(0, x - margin), min(frame.shape[1], x + w + margin)
                    face_crop = frame[y1:y2, x1:x2]
                    
                    if face_crop.size == 0:
                        continue
                        
                    name = recognize_face(face_crop)
                    
                    if name == "Unknown":
                        # In non-blocking streaming mode, notify hardware but avoid blocking terminal inputs
                        send_result_to_hardware("Unknown", "Unknown", "unknown")
                        current_faces_display.append({
                            "box": (x, y, w, h), 
                            "text": "Unknown Person"
                        })
                    elif name:
                        relation = relations.get(name.lower(), "Unknown")
                        current_time = time.time()
                        
                        if current_time - last_seen.get(name, 0) > COOLDOWN_SECONDS:
                            speak(f"Known person detected. Name {name}. Relation {relation}.")
                            last_seen[name] = current_time
                            send_result_to_hardware(name, relation, "known")
                            
                        current_faces_display.append({
                            "box": (x, y, w, h), 
                            "text": f"{name} ({relation})"
                        })

            # Draw boxes on stream frame
            for (x, y, w, h) in faces:
                closest_text = "Scanning..."
                for display in current_faces_display:
                    bx, by, bw, bh = display["box"]
                    if abs(x - bx) < 50 and abs(y - by) < 50:
                        closest_text = display["text"]
                        break
                        
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, closest_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Encode frame as JPEG bytes
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
        cap.release()
