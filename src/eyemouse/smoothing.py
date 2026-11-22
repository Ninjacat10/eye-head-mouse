"""Removes jitter from the gaze point and applies sensitivity.

One Euro filter (Casiez et al., 2012): heavy smoothing when your eyes are
still (kills jitter), light smoothing when they move fast (kills lag).
"""
import math

from .config import CONFIG


class _LowPass:
    def __init__(self):
        self.y = None

    def __call__(self, x, alpha):
        self.y = x if self.y is None else alpha * x + (1 - alpha) * self.y
        return self.y


class OneEuro:
    def __init__(self):
        self.x_f, self.dx_f = _LowPass(), _LowPass()
        self.last_x = self.last_t = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, t, min_cutoff, beta, d_cutoff=1.0):
        if self.last_t is None:
            self.last_x, self.last_t = x, t
            return self.x_f(x, 1.0)
        dt = max(t - self.last_t, 1e-3)
        dx = (x - self.last_x) / dt
        edx = self.dx_f(dx, self._alpha(d_cutoff, dt))
        cutoff = min_cutoff + beta * abs(edx)          # faster motion -> less smoothing
        self.last_x, self.last_t = x, t
        return self.x_f(x, self._alpha(cutoff, dt))


class GazeSmoother:
    """Filters normalised (x, y) gaze, then scales it by sensitivity."""

    def __init__(self):
        self.fx, self.fy = OneEuro(), OneEuro()

    def reset(self):
        self.fx, self.fy = OneEuro(), OneEuro()

    def __call__(self, x, y, t):
        s = min(max(CONFIG.smoothing, 0.0), 1.0)
        min_cutoff = 3.0 * (0.03 / 3.0) ** s     # 3 Hz (raw) .. 0.03 Hz (very smooth)
        beta = 2.0 * (1 - s) + 0.05
        sx = self.fx(x, t, min_cutoff, beta)
        sy = self.fy(y, t, min_cutoff, beta)
        k = CONFIG.sensitivity                    # stretch around the screen centre
        sx = 0.5 + (sx - 0.5) * k
        sy = 0.5 + (sy - 0.5) * k
        return min(max(sx, 0.0), 1.0), min(max(sy, 0.0), 1.0)
