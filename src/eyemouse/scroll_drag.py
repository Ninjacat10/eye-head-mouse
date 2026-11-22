"""Mouse modes: what a confirmed nod DOES, plus scroll and drag behaviour.

CLICK   nod = left click (default)
RIGHT   next nod = right click, then back to CLICK
DOUBLE  next nod = double click, then back to CLICK
DRAG    1st nod = press and hold, move with your eyes, 2nd nod = drop
SCROLL  cursor stays put; look at the top/bottom band of the screen to
        scroll that way (faster the further you look); nod = exit scroll
"""
from enum import Enum

from .config import CONFIG


class Mode(str, Enum):
    CLICK = "Click"
    RIGHT = "Right click"
    DOUBLE = "Double click"
    DRAG = "Drag"
    SCROLL = "Scroll"


class Scroller:
    def __init__(self):
        self.carry = 0.0  # fractional notches carried between frames

    def reset(self):
        self.carry = 0.0

    def speed(self, ny):
        """-1..+1: positive scrolls up (looking at the top band)."""
        band = CONFIG.scroll_band
        if ny < band:
            return (band - ny) / band
        if ny > 1 - band:
            return -(ny - (1 - band)) / band
        return 0.0

    def step(self, ny, dt):
        """Return whole wheel notches to send this frame."""
        self.carry += self.speed(ny) * CONFIG.scroll_speed * dt
        notches = int(self.carry)
        self.carry -= notches
        return notches


class Dragger:
    def __init__(self):
        self.holding = False

    def toggle(self, cursor, nx, ny):
        """1st call presses the button, 2nd releases. Returns True while holding."""
        if not self.holding:
            cursor.press(nx, ny)
            self.holding = True
        else:
            cursor.release(nx, ny)
            self.holding = False
        return self.holding

    def cancel(self, cursor):
        if self.holding:
            cursor.release()
            self.holding = False
