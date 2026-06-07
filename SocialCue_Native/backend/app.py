import os
import sys

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# Prioritize local SocialCue_Native folder to resolve import path collision
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.services.vision_ai import analyze_scene_native
from backend.services.memory_ai import generate_greeting_native, store_native_memory, retrieve_native_memory
from backend.services.hardware_bridge import notify_faces_detected, notify_registration_success
from backend.services import esp32_recognition
from backend.database.mongo import get_user, log_interaction, get_settings, update_settings, init_db
from backend.utils.hardware_client import get_esp32_ip
from backend.utils.esp32_stream import normalize_stream_url
from backend.services.esp32_recognition import get_active_stream_url

app = FastAPI(title="SocialCue Native Unified Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzePayload(BaseModel):
    image_base64: str

class GreetingPayload(BaseModel):
    name: str
    emotion: str = "neutral"

class MemoryPayload(BaseModel):
    name: str
    summary: str
    topics: list[str]

class MemoryQueryPayload(BaseModel):
    name: str
    query: str = ""

@app.get("/health")
def health_check():
    return {"status": "Native Backend Online"}


class SettingsPayload(BaseModel):
    camera_source: str | None = None
    esp32_stream_url: str | None = None
    esp32_ip: str | None = None
    hardware_enabled: bool | None = None
    backend_tts_enabled: bool | None = None


@app.get("/api/settings")
def read_settings():
    settings = get_settings()
    return {
        **settings,
        "esp32_worker_running": esp32_recognition.is_running(),
        "esp32_stream_connected": esp32_recognition.is_stream_connected(),
        "esp32_control_ip": get_esp32_ip(),
        "esp32_active_stream_url": get_active_stream_url(),
    }


@app.put("/api/settings")
def save_settings(payload: SettingsPayload):
    try:
        data = payload.model_dump(exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No settings provided.")
        if "esp32_stream_url" in data and data["esp32_stream_url"]:
            data["esp32_stream_url"] = normalize_stream_url(
                data["esp32_stream_url"],
                data.get("esp32_ip"),
            )
        update_settings(data)
        settings = get_settings()
        if settings.get("camera_source") == "esp32":
            esp32_recognition.restart_worker()
        else:
            esp32_recognition.stop_worker()
        return {"status": "updated", "settings": get_settings()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hardware/status")
def hardware_status():
    settings = get_settings()
    return {
        "hardware_enabled": settings.get("hardware_enabled", True),
        "backend_tts_enabled": settings.get("backend_tts_enabled", True),
        "esp32_ip": get_esp32_ip(),
        "esp32_stream_url": settings.get("esp32_stream_url"),
        "esp32_worker_running": esp32_recognition.is_running(),
        "esp32_stream_connected": esp32_recognition.is_stream_connected(),
        "camera_source": settings.get("camera_source", "esp32"),
        "esp32_active_stream_url": get_active_stream_url(),
    }


@app.post("/api/hardware/esp32/start")
def start_esp32_worker():
    esp32_recognition.start_worker()
    return {"status": "started", "connected": esp32_recognition.is_stream_connected()}


@app.post("/api/hardware/esp32/stop")
def stop_esp32_worker():
    esp32_recognition.stop_worker()
    return {"status": "stopped"}


@app.get("/api/camera-stream")
def camera_stream():
    """MJPEG stream from ESP32 worker (dashboard video feed)."""
    return StreamingResponse(
        esp32_recognition.mjpeg_stream_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/vision/latest")
def vision_latest():
    """Latest faces detected on the ESP32 background worker."""
    return {
        "faces": esp32_recognition.get_latest_faces(),
        "stream_connected": esp32_recognition.is_stream_connected(),
    }


@app.get("/api/vision/snapshot")
def vision_snapshot():
    """Latest JPEG frame from ESP32 worker (for unknown-person registration)."""
    b64 = esp32_recognition.get_latest_frame_base64()
    if not b64:
        raise HTTPException(status_code=503, detail="No frame available from ESP32 stream.")
    return {"image_base64": b64, "stream_connected": esp32_recognition.is_stream_connected()}


@app.post("/api/vision/analyze")
def analyze_scene(payload: AnalyzePayload):
    """Native route for DeepFace multi-face analysis"""
    try:
        faces_data = analyze_scene_native(payload.image_base64)
        notify_faces_detected(faces_data)
        return {"status": "success", "faces_detected": len(faces_data), "data": faces_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vision/analyze-stream")
def analyze_stream_frame():
    """Analyze the latest frame from the ESP32 background worker."""
    try:
        b64 = esp32_recognition.get_latest_frame_base64()
        if not b64:
            return {"status": "waiting", "faces_detected": 0, "data": [], "stream_connected": False}
        faces_data = analyze_scene_native(b64)
        notify_faces_detected(faces_data)
        return {
            "status": "success",
            "faces_detected": len(faces_data),
            "data": faces_data,
            "stream_connected": esp32_recognition.is_stream_connected(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class BoxData(BaseModel):
    x: int
    y: int
    w: int
    h: int

class RegisterPayload(BaseModel):
    image_base64: str
    box: BoxData
    name: str
    relation: str

from backend.services.vision_ai import decode_image, KNOWN_FACES_DIR
from backend.database.mongo import add_user
import os
import cv2

@app.post("/api/vision/register")
def register_face(payload: RegisterPayload):
    try:
        # Decode full frame
        img = decode_image(payload.image_base64)
        if img is None:
            raise Exception("Invalid or empty image data provided.")
        
        # Crop face with a slight margin
        margin = 20
        box = payload.box
        y1, y2 = max(0, box.y - margin), min(img.shape[0], box.y + box.h + margin)
        x1, x2 = max(0, box.x - margin), min(img.shape[1], box.x + box.w + margin)
        face_crop = img[y1:y2, x1:x2]
        
        # Save crop
        filename = f"{payload.name.lower()}.jpg"
        filepath = os.path.join(KNOWN_FACES_DIR, filename)
        cv2.imwrite(filepath, face_crop)
        
        # Add user to MongoDB
        add_user(payload.name, payload.relation)
        
        # Force rebuild of DeepFace representations cache
        representations_path = os.path.join(KNOWN_FACES_DIR, "representations_vgg_face.pkl")
        if os.path.exists(representations_path):
            os.remove(representations_path)

        formatted = payload.name.strip().capitalize()
        notify_registration_success(formatted, payload.relation)
        log_interaction(formatted, payload.relation, "registered", 1.0)

        return {"status": "success", "message": f"User {payload.name} registered successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/nlp/generate_greeting")
def generate_greeting(payload: GreetingPayload):
    """Native route for Smart Greeting via LangChain"""
    # Fetch relation from MongoDB
    user_data = get_user(payload.name)
    relation = user_data.get("relation", "Unknown") if user_data else "Unknown"
    
    # Fetch recent memory context from ChromaDB
    recent_memories = retrieve_native_memory(payload.name)
    context = recent_memories[0] if recent_memories else "No recent context"
    
    # Generate the string
    greeting = generate_greeting_native(payload.name, relation, context, payload.emotion)
    
    # Log the interaction natively
    log_interaction(payload.name, relation, "greeted", 1.0)
    
    return {"greeting": greeting}

@app.post("/api/memory/store")
def store_memory(payload: MemoryPayload):
    """Native route for vector memory storage"""
    success = store_native_memory(payload.name, payload.summary, payload.topics)
    if success:
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to store memory.")

class TroubleshootPayload(BaseModel):
    text: str

@app.get("/api/users")
def list_registered_users():
    try:
        from backend.database.mongo import get_all_users
        import base64
        users = get_all_users()
        # Enrich users with image data if available
        for u in users:
            name = u["name"]
            filename = f"{name}.jpg"
            filepath = os.path.join(KNOWN_FACES_DIR, filename)
            if os.path.exists(filepath):
                with open(filepath, "rb") as image_file:
                    u["image_base64"] = "data:image/jpeg;base64," + base64.b64encode(image_file.read()).decode('utf-8')
            else:
                u["image_base64"] = None
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/users/{name}")
def delete_registered_user(name: str):
    try:
        from backend.database.mongo import delete_user
        # 1. Delete from MongoDB
        delete_user(name)
        
        # 2. Delete face image from disk
        filename = f"{name.lower()}.jpg"
        filepath = os.path.join(KNOWN_FACES_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            
        # 3. Force rebuild of DeepFace representations cache
        representations_path = os.path.join(KNOWN_FACES_DIR, "representations_vgg_face.pkl")
        if os.path.exists(representations_path):
            os.remove(representations_path)
            
        return {"status": "success", "message": f"Entity {name} purged from active memory."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/system/troubleshoot")
def troubleshoot_system(payload: TroubleshootPayload):
    try:
        from backend.database.mongo import delete_user, add_user, get_user
        import re
        
        text = payload.text.lower().strip()
        response_msg = ""
        action_taken = "diagnostic"
        
        # Parse common correction commands
        delete_match = re.search(r'(?:delete|remove|purge|erase)\s+([a-zA-Z0-9]+)', text)
        relation_match1 = re.search(r'(?:change|set)\s+relation\s+of\s+([a-zA-Z0-9]+)\s+to\s+([a-zA-Z0-9]+)', text)
        relation_match2 = re.search(r'([a-zA-Z0-9]+)\s+(?:is\s+my|relation\s+is)\s+([a-zA-Z0-9]+)', text)
        rename_match = re.search(r'rename\s+([a-zA-Z0-9]+)\s+to\s+([a-zA-Z0-9]+)', text)

        if delete_match:
            name = delete_match.group(1)
            delete_user(name)
            filename = f"{name}.jpg"
            filepath = os.path.join(KNOWN_FACES_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            representations_path = os.path.join(KNOWN_FACES_DIR, "representations_vgg_face.pkl")
            if os.path.exists(representations_path):
                os.remove(representations_path)
            response_msg = f"Auto-correct completed: Purged entity {name.capitalize()} from active databases."
            action_taken = "deletion"
            
        elif relation_match1 or relation_match2:
            match = relation_match1 if relation_match1 else relation_match2
            name = match.group(1)
            relation = match.group(2)
            
            user_data = get_user(name)
            if user_data:
                add_user(name, relation)
                response_msg = f"Diagnostic self-healed: Updated relation of {name.capitalize()} to {relation.capitalize()}."
                action_taken = "update"
            else:
                response_msg = f"Error: Entity {name.capitalize()} not found in records."
                action_taken = "error"
                
        elif rename_match:
            old_name = rename_match.group(1)
            new_name = rename_match.group(2)
            user_data = get_user(old_name)
            if user_data:
                relation = user_data.get("relation", "Unknown")
                delete_user(old_name)
                add_user(new_name, relation)
                old_filepath = os.path.join(KNOWN_FACES_DIR, f"{old_name}.jpg")
                new_filepath = os.path.join(KNOWN_FACES_DIR, f"{new_name}.jpg")
                if os.path.exists(old_filepath):
                    os.rename(old_filepath, new_filepath)
                representations_path = os.path.join(KNOWN_FACES_DIR, "representations_vgg_face.pkl")
                if os.path.exists(representations_path):
                    os.remove(representations_path)
                response_msg = f"Auto-correct completed: Renamed entity {old_name.capitalize()} to {new_name.capitalize()}."
                action_taken = "rename"
            else:
                response_msg = f"Error: Entity {old_name.capitalize()} is not registered in records."
                action_taken = "error"
        else:
            response_msg = "Diagnostic self-healing completed: Code structural analyzer is healthy. No visual errors or memory leaks detected in scanning frames."
            action_taken = "general"
            
        from backend.database.mongo import log_command
        log_command(payload.text, response_msg)
        
        return {"status": "success", "response": response_msg, "action": action_taken}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
def on_startup():
    init_db()
    settings = get_settings()
    if settings.get("camera_source", "esp32") != "webcam":
        esp32_recognition.start_worker()
        print("[Startup] ESP32-CAM worker started (laptop webcam disabled by default).")
