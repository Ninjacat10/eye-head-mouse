from dataclasses import dataclass

@dataclass
class Config:
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    target_fps: int = 30

    confidence_threshold: float = 0.95
    frames_required: int = 5
    click_delay_s: float = 0.5
    click_cooldown_s: float = 0.6

    sensitivity: float = 1.0
    smoothing: float = 0.5

CONFIG = Config()