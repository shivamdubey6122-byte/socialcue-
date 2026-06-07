import os
import threading

import speech_recognition as sr

from backend.database.mongo import delete_user, log_command, update_user_relation
from backend.utils.speaker import speak


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
            print("Native Voice Assistant started in background.")

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
                    print(f"[Voice Command] {text}")
                    self._process_command(text)
                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    pass
                except Exception as e:
                    print(f"Voice recognition error: {e}")

    def _process_command(self, text):
        if "register person" in text:
            speak("Command accepted. Use the dashboard to register unknown faces.")
            log_command(text, "Registration hint spoken")
        elif "who is this" in text:
            speak("Command accepted. Identifying face on active camera feed.")
            log_command(text, "Triggered manual recognition")
        elif "stop listening" in text:
            speak("Command accepted. Microphone disabled.")
            log_command(text, "Mic stopped")
            self.stop()
        elif "shutdown system" in text:
            speak("Command accepted. Shutting down.")
            log_command(text, "System shutdown")
            os._exit(0)
        elif text.startswith("delete person"):
            name = text.replace("delete person", "").strip()
            if name:
                delete_user(name)
                speak(f"Command accepted. Deleted {name}.")
                log_command(text, f"Deleted {name}")
        elif text.startswith("update relation"):
            parts = text.replace("update relation", "").strip().split()
            if len(parts) >= 2:
                name = parts[0]
                relation = " ".join(parts[1:])
                update_user_relation(name, relation)
                speak(f"Command accepted. Updated {name} to {relation}.")
                log_command(text, f"Updated relation for {name}")
        else:
            log_command(text, "Parsed natively")
