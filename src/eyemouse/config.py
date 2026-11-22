from dataclasses import dataclass


@dataclass
class Config:
    # Camera
    camera_index: int = 0          # 0 = built-in webcam, 1 = external
    frame_width: int = 640
    frame_height: int = 480
    target_fps: int = 30

    # "Only act when sure" rule
    confidence_threshold: float = 0.95
    frames_required: int = 5

    # Click timing
    click_delay_s: float = 0.5     # wait before a click fires
    click_cooldown_s: float = 0.6  # stops one gesture = many clicks

    # Cursor feel (sliders in Chat 6)
    sensitivity: float = 1.0
    smoothing: float = 0.5


CONFIG = Config()
