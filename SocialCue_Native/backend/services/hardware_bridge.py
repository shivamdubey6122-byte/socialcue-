"""
Bridges vision results to ESP32 OLED/speaker and backend TTS.
"""
import time

from backend.database.mongo import get_settings, get_user, log_interaction
from backend.utils.hardware_client import send_result_to_hardware, set_esp32_ip
from backend.utils.speaker import speak

COOLDOWN_SECONDS = 5.0
_last_spoken = {}
_last_unknown_alert = 0.0


def _settings():
    try:
        return get_settings() or {}
    except Exception:
        return {}


def sync_esp32_ip_from_settings():
    settings = _settings()
    ip = settings.get("esp32_ip")
    stream_url = settings.get("esp32_stream_url", "")
    if not ip and isinstance(stream_url, str) and stream_url.startswith("http"):
        from urllib.parse import urlparse

        try:
            parsed = urlparse(stream_url)
            # netloc may contain hostname and optional port
            ip = parsed.netloc
        except Exception:
            ip = None
    if ip:
        set_esp32_ip(ip)


def notify_faces_detected(faces: list, *, use_backend_tts: bool = None, use_hardware: bool = None):
    """
    Process multi-face recognition results: OLED update, speaker, Mongo logs.
    """
    global _last_unknown_alert

    if not faces:
        return

    settings = _settings()
    if use_backend_tts is None:
        use_backend_tts = settings.get("backend_tts_enabled", True)
    if use_hardware is None:
        use_hardware = settings.get("hardware_enabled", True)

    sync_esp32_ip_from_settings()
    now = time.time()

    for face in faces:
        name = face.get("name", "Unknown")
        relation = face.get("relation", "Unknown")
        confidence = float(face.get("confidence", 1.0))

        if name == "Unknown":
            if use_hardware:
                send_result_to_hardware("Unknown", "Unknown", "unknown")
            if use_backend_tts and now - _last_unknown_alert > COOLDOWN_SECONDS:
                speak("Unknown person detected.")
                _last_unknown_alert = now
            continue

        if relation in ("Unknown", "N/A", None):
            user_data = get_user(name)
            relation = user_data.get("relation", "Unknown") if user_data else "Unknown"
            face["relation"] = relation

        last = _last_spoken.get(name.lower(), 0)
        if now - last <= COOLDOWN_SECONDS:
            continue

        _last_spoken[name.lower()] = now
        log_interaction(name, relation, "detected", confidence)

        if use_hardware:
            send_result_to_hardware(name, relation, "known")

        if use_backend_tts:
            speak(f"Known person detected. Name {name}. Relation {relation}.")


def notify_registration_success(name: str, relation: str):
    sync_esp32_ip_from_settings()
    settings = _settings()
    if settings.get("hardware_enabled", True):
        send_result_to_hardware(name, relation, "known")
    if settings.get("backend_tts_enabled", True):
        speak(f"Registration successful. Name is {name}. Relation is {relation}.")
