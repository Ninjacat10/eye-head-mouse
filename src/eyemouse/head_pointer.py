"""HEAD mode: point your nose at the screen, the cursor goes there.

Pose features come from eye_tracker (yaw = nose left/right of the cheek centre,
pitch = nose below the eye line, both / face width). A straight-line fit maps
them to normalised screen coords:

    x = a0 + a1*yaw + a2*pitch        y = b0 + b1*yaw + b2*pitch

* Works instantly with default gains (about 15 degrees of head turn reaches an edge).
* "Recalibrate" in head mode fits the gains to YOUR range of motion (9 dots).
* "Recenter" (Ctrl+Alt+R) re-zeroes it so where you point now = screen centre.

Calibration also records your neutral face (eye openness, mouth gap), which
the gesture detector uses as the baseline for winks and open-mouth clicks.
"""
import json
from pathlib import Path

import numpy as np

HEAD_CALIB_FILE = Path(__file__).resolve().parents[2] / "head_calibration.json"

DEFAULT_COEF = np.array([[0.5, 0.5],      # intercepts
                         [4.0, 0.0],      # yaw   -> x
                         [0.0, 5.0]])     # pitch -> y
DEFAULT_BASELINE = {"eye_a": 0.28, "eye_b": 0.28, "mouth": 0.03}


def _design(head):
    head = np.atleast_2d(head)
    return np.column_stack([np.ones(len(head)), head[:, 0], head[:, 1]])


class HeadMapper:
    def __init__(self):
        self.coef = DEFAULT_COEF.copy()
        self.offset = np.zeros(2)
        self.baseline = dict(DEFAULT_BASELINE)
        self.calibrated = False
        self.needs_recenter = True   # default gains have no idea where "centre" is

    def _raw(self, head):
        return (_design(head) @ self.coef)[0]

    def predict(self, head):
        return np.clip(self._raw(head) + self.offset, 0.0, 1.0)

    def recenter(self, head):
        """Make the current pose point at the middle of the screen."""
        self.offset = np.array([0.5, 0.5]) - self._raw(head)
        self.needs_recenter = False

    def fit(self, H, Y, groups, eye_a, eye_b, mouth):
        """H: (n,2) poses, Y: (n,2) targets. Returns leave-one-target-out error."""
        H, Y, groups = np.asarray(H), np.asarray(Y), np.asarray(groups)
        errs = []
        for g in np.unique(groups):
            tr, te = groups != g, groups == g
            c, *_ = np.linalg.lstsq(_design(H[tr]), Y[tr], rcond=None)
            errs.append(np.linalg.norm((_design(H[te]) @ c).mean(0) - Y[te][0]))
        self.coef, *_ = np.linalg.lstsq(_design(H), Y, rcond=None)
        self.offset = np.zeros(2)
        self.baseline = {"eye_a": float(np.median(eye_a)), "eye_b": float(np.median(eye_b)),
                         "mouth": float(np.median(mouth))}
        self.calibrated = True
        self.needs_recenter = False
        return float(np.mean(errs))

    def save(self, path=HEAD_CALIB_FILE):
        Path(path).write_text(json.dumps({"coef": self.coef.tolist(), "baseline": self.baseline}))

    def load(self, path=HEAD_CALIB_FILE):
        if not Path(path).exists():
            return False
        d = json.loads(Path(path).read_text())
        self.coef = np.array(d["coef"])
        self.baseline = d["baseline"]
        self.calibrated = True
        self.needs_recenter = False
        return True
