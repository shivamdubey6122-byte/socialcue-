import os
import sys

# Disable ChromaDB telemetry (avoids "capture() takes 1 positional argument" warnings)
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from backend.database.mongo import get_settings, init_db
from backend.services import esp32_recognition
from backend.services.voice_ai import VoiceAssistant


def start_voice_assistant():
    assistant = VoiceAssistant()
    assistant.start()
    return assistant


def maybe_start_esp32_worker():
    settings = get_settings()
    # Default is ESP32 hardware camera — always start worker unless explicitly webcam-only
    if settings.get("camera_source", "esp32") != "webcam":
        esp32_recognition.start_worker()
        print("[Startup] ESP32-CAM worker started (not using laptop webcam).")


if __name__ == "__main__":
    print("==================================================")
    print(" SocialCue Native - Enterprise AI Platform Started")
    print("==================================================")

    init_db()
    assistant = start_voice_assistant()
    maybe_start_esp32_worker()

    try:
        uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
        esp32_recognition.stop_worker()
        assistant.stop()
        sys.exit(0)
