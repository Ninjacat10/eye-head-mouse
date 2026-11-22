"""Only report a class when the model is SURE about it.

A neural net never outputs exactly 100%, so "sure" means: the class
probability is >= CONFIG.confidence_threshold (0.95) for
CONFIG.frames_required (5) frames IN A ROW. Anything less -> None
("uncertain"), and the app does nothing.
"""
from .config import CONFIG


class ConfidenceGate:
    def __init__(self, num_classes: int):
        self.streaks = [0] * num_classes

    def update(self, probs):
        """Feed one frame of probabilities. Returns the confident class index or None."""
        thr = CONFIG.confidence_threshold
        for i, p in enumerate(probs):
            # Grow the streak if this frame is confident, otherwise reset to zero
            self.streaks[i] = self.streaks[i] + 1 if p >= thr else 0
        for i, s in enumerate(self.streaks):
            if s >= CONFIG.frames_required:
                return i
        return None

    def reset(self):
        self.streaks = [0] * len(self.streaks)
