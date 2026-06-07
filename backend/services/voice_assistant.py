import speech_recognition as sr
import threading
from backend.utils.speaker import speak
from backend.database.mongo import log_command

class VoiceAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.listen_thread = None

    def start(self):
        if not self.is_listening:
            self.is_listening = True
            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()
            print("Voice Assistant started.")

    def stop(self):
        self.is_listening = False
        print("Voice Assistant stopped.")

    def _listen_loop(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while self.is_listening:
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"Command heard: {text}")
                    self._process_command(text)
                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    pass
                except Exception as e:
                    print(f"Voice recognition error: {e}")

    def _process_command(self, text):
        # NLP Intent Mapping (Basic Regex/Keyword matching)
        if "register person" in text:
            speak("Command accepted. Starting registration.")
            log_command(text, "Started registration")
            # Trigger registration logic via global state or callback
        elif "who is this" in text:
            speak("Command accepted. Identifying face.")
            log_command(text, "Triggered manual recognition")
        elif "repeat" in text:
            speak("Command accepted. Repeating last interaction.")
            log_command(text, "Repeated speech")
        elif "show history" in text:
            speak("Command accepted. Showing history on dashboard.")
            log_command(text, "Dashboard navigated to history")
        elif "stop listening" in text:
            speak("Command accepted. Microphone disabled.")
            log_command(text, "Mic stopped")
            self.stop()
        elif "shutdown system" in text:
            speak("Command accepted. Shutting down.")
            log_command(text, "System shutdown")
            import os
            os._exit(0)
        else:
            # Check dynamic commands like 'delete person X'
            if text.startswith("delete person"):
                name = text.replace("delete person", "").strip()
                if name:
                    speak(f"Command accepted. Deleting {name}.")
                    from backend.database.mongo import users_collection
                    users_collection.delete_one({"name": name})
                    log_command(text, f"Deleted {name}")
            elif text.startswith("update relation"):
                parts = text.replace("update relation", "").strip().split(" ")
                if len(parts) >= 2:
                    name = parts[0]
                    relation = " ".join(parts[1:])
                    speak(f"Command accepted. Updating {name} to {relation}.")
                    from backend.database.mongo import users_collection
                    users_collection.update_one({"name": name}, {"$set": {"relation": relation}})
                    log_command(text, f"Updated relation for {name}")

# Singleton
assistant = VoiceAssistant()
