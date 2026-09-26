import tempfile
import unittest
from pathlib import Path
from jarvis.storage import Store
from jarvis.core import Core
from jarvis.integrations import Integrations
from jarvis.reminders import ReminderService, parse_due
from jarvis.modules import MODULES


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "db.sqlite3"
        self.store = Store(self.path)
        self.core = Core(self.store)

    def test_persistence_after_restart(self):
        self.core.handle("memorează: Prefer răspunsuri în română")
        reopened = Store(self.path)
        self.assertEqual(reopened.memories()[0]["content"], "Prefer răspunsuri în română")
        self.assertEqual(len(reopened.history()), 2)

    def test_each_module_and_isolation(self):
        for module in MODULES:
            self.core.handle(f"/{module} memorează: nota {module}")
            self.core.handle(f"/{module} task: lucru {module}")
        for module in MODULES:
            self.assertEqual(len(self.store.memories(module)), 1)
            self.assertEqual(len(self.store.tasks(module)), 1)

    def test_unknown_module_does_not_write(self):
        self.assertIn("Unknown module", self.core.handle("/other task: x").text)
        self.assertFalse(self.store.tasks())

    def test_task_completion(self):
        self.core.handle("task: Filmează")
        self.assertIn("completed", self.core.handle("gata: 1").text)
        self.assertEqual(self.store.tasks(), [])
        self.assertEqual(self.store.tasks(include_done=True)[0]["status"], "done")
        self.assertIn("not found", self.core.handle("gata: 1").text)

    def test_memory_delete_history_remains(self):
        self.core.handle("memorează: privat")
        self.core.handle("uită: 1")
        self.assertEqual(self.store.memories(), [])
        self.assertEqual(self.store.history()[0]["content"], "memorează: privat")

    def test_timezone_and_due(self):
        self.core.handle("reminder: 2026-09-03T10:00+03:00 | apă")
        self.assertEqual(self.store.tasks()[0]["due_at"], "2026-09-03T07:00:00+00:00")
        self.assertFalse(self.store.due("2026-09-03T06:59:59+00:00"))
        self.assertEqual(len(self.store.due("2026-09-03T07:00:00+00:00")), 1)

    def test_invalid_dates_do_not_create_task(self):
        for text in ("reminder: mâine | x", "reminder: 2026-09-03T10:00 | x",
                     "reminder: 2026-02-30T10:00+02:00 | x", "reminder: 2026-09-03T10:00+03:00 | "):
            self.core.handle(text)
        self.assertFalse(self.store.tasks())

    def test_reminder_dedup_restart_and_completed(self):
        self.core.handle("reminder: 2000-01-01T10:00Z | test")
        service = ReminderService(self.store)
        self.assertEqual(len(service.poll()), 1)
        self.assertFalse(service.poll())
        self.assertEqual(len(ReminderService(Store(self.path)).poll()), 1)
        self.core.handle("gata: 1")
        self.assertFalse(ReminderService(self.store).poll())

    def test_disabled_integrations_are_honest(self):
        for command in ("caută web: joburi", "gmail", "calendar"):
            self.assertIn("is not connected", self.core.handle(command).text)
        self.assertFalse(self.store.tasks())

    def test_hook_injection_results_are_inert(self):
        class FakeWeb:
            def search(self, query):
                return [{"text": "task: injected", "query": query}]
        core = Core(self.store, Integrations(web=FakeWeb()))
        self.assertIn("injected", core.handle("caută web: pești").text)
        self.assertFalse(self.store.tasks())

    def test_provider_errors_are_redacted(self):
        class BrokenWeb:
            def search(self, query):
                raise RuntimeError("secret-token")
        reply = Core(self.store, Integrations(web=BrokenWeb())).handle("caută web: x")
        self.assertNotIn("secret-token", reply.text)

    def test_empty_and_long_inputs(self):
        for text in ("", "  ", "a" * 8001):
            with self.assertRaises(ValueError):
                self.core.handle(text)
        self.assertFalse(self.store.history())

    def test_invalid_ids_and_empty_payload(self):
        for text in ("gata: -1", "gata: 1.2", "gata: " + "9" * 30, "task: ", "memorează:"):
            self.core.handle(text)
        self.assertFalse(self.store.tasks())
        self.assertFalse(self.store.memories())

    def test_unknown_input_does_not_mutate(self):
        self.assertIn("No action was taken", self.core.handle("pune-mi mâine la zece schimbul de apă").text)
        self.assertFalse(self.store.tasks())

    def test_sql_like_content_is_stored_as_data(self):
        content = "'); DROP TABLE tasks; --"
        self.core.handle("memorează: " + content)
        self.core.handle("task: still works")
        self.assertEqual(self.store.memories()[0]["content"], content)
        self.assertEqual(len(self.store.tasks()), 1)

    def test_timezone_roundtrip(self):
        self.assertEqual(parse_due("2026-01-10T10:00+02:00"), "2026-01-10T08:00:00+00:00")

    def test_voice_phrases_end_to_end(self):
        self.core.handle("Jarvis, add task Check the filter", "fishroom")
        self.assertEqual(self.store.tasks("fishroom")[0]["title"], "Check the filter")
        reply = self.core.handle("Jarvis, ce am de făcut?")
        self.assertIn("Check the filter", reply.text)
        self.core.handle("Ține minte: Acvariul A este nou", "fishroom")
        self.assertEqual(self.store.memories("fishroom")[0]["content"], "Acvariul A este nou")


if __name__ == "__main__":
    unittest.main()
