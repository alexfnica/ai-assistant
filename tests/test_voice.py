import threading
import unittest
from jarvis.core import spoken_command
from jarvis.voice import VoiceController, preferred_voice


class FakeBackend:
    def __init__(self):
        self.finished = threading.Event()
        self.requests = []
        self.stop_count = 0

    def run(self, request, cancel=None):
        self.requests.append(request)
        self.finished.set()
        return {"ok": True, "text": "show my tasks"}

    def stop(self):
        self.stop_count += 1


class VoiceTests(unittest.TestCase):
    def test_prefer_british_male(self):
        voices = [{"id": "a", "gender": "Male", "culture": "en-US"},
                  {"id": "b", "gender": "Male", "culture": "en-GB"}]
        self.assertEqual(preferred_voice(voices)["id"], "b")
        self.assertEqual(preferred_voice(voices[:1])["id"], "a")
        self.assertIsNone(preferred_voice([]))

    def test_aliases_and_payload_preservation(self):
        self.assertEqual(spoken_command("Jarvis, ce am de făcut?"), "task-uri toate")
        self.assertEqual(spoken_command("Jarvis show my tasks."), "task-uri toate")
        self.assertEqual(spoken_command("Add a task Verifică Filtrul A"), "task: Verifică Filtrul A")
        self.assertEqual(spoken_command("Ține minte: Peștii sunt activi"), "memorează: Peștii sunt activi")
        self.assertEqual(spoken_command("Remember that tank A is new"), "memorează: tank A is new")

    def test_unknown_phrase_not_guessed(self):
        self.assertEqual(spoken_command("delete everything"), "delete everything")
        self.assertEqual(spoken_command("memorează: Jarvis, task: x"), "memorează: Jarvis, task: x")

    def test_controller_worker_delivers_data(self):
        backend = FakeBackend()
        controller = VoiceController(backend)
        controller.start("listen", recognizer="test")
        self.assertTrue(backend.finished.wait(2))
        # Read queue deterministically; completion is independent of UI polling.
        event = controller.events.get(timeout=2)
        controller.events.put(event)
        self.assertEqual(list(controller.drain())[0][1]["text"], "show my tasks")
        self.assertFalse(controller.busy)
        self.assertEqual(backend.requests[0]["recognizer"], "test")

    def test_cancel_discards_stale_event(self):
        controller = VoiceController(FakeBackend())
        old_generation = controller.generation
        controller.stop()
        controller.events.put((old_generation, "listen", {"text": "task: unwanted"}, None))
        self.assertEqual(list(controller.drain()), [])

    def test_worker_failure_delivered(self):
        class Broken(FakeBackend):
            def run(self, request, cancel=None):
                raise RuntimeError("Microphone unavailable")
        controller = VoiceController(Broken())
        controller.start("listen")
        event = controller.events.get(timeout=2)
        controller.events.put(event)
        self.assertEqual(list(controller.drain())[0][2], "Microphone unavailable")


if __name__ == "__main__":
    unittest.main()
