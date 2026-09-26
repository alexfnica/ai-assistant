import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from jarvis.core import Core
from jarvis.routines import Routines, parse_days, parse_times
from jarvis.storage import Store


class RoutineTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.core = Core(Store(self.dir / "jarvis.sqlite3"))

    def say(self, text):
        return self.core.handle(text, "fishroom").text

    def test_parsing(self):
        self.assertEqual(parse_days("sunday and wednesday"), [2, 6])
        self.assertEqual(parse_days("day"), list(range(7)))
        self.assertEqual(parse_times("10:00 am and 8 pm"), ["10:00", "20:00"])
        self.assertEqual(parse_times("12:00 pm"), ["12:00"])
        self.assertEqual(parse_times(None, "morning"), ["08:00"])

    def test_add_list_remove(self):
        reply = self.say("remind me every day at 10:00 am to feed the fish")
        self.assertIn("Routine #1 saved", reply)
        self.assertIn("Feed the fish", reply)
        self.say("remind me every Sunday at 12:00 to change water in tank A")
        listing = self.say("routines")
        self.assertIn("#2 Change water in tank A - every Sunday at 12:00", listing)
        self.assertIn("removed", self.say("remove routine 1"))
        self.assertNotIn("Feed the fish", self.say("routines"))

    def test_fires_once_per_slot_and_becomes_a_task(self):
        self.say("remind me every day at 10:00 to feed the fish")
        # created "now"; move the clock: a later slot on any day fires once
        routines = Routines(self.dir)
        row = routines.list()[0]
        row["last"] = "2000-01-01 00:00"
        routines._write([row])
        noon = datetime(2026, 9, 27, 10, 5)
        self.assertEqual(len(self.core.routines_tick(noon)), 1)
        self.assertEqual(self.core.routines_tick(noon), [])
        tasks = self.core.store.tasks("fishroom")
        self.assertEqual(tasks[0]["title"], "Routine: Feed the fish")

    def test_missed_slot_older_than_six_hours_is_skipped(self):
        self.say("remind me every day at 08:00 to feed the fish")
        routines = Routines(self.dir)
        row = routines.list()[0]
        row["last"] = "2000-01-01 00:00"
        routines._write([row])
        self.assertEqual(self.core.routines_tick(datetime(2026, 9, 27, 20, 0)), [])
        self.assertEqual(len(self.core.routines_tick(datetime(2026, 9, 27, 11, 0))), 1)

    def test_not_a_routine(self):
        self.assertNotIn("Routine #", self.say("remind me later about the fish"))


if __name__ == "__main__":
    unittest.main()
