import unittest
from jarvis.wake import WakeGate, is_wake_phrase


class FakeController:
    def __init__(self):
        self.busy = False
        self.started = []
        self.events = []
        self.stops = 0

    def start(self, action, **fields):
        self.started.append((action, fields))
        self.busy = True

    def stop(self):
        self.stops += 1
        self.busy = False
        self.events.clear()

    def drain(self):
        while self.events:
            self.busy = False
            yield self.events.pop(0)


class WakeTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.controller = FakeController()
        self.gate = WakeGate(self.controller, lambda: self.now)
        self.recognizers = [{"id": "english", "culture": "en-US"}]

    def test_explicit_opt_in(self):
        self.assertFalse(self.gate.tick(True))
        self.assertFalse(self.controller.started)
        self.assertTrue(self.gate.enable(self.recognizers))
        self.gate.tick(True)
        self.assertEqual(self.controller.started, [("wake", {"recognizer": "english"})])

    def test_phrase_and_confidence(self):
        self.assertTrue(is_wake_phrase("Hey, Jarvis!", .9))
        for text, score in [("Jarvis", .9), ("hey jarvis delete everything", .9),
                            ("hey jarvis", .4), ("hey jarvis", None), ("hey jarvis", float("nan"))]:
            self.assertFalse(is_wake_phrase(text, score))

    def test_no_english_recognizer(self):
        self.assertFalse(self.gate.enable([{"id": "romanian", "culture": "ro-RO"}]))
        self.assertIn("engleză", self.gate.error)
        self.assertFalse(self.gate.enabled)

    def test_wake_detected_once_then_cooldown(self):
        self.gate.enable(self.recognizers)
        self.gate.tick(True)
        self.controller.events.append(("wake", {"text": "Hey Jarvis", "confidence": .92}, None))
        self.assertTrue(self.gate.tick(True))
        self.assertFalse(self.gate.tick(True))
        self.assertEqual(len(self.controller.started), 1)
        self.now = 1
        self.gate.tick(True)
        self.assertEqual(len(self.controller.started), 2)

    def test_no_overlapping_listeners(self):
        self.gate.enable(self.recognizers)
        self.gate.tick(True)
        self.gate.tick(True)
        self.assertEqual(len(self.controller.started), 1)
        self.gate.tick(False)  # TTS, dictation, or review is active.
        self.assertFalse(self.controller.busy)
        self.assertEqual(self.controller.stops, 1)

    def test_silence_rearms_after_short_gap(self):
        self.gate.enable(self.recognizers)
        self.gate.tick(True)
        self.controller.events.append(("wake", {"text": "", "confidence": 0}, None))
        self.assertFalse(self.gate.tick(True))
        self.now = 0.5
        self.gate.tick(True)
        self.assertEqual(len(self.controller.started), 2)

    def test_failure_disables_instead_of_retry_loop(self):
        self.gate.enable(self.recognizers)
        self.gate.tick(True)
        self.controller.events.append(("wake", None, "Microphone unavailable"))
        self.assertFalse(self.gate.tick(True))
        self.assertFalse(self.gate.enabled)
        self.now = 20
        self.gate.tick(True)
        self.assertEqual(len(self.controller.started), 1)

    def test_stop_discards_late_wake(self):
        self.gate.enable(self.recognizers)
        self.gate.tick(True)
        self.controller.events.append(("wake", {"text": "Hey Jarvis", "confidence": .99}, None))
        self.gate.disable()
        self.assertFalse(self.gate.tick(True))
