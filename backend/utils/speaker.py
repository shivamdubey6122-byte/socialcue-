import pyttsx3
import threading
import queue
import time

class Speaker:
    def __init__(self):
        self.q = queue.Queue()
        self.engine = None
        self.is_running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _init_engine(self):
        if self.engine is None:
            try:
                self.engine = pyttsx3.init()
                # Set default speed and gender
                self.engine.setProperty('rate', 150)
                voices = self.engine.getProperty('voices')
                if voices:
                    # Try to set female voice if available, else use default
                    for voice in voices:
                        if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                            self.engine.setProperty('voice', voice.id)
                            break
            except Exception as e:
                print(f"Failed to initialize TTS engine: {e}")

    def _worker(self):
        self._init_engine()
        while self.is_running:
            try:
                text = self.q.get(timeout=0.5)
                if text is None:
                    break
                if self.engine:
                    self.engine.say(text)
                    self.engine.runAndWait()
                self.q.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"TTS Error: {e}")

    def speak(self, text):
        if not text:
            return
        # Prevent queue buildup of same repeated messages if busy
        if self.q.qsize() < 3:
            self.q.put(text)

    def set_speed(self, rate):
        if self.engine:
            self.engine.setProperty('rate', rate)

    def set_gender(self, gender='female'):
        if self.engine:
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if gender.lower() in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    return

    def stop(self):
        self.is_running = False
        self.q.put(None)
        self.thread.join()

# Global speaker instance
_speaker_instance = Speaker()

def speak(text):
    """Reusable speak function callable from any module."""
    _speaker_instance.speak(text)
