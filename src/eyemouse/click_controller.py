"""Turns confident head-down frames into ONE action, with your 0.5 s wait.

Timeline of a click:
  head down (confident) -> countdown starts, cursor is frozen
  stays down 0.5 s      -> FIRE (once)
  head must come back up confidently before the next click can arm
A brief uncertain wobble (< uncertain_grace_s) does not cancel the countdown;
anything longer, or head-up, cancels it.
"""
from .config import CONFIG


class ClickController:
    def __init__(self):
        self.arm_start = None       # time the countdown began
        self.last_down = None       # last time the gate said DOWN
        self.need_up = False        # True after firing until head is up again
        self.last_fire = -1e9

    @property
    def armed(self):
        return self.arm_start is not None

    def progress(self, now):
        if self.arm_start is None:
            return 0.0
        return min((now - self.arm_start) / CONFIG.click_delay_s, 1.0)

    def update(self, gate, now, UP, DOWN):
        """gate = confident class or None. Returns True on the frame a click should fire."""
        if gate == UP:
            self.arm_start = None
            self.need_up = False
            return False

        if gate == DOWN:
            self.last_down = now
            if self.need_up or now - self.last_fire < CONFIG.cooldown_s:
                return False
            if self.arm_start is None:
                self.arm_start = now
            if now - self.arm_start >= CONFIG.click_delay_s:
                self.arm_start = None
                self.need_up = True
                self.last_fire = now
                return True
            return False

        # Uncertain frame: keep the countdown only for a short grace period
        if self.arm_start is not None and (self.last_down is None or now - self.last_down > CONFIG.uncertain_grace_s):
            self.arm_start = None
        return False

    def cancel(self):
        self.arm_start = None
