import requests

ESP32_CONTROL_IP = "10.81.203.182"


def set_esp32_ip(ip):
    """Dynamically updates the destination ESP32 IP address."""
    global ESP32_CONTROL_IP
    if not ip:
        return

    # Strip protocol prefix to normalize
    clean_ip = ip
    if clean_ip.startswith("http://"):
        clean_ip = clean_ip[7:]
    elif clean_ip.startswith("https://"):
        clean_ip = clean_ip[8:]

    # Strip trailing paths, but keep ports
    if "/" in clean_ip:
        clean_ip = clean_ip.split("/")[0]

    ESP32_CONTROL_IP = clean_ip
    print(f"[Hardware Client] ESP32 control target IP set to: {ESP32_CONTROL_IP}")


def get_esp32_ip():
    return ESP32_CONTROL_IP


def send_result_to_hardware(name, relation, status):
    """
    Sends recognition result JSON to ESP32 OLED/speaker endpoint.
    Falls back to terminal mock if device is offline.
    """
    payload = {
        "name": name,
        "relation": relation,
        "status": status,
    }

    url = f"http://{ESP32_CONTROL_IP}/result"
    print(f"\n[Hardware Client] Attempting transmission to ESP32 ({url})...")

    try:
        response = requests.post(url, json=payload, timeout=1.5)
        if response.status_code == 200:
            print(f"[Hardware Client] [OK] Success! ESP32 Response: {response.text.strip()}")
            return True
        print(f"[Hardware Client] [WARN] Hardware returned code: {response.status_code}")
        _simulate_rendering(name, relation, status)
        return False
    except requests.exceptions.Timeout:
        print("[Hardware Client] [ERROR] Timeout: ESP32 took too long to respond.")
        _simulate_rendering(name, relation, status)
        return False
    except requests.exceptions.RequestException:
        print("[Hardware Client] [ERROR] ESP32 is offline or unreachable.")
        _simulate_rendering(name, relation, status)
        return False


def _simulate_rendering(name, relation, status):
    print("------------------------------------------")
    print("|         --- VIRTUAL OLED ---           |")
    print(f"|  Name:     {name:<27} |")
    print(f"|  Relation: {relation:<27} |")
    print(f"|  Status:   {status:<27} |")
    print("------------------------------------------")

    if status == "known":
        print(f'[Speaker simulation]: "{name} detected, {relation}"\n')
    else:
        print('[Speaker simulation]: "Unknown person detected"\n')
