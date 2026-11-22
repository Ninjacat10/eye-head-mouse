"""Every tunable number in one place. Other modules import CONFIG."""
from dataclasses import dataclass


@dataclass
class Config:
    # Camera
    camera_index: int = 0          # 0 = built-in webcam, 1 = external
    frame_width: int = 640
    frame_height: int = 480
    target_fps: int = 30

    # "Only act when sure" rule: class prob >= threshold for N frames in a row
    confidence_threshold: float = 0.95
    frames_required: int = 5

    # Click timing
    click_delay_s: float = 0.5      # head must stay down this long before a click
    uncertain_grace_s: float = 0.15 # brief wobble allowed during the countdown
    click_lookback_s: float = 0.15  # click where the cursor was just BEFORE the nod
    cooldown_s: float = 0.4         # min time between actions (plus head must come up)

    # Cursor feel (live sliders in the control panel)
    sensitivity: float = 1.0        # 0.5 = calmer/smaller moves, 2.0 = reach edges easier
    smoothing: float = 0.6          # 0 = raw and jittery, 1 = very smooth and laggy

    # Eyes
    blink_ratio: float = 0.17       # eye openness below this = blink -> freeze cursor

    # Scroll mode: look at the top/bottom band of the screen to scroll
    scroll_band: float = 0.35       # top 35% scrolls up, bottom 35% scrolls down
    scroll_speed: float = 12.0      # wheel notches per second at full speed

    # The "Menu" tab at the top-centre of the screen (normalised 0..1 coords)
    menu_tab: tuple = (0.43, 0.0, 0.14, 0.05)   # x, y, w, h

    # What moves the cursor:  "head" = nose pointing,  "eye" = eye gaze
    control_mode: str = "head"
    # What clicks:  "gesture" = open mouth / wink,  "nod" = your head-down model
    click_method: str = "gesture"

    # Gesture thresholds (relative to your neutral face from calibration)
    mouth_open_delta: float = 0.25  # lip gap / mouth width above neutral = "open"
    eye_closed_frac: float = 0.5    # eye below 50% of its normal openness = shut
    eye_open_frac: float = 0.75     # other eye above 75% = open (so it is a wink, not a blink)
    wink_right_click: bool = True


CONFIG = Config()

# --- remember the user's choices between runs ------------------------------
import json as _json  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

from .paths import DATA_DIR as _DATA_DIR  # noqa: E402

SETTINGS_FILE = _DATA_DIR / "settings.json"
_SAVED = ("control_mode", "click_method", "sensitivity", "smoothing")


def load_settings():
    try:
        for k, v in _json.loads(SETTINGS_FILE.read_text()).items():
            if k in _SAVED:
                setattr(CONFIG, k, v)
    except (OSError, ValueError):
        pass


def save_settings():
    try:
        SETTINGS_FILE.write_text(_json.dumps({k: getattr(CONFIG, k) for k in _SAVED}))
    except OSError:
        pass
