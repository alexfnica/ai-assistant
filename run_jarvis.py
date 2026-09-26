"""Launch using the project location, independent of cwd and Python safe-path mode."""
import runpy
import sys
from pathlib import Path


def main():
    project = Path(__file__).resolve().parent
    if not (project / "jarvis" / "__main__.py").is_file():
        print("JARVIS: lipseste folderul aplicatiei 'jarvis'.", file=sys.stderr)
        print("Dezarhiveaza intregul pachet. Nu muta separat Start-Jarvis.cmd sau run_jarvis.py.", file=sys.stderr)
        return 2
    # Embedded/isolated Python can omit both cwd and script directories from sys.path.
    sys.path.insert(0, str(project))
    runpy.run_module("jarvis", run_name="__main__", alter_sys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
