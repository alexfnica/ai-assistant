import unittest
import wave
import io
from jarvis.kokoro_service import KokoroService


class FakeEngine:
    def create(self, text, voice, speed, lang):
        return [0.0, 0.5, -0.5, 0.25] * 100, 24000


class KokoroServiceTests(unittest.TestCase):
    def test_returns_valid_wav_and_loads_once(self):
        calls = []
        service = KokoroService(loader=lambda: calls.append(1) or FakeEngine())
        for _ in range(2):
            data = service.speak("Good afternoon, sir.", "george")
        self.assertEqual(len(calls), 1)
        with wave.open(io.BytesIO(data)) as wav:
            self.assertEqual((wav.getnchannels(), wav.getframerate(), wav.getnframes()), (1, 24000, 400))

    def test_jarvis_preset_is_calm_and_blends_two_voices(self):
        class Style(list):
            def __mul__(self, w): return Style(x * w for x in self)
            def __add__(self, o): return Style(a + b for a, b in zip(self, o))
        class Engine(FakeEngine):
            def __init__(self): self.seen = []
            def get_voice_style(self, name): return Style([1.0, 2.0])
            def create(self, text, voice, speed, lang):
                self.seen.append((voice, speed)); return super().create(text, voice, speed, lang)
        engine = Engine()
        data = KokoroService(loader=lambda: engine).speak("Hello.", "jarvis")
        self.assertEqual(engine.seen[0][0], [1.0, 2.0])  # the two halves of the blend
        self.assertLess(engine.seen[0][1], 1.0)  # calmer tempo
        self.assertEqual(len(KokoroService(loader=lambda: engine).speak('Hi.', 'jarvis3')), len(KokoroService(loader=lambda: engine).speak('Hi.', 'jarvis3')))
        with wave.open(io.BytesIO(data)) as wav:
            self.assertEqual(wav.getframerate(), 24000)

    def test_unavailable_engine_raises_runtime_error_and_bad_text_value_error(self):
        service = KokoroService()  # no Kokoro files in the test environment
        with self.assertRaises(RuntimeError):
            service.speak("hello")
        with self.assertRaises(ValueError):
            KokoroService(loader=lambda: FakeEngine()).speak("  ")


if __name__ == "__main__":
    unittest.main()
