"""One global local voice session for the browser UI; opt-in mic, no audio uploads."""
import threading
import time
from .voice import VoiceController, preferred_voice
from .wake import WakeGate


class HoloVoice:
    def __init__(self):
        self.lock = threading.RLock()
        self.closed = threading.Event()
        self.last_client = time.monotonic()
        self.controller, self.wake = VoiceController(), WakeGate()
        self.state, self.detail = "loading", "Verific vocile Windows; microfon oprit."
        self.voices, self.recognizers = [], []
        self.voice_id, self.recognizer_id = "", ""
        self.transcript, self.transcript_id, self.activation = "", 0, 0
        self.controller.start("inventory")
        self.thread = threading.Thread(target=self.loop, name="holo-voice", daemon=True)
        self.thread.start()

    def snapshot(self):
        with self.lock:
            self.last_client = time.monotonic()
            return {"state": self.state, "detail": self.detail, "wake": self.wake.enabled,
                    "voices": self.voices, "recognizers": self.recognizers,
                    "voice_id": self.voice_id, "recognizer_id": self.recognizer_id,
                    "transcript": self.transcript, "transcript_id": self.transcript_id,
                    "activation": self.activation}

    def listen(self):
        if not self.recognizer_id:
            raise ValueError("Recunoașterea Windows nu este disponibilă.")
        self.wake.pause()
        self.state, self.detail = "listening", "ASCULT · spune comanda, apoi verifică textul înainte de trimitere."
        self.controller.start("listen", recognizer=self.recognizer_id)

    def action(self, body):
        with self.lock:
            self.last_client = time.monotonic()
            action = body.get("action")
            if action == "stop":
                self.wake.disable()
                self.wake.error = ""
                self.controller.stop()
                self.state, self.detail = "ready", "Camera se oprește separat; microfonul și vocea sunt oprite."
            elif action == "listen":
                self.listen()
            elif action == "wake":
                if body.get("enabled") is True:
                    if not self.wake.enable(self.recognizers):
                        raise ValueError(self.wake.error)
                    if self.state not in ("listening", "speaking", "review", "loading"):
                        self.state = "ready"
                else:
                    self.wake.disable()
                    if self.state == "armed":
                        self.state, self.detail = "ready", "Hey Jarvis oprit."
            elif action == "reviewed":
                if self.state == "review":
                    self.state, self.detail = "ready", "Transcriere verificată."
            elif action == "speak":
                if not self.voice_id:
                    raise ValueError("Voce Windows indisponibilă.")
                if self.state == "listening":
                    raise ValueError("Oprește dictarea înainte de redare.")
                text = body.get("text")
                if not isinstance(text, str) or not text.strip() or len(text) > 8000:
                    raise ValueError("Text vocal invalid")
                self.wake.pause()
                self.state, self.detail = "speaking", "VORBESC · microfon oprit."
                self.controller.start("speak", voice=self.voice_id, text=text[:650], rate=-1, volume=85)
            elif action == "select":
                if body.get("voice_id"):
                    if body["voice_id"] not in [v["id"] for v in self.voices]:
                        raise ValueError("Voce necunoscută")
                    self.voice_id = body["voice_id"]
                if body.get("recognizer_id"):
                    if body["recognizer_id"] not in [r["id"] for r in self.recognizers]:
                        raise ValueError("Limbă necunoscută")
                    self.recognizer_id = body["recognizer_id"]
            else:
                raise ValueError("Acțiune vocală necunoscută")

    def loop(self):
        while not self.closed.wait(.1):
            with self.lock:
                if time.monotonic() - self.last_client > 10 and (self.wake.enabled or self.controller.busy):
                    self.wake.disable()
                    self.wake.error = ""
                    self.controller.stop()
                    self.state, self.detail = "ready", "Sesiune inactivă: microfonul și vocea au fost oprite."
                for action, result, error in self.controller.drain():
                    if error:
                        self.state, self.detail = "error", error[:220]
                    elif action == "inventory":
                        self.voices, self.recognizers = result.get("voices", []), result.get("recognizers", [])
                        voice = preferred_voice(self.voices)
                        self.voice_id = voice["id"] if voice else ""
                        recognizer = None
                        for wanted in ("en-GB", "en-US"):
                            recognizer = recognizer or next((r for r in self.recognizers if r["culture"] == wanted), None)
                        recognizer = recognizer or next((r for r in self.recognizers if r["culture"].lower().startswith("en-")), None) \
                            or (self.recognizers[0] if self.recognizers else None)  # English first: Jarvis commands are English
                        self.recognizer_id = recognizer["id"] if recognizer else ""
                        self.state, self.detail = "ready", "Pregătit. Microfon oprit."
                    elif action == "listen" and result.get("text"):
                        self.transcript, self.transcript_id = result["text"], self.transcript_id + 1
                        self.state, self.detail = "review", "Verifică transcrierea și apasă Trimite."
                    else:
                        self.state, self.detail = "ready", "Pregătit."
                if self.wake.tick(not self.controller.busy and self.state in ("ready", "armed")):
                    self.activation += 1
                    try:
                        self.listen()
                    except ValueError as error:
                        self.state, self.detail = "error", str(error)
                if self.wake.error and not self.wake.enabled:
                    self.state, self.detail = "error", self.wake.error
                if self.wake.enabled and self.state in ("ready", "armed"):
                    self.state, self.detail = "armed", "HEY JARVIS · microfon local în așteptare."

    def close(self):
        self.closed.set()
        with self.lock:
            self.wake.disable()
            self.controller.stop()
        self.thread.join(timeout=2)
