import requests
import json

# ESP32 base URL (change to match your ESP32's IP address)
ESP32_CONTROL_IP = "10.0.0.1" 

def set_esp32_ip(ip):
    """Dynamically updates the destination ESP32 IP address."""
    global ESP32_CONTROL_IP
    if not ip:
        return
    
    # Strip protocols if provided
    if ip.startswith("http://"):
        ip = ip[7:]
    elif ip.startswith("https://"):
        ip = ip[8:]
    
    # Extract only the base host (remove ports and paths)
    if "/" in ip:
        ip = ip.split("/")[0]
    if ":" in ip:
        ip = ip.split(":")[0]
        
    ESP32_CONTROL_IP = ip
    print(f"[Hardware Client] ESP32 control target IP set to: {ESP32_CONTROL_IP}")

def send_result_to_hardware(name, relation, status):
    """
    Sends the facial recognition result JSON payload to the ESP32-CAM hardware.
    If the device is offline, falls back to a terminal mock rendering.
    """
    payload = {
        "name": name,
        "relation": relation,
        "status": status
    }
    
    # Targets the ESP32 API endpoint
    url = f"http://{ESP32_CONTROL_IP}/result"
    
    print(f"\n[Hardware Client] Attempting transmission to ESP32 ({url})...")
    
    try:
        # Use a short timeout of 1.5s so we don't stall the camera feed if the device is laggy
        response = requests.post(url, json=payload, timeout=1.5)
        if response.status_code == 200:
            print(f"[Hardware Client] [OK] Success! ESP32 Response: {response.text.strip()}")
            return True
        else:
            print(f"[Hardware Client] [WARN] Hardware returned warning code: {response.status_code}")
            _simulate_rendering(name, relation, status)
            return False
    except requests.exceptions.Timeout:
        print("[Hardware Client] [ERROR] Timeout: ESP32 took too long to respond.")
        _simulate_rendering(name, relation, status)
        return False
    except requests.exceptions.RequestException as e:
        print(f"[Hardware Client] [ERROR] Network Exception: ESP32 is offline or unreachable.")
        _simulate_rendering(name, relation, status)
        return False

def _simulate_rendering(name, relation, status):
    """Renders a beautiful mockup of the OLED screen & Speaker output in the terminal."""
    print("------------------------------------------")
    print("|         --- VIRTUAL OLED ---           |")
    print(f"|  Name:     {name:<27} |")
    print(f"|  Relation: {relation:<27} |")
    print(f"|  Status:   {status:<27} |")
    print("------------------------------------------")
    
    if status == "known":
        print(f"[Speaker simulation]: \"{name} detected, {relation}\"\n")
    else:
        print("[Speaker simulation]: \"Unknown person detected\"\n")
