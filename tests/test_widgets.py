import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from jarvis.storage import Store
from jarvis.widgets import WidgetPreferences, WidgetManager, clamp_position, widget_rows


class WidgetTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.store = Store(self.folder / "jarvis.sqlite3")

    def test_preferences_persist_and_update(self):
        path = self.folder / "widgets.sqlite3"
        prefs = WidgetPreferences(path)
        prefs.save("tasks", 100, 200, True, True)
        self.assertEqual(WidgetPreferences(path).load()["tasks"],
                         {"x": 100, "y": 200, "pinned": True, "visible": True})
        prefs.save("tasks", 300, 400, False, False)
        self.assertEqual(len(prefs.load()), 1)
        self.assertFalse(prefs.load()["tasks"]["visible"])
        self.assertFalse(self.store.tasks())

    def test_unknown_widget_rejected(self):
        with self.assertRaises(ValueError):
            WidgetPreferences(self.folder / "widgets.sqlite3").save("wrong", 0, 0, True, True)

    def test_offscreen_position_recovery(self):
        self.assertEqual(clamp_position(-1500, -900, 440, 350, 1920, 1080), (0, 0))
        self.assertEqual(clamp_position(4000, 2000, 440, 350, 1920, 1080), (1480, 670))
        self.assertEqual(clamp_position(100, 200, 440, 350, 1920, 1080), (100, 200))

    def test_widget_records_share_source_and_filter(self):
        task = self.store.add_task("fishroom", "Filtru")
        self.store.add_task("game", "Build", "2026-10-01T08:00:00+00:00")
        self.store.remember("youtube", "Idee video")
        self.assertEqual(len(widget_rows(self.store, "tasks")), 2)
        self.assertEqual(len(widget_rows(self.store, "reminders")), 1)
        self.assertEqual(len(widget_rows(self.store, "notes", "youtube")), 1)
        self.assertEqual(widget_rows(self.store, "notes", "fishroom"), [])
        self.store.complete(task)
        self.assertEqual(widget_rows(self.store, "tasks", "fishroom"), [])

    def test_transcript_routes_to_widget_without_execution(self):
        manager = WidgetManager.__new__(WidgetManager)
        widget = Mock()
        widget.kind = "command"
        widget.input.get.return_value = ""
        manager.windows = {"command": widget}
        manager.capture_target = widget
        self.assertTrue(manager.accept_transcript("add task Filtru"))
        widget.input.insert.assert_called_once_with(0, "add task Filtru")
        widget.send.assert_not_called()
        self.assertIsNone(manager.capture_target)

    def test_existing_draft_preserved(self):
        manager = WidgetManager.__new__(WidgetManager)
        widget = Mock()
        widget.kind = "command"
        widget.input.get.return_value = "draft"
        manager.windows = {"command": widget}
        manager.capture_target = widget
        manager.accept_transcript("new words")
        widget.input.insert.assert_called_once_with("end", " new words")

    def test_closed_capture_target_falls_back(self):
        manager = WidgetManager.__new__(WidgetManager)
        manager.capture_target = Mock(kind="command")
        manager.windows = {}
        self.assertFalse(manager.accept_transcript("anything"))

    def test_wake_opens_command_and_starts_capture(self):
        manager = WidgetManager.__new__(WidgetManager)
        manager.app = Mock()
        widget = Mock()
        widget.input.get.return_value = ""
        manager.open = Mock(return_value=widget)
        manager.activate_from_wake()
        manager.open.assert_called_once_with("command")
        widget.listen.assert_called_once()

    def test_wake_preserves_existing_draft(self):
        manager = WidgetManager.__new__(WidgetManager)
        manager.app = Mock()
        widget = Mock()
        widget.input.get.return_value = "mesaj netrimis"
        manager.open = Mock(return_value=widget)
        manager.activate_from_wake()
        widget.listen.assert_not_called()
        manager.app.voice.set_state.assert_called_once()


if __name__ == "__main__":
    unittest.main()
