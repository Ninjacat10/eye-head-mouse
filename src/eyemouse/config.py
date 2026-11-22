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


CONFIG = Config()
