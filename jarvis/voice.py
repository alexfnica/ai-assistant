"""Cancellable Windows speech workers. No Tk calls outside the UI thread."""
import base64
import json
import os
import queue
import subprocess
import threading
import sys
from pathlib import Path


class VoiceError(RuntimeError):
    pass


def preferred_voice(voices):
    """British male when installed, then male, then any available voice."""
    return next((v for v in voices if v.get("culture") == "en-GB" and v.get("gender") == "Male"),
                next((v for v in voices if v.get("gender") == "Male"), voices[0] if voices else None))


class WindowsSpeech:
    def __init__(self):
        self._lock = threading.Lock()
        self._processes = set()

    def run(self, request, cancel=None):
        if os.name != "nt":
            raise VoiceError("Vocea locală necesită Windows. Chatul text rămâne disponibil.")
        from .neural_voice import VOICE_ID, HUD_ID, available_voices
        from .natural_voice import VOICE_IDS, available_voices as natural_voices
        neural = request.get('voice') in (VOICE_ID, HUD_ID) and request['action'] in ('speak', 'render')
        natural = request.get('voice') in VOICE_IDS and request['action'] in ('speak', 'render')
        if natural:
            args = [sys.executable, '-X', 'utf8', str(Path(__file__).with_name('natural_voice.py'))]
        elif neural:
            args = [sys.executable, '-X', 'utf8', str(Path(__file__).with_name('neural_voice.py'))]
        else:
            script = Path(__file__).with_name("speech_bridge.ps1").read_text(encoding="utf-8")
            command = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
            args = ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", command]
        with self._lock:
            if cancel and cancel.is_set():
                return {}
            process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW)
            self._processes.add(process)
        try:
            timeout = 25 if request["action"] in ("inventory", "listen", "wake") else 100
            output, _ = process.communicate(json.dumps(request, ensure_ascii=False), timeout=timeout)
            if cancel and cancel.is_set():
                return {}
            try:
                result = json.loads(output.strip().lstrip("\ufeff"))
            except (ValueError, TypeError):
                raise VoiceError("Motorul vocal nu a răspuns corect. Verifică componentele Speech din Windows.") from None
            if not result.get("ok"):
                # Native errors contain no request text or credentials in this local bridge.
                raise VoiceError(str(result.get("error", "Eroare audio"))[:300])
            if request['action'] == 'inventory':
                result['voices'] = natural_voices() + available_voices() + (result.get('voices') or [])
            return result
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise VoiceError("Operația audio a expirat. Verifică microfonul sau vocea selectată.") from None
        finally:
            with self._lock:
                self._processes.discard(process)

    def stop(self):
        with self._lock:
            for process in tuple(self._processes):
                if process.poll() is None:
                    process.kill()


class VoiceController:
    def __init__(self, backend=None):
        self.backend = backend or WindowsSpeech()
        self.events = queue.Queue()
        self.generation = 0
        self.cancel = threading.Event()
        self.busy = False

    def start(self, action, **fields):
        self.stop()
        generation = self.generation
        cancel = self.cancel
        self.busy = True

        def work():
            try:
                result = self.backend.run({"action": action, **fields}, cancel)
                self.events.put((generation, action, result, None))
            except Exception as error:
                self.events.put((generation, action, None, str(error)))

        threading.Thread(target=work, daemon=True, name="jarvis-speech").start()

    def stop(self):
        self.cancel.set()
        self.backend.stop()
        self.generation += 1
        self.cancel = threading.Event()
        self.busy = False

    def drain(self):
        while True:
            try:
                generation, action, result, error = self.events.get_nowait()
            except queue.Empty:
                return
            if generation == self.generation:
                self.busy = False
                yield action, result, error
