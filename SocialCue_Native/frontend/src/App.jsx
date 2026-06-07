import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Camera, Activity, Server, Users, Settings, Mic, BrainCircuit, ScanEye, 
  Zap, Lock, ShieldCheck, Fingerprint, Database, UserCheck, Flame, 
  HelpCircle, Send, MessageSquare, Clock, Heart, Radio, Cpu, RefreshCw
} from 'lucide-react';

const API_URL = "http://localhost:8000";

function App() {
  // Navigation & Authentication
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [loginRole, setLoginRole] = useState("Admin");
  const [loginEmail, setLoginEmail] = useState("shiva@socialcue.ai");
  const [loginPassword, setLoginPassword] = useState("••••••••");
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  
  // Dashboard & Navigation tabs
  const [currentTab, setCurrentTab] = useState("dashboard"); // dashboard, analytics, timeline, chat, matrix, settings
  const [isAnalyzing, setIsAnalyzing] = useState(true);
  const [facesData, setFacesData] = useState([]);
  const [interactionLogs, setInteractionLogs] = useState([]);
  const [registeredUsers, setRegisteredUsers] = useState([]);
  const [troubleshootInput, setTroubleshootInput] = useState("");
  const [troubleshootResponse, setTroubleshootResponse] = useState("");
  const [isTroubleshooting, setIsTroubleshooting] = useState(false);

  // Hardware / ESP32 settings
  const [cameraSource, setCameraSource] = useState("webcam");
  const [esp32StreamUrl, setEsp32StreamUrl] = useState("http://10.81.203.182/");
  const [esp32Ip, setEsp32Ip] = useState("10.81.203.182");
  const [hardwareEnabled, setHardwareEnabled] = useState(true);
  const [backendTtsEnabled, setBackendTtsEnabled] = useState(true);
  const [esp32Connected, setEsp32Connected] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  
  // Registration Modal State
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [unknownFaceData, setUnknownFaceData] = useState(null);
  const [regName, setRegName] = useState("");
  const [regRelation, setRegRelation] = useState("");
  
  // Details of currently detected person
  const [selectedPerson, setSelectedPerson] = useState({
    name: "Awaiting Detection",
    relation: "N/A",
    emotion: "N/A",
    status: "Standby",
    lastSeen: "Never",
    visits: 0
  });

  // Jarvis Chat State
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState([
    { sender: "jarvis", text: "System initialized. Cognitive Core loaded. Ready to assist you, Shiva." }
  ]);
  const [isJarvisSpeaking, setIsJarvisSpeaking] = useState(false);

  // Time & System Stats
  const [systemTime, setSystemTime] = useState(new Date().toLocaleTimeString());
  const [systemHealth, setSystemHealth] = useState({ cpu: 14, ram: 42, fps: 0 });

  const lastSpokenRef = useRef({});
  const isProcessingRef = useRef(false);

  const videoRef = useRef(null);
  const esp32ImgRef = useRef(null);
  const canvasRef = useRef(null);
  const hiddenCanvasRef = useRef(null);

  const fetchSettings = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/settings`);
      setCameraSource(res.data.camera_source || "esp32");
      setEsp32StreamUrl(res.data.esp32_stream_url || "http://10.81.203.182/");
      setEsp32Ip(res.data.esp32_ip || "10.81.203.182");
      setHardwareEnabled(res.data.hardware_enabled !== false);
      setBackendTtsEnabled(res.data.backend_tts_enabled !== false);
      setEsp32Connected(!!res.data.esp32_stream_connected);
    } catch (e) {
      console.error("Failed to load settings:", e);
    }
  };

  const saveHardwareSettings = async () => {
    setSavingSettings(true);
    try {
      const res = await axios.put(`${API_URL}/api/settings`, {
        camera_source: cameraSource,
        esp32_stream_url: esp32StreamUrl,
        esp32_ip: esp32Ip,
        hardware_enabled: hardwareEnabled,
        backend_tts_enabled: backendTtsEnabled,
      });
      setEsp32Connected(!!res.data.settings?.esp32_stream_connected);
      speak("Hardware configuration saved. ESP32 integration updated.");
    } catch (e) {
      console.error("Failed to save settings:", e);
      speak("Failed to save hardware settings.");
    } finally {
      setSavingSettings(false);
    }
  };

  const drawBoxes = (faces) => {
    if (!canvasRef.current) return;
    const ctx = canvasRef.current.getContext('2d');
    ctx.clearRect(0, 0, 640, 480);

    faces.forEach(f => {
      const { box, name, relation, emotion, gender, confidence } = f;

      const isKnown = name !== "Unknown";
      const color = isKnown ? '#00f0ff' : '#ff0055';
      const rgb = isKnown ? '0, 240, 255' : '255, 0, 85';

      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;

      const length = 25;
      ctx.beginPath();
      ctx.moveTo(box.x, box.y + length); ctx.lineTo(box.x, box.y); ctx.lineTo(box.x + length, box.y);
      ctx.moveTo(box.x + box.w - length, box.y); ctx.lineTo(box.x + box.w, box.y); ctx.lineTo(box.x + box.w, box.y + length);
      ctx.moveTo(box.x, box.y + box.h - length); ctx.lineTo(box.x, box.y + box.h); ctx.lineTo(box.x + length, box.y + box.h);
      ctx.moveTo(box.x + box.w - length, box.y + box.h); ctx.lineTo(box.x + box.w, box.y + box.h); ctx.lineTo(box.x + box.w, box.y + box.h - length);
      ctx.stroke();

      ctx.shadowBlur = 10;
      ctx.shadowColor = color;

      ctx.fillStyle = `rgba(${rgb}, 0.2)`;
      ctx.strokeStyle = `rgba(${rgb}, 0.6)`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(box.x, box.y - 60, Math.max(190, box.w), 50, 4);
      ctx.fill();
      ctx.stroke();

      ctx.shadowBlur = 0;

      ctx.fillStyle = '#ffffff';
      ctx.font = '600 13px monospace';
      ctx.fillText(`${name.toUpperCase()} [${(relation || 'UNKNOWN').toUpperCase()}]`, box.x + 8, box.y - 42);

      ctx.fillStyle = `rgba(${rgb}, 0.95)`;
      ctx.font = '500 11px monospace';
      ctx.fillText(`${gender.toUpperCase()} // CONFIDENCE: ${(confidence*100).toFixed(0)}%`, box.x + 8, box.y - 25);
      ctx.fillText(`EMOTION: ${emotion.toUpperCase()}`, box.x + 8, box.y - 12);
    });
  };

  const applyFacesToUi = (faces, base64Image = null) => {
    setFacesData(faces);
    drawBoxes(faces);

    if (faces.length > 0) {
      const mainFace = faces[0];
      setSelectedPerson({
        name: mainFace.name,
        relation: mainFace.relation || "Unknown",
        emotion: mainFace.emotion,
        status: mainFace.name !== "Unknown" ? "Known" : "Unidentified",
        lastSeen: "Active now",
        visits: mainFace.name !== "Unknown" ? 15 : 0,
      });

      setInteractionLogs((prev) => {
        const newLogs = [
          ...faces.map((f) => ({ ...f, time: new Date().toLocaleTimeString() })),
          ...prev,
        ];
        return newLogs.slice(0, 8);
      });

      const unknownFace = faces.find((f) => f.name === "Unknown");
      if (unknownFace && !showRegisterModal) {
        if (!backendTtsEnabled) {
          speak("Warning. Unknown person detected in security feed. Halting scan for registration.");
        }
        setIsAnalyzing(false);

        const attachUnknown = async () => {
          let image = base64Image;
          if (!image && cameraSource === "esp32") {
            try {
              const snap = await axios.get(`${API_URL}/api/vision/snapshot`);
              image = snap.data.image_base64;
            } catch (err) {
              console.error("Snapshot failed:", err);
            }
          }
          if (image) {
            setUnknownFaceData({ image, box: unknownFace.box });
            setShowRegisterModal(true);
          }
        };
        attachUnknown();
      } else if (!unknownFace) {
        if (!backendTtsEnabled) {
          faces.forEach((f) => {
            if (f.name !== "Unknown") {
              const now = Date.now();
              const lastSpoken = lastSpokenRef.current[f.name] || 0;
              if (now - lastSpoken > 15000) {
                speak(`Known person detected. Name ${f.name}. Relation ${f.relation || "Unknown"}.`);
                lastSpokenRef.current[f.name] = now;
              }
            }
          });
        }
      }
    }
  };

  // System time updater
  useEffect(() => {
    const timer = setInterval(() => {
      setSystemTime(new Date().toLocaleTimeString());
      if (isAnalyzing) {
        setSystemHealth(prev => ({
          cpu: Math.floor(Math.random() * 20) + 30,
          ram: Math.floor(Math.random() * 5) + 55,
          fps: Math.floor(Math.random() * 3) + 28
        }));
      } else {
        setSystemHealth(prev => ({
          cpu: Math.floor(Math.random() * 5) + 10,
          ram: Math.floor(Math.random() * 2) + 40,
          fps: 0
        }));
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [isAnalyzing]);

  // Audio synthesis helper
  const speak = (text) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel(); // Cancel ongoing speech
      const msg = new SpeechSynthesisUtterance(text);
      msg.onstart = () => setIsJarvisSpeaking(true);
      msg.onend = () => setIsJarvisSpeaking(false);
      msg.onerror = () => setIsJarvisSpeaking(false);
      window.speechSynthesis.speak(msg);
    }
  };

  const fetchRegisteredUsers = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/users`);
      setRegisteredUsers(res.data);
    } catch (e) {
      console.error("Failed to fetch registered users:", e);
    }
  };

  useEffect(() => {
    if (isLoggedIn) {
      fetchRegisteredUsers();
      fetchSettings().then(async () => {
        try {
          await axios.post(`${API_URL}/api/hardware/esp32/start`);
          const st = await axios.get(`${API_URL}/api/hardware/status`);
          setEsp32Connected(!!st.data.esp32_stream_connected);
          if (st.data.camera_source) setCameraSource(st.data.camera_source);
        } catch (e) {
          console.error("ESP32 worker start:", e);
        }
      });
    }
  }, [isLoggedIn, currentTab]);

  const handleDeleteUser = async (name) => {
    if (!confirm(`Are you sure you want to permanently delete and purge ${name} from active memory?`)) return;
    try {
      const res = await axios.delete(`${API_URL}/api/users/${name}`);
      speak(res.data.message || `Purged ${name} from active database.`);
      fetchRegisteredUsers();
    } catch (e) {
      console.error("Failed to delete user:", e);
      speak(`Error purging ${name} from memory.`);
    }
  };

  const handleTroubleshootSubmit = async (e) => {
    e.preventDefault();
    if (!troubleshootInput.trim()) return;

    setIsTroubleshooting(true);
    speak("Initializing auto-correct diagnostics core...");
    try {
      const res = await axios.post(`${API_URL}/api/system/troubleshoot`, { text: troubleshootInput });
      setTroubleshootResponse(res.data.response);
      speak(res.data.response);
      setTroubleshootInput("");
      fetchRegisteredUsers();
    } catch (e) {
      console.error("Troubleshooter failed:", e);
      setTroubleshootResponse("Auto-correct engine offline. Please check connection.");
      speak("Error occurred. Troubleshooter failed.");
    } finally {
      setIsTroubleshooting(false);
    }
  };

  const handleLogin = () => {
    setIsLoggingIn(true);
    speak("Initializing biometric scan. User authentication authorized.");
    setTimeout(() => {
      setIsLoggedIn(true);
      setIsLoggingIn(false);
      speak(`Welcome back, Shiva. Level ${loginRole} access granted.`);
    }, 2000);
  };

  const handleRegister = async () => {
    if (!regName || !regRelation || !unknownFaceData) return;
    try {
      await axios.post(`${API_URL}/api/vision/register`, {
        image_base64: unknownFaceData.image,
        box: unknownFaceData.box,
        name: regName,
        relation: regRelation
      });
      speak(`Registration successful. Registered ${regName} as ${regRelation}. Resuming neural scan.`);
      
      // Update selected person on registration success
      setSelectedPerson({
        name: regName.charAt(0).toUpperCase() + regName.slice(1),
        relation: regRelation,
        emotion: "neutral",
        status: "Known",
        lastSeen: "Just now",
        visits: 1
      });

      setShowRegisterModal(false);
      setRegName("");
      setRegRelation("");
      setUnknownFaceData(null);
      setIsAnalyzing(true);
    } catch(e) {
      console.error(e);
      speak("Error occurred during registration database insert.");
      alert("Failed to register.");
    }
  };

  // Initialize camera: browser webcam OR ESP32 MJPEG from backend
  useEffect(() => {
    const startWebcam = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (err) {
        console.error("Webcam Initialization Error:", err);
      }
    };

    if (!isLoggedIn) return;

    if (cameraSource === "webcam") {
      startWebcam();
    } else if (videoRef.current?.srcObject) {
      videoRef.current.srcObject.getTracks().forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }

    return () => {
      if (videoRef.current?.srcObject) {
        videoRef.current.srcObject.getTracks().forEach((t) => t.stop());
      }
    };
  }, [isLoggedIn, cameraSource]);

  // AI Analysis Loop (webcam POST frames, ESP32 polls backend stream worker)
  useEffect(() => {
    let interval;
    if (isAnalyzing && isLoggedIn) {
      interval = setInterval(async () => {
        if (isProcessingRef.current) return;
        isProcessingRef.current = true;

        try {
          if (cameraSource === "esp32") {
            const res = await axios.get(`${API_URL}/api/vision/latest`);
            setEsp32Connected(!!res.data.stream_connected);
            applyFacesToUi(res.data.faces || []);
          } else {
            if (!videoRef.current || !hiddenCanvasRef.current) return;
            const hiddenCtx = hiddenCanvasRef.current.getContext("2d");
            hiddenCtx.drawImage(videoRef.current, 0, 0, 640, 480);
            const base64Image = hiddenCanvasRef.current.toDataURL("image/jpeg", 0.8);
            const res = await axios.post(`${API_URL}/api/vision/analyze`, { image_base64: base64Image });
            applyFacesToUi(res.data.data || [], base64Image);
          }
        } catch (e) {
          console.error("Backend server connection failed:", e);
        } finally {
          isProcessingRef.current = false;
        }
      }, 800);
    } else {
      if (canvasRef.current) {
        const ctx = canvasRef.current.getContext("2d");
        ctx.clearRect(0, 0, 640, 480);
      }
      setFacesData([]);
    }
    return () => clearInterval(interval);
  }, [isAnalyzing, isLoggedIn, cameraSource, backendTtsEnabled, showRegisterModal]);

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userText = chatInput;
    setChatMessages(prev => [...prev, { sender: "user", text: userText }]);
    setChatInput("");

    const textLower = userText.toLowerCase();

    // Check if it's a database correction or deletion command
    const isCommand = textLower.includes("delete") || 
                      textLower.includes("remove") || 
                      textLower.includes("purge") || 
                      textLower.includes("erase") || 
                      textLower.includes("relation") || 
                      textLower.includes("is my") || 
                      textLower.includes("rename");

    if (isCommand) {
      try {
        const res = await axios.post(`${API_URL}/api/system/troubleshoot`, { text: userText });
        const jarvisReply = res.data.response;
        setChatMessages(prev => [...prev, { sender: "jarvis", text: jarvisReply }]);
        speak(jarvisReply);
        fetchRegisteredUsers();
      } catch (err) {
        console.error("AI troubleshooting via chat failed:", err);
        const errorReply = "Core connection error. Unable to perform secure database modifications.";
        setChatMessages(prev => [...prev, { sender: "jarvis", text: errorReply }]);
        speak(errorReply);
      }
    } else {
      // General conversation responses (with 1s simulated thinking delay)
      setTimeout(() => {
        let jarvisReply = "";
        if (textLower.includes("who visited") || textLower.includes("visitor")) {
          jarvisReply = "Querying MongoDB logs. Shivam, registered as Admin, was matched in the main visual scanner. No foreign or unknown entities have breached visual sensors today.";
        } else if (textLower.includes("health") || textLower.includes("status")) {
          jarvisReply = "All systems operational, Shiva. Core neural processor is executing at 800ms frame gaps. Database client: active. Audio synthesizer: online. Camera buffer: nominal.";
        } else if (textLower.includes("hello") || textLower.includes("jarvis") || textLower.includes("hi")) {
          jarvisReply = "Always standing by, Shiva. How can I assist you with your cognitive surveillance overlay today?";
        } else {
          jarvisReply = "Surveillance networks are scanning. Cognitive data analytics show a stable visual field. Speak a specific query and I shall parse it.";
        }
        setChatMessages(prev => [...prev, { sender: "jarvis", text: jarvisReply }]);
        speak(jarvisReply);
      }, 1000);
    }
  };

  const emotionEmoji = {
      happy: '😊', sad: '😢', angry: '😠', surprise: '😲', fear: '😨', disgust: '🤢', neutral: '😐'
  };

  // Render Futuristic Login Page
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-[#030303] text-gray-100 font-mono flex items-center justify-center relative overflow-hidden selection:bg-cyan-500/30">
        {/* Animated Cyber Grid Overlay */}
        <div className="absolute inset-0 cyber-grid-overlay opacity-30 pointer-events-none"></div>
        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-indigo-500/5 via-transparent to-cyan-500/5 pointer-events-none"></div>
        
        {/* Glowing Orbs */}
        <div className="absolute top-1/4 left-1/4 w-80 h-80 bg-violet-600/10 blur-[130px] rounded-full"></div>
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-cyan-600/10 blur-[130px] rounded-full"></div>

        <div className="w-full max-w-md p-8 rounded-2xl border border-cyan-500/25 bg-black/60 backdrop-blur-xl relative z-10 shadow-[0_0_50px_rgba(6,182,212,0.1)]">
          <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-cyan-500 via-violet-500 to-cyan-500"></div>
          
          <div className="text-center mb-8">
            <BrainCircuit className="w-16 h-16 text-cyan-400 mx-auto mb-3 animate-[rotate-hud_15s_linear_infinite]" />
            <h1 className="text-2xl font-black tracking-widest text-cyan-400">COGNITIVE AID SECURE</h1>
            <p className="text-xs text-gray-500 mt-1 uppercase">Neural Surveillance & Memory System</p>
          </div>

          <div className="space-y-5">
            <div>
              <label className="block text-xxs font-bold text-cyan-500/80 uppercase tracking-widest mb-1.5">Access Role</label>
              <div className="grid grid-cols-3 gap-2">
                {["Admin", "Caregiver", "Observer"].map(role => (
                  <button 
                    key={role}
                    onClick={() => setLoginRole(role)}
                    className={`py-1.5 rounded border text-xxs font-bold uppercase transition-all ${
                      loginRole === role 
                        ? 'bg-cyan-500/15 border-cyan-400 text-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.2)]' 
                        : 'bg-white/5 border-white/5 text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    {role}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xxs font-bold text-cyan-500/80 uppercase tracking-widest mb-1.5">Security Identifier</label>
              <div className="relative">
                <input 
                  type="email" 
                  value={loginEmail}
                  onChange={e => setLoginEmail(e.target.value)}
                  className="w-full bg-black/85 border border-white/10 rounded-lg px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500/50 transition-colors"
                />
                <Lock className="w-4 h-4 text-cyan-500/50 absolute right-3 top-3" />
              </div>
            </div>

            <div>
              <label className="block text-xxs font-bold text-cyan-500/80 uppercase tracking-widest mb-1.5">Secure Password</label>
              <input 
                type="password" 
                value={loginPassword}
                onChange={e => setLoginPassword(e.target.value)}
                className="w-full bg-black/85 border border-white/10 rounded-lg px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500/50 transition-colors"
              />
            </div>

            <div className="pt-2">
              <button 
                onClick={handleLogin}
                disabled={isLoggingIn}
                className="w-full py-3 rounded-lg bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-500 hover:to-violet-500 text-white font-bold text-xs uppercase tracking-widest transition-all duration-300 shadow-[0_0_15px_rgba(6,182,212,0.3)] hover:shadow-[0_0_25px_rgba(6,182,212,0.5)] flex items-center justify-center gap-2"
              >
                {isLoggingIn ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-white" />
                    Biometrics Scanning...
                  </>
                ) : (
                  <>
                    <Fingerprint className="w-4 h-4 text-white" />
                    Initialize AI Interface
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-center gap-2 text-xxs text-cyan-500/60 uppercase">
            <ShieldCheck className="w-3.5 h-3.5" /> SECURE HANDSHAKE NOMINAL
          </div>
        </div>
      </div>
    );
  }

  // Main Futuristic Dashboard View
  return (
    <div className="min-h-screen bg-[#030303] text-gray-100 font-mono flex selection:bg-cyan-500/30">
      
      {/* HUD left sidebar */}
      <aside className="w-64 border-r border-cyan-500/10 bg-black/60 backdrop-blur-xl flex flex-col py-6 relative z-30">
        <div className="px-6 mb-8 flex items-center gap-2">
          <BrainCircuit className="w-8 h-8 text-cyan-400 animate-[rotate-hud_20s_linear_infinite]" />
          <div>
            <span className="text-sm font-black tracking-widest bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">JARVIS CORE</span>
            <p className="text-[9px] text-cyan-500/50 uppercase tracking-wider">Surveillance Overlay</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1.5 px-4 w-full">
          <SidebarBtn active={currentTab === "dashboard"} icon={<ScanEye className="w-4 h-4"/>} label="TACTICAL HUD" onClick={() => setCurrentTab("dashboard")} />
          <SidebarBtn active={currentTab === "analytics"} icon={<Activity className="w-4 h-4"/>} label="COGNITIVE GRAPH" onClick={() => setCurrentTab("analytics")} />
          <SidebarBtn active={currentTab === "timeline"} icon={<Clock className="w-4 h-4"/>} label="MEMORY TIMELINE" onClick={() => setCurrentTab("timeline")} />
          <SidebarBtn active={currentTab === "chat"} icon={<MessageSquare className="w-4 h-4"/>} label="JARVIS CONSOLE" onClick={() => setCurrentTab("chat")} />
          <SidebarBtn active={currentTab === "matrix"} icon={<Database className="w-4 h-4"/>} label="ENTITY MATRIX" onClick={() => setCurrentTab("matrix")} />
          <SidebarBtn active={currentTab === "settings"} icon={<Settings className="w-4 h-4"/>} label="HARDWARE LINK" onClick={() => setCurrentTab("settings")} />
        </nav>

        {/* System Health Overlay */}
        <div className="px-4 mt-auto">
          <div className="p-4 rounded-xl bg-black/40 border border-cyan-500/15">
            <span className="text-xxs font-bold text-cyan-400/80 uppercase tracking-widest block mb-2">SYSTEM SENSORS</span>
            <div className="space-y-2 text-xxs">
              <HealthGauge label="CPU LOAD" percent={systemHealth.cpu} color="from-cyan-500 to-cyan-300" />
              <HealthGauge label="RAM USAGE" percent={systemHealth.ram} color="from-violet-500 to-violet-300" />
              {isAnalyzing && <HealthGauge label="AI FRAME RATE" percent={Math.round((systemHealth.fps / 30) * 100)} display={`${systemHealth.fps} FPS`} color="from-emerald-500 to-emerald-300" />}
            </div>
            <div className="mt-3 flex items-center gap-1.5 text-[9px] text-gray-500 border-t border-cyan-500/5 pt-2">
              <Radio className="w-3 h-3 text-cyan-400 animate-pulse" />
              <span>MATRIX: NOMINAL</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <main className="flex-1 p-6 overflow-y-auto flex flex-col relative z-10">
        {/* Glow Effects */}
        <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-cyan-500/5 blur-[150px] rounded-full pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-violet-500/5 blur-[150px] rounded-full pointer-events-none"></div>

        {/* Top Diagnostic Header */}
        <header className="mb-6 flex justify-between items-center border-b border-cyan-500/10 pb-4 relative z-20">
          <div>
            <h2 className="text-lg font-black tracking-widest text-cyan-400 uppercase">SURVEILLANCE NODE #04</h2>
            <p className="text-xxs text-gray-500 uppercase tracking-wider">Active surveillance & deep cognitive learning matrix</p>
          </div>
          
          <div className="flex items-center gap-4">
            {/* System Clock */}
            <div className="px-3 py-1 border border-cyan-500/10 rounded bg-black/40 text-xs font-bold text-cyan-500">
              {systemTime}
            </div>

            {/* Engage AI button */}
            {currentTab === "dashboard" && (
              <button 
                onClick={async () => {
                  if (!isAnalyzing) {
                    if (cameraSource === "esp32") {
                      try {
                        await axios.post(`${API_URL}/api/hardware/esp32/start`);
                        const st = await axios.get(`${API_URL}/api/hardware/status`);
                        setEsp32Connected(!!st.data.esp32_stream_connected);
                      } catch (e) {
                        console.error("ESP32 worker start failed:", e);
                      }
                    }
                    speak("Cognitive neural net online. Initializing real time camera feed.");
                  } else {
                    speak("Neural scan halted.");
                  }
                  setIsAnalyzing(!isAnalyzing);
                }}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-bold text-xxs tracking-widest transition-all duration-300 ${
                  isAnalyzing 
                    ? 'bg-rose-500/10 text-rose-500 border border-rose-500/50 hover:bg-rose-500/20 shadow-[0_0_15px_rgba(239,68,68,0.2)]' 
                    : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/50 hover:bg-cyan-500/20 hover:shadow-[0_0_15px_rgba(6,182,212,0.3)]'
                }`}
              >
                <Zap className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-pulse' : ''}`} />
                {isAnalyzing ? 'HALT NEURAL SCAN' : 'ENGAGE NEURAL SCAN'}
              </button>
            )}
          </div>
        </header>

        {/* Tab 1: Dashboard */}
        {currentTab === "dashboard" && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 relative z-10 flex-1">
            {/* Camera Frame (Center HUD) */}
            <div className="xl:col-span-2 space-y-4">
              <div className="relative rounded-2xl overflow-hidden border border-cyan-500/20 bg-black/60 aspect-video flex items-center justify-center group shadow-[0_8px_30px_rgb(0,0,0,0.7)]">
                {/* HUD Corners */}
                <div className="absolute top-4 left-4 w-6 h-6 border-t-2 border-l-2 border-cyan-500/40 pointer-events-none z-20"></div>
                <div className="absolute top-4 right-4 w-6 h-6 border-t-2 border-r-2 border-cyan-500/40 pointer-events-none z-20"></div>
                <div className="absolute bottom-4 left-4 w-6 h-6 border-b-2 border-l-2 border-cyan-500/40 pointer-events-none z-20"></div>
                <div className="absolute bottom-4 right-4 w-6 h-6 border-b-2 border-r-2 border-cyan-500/40 pointer-events-none z-20"></div>
                
                {/* HUD Grid Overlay */}
                <div className="absolute inset-0 cyber-grid-overlay opacity-15 pointer-events-none z-10"></div>

                {/* Diagnostics overlay in corners */}
                <div className="absolute top-6 left-6 text-[8px] text-cyan-400/60 uppercase tracking-widest font-mono z-20 pointer-events-none hidden md:block">
                  CAM: {cameraSource === "esp32" ? "ESP32" : "WEBCAM"} // RES: 640x480<br/>
                  MATRIX: ACTIVE // FPS: {systemHealth.fps}
                </div>
                <div className="absolute bottom-6 right-6 text-[8px] text-cyan-400/60 uppercase tracking-widest font-mono text-right z-20 pointer-events-none hidden md:block">
                  NEURAL SCANNER CORE v2.5<br/>
                  SURVEILLANCE NODE OPERATIONAL
                </div>

                {cameraSource === "esp32" && !esp32Connected && (
                  <div className="absolute inset-0 z-25 flex items-center justify-center bg-black/85 backdrop-blur-sm pointer-events-none">
                    <div className="text-center px-6">
                      <Radio className="w-10 h-10 text-rose-500 mx-auto mb-2 animate-pulse" />
                      <p className="text-xs text-rose-400 font-bold uppercase tracking-widest">ESP32-CAM NOT CONNECTED</p>
                      <span className="text-[10px] text-gray-500 block mt-2 uppercase">
                        Using hardware camera — not laptop webcam.<br />
                        Check WiFi, power, URL: {esp32StreamUrl}
                      </span>
                    </div>
                  </div>
                )}

                {!isAnalyzing && (
                  <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/80 backdrop-blur-sm pointer-events-none transition-all duration-500">
                    <div className="text-center">
                      <Camera className="w-12 h-12 text-cyan-500/50 mx-auto mb-2 animate-pulse" />
                      <p className="text-xs text-gray-500 font-bold uppercase tracking-widest">COGNITIVE AID CAMERA DISENGAGED</p>
                      <span className="text-[10px] text-cyan-500/40 block mt-1 uppercase">
                        {cameraSource === "esp32" ? "ESP32 stream ready — engage scanner" : "Engage scanner above to active grid"}
                      </span>
                    </div>
                  </div>
                )}
                
                {cameraSource === "esp32" ? (
                  <img
                    ref={esp32ImgRef}
                    src={`${API_URL}/api/camera-stream`}
                    alt="ESP32-CAM feed"
                    className="absolute inset-0 w-full h-full object-cover"
                  />
                ) : (
                  <video ref={videoRef} className="absolute inset-0 w-full h-full object-cover" autoPlay playsInline muted />
                )}
                <canvas ref={canvasRef} width="640" height="480" className="absolute inset-0 w-full h-full object-cover z-10" />
                <canvas ref={hiddenCanvasRef} width="640" height="480" className="hidden" />

                {/* Laser scan line effect */}
                {isAnalyzing && <div className="absolute inset-0 w-full h-0.5 bg-cyan-400/50 shadow-[0_0_15px_rgba(6,182,212,0.8)] z-20 animate-[scan_2.2s_ease-in-out_infinite]"></div>}
              </div>
            </div>

            {/* Sidebar Diagnostic & Info Panels */}
            <div className="space-y-4">
              {/* Detailed Person Info Card */}
              <div className="bg-black/60 border border-cyan-500/10 backdrop-blur-xl rounded-2xl p-5 relative overflow-hidden shadow-lg">
                <div className="absolute top-0 right-0 w-16 h-16 border-t border-r border-cyan-500/20 pointer-events-none"></div>
                <h3 className="text-xxs font-bold text-cyan-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <UserCheck className="w-3.5 h-3.5" />
                  COGNITIVE MATRIX RESOLVED
                </h3>
                
                <div className="space-y-3.5 text-xs">
                  <div className="border-b border-cyan-500/5 pb-2">
                    <span className="text-[10px] text-gray-500 uppercase block mb-0.5">TARGET NAME</span>
                    <span className="font-bold text-white tracking-wider uppercase text-sm">{selectedPerson.name}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 border-b border-cyan-500/5 pb-2">
                    <div>
                      <span className="text-[10px] text-gray-500 uppercase block mb-0.5">RELATIONSHIP</span>
                      <span className="font-bold text-cyan-300 uppercase tracking-wider">{selectedPerson.relation}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-gray-500 uppercase block mb-0.5">DETECTED STATUS</span>
                      <span className={`font-bold uppercase tracking-wider ${selectedPerson.status === 'Known' ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {selectedPerson.status}
                      </span>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 border-b border-cyan-500/5 pb-2">
                    <div>
                      <span className="text-[10px] text-gray-500 uppercase block mb-0.5">DOMINANT EMOTION</span>
                      <span className="font-bold text-violet-300 uppercase tracking-wider">
                        {selectedPerson.emotion} {emotionEmoji[selectedPerson.emotion] || ''}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-gray-500 uppercase block mb-0.5">TOTAL VISITS</span>
                      <span className="font-bold text-cyan-400 tracking-wider">{selectedPerson.visits} CLICKS</span>
                    </div>
                  </div>
                  <div>
                    <span className="text-[10px] text-gray-500 uppercase block mb-0.5">LAST VISUALLY INDEXED</span>
                    <span className="font-bold text-gray-300 text-xxs tracking-widest">{selectedPerson.lastSeen}</span>
                  </div>
                </div>
              </div>

              {/* Core Telemetry Sensors Panel */}
              <div className="bg-black/60 border border-cyan-500/10 backdrop-blur-xl rounded-2xl p-5 shadow-lg">
                <h3 className="text-xxs font-bold text-cyan-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <Database className="w-3.5 h-3.5" />
                  SENSOR INTEGRITY CHECK
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  <SensorPill label="LOCAL AI ENGINE" active={isAnalyzing} />
                  <SensorPill label="MONGODB NODE" active={true} />
                  <SensorPill label="TTS SYNTH CORE" active={true} />
                  <SensorPill label="ESP32 RECEIVER" active={cameraSource === "esp32" && esp32Connected} />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Analytics */}
        {currentTab === "analytics" && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 relative z-10 flex-1">
            {/* Custom SVG Area Graph (Weekly Activity) */}
            <div className="xl:col-span-2 bg-black/60 border border-cyan-500/10 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
              <div>
                <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-widest mb-1 flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  WEEKLY MATRIX ACTIVITY LOGS
                </h3>
                <p className="text-xxs text-gray-500 uppercase mb-6">Cognitive scanning counts across the past 7 daily segments</p>
              </div>

              {/* Cyber Grid SVG Chart */}
              <div className="relative w-full h-[220px] mb-4">
                <svg className="w-full h-full" viewBox="0 0 500 200" preserveAspectRatio="none">
                  {/* Grid Lines */}
                  <line x1="0" y1="40" x2="500" y2="40" stroke="rgba(6, 182, 212, 0.05)" strokeWidth="1" />
                  <line x1="0" y1="80" x2="500" y2="80" stroke="rgba(6, 182, 212, 0.05)" strokeWidth="1" />
                  <line x1="0" y1="120" x2="500" y2="120" stroke="rgba(6, 182, 212, 0.05)" strokeWidth="1" />
                  <line x1="0" y1="160" x2="500" y2="160" stroke="rgba(6, 182, 212, 0.05)" strokeWidth="1" />
                  <line x1="83" y1="0" x2="83" y2="200" stroke="rgba(6, 182, 212, 0.05)" strokeWidth="1" />
                  <line x1="166" y1="0" x2="166" y2="200" stroke="rgba(6, 182, 212, 0.05)" strokeWidth="1" />
                  <line x1="249" y1="0" x2="249" y2="200" stroke="rgba(6, 182, 212, 0.05)" strokeWidth="1" />
                  <line x1="332" y1="0" x2="332" y2="200" stroke="rgba(6, 182, 212, 0.05)" strokeWidth="1" />
                  <line x1="415" y1="0" x2="415" y2="200" stroke="rgba(6, 182, 212, 0.05)" strokeWidth="1" />

                  {/* Gradient Area Definition */}
                  <defs>
                    <linearGradient id="cyan-gradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.45" />
                      <stop offset="100%" stopColor="#00f0ff" stopOpacity="0" />
                    </linearGradient>
                  </defs>

                  {/* Shaded Area */}
                  <path 
                    d="M0,180 Q83,120 166,160 T332,60 T500,80 L500,200 L0,200 Z" 
                    fill="url(#cyan-gradient)" 
                  />

                  {/* Shaded Glowing Neon Line */}
                  <path 
                    d="M0,180 Q83,120 166,160 T332,60 T500,80" 
                    fill="none" 
                    stroke="#00f0ff" 
                    strokeWidth="3.5" 
                    filter="drop-shadow(0px 0px 8px rgba(0, 240, 255, 0.8))"
                  />

                  {/* Key nodes circles */}
                  <circle cx="83" cy="133" r="4.5" fill="#00f0ff" />
                  <circle cx="249" cy="115" r="4.5" fill="#00f0ff" />
                  <circle cx="332" cy="60" r="4.5" fill="#00f0ff" />
                  <circle cx="415" cy="70" r="4.5" fill="#00f0ff" />
                </svg>
              </div>

              {/* Chart Legend Footer */}
              <div className="grid grid-cols-6 gap-2 text-center text-[10px] text-gray-500 tracking-wider">
                <span>MON</span>
                <span>TUE</span>
                <span>WED</span>
                <span>THU</span>
                <span>FRI</span>
                <span>SAT / SUN</span>
              </div>
            </div>

            {/* Mini Donut & Emotion Analytics */}
            <div className="space-y-6">
              {/* Concentric circles loop analytics */}
              <div className="bg-black/60 border border-cyan-500/10 rounded-2xl p-5 shadow-xl">
                <h3 className="text-xxs font-bold text-cyan-400 uppercase tracking-widest mb-4">EMOTION DISSOCIATION INDEX</h3>
                <div className="flex flex-col items-center py-4">
                  <div className="relative w-36 h-36 flex items-center justify-center">
                    {/* SVG Concentric Loops */}
                    <svg className="absolute inset-0 w-full h-full transform -rotate-90">
                      <circle cx="72" cy="72" r="60" fill="none" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="6" />
                      <circle cx="72" cy="72" r="60" fill="none" stroke="#00f0ff" strokeWidth="6" strokeDasharray="376" strokeDashoffset="120" strokeLinecap="round" />
                      
                      <circle cx="72" cy="72" r="46" fill="none" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="6" />
                      <circle cx="72" cy="72" r="46" fill="none" stroke="#8b5cf6" strokeWidth="6" strokeDasharray="289" strokeDashoffset="110" strokeLinecap="round" />

                      <circle cx="72" cy="72" r="32" fill="none" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="6" />
                      <circle cx="72" cy="72" r="32" fill="none" stroke="#ff0055" strokeWidth="6" strokeDasharray="201" strokeDashoffset="150" strokeLinecap="round" />
                    </svg>
                    
                    <div className="text-center z-10">
                      <Flame className="w-6 h-6 text-cyan-400 mx-auto animate-pulse" />
                      <span className="text-[10px] text-gray-500 uppercase block mt-1">NOMINAL</span>
                    </div>
                  </div>

                  {/* Concentric Details lists */}
                  <div className="w-full mt-6 space-y-2 text-[10px] uppercase font-bold tracking-wider">
                    <div className="flex justify-between items-center text-cyan-400">
                      <span>NEUTRAL ASPECT</span>
                      <span>68%</span>
                    </div>
                    <div className="flex justify-between items-center text-violet-400">
                      <span>HAPPY ASPECT</span>
                      <span>61%</span>
                    </div>
                    <div className="flex justify-between items-center text-rose-500">
                      <span>SURPRISE ASPECT</span>
                      <span>25%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Known vs Unknown Ratio loop */}
              <div className="bg-black/60 border border-cyan-500/10 rounded-2xl p-5 shadow-xl">
                <h3 className="text-xxs font-bold text-cyan-400 uppercase tracking-widest mb-3">COGNITIVE MATCH RATIO</h3>
                <div className="flex items-center gap-4 py-1">
                  <div className="w-16 h-16 rounded-full border-4 border-cyan-500/20 border-t-cyan-400 flex items-center justify-center text-sm font-bold text-cyan-300">
                    84%
                  </div>
                  <div>
                    <span className="text-xxs text-emerald-400 font-bold block">KNOWN ENTITIES // 84%</span>
                    <span className="text-xxs text-rose-500 font-bold block">FOREIGN ENTITIES // 16%</span>
                    <span className="text-[9px] text-gray-500 uppercase mt-0.5 block">SURVEILLANCE ACCURACY EXCELLENT</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Memory Timeline */}
        {currentTab === "timeline" && (
          <div className="bg-black/60 border border-cyan-500/10 rounded-2xl p-6 shadow-xl flex-1 flex flex-col z-10 relative">
            <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              COGNITIVE MEMORY STRUCTURES
            </h3>
            
            {/* Search filter panel */}
            <div className="flex gap-3 mb-6">
              <input 
                type="text" 
                placeholder="QUERY SEMANTIC MEMORY... (e.g. FRIEND, ADMIN)" 
                className="flex-1 bg-black/70 border border-cyan-500/15 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500/40 focus:shadow-[0_0_10px_rgba(6,182,212,0.1)] transition-all font-mono"
              />
              <button className="px-5 py-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20 text-xs font-bold tracking-widest transition-colors font-mono">
                EXECUTE SEARCH
              </button>
            </div>

            {/* List timeline grid */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-2 cyber-scroll">
              {interactionLogs.length === 0 ? (
                <div className="text-center py-20 border border-dashed border-cyan-500/5 rounded-2xl bg-white/2">
                  <ScanEye className="w-10 h-10 text-cyan-500/20 mx-auto mb-2 animate-pulse" />
                  <p className="text-xs text-gray-500 uppercase tracking-widest font-mono">Surveillance buffers empty. Engage scanner to fill memories.</p>
                </div>
              ) : (
                interactionLogs.map((log, index) => (
                  <div key={index} className="p-4 rounded-xl border border-cyan-500/5 bg-black/40 hover:border-cyan-500/25 transition-all flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-cyan-500/10 flex items-center justify-center text-xl text-cyan-400 border border-cyan-500/20">
                      {emotionEmoji[log.emotion] || '👤'}
                    </div>
                    <div className="flex-grow grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                      <div>
                        <span className="text-[9px] text-gray-600 uppercase block mb-0.5">IDENTIFIED OBJECT</span>
                        <span className="font-bold text-white uppercase tracking-wider">{log.name}</span>
                      </div>
                      <div>
                        <span className="text-[9px] text-gray-600 uppercase block mb-0.5">RELATION</span>
                        <span className="font-bold text-cyan-300 uppercase tracking-wider">{log.relation || 'Unknown'}</span>
                      </div>
                      <div>
                        <span className="text-[9px] text-gray-600 uppercase block mb-0.5">SURFACE ASPECT</span>
                        <span className="font-bold text-violet-300 uppercase tracking-wider">{log.gender} // {log.emotion}</span>
                      </div>
                      <div>
                        <span className="text-[9px] text-gray-600 uppercase block mb-0.5">TIMESTAMP</span>
                        <span className="font-bold text-gray-400 tracking-widest">{log.time}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Tab 4: AI Jarvis Chat */}
        {currentTab === "chat" && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 relative z-10 flex-1">
            {/* Chat Messages Log */}
            <div className="xl:col-span-2 bg-black/60 border border-cyan-500/10 rounded-2xl p-5 flex flex-col justify-between shadow-xl min-h-[400px]">
              
              {/* Chat messages box */}
              <div className="flex-1 overflow-y-auto space-y-4 pr-2 cyber-scroll max-h-[350px] mb-4">
                {chatMessages.map((msg, index) => (
                  <div key={index} className={`flex ${msg.sender === 'jarvis' ? 'justify-start' : 'justify-end'}`}>
                    <div className={`max-w-[80%] p-4 rounded-xl text-xs font-mono tracking-wider leading-relaxed ${
                      msg.sender === 'jarvis' 
                        ? 'bg-cyan-500/5 border border-cyan-500/20 text-cyan-300' 
                        : 'bg-violet-500/10 border border-violet-500/20 text-violet-300'
                    }`}>
                      <span className="text-[9px] font-bold block uppercase mb-1.5 opacity-60">
                        {msg.sender === 'jarvis' ? '🤖 JARVIS CORE ACTIVE' : '👤 Shiva (Admin)'}
                      </span>
                      {msg.text}
                    </div>
                  </div>
                ))}
              </div>

              {/* Chat send input */}
              <form onSubmit={handleChatSubmit} className="flex gap-2 border-t border-cyan-500/10 pt-4">
                <input 
                  type="text" 
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  placeholder="INPUT TACTICAL SURVEILLANCE QUERY... (e.g. WHO VISITED TODAY?)"
                  className="flex-1 bg-black/80 border border-cyan-500/15 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-cyan-500/40 font-mono focus:shadow-[0_0_10px_rgba(6,182,212,0.1)] transition-all"
                />
                <button type="submit" className="px-5 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white flex items-center justify-center shadow-[0_0_10px_rgba(6,182,212,0.3)] transition-all duration-200">
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>

            {/* Pulsating Jarvis Speech Orb */}
            <div className="bg-black/60 border border-cyan-500/10 rounded-2xl p-6 shadow-xl flex flex-col items-center justify-center text-center">
              <div className="relative w-36 h-36 mb-8 flex items-center justify-center">
                {/* Rotating HUD compass loops */}
                <div className="absolute inset-0 rounded-full border border-dashed border-cyan-500/25 animate-[rotate-hud_30s_linear_infinite]"></div>
                <div className="absolute inset-2 rounded-full border border-dashed border-violet-500/25 animate-[rotate-hud-reverse_15s_linear_infinite]"></div>
                
                {/* Glowing Pulsating Orb */}
                <div className={`w-20 h-20 rounded-full bg-gradient-to-br from-cyan-500 to-violet-600 animate-[orb-glow_3s_ease-in-out_infinite] flex items-center justify-center`}>
                  <Radio className={`w-8 h-8 text-white ${isJarvisSpeaking ? 'animate-ping' : ''}`} />
                </div>
              </div>

              <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-widest mb-1.5">Jarvis Audio Synthesizer</h4>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-6">Neural speaking waveform simulator</p>

              {/* Dynamic waveform simulator */}
              <div className="flex gap-1.5 items-end justify-center h-8">
                {[0.6, 0.4, 0.8, 1.0, 0.7, 0.3, 0.9, 0.5, 0.8, 0.4, 0.6].map((h, i) => (
                  <div 
                    key={i} 
                    style={{ 
                      animation: isJarvisSpeaking ? `wave-pulse 0.8s ease-in-out infinite alternate` : 'none',
                      animationDelay: `${i * 0.08}s`,
                      height: `${h * 100}%` 
                    }} 
                    className="w-1 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.8)]"
                  ></div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab: Hardware / ESP32 Settings */}
        {currentTab === "settings" && (
          <div className="bg-black/60 border border-cyan-500/10 rounded-2xl p-6 shadow-xl max-w-2xl relative z-10">
            <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              <Cpu className="w-4 h-4" />
              ESP32-CAM & OLED Hardware Link
            </h3>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-6">
              Connect ESP32 stream for capture. Recognition results are sent to OLED and speaker at /result.
            </p>

            <div className="space-y-5">
              <div>
                <label className="block text-xxs font-bold text-cyan-500/80 uppercase tracking-widest mb-2">Video Source</label>
                <div className="grid grid-cols-2 gap-2">
                  {["webcam", "esp32"].map((src) => (
                    <button
                      key={src}
                      type="button"
                      onClick={() => setCameraSource(src)}
                      className={`py-2 rounded-lg border text-xxs font-bold uppercase ${
                        cameraSource === src
                          ? "bg-cyan-500/15 border-cyan-400 text-cyan-400"
                          : "bg-white/5 border-white/10 text-gray-500"
                      }`}
                    >
                      {src === "webcam" ? "Browser Webcam" : "ESP32-CAM Stream"}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xxs font-bold text-cyan-500/80 uppercase tracking-widest mb-1.5">ESP32 Stream URL</label>
                <input
                  type="text"
                  value={esp32StreamUrl}
                  onChange={(e) => setEsp32StreamUrl(e.target.value)}
                  placeholder="http://10.81.203.182/"
                  className="w-full bg-black/85 border border-white/10 rounded-lg px-4 py-2.5 text-xs text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-xxs font-bold text-cyan-500/80 uppercase tracking-widest mb-1.5">ESP32 Control IP (OLED / Speaker)</label>
                <input
                  type="text"
                  value={esp32Ip}
                  onChange={(e) => setEsp32Ip(e.target.value)}
                  placeholder="10.81.203.182"
                  className="w-full bg-black/85 border border-white/10 rounded-lg px-4 py-2.5 text-xs text-white font-mono"
                />
              </div>

              <div className="flex flex-wrap gap-4 text-xs">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={hardwareEnabled} onChange={(e) => setHardwareEnabled(e.target.checked)} />
                  <span className="text-gray-400 uppercase text-xxs font-bold">Send to ESP32 OLED</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={backendTtsEnabled} onChange={(e) => setBackendTtsEnabled(e.target.checked)} />
                  <span className="text-gray-400 uppercase text-xxs font-bold">Backend AI Voice (pyttsx3)</span>
                </label>
              </div>

              <button
                type="button"
                onClick={saveHardwareSettings}
                disabled={savingSettings}
                className="w-full py-3 rounded-lg bg-cyan-600/20 border border-cyan-500/40 text-cyan-400 font-bold text-xxs uppercase tracking-widest hover:bg-cyan-500/20 flex items-center justify-center gap-2"
              >
                {savingSettings ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                Save & Apply Hardware Config
              </button>

              <p className="text-[10px] text-gray-600 font-mono">
                Test stream only: <code className="text-cyan-600">python backend/camera_stream.py YOUR_IP</code>
                <br />
                Test detection: <code className="text-cyan-600">python backend/face_detect.py YOUR_IP</code>
              </p>
            </div>
          </div>
        )}

        {/* Tab 5: Entity Matrix Manager */}
        {currentTab === "matrix" && (
          <div className="space-y-6 relative z-10 flex-1 flex flex-col">
            {/* Self-Healing Diagnostic AI Console */}
            <div className="bg-black/60 border border-cyan-500/15 rounded-2xl p-6 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 border-t border-r border-cyan-500/10 pointer-events-none"></div>
              
              <div className="flex items-center gap-3 mb-4">
                <BrainCircuit className="w-5 h-5 text-cyan-400 animate-pulse" />
                <div>
                  <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-widest">
                    Cognitive Core Diagnostic & Troubleshooter
                  </h3>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider">
                    Type a correction command (e.g., "Change relation of Shivam to Brother", "Rename Guest to Rahul", "Delete guest")
                  </p>
                </div>
              </div>

              <form onSubmit={handleTroubleshootSubmit} className="flex gap-3 mb-4">
                <input 
                  type="text" 
                  value={troubleshootInput}
                  onChange={e => setTroubleshootInput(e.target.value)}
                  placeholder="EXPLAIN ERROR OR TYPE NLP COMMAND... (e.g. Shivam is my Brother)"
                  className="flex-1 bg-black/85 border border-cyan-500/20 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-cyan-500/50 focus:shadow-[0_0_12px_rgba(6,182,212,0.15)] transition-all font-mono uppercase"
                  disabled={isTroubleshooting}
                />
                <button 
                  type="submit" 
                  disabled={isTroubleshooting}
                  className="px-6 py-3 rounded-xl bg-cyan-600/10 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20 text-xs font-bold tracking-widest transition-all uppercase flex items-center gap-2 font-mono"
                >
                  {isTroubleshooting ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Zap className="w-4 h-4" />
                  )}
                  Execute Core Auto-Correct
                </button>
              </form>

              {troubleshootResponse && (
                <div className="p-4 rounded-xl border border-cyan-500/15 bg-cyan-950/15 font-mono text-xs text-cyan-300 relative flex items-start gap-3 shadow-[inset_0_0_15px_rgba(6,182,212,0.05)] animate-fade-in">
                  <div className="w-2 h-2 rounded-full bg-cyan-400 animate-ping mt-1.5 shrink-0"></div>
                  <div>
                    <span className="text-[9px] font-bold block text-cyan-500/80 uppercase mb-1">Jarvis Auto-Correct Core Diagnostic Response</span>
                    {troubleshootResponse}
                  </div>
                </div>
              )}
            </div>

            {/* Registered Entities Grid */}
            <div className="bg-black/60 border border-cyan-500/10 rounded-2xl p-6 shadow-xl flex-grow flex flex-col">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-widest">
                    Cognitive Memory Database Matrix
                  </h3>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">
                    Registered persons currently indexing in the deep neural face-matching model
                  </p>
                </div>
                <div className="px-3 py-1 border border-cyan-500/15 rounded bg-cyan-500/5 text-xxs font-bold text-cyan-400 font-mono">
                  {registeredUsers.length} REGISTERED ENTITIES
                </div>
              </div>

              {registeredUsers.length === 0 ? (
                <div className="text-center py-20 border border-dashed border-cyan-500/5 rounded-2xl bg-white/2 flex-grow flex flex-col justify-center">
                  <Users className="w-12 h-12 text-cyan-500/20 mx-auto mb-3 animate-pulse" />
                  <p className="text-xs text-gray-500 uppercase tracking-widest font-mono">
                    System record buffers empty.
                  </p>
                  <span className="text-[10px] text-cyan-500/40 uppercase block mt-1">
                    Please use the scanner or register a new target to fill the matrix.
                  </span>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 overflow-y-auto max-h-[380px] pr-2 cyber-scroll">
                  {registeredUsers.map((user, index) => (
                    <div key={index} className="bg-black/50 border border-cyan-500/10 rounded-2xl p-5 relative overflow-hidden group hover:border-cyan-500/30 transition-all duration-300 shadow-md">
                      {/* Sci-fi bounding corner lines */}
                      <div className="absolute top-3 left-3 w-4 h-4 border-t border-l border-cyan-500/30 pointer-events-none"></div>
                      <div className="absolute top-3 right-3 w-4 h-4 border-t border-r border-cyan-500/30 pointer-events-none"></div>
                      <div className="absolute bottom-3 left-3 w-4 h-4 border-b border-l border-cyan-500/30 pointer-events-none"></div>
                      <div className="absolute bottom-3 right-3 w-4 h-4 border-b border-r border-cyan-500/30 pointer-events-none"></div>
                      
                      <div className="flex gap-4 items-center">
                        {/* Face Thumbnail */}
                        {user.image_base64 ? (
                          <img 
                            src={user.image_base64} 
                            alt={user.name} 
                            className="w-16 h-16 object-cover rounded-xl border border-cyan-500/20 shadow-inner group-hover:border-cyan-500/40 transition-colors"
                          />
                        ) : (
                          <div className="w-16 h-16 rounded-xl bg-cyan-500/5 border border-cyan-500/20 flex items-center justify-center text-cyan-400/50">
                            <Users className="w-8 h-8" />
                          </div>
                        )}

                        <div className="flex-1 min-w-0">
                          <span className="text-[9px] text-gray-500 uppercase block tracking-wider">SECURE ID ENTITY</span>
                          <h4 className="text-sm font-bold text-white uppercase truncate mb-1 font-mono">{user.name}</h4>
                          <span className="px-2.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-[9px] font-black text-cyan-400 uppercase tracking-widest inline-block font-mono">
                            {user.relation || 'Unknown'}
                          </span>
                        </div>
                      </div>

                      <div className="mt-5 pt-3.5 border-t border-cyan-500/5 flex justify-between items-center text-[10px] font-mono">
                        <div>
                          <span className="text-gray-500 block text-[8px] uppercase">INDEX VISITS</span>
                          <span className="font-bold text-gray-300">{user.visit_count || 1} DETECTIONS</span>
                        </div>
                        <button 
                          onClick={() => handleDeleteUser(user.name)}
                          className="px-3.5 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 hover:bg-rose-500/20 hover:shadow-[0_0_10px_rgba(239,68,68,0.2)] text-[9px] font-black uppercase tracking-wider transition-all font-mono"
                        >
                          Purge Entity
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

      </main>

      {/* Futuristic Unknown face popup registration modal overlay */}
      {showRegisterModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-4">
          <div className="bg-[#050610] border border-cyan-500/30 rounded-2xl p-6 max-w-sm w-full shadow-[0_0_50px_rgba(255,0,85,0.15)] relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-rose-500 via-orange-500 to-rose-500"></div>
            
            <h2 className="text-sm font-black text-rose-500 mb-1.5 uppercase tracking-widest flex items-center gap-1.5">
              <ScanEye className="w-4 h-4 text-rose-500 animate-pulse" />
              ⚠️ UNKNOWN TARGET ACQUIRED
            </h2>
            <p className="text-gray-500 text-[10px] uppercase mb-5 tracking-widest">Register entity context in neural matrix</p>
            
            <div className="space-y-4">
              <div>
                <label className="block text-xxs font-bold text-cyan-400 uppercase tracking-widest mb-1.5">Target Name</label>
                <input 
                  type="text" 
                  value={regName}
                  onChange={e => setRegName(e.target.value)}
                  className="w-full bg-black border border-cyan-500/20 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500/60 focus:shadow-[0_0_10px_rgba(6,182,212,0.15)] font-mono"
                  placeholder="ENTER ASSIGNED NAME"
                />
              </div>
              <div>
                <label className="block text-xxs font-bold text-cyan-400 uppercase tracking-widest mb-1.5">Target Relation</label>
                <input 
                  type="text" 
                  value={regRelation}
                  onChange={e => setRegRelation(e.target.value)}
                  className="w-full bg-black border border-cyan-500/20 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500/60 focus:shadow-[0_0_10px_rgba(6,182,212,0.15)] font-mono"
                  placeholder="e.g. FRIEND, ADMIN, COLLEAGUE"
                />
              </div>
            </div>
            
            <div className="mt-6 flex gap-3">
              <button 
                onClick={() => {
                  setShowRegisterModal(false);
                  setIsAnalyzing(true);
                  setUnknownFaceData(null);
                  speak("Registration aborted. Resuming neural scan.");
                }}
                className="flex-1 py-2.5 rounded-lg font-bold text-xxs bg-white/5 border border-white/10 hover:bg-white/10 text-white tracking-widest transition-colors font-mono"
              >
                ABORT
              </button>
              <button 
                onClick={handleRegister}
                className="flex-1 py-2.5 rounded-lg font-bold text-xxs bg-cyan-500/10 border border-cyan-400 hover:bg-cyan-500/20 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.25)] transition-all font-mono"
              >
                REGISTER
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Sidebar Button Helper Component
function SidebarBtn({ icon, label, active, onClick }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-lg border text-xxs font-bold tracking-widest transition-all duration-200 ${
        active 
          ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/35 shadow-[inset_0_0_10px_rgba(6,182,212,0.1),0_0_10px_rgba(6,182,212,0.05)]' 
          : 'bg-transparent border-transparent text-gray-500 hover:bg-white/2 hover:text-gray-300'
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

// Health gauge progress simulator
function HealthGauge({ label, percent, display, color }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[9px] text-gray-500 uppercase tracking-widest">
        <span>{label}</span>
        <span className="font-bold text-cyan-500">{display || `${percent}%`}</span>
      </div>
      <div className="h-1 bg-white/5 rounded-full overflow-hidden">
        <div 
          style={{ width: `${percent}%` }} 
          className={`h-full bg-gradient-to-r ${color} transition-all duration-500`}
        ></div>
      </div>
    </div>
  );
}

// Diagnostic Sensor Pill Helper Component
function SensorPill({ label, active }) {
  return (
    <div className={`p-2.5 rounded-lg border flex items-center justify-between transition-colors ${
      active 
        ? 'bg-cyan-500/5 border-cyan-500/20 text-cyan-400' 
        : 'bg-rose-500/5 border-rose-500/10 text-gray-500'
    }`}>
      <span className="text-[9px] uppercase font-bold tracking-widest">{label}</span>
      <div className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-cyan-400 animate-pulse' : 'bg-rose-500'}`}></div>
    </div>
  );
}

export default App;
