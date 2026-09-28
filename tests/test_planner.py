import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from jarvis.storage import Store
from jarvis.planner import Planner
from jarvis.briefing import build_briefing


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data_dir = Path(self.temp.name)
        self.store = Store(self.data_dir / "db.sqlite3")
        self.planner = Planner(self.data_dir)
        for i in range(5):
            self.store.add_task("game", f"game backlog {i}")
        for i in range(5):
            self.store.add_task("shop", f"shop backlog {i}")
        for i in range(5):
            self.store.add_task("assistant", f"assistant backlog {i}")

    def test_promotes_up_to_two_per_module(self):
        picks = self.planner.todays_picks(self.store)
        self.assertEqual(len(picks["game"]), 2)
        self.assertEqual(len(picks["shop"]), 2)
        self.assertEqual(len(picks["assistant"]), 2)
        for module, tasks in picks.items():
            for task in tasks:
                self.assertIsNotNone(task["due_at"])

    def test_same_day_is_idempotent(self):
        first = self.planner.todays_picks(self.store)
        second = self.planner.todays_picks(self.store)
        self.assertEqual([t["id"] for t in first["game"]], [t["id"] for t in second["game"]])
        # backlog beyond the first two stays untouched (no due date) on the same day
        remaining = [t for t in self.store.tasks("game") if not t["due_at"]]
        self.assertEqual(len(remaining), 3)

    def test_new_day_promotes_the_next_batch(self):
        day_one = self.planner.todays_picks(self.store, now=datetime(2026, 9, 28))
        day_two = self.planner.todays_picks(self.store, now=datetime(2026, 9, 29))
        self.assertNotEqual({t["id"] for t in day_one["game"]}, {t["id"] for t in day_two["game"]})

    def test_briefing_includes_todays_picks(self):
        text = build_briefing(self.store, now=datetime.now().astimezone())
        self.assertIn("Today's picks:", text)
        self.assertIn("game backlog 0", text)


if __name__ == "__main__":
    unittest.main()
