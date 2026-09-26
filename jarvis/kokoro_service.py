"""Resident local Kokoro voice: the model is loaded once in the background, then each sentence is
synthesised in well under a second and served to the page as WAV. Nothing leaves this computer."""
import io
import threading
import wave
from . import natural_voice as nv

MAX_CHARS = 600
# name -> (voice or blend, pitch factor, tempo). A pitch factor of 1.0 keeps the natural timbre (no resampling artefacts);
# the tempo is a little slower than Kokoro's default, which sounds calmer and less synthetic.
PRESETS = {
    # Modelled on the film assistant: a smooth, dry, measured British baritone, clear and not old.
    "jarvis": ({"bm_daniel": .5, "bm_lewis": .5}, 1.0, .97),
    "jarvis2": ({"bm_george": .5, "bm_daniel": .5}, .97, .96),   # a little deeper and warmer
    "jarvis3": ({"bm_lewis": .6, "bm_fable": .4}, 1.0, 1.0),      # lighter and quicker
    "deep": ({"bm_george": 1.0}, .93, .95),
    "george": ({"bm_george": 1.0}, 1.0, .95),
    "daniel": ({"bm_daniel": 1.0}, 1.0, .95),
    "lewis": ({"bm_lewis": 1.0}, 1.0, .95),
    "fable": ({"bm_fable": 1.0}, 1.0, .95),
}
DEFAULT_PRESET = "jarvis"


class KokoroService:
    def __init__(self, voice="bm_daniel", speed=1.0, loader=None):
        self.voice, self.speed = voice, speed
        self.loader = loader or self._load_real
        self.engine = None
        self.error = ""
        self.lock = threading.Lock()
        self.loading = False

    @property
    def possible(self):
        return bool(nv.available_voices())

    def warm(self):
        if not self.possible or self.loading or self.engine:
            return
        self.loading = True
        threading.Thread(target=self._ensure, name="kokoro-warm", daemon=True).start()

    def _load_real(self):
        import sys
        sys.path.insert(0, str(nv.RUNTIME))
        import onnxruntime as ort
        ort.disable_telemetry_events()
        from kokoro_onnx import Kokoro
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(str(nv.MODEL_DIR / "kokoro-v1.0.onnx"), sess_options=options,
                                       providers=["CPUExecutionProvider"])
        return Kokoro.from_session(session, str(nv.MODEL_DIR / "voices-v1.0.bin"))

    def _ensure(self):
        with self.lock:
            try:
                if self.engine is None:
                    self.engine = self.loader()
            except Exception:
                self.error = "Kokoro nu a putut fi încărcat."
            finally:
                self.loading = False
        return self.engine

    def _style(self, engine, mix):
        """One voice name, or a weighted blend of voice styles."""
        try:
            if len(mix) == 1:
                return next(iter(mix))
            parts = [engine.get_voice_style(name) * weight for name, weight in mix.items()]
            style = parts[0]
            for part in parts[1:]:
                style = style + part
            return style
        except Exception:
            return "bm_george"

    def speak(self, text, preset=DEFAULT_PRESET):
        """Return WAV bytes for one short piece of text (a sentence)."""
        mix, depth, tempo = PRESETS.get(preset, PRESETS[DEFAULT_PRESET])
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Text vocal invalid")
        engine = self.engine or (self._ensure() if self.possible or self.loader is not self._load_real else None)
        if engine is None:
            raise RuntimeError("Vocea Kokoro locală nu este disponibilă.")
        with self.lock:
            samples, rate = engine.create(text.strip()[:MAX_CHARS], voice=self._style(engine, mix),
                                          speed=self.speed * tempo / depth, lang="en-gb")
        rate = int(rate * depth)
        if not len(samples):
            raise ValueError("Audio invalid")
        peak = max(1.0, float(max(abs(float(s)) for s in samples[:: max(1, len(samples) // 4000)]))) if len(samples) else 1.0
        out = io.BytesIO()
        with wave.open(out, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            import array
            pcm = array.array("h", (int(max(-1.0, min(1.0, float(s) / peak * 0.92)) * 32767) for s in samples))
            wav.writeframes(pcm.tobytes())
        return out.getvalue()
