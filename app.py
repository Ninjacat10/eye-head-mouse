"""Launcher used by the packaged Windows app (and `python app.py`)."""
import sys

from src.eyemouse.paths import DATA_DIR, FROZEN

if FROZEN or "--log" in sys.argv or sys.stdout is None or sys.stderr is None:
    # No console (packaged .exe or pythonw shortcut): send all output to a log file
    log = open(DATA_DIR / "app.log", "w", buffering=1, encoding="utf-8")
    sys.stdout = sys.stderr = log

from src.main import App  # noqa: E402

if __name__ == "__main__":
    sys.exit(App().run())
