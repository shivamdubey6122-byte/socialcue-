"""ESP32-CAM stream URL helpers (multiple common firmware paths)."""

import os
from urllib.parse import urlparse

# Your working ESP32-CAM stream (from Serial Monitor / browser)
DEFAULT_ESP32_IP = "10.81.203.182"
DEFAULT_ESP32_STREAM_URL = f"http://{DEFAULT_ESP32_IP}/"


def extract_ip(url_or_ip: str) -> str:
    if not url_or_ip:
        return DEFAULT_ESP32_IP
    s = url_or_ip.strip()
    if s.startswith("http://"):
        s = s[7:]
    elif s.startswith("https://"):
        s = s[8:]
    if "/" in s:
        s = s.split("/")[0]
    if ":" in s:
        s = s.split(":")[0]
    return s


def build_stream_candidates(settings: dict | None = None) -> list:
    """
    ESP32-CAM firmware varies. Your device uses http://IP/ — try that first.
    """
    settings = settings or {}
    primary = os.getenv("ESP32_URL") or settings.get("esp32_stream_url") or DEFAULT_ESP32_STREAM_URL
    ip = settings.get("esp32_ip") or extract_ip(str(primary)) or DEFAULT_ESP32_IP

    candidates = []

    def add(url):
        if url and url not in candidates:
            candidates.append(url)

    if primary:
        add(primary if isinstance(primary, str) else str(primary))

    # Your firmware: root URL (most important for 10.81.203.182)
    add(f"http://{ip}/")
    add(f"http://{ip}/stream")
    add(f"http://{ip}:81/stream")
    add(f"http://{ip}:81/")

    if primary and not str(primary).startswith("http"):
        add(f"http://{extract_ip(str(primary))}/")

    return candidates


def normalize_stream_url(url: str, ip: str | None = None) -> str:
    """Keep http://IP/ as-is when that is what the ESP32 serves."""
    if not url:
        host = ip or DEFAULT_ESP32_IP
        return f"http://{host}/"

    u = url.strip()
    if not u.startswith("http"):
        u = f"http://{u}"

    parsed = urlparse(u)
    host = parsed.hostname or ip or extract_ip(u)

    # Already a full path (/stream, :81/stream, etc.) — do not rewrite
    path = parsed.path or ""
    if path not in ("", "/") or parsed.port:
        if not u.endswith("/") and path in ("", "/"):
            return u + "/"
        return u

    return f"http://{host}/"
