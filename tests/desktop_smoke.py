"""Explicit Tk smoke test; not part of headless test discovery."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from jarvis.storage import Store
from jarvis.core import Core
from jarvis.desktop import Desktop
from jarvis.voice import VoiceController
from tests.test_voice import FakeBackend


class DesktopSmoke(unittest.TestCase):
    def test_desktop_workflow(self):
        with tempfile.TemporaryDirectory() as folder:
            root = tk.Tk()
            root.withdraw()
            app = None
            try:
                app = Desktop(root, Core(Store(Path(folder) / "test.sqlite3")), VoiceController(FakeBackend()))
                app.voice.enabled.set(False)
                root.update_idletasks()
                for module in ("general", "fishroom", "youtube", "jobs", "game", "shop", "assistant"):
                    app.select_module(module)
                    for view in app.views:
                        app.show(view)
                        root.update_idletasks()
                app.select_module("fishroom")
                app.transcript("show my tasks")
                self.assertEqual(app.input.get(), "show my tasks")
                app.input.delete(0, "end")
                for kind in ("command", "tasks", "reminders", "notes", "clock"):
                    widget = app.widgets.open(kind)
                    widget.refresh()
                    root.update_idletasks()
                    self.assertIs(app.widgets.open(kind), widget)
                    widget.close()
                app.widgets.desktop_mode()
                self.assertEqual(root.state(), "withdrawn")
                for widget in list(app.widgets.windows.values()):
                    widget.close()
                self.assertNotEqual(root.state(), "withdrawn")
                self.assertTrue(app.send("memorează: Acvariu test"))
                self.assertEqual(len(app.memory_tree.get_children()), 1)
                self.assertTrue(app.send("task: Verifică filtrul"))
                self.assertEqual(len(app.tasks_tree.get_children()), 1)
                app.tasks_tree.selection_set(app.tasks_tree.get_children()[0])
                app.complete_task()
                self.assertEqual(len(app.tasks_tree.get_children()), 0)
                for reminder in (False, True):
                    app.task_dialog(reminder)
                    root.update_idletasks()
                    for child in root.winfo_children():
                        if isinstance(child, tk.Toplevel):
                            child.destroy()
                app.note_dialog()
                root.update_idletasks()
                for child in root.winfo_children():
                    if isinstance(child, tk.Toplevel):
                        child.destroy()
            finally:
                if app:
                    app.close()
                else:
                    root.destroy()


if __name__ == "__main__":
    unittest.main()
