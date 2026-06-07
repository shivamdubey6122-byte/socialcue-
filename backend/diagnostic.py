import requests

ip = '10.81.203.182'
endpoints = [
    f'http://{ip}/stream',
    f'http://{ip}:81/stream',
    f'http://{ip}/capture',
    f'http://{ip}/'
]

print("=== ESP32-CAM Diagnostic Check ===")
for url in endpoints:
    try:
        r = requests.get(url, timeout=2.0, stream=True)
        content_type = r.headers.get("Content-Type", "None")
        print(f"[FOUND] {url}")
        print(f"        Status Code: {r.status_code}")
        print(f"        Content-Type: {content_type}\n")
    except Exception as e:
        print(f"[FAILED] {url}")
        print(f"         Reason: {type(e).__name__}\n")
