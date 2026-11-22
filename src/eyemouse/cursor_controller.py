"""Moves the real mouse and sends clicks/keys (via pynput).

Positions come in NORMALISED (0..1) coords and are converted to physical
pixels of the primary monitor. A short history of where the cursor was lets
the click land where you were looking BEFORE your head started to dip.
"""
import ctypes
import time
from collections import deque

from pynput.keyboard import Controller as KeyController, Key
from pynput.mouse import Button, Controller as MouseController


def _primary_screen_px():
    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDPIAware()  # so sizes are real pixels, not scaled
    except Exception:
        pass
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


class CursorController:
    def __init__(self):
        self.mouse = MouseController()
        self.keys = KeyController()
        self.width, self.height = _primary_screen_px()
        self.history = deque(maxlen=90)  # (time, nx, ny) ~3 s at 30 fps
        self.nx, self.ny = 0.5, 0.5

    def to_px(self, nx, ny):
        return int(nx * (self.width - 1)), int(ny * (self.height - 1))

    def move(self, nx, ny):
        self.nx, self.ny = nx, ny
        self.mouse.position = self.to_px(nx, ny)
        self.history.append((time.monotonic(), nx, ny))

    def position_before(self, seconds):
        """Where the cursor was `seconds` ago (falls back to the oldest/current)."""
        cutoff = time.monotonic() - seconds
        best = (self.nx, self.ny)
        for t, x, y in reversed(self.history):
            best = (x, y)
            if t <= cutoff:
                break
        return best

    # --- mouse actions at a normalised position ---------------------------
    def click(self, nx, ny, button="left", count=1):
        self.move(nx, ny)
        self.mouse.click(Button.left if button == "left" else Button.right, count)

    def press(self, nx, ny):
        self.move(nx, ny)
        self.mouse.press(Button.left)

    def release(self, nx=None, ny=None):
        if nx is not None:
            self.move(nx, ny)
        self.mouse.release(Button.left)

    def scroll(self, notches):
        self.mouse.scroll(0, notches)  # + = up, - = down

    # --- keyboard shortcuts for the navigator menu ------------------------
    def hotkey(self, *keys):
        for k in keys:
            self.keys.press(k)
        for k in reversed(keys):
            self.keys.release(k)


KEY = Key  # re-export so other modules do not import pynput directly
