"""Face-gesture clicks (no extra model needed - measured from face landmarks).

  OPEN MOUTH  -> left click     (inner-lip gap well above your neutral face)
  WINK        -> right click    (one eye shut, the other clearly open)
  blink (both eyes) is ignored, so normal blinking never clicks.

Same "only when sure" rule as the head model: a gesture must be clearly
present for CONFIG.frames_required frames in a row. In-between faces
(half-open mouth, squint) count as UNCERTAIN and do nothing.

Output matches ConfidenceGate so the click controller works unchanged:
  gate = UP (neutral face) / DOWN (gesture held) / None (uncertain)
"""
from .config import CONFIG
from .head_classifier import HEAD_DOWN, HEAD_UP


class GestureGate:
    def __init__(self):
        self.streak_label = None
        self.streak = 0
        self.values = {}

    def _classify(self, eye, base):
        mouth_open = base["mouth"] + CONFIG.mouth_open_delta
        mouth_neutral = base["mouth"] + CONFIG.mouth_open_delta * 0.45
        a_closed = eye.eye_a < base["eye_a"] * CONFIG.eye_closed_frac
        b_closed = eye.eye_b < base["eye_b"] * CONFIG.eye_closed_frac
        a_open = eye.eye_a > base["eye_a"] * CONFIG.eye_open_frac
        b_open = eye.eye_b > base["eye_b"] * CONFIG.eye_open_frac
        self.values = {"mouth": eye.mouth, "eye_a": eye.eye_a, "eye_b": eye.eye_b,
                       "mouth_thr": mouth_open}

        if eye.mouth >= mouth_open:
            return "left"
        if (a_closed and b_open) or (b_closed and a_open):
            return "right" if CONFIG.wink_right_click else None
        if eye.mouth <= mouth_neutral:
            return "neutral"          # includes normal blinks (both eyes closed)
        return None                   # half-open mouth etc. -> not sure

    def update(self, eye, base):
        """Returns (gate, button)."""
        if eye is None:
            self.streak_label, self.streak = None, 0
            return None, None
        label = self._classify(eye, base)
        if label == self.streak_label:
            self.streak += 1
        else:
            self.streak_label, self.streak = label, 1
        if label is None or self.streak < CONFIG.frames_required:
            return None, None
        if label == "neutral":
            return HEAD_UP, None
        return HEAD_DOWN, label
