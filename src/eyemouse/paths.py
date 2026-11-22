"""Where files live, both when running from source and as the packaged .exe.

RESOURCE_DIR  read-only files shipped with the app (models)
DATA_DIR      per-user files the app writes (calibration, settings)
"""
import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)   # True inside the PyInstaller build

if FROZEN:
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "EyeHeadMouse"
else:
    RESOURCE_DIR = Path(__file__).resolve().parents[2]
    DATA_DIR = RESOURCE_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR = RESOURCE_DIR / "models"
