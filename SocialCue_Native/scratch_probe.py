import socket
import requests

ips = ["10.81.203.182", "10.81.203.188"]
ports = [80, 81, 8080, 8888]

print("=== Starting Probing ===")
for ip in ips:
    for port in ports:
        # Test TCP connection
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        res = s.connect_ex((ip, port))
        s.close()
        
        if res == 0:
            print(f"[OPEN] {ip}:{port}")
            # Try HTTP requests on common paths
            for path in ["/", "/stream", "/capture"]:
                url = f"http://{ip}:{port}{path}"
                try:
                    r = requests.get(url, timeout=1.0, stream=True)
                    content_type = r.headers.get("Content-Type", "None")
                    print(f"  -> HTTP {url} returns status: {r.status_code}, content-type: {content_type}")
                except Exception as e:
                    print(f"  -> HTTP {url} failed: {type(e).__name__}")
print("=== Probing Done ===")
