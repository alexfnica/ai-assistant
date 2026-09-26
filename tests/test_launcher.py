import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class LauncherTests(unittest.TestCase):
    def test_bootstrap_from_other_directory_in_isolated_python(self):
        script = Path(__file__).resolve().parents[1] / "run_jarvis.py"
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-I", "-X", "utf8", str(script), "--help"],
                                    cwd=folder, capture_output=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--data-dir", result.stdout)

    def test_missing_package_has_clear_error(self):
        script = Path(__file__).resolve().parents[1] / "run_jarvis.py"
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "run_jarvis.py"
            shutil.copy2(script, copy)
            result = subprocess.run([sys.executable, "-I", str(copy)], cwd=folder,
                                    capture_output=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Dezarhiveaza intregul pachet", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
