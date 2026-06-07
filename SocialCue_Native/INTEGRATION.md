# SocialCue Native — ESP32 Integration

## Your ESP32 stream URL

```
http://10.81.203.182/
```

## Run (2 terminals)

### Terminal 1 — Backend
```powershell
cd SocialCue_Native
python run_server.py
```

### Terminal 2 — Frontend
```powershell
cd SocialCue_Native\frontend
npm run dev
```

Open the URL Vite prints (e.g. http://localhost:5173).

## Dashboard

1. Log in
2. **HARDWARE LINK** → **ESP32-CAM Stream** → URL `http://10.81.203.182/` → **Save & Apply**
3. **TACTICAL HUD** → **ENGAGE NEURAL SCAN**

## Test ESP32 only (Python)

```powershell
cd SocialCue_Native
python test_camera.py
```

## If port 8000 is busy

```powershell
netstat -ano | findstr ":8000"
taskkill /PID <pid> /F
python run_server.py
```
