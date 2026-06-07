"""
Background ESP32-CAM capture, face recognition, hardware output, and MJPEG feed for the dashboard.
"""
import base64
import os
import threading
import time

import cv2
from backend.database.mongo import get_settings
from backend.services.hardware_bridge import notify_faces_detected, sync_esp32_ip_from_settings
from backend.services.vision_ai import analyze_scene_native
from backend.utils.esp32_stream import build_stream_candidates, normalize_stream_url
from backend.utils.hardware_client import get_esp32_ip

_active_stream_url = None

_lock = threading.Lock()
_latest_jpeg = None
_latest_faces = []
_running = False
_worker_thread = None
_stream_connected = False
_frame_count = 0


def get_active_stream_url():
    return _active_stream_url


def _resolve_stream_url():
    settings = get_settings() or {}
    url = os.getenv("ESP32_URL") or settings.get("esp32_stream_url") or "http://10.81.203.182/"
    if isinstance(url, str) and url.isdigit():
        return int(url)
    return normalize_stream_url(str(url), settings.get("esp32_ip"))


def _open_esp32_capture():
    """Try multiple ESP32 stream URLs until one delivers frames."""
    global _active_stream_url
    settings = get_settings() or {}
    candidates = build_stream_candidates(settings)

    for url in candidates:
        print(f"[ESP32 Recognition] Trying stream: {url}")
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        # Avoid hanging when ESP32 is offline (OpenCV 4+)
        try:
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
        except Exception:
            pass
        if not cap.isOpened():
            cap.release()
            continue
        ret, frame = cap.read()
        if ret and frame is not None and frame.size > 0:
            _active_stream_url = url
            print(f"[ESP32 Recognition] Connected: {url}")
            return cap
        cap.release()

    _active_stream_url = None
    return None


def is_running():
    return _running


def is_stream_connected():
    return _stream_connected


def get_latest_faces():
    with _lock:
        return list(_latest_faces)


def get_latest_frame_base64():
    with _lock:
        if _latest_jpeg is None:
            return None
        b64 = base64.b64encode(_latest_jpeg).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"


def mjpeg_stream_generator():
    """Yields multipart JPEG frames for FastAPI StreamingResponse."""
    while True:
        with _lock:
            frame = _latest_jpeg
        if frame is None:
            time.sleep(0.05)
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )
        time.sleep(0.05)


def _encode_frame(frame):
    ret, buffer = cv2.imencode(".jpg", frame)
    if not ret:
        return None
    return buffer.tobytes()


def _process_frame(frame):
    global _latest_faces, _frame_count

    jpeg = _encode_frame(frame)
    if jpeg:
        with _lock:
            global _latest_jpeg
            _latest_jpeg = jpeg

    _frame_count += 1
    if _frame_count % 8 != 0:
        return

    b64 = base64.b64encode(jpeg).decode("utf-8") if jpeg else ""
    if not b64:
        return

    faces = analyze_scene_native(f"data:image/jpeg;base64,{b64}")
    with _lock:
        _latest_faces = faces

    notify_faces_detected(faces)


def _worker_loop():
    global _running, _stream_connected, _frame_count

    sync_esp32_ip_from_settings()
    print(f"[ESP32 Recognition] Hardware target IP: {get_esp32_ip()}")
    print(f"[ESP32 Recognition] Preferred stream: {_resolve_stream_url()}")

    cap = _open_esp32_capture()
    if cap is None:
        print("[ESP32 Recognition] ERROR: Could not open ESP32-CAM stream.")
        print("  Check: ESP32 powered on, same WiFi, URL http://10.81.203.182/")
        _stream_connected = False
        _running = False
        return

    _stream_connected = True
    _frame_count = 0

    try:
        while _running:
            ret, frame = cap.read()
            if not ret:
                print("[ESP32 Recognition] Frame read failed — retrying...")
                _stream_connected = False
                time.sleep(1)
                cap.release()
                cap = _open_esp32_capture()
                if cap is not None:
                    _stream_connected = True
                continue

            _stream_connected = True
            try:
                _process_frame(frame)
            except Exception as e:
                print(f"[ESP32 Recognition] Frame processing error: {e}")

            time.sleep(0.03)
    finally:
        cap.release()
        _stream_connected = False
        print("[ESP32 Recognition] Stream worker stopped.")


def start_worker():
    global _running, _worker_thread
    if _running:
        return True

    _running = True
    _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
    _worker_thread.start()
    return True


def stop_worker():
    global _running
    _running = False


def restart_worker():
    stop_worker()
    time.sleep(0.5)
    start_worker()
