"""9-dot calibration: look at each dot, the app learns your eyes -> screen mapping.

Each dot: 0.9 s to settle your eyes, then 1.1 s of samples (dot shrinks).
Keep your head up and still-ish, move only your eyes. Esc cancels.
"""
import time

import numpy as np
from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from .gaze_mapper import GazeMapper
from .config import CONFIG

SETTLE_S, COLLECT_S = 0.9, 1.1
M = 0.06
TARGETS = [(x, y) for y in (M, 0.5, 1 - M) for x in (M, 0.5, 1 - M)]


class CalibrationWindow(QWidget):
    finished = pyqtSignal(object)  # GazeMapper on success, None if cancelled

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.idx = -1          # -1 = intro screen
        self.t0 = time.monotonic()
        self.X, self.Y, self.G = [], [], []
        self.result_text = None
        self.timer = QTimer(self, interval=16, timeout=self._tick)
        self.timer.start()

    # Called by the worker (via a signal) with every frame of eye data
    def add_sample(self, eye, gate_is_down):
        if self.idx < 0 or self.idx >= len(TARGETS) or eye is None or gate_is_down:
            return
        if eye.openness < CONFIG.blink_ratio:
            return
        if time.monotonic() - self.t0 >= SETTLE_S:
            self.X.append(eye.features)
            self.Y.append(TARGETS[self.idx])
            self.G.append(self.idx)

    def _tick(self):
        now = time.monotonic()
        if self.result_text is not None:
            if now - self.t0 > 2.5:
                self.timer.stop()
                self.close()
        elif self.idx < 0 and now - self.t0 > 2.5:
            self.idx, self.t0 = 0, now
        elif 0 <= self.idx < len(TARGETS) and now - self.t0 > SETTLE_S + COLLECT_S:
            self.idx, self.t0 = self.idx + 1, now
            if self.idx == len(TARGETS):
                self._finish()
        self.update()

    def _finish(self):
        groups = set(self.G)
        if len(groups) < 7:
            self.result_text = "Calibration failed - face not visible enough. Try again."
            self.finished.emit(None)
        else:
            mapper = GazeMapper()
            err = mapper.fit(np.array(self.X), np.array(self.Y), np.array(self.G))
            mapper.save()
            px = err * self.width()
            self.result_text = f"Calibrated!  Typical error ~{err * 100:.1f}% of screen (~{px:.0f} px)"
            self.finished.emit(mapper)
        self.t0 = time.monotonic()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.timer.stop()
            self.finished.emit(None)
            self.close()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        p.fillRect(0, 0, W, H, QColor(18, 18, 24))
        p.setPen(QColor(230, 230, 240))
        p.setFont(QFont("Segoe UI", 20))
        if self.result_text is not None:
            p.drawText(QRectF(0, 0, W, H), Qt.AlignmentFlag.AlignCenter, self.result_text)
            return
        if self.idx < 0:
            p.drawText(QRectF(0, 0, W, H), Qt.AlignmentFlag.AlignCenter,
                       "Calibration\n\nKeep your head UP and fairly still.\nFollow each dot with your EYES.\n\nEsc to cancel")
            return
        x, y = TARGETS[self.idx]
        t = time.monotonic() - self.t0
        collecting = t >= SETTLE_S
        frac = 1.0 if not collecting else max(0.0, 1 - (t - SETTLE_S) / COLLECT_S)
        r = 10 + 22 * frac
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(120, 255, 150) if collecting else QColor(255, 200, 60))
        p.drawEllipse(QRectF(x * W - r, y * H - r, 2 * r, 2 * r))
        p.setBrush(QColor(18, 18, 24))
        p.drawEllipse(QRectF(x * W - 3, y * H - 3, 6, 6))
        p.setPen(QColor(150, 150, 170))
        p.setFont(QFont("Segoe UI", 12))
        p.drawText(QRectF(0, H * 0.5 + 60, W, 30), Qt.AlignmentFlag.AlignCenter,
                   f"Dot {self.idx + 1} of {len(TARGETS)}")
