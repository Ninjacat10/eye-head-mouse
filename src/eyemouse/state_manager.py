"""The brain: one place that decides what happens each frame.

Inputs per frame : confident head class (or None), eye features, time
Outputs          : cursor moves / clicks / scrolls, and a Status snapshot
                   that the overlay and control panel draw.

States (drive the edge-glow colour):
  PAUSED     tracking stopped (red)
  NO_FACE    camera cannot see you (grey)
  UNCERTAIN  model not sure -> do nothing, cursor frozen (amber)
  HOVER      head up, eyes move the cursor (blue)
  ARMING     head down, 0.5 s countdown running (green, fills up)
  COOLDOWN   clicked, waiting for head to come back up (dim green)
"""
import time
from dataclasses import dataclass

from .click_controller import ClickController
from .config import CONFIG
from .cursor_controller import KEY, CursorController
from .gaze_mapper import GazeMapper
from .head_classifier import HEAD_DOWN, HEAD_UP
from .head_pointer import HeadMapper
from .scroll_drag import Dragger, Mode, Scroller
from .smoothing import GazeSmoother

# Navigator menu: (id, label), laid out as a 5 x 4 grid of big gaze-friendly tiles.
MENU_ITEMS = [
    ("left", "Left click"), ("right", "Right click"), ("double", "Double click"),
    ("drag", "Drag"), ("scroll", "Scroll"),
    ("osk", "Keyboard"), ("voice", "Voice typing"), ("taskview", "Task view"),
    ("desktop", "Show desktop"), ("back", "Back"),
    ("copy", "Copy"), ("paste", "Paste"), ("recenter", "Recenter"),
    ("pause", "Pause"), ("recal", "Recalibrate"),
    ("sens_dn", "Sensitivity -"), ("sens_up", "Sensitivity +"),
    ("smooth_dn", "Smoothing -"), ("smooth_up", "Smoothing +"), ("close", "Close menu"),
]
MENU_COLS, MENU_ROWS = 5, 4
MENU_AREA = (0.08, 0.14, 0.84, 0.76)  # x, y, w, h (normalised)


def menu_rect(i):
    """Normalised (x, y, w, h) of tile i - shared by drawing and hit-testing."""
    ax, ay, aw, ah = MENU_AREA
    gap = 0.012
    w = (aw - gap * (MENU_COLS - 1)) / MENU_COLS
    h = (ah - gap * (MENU_ROWS - 1)) / MENU_ROWS
    c, r = i % MENU_COLS, i // MENU_COLS
    return ax + c * (w + gap), ay + r * (h + gap), w, h


def inside(nx, ny, rect):
    x, y, w, h = rect
    return x <= nx <= x + w and y <= ny <= y + h


def menu_hit(nx, ny):
    for i in range(len(MENU_ITEMS)):
        if inside(nx, ny, menu_rect(i)):
            return i
    return None


@dataclass
class Status:
    state: str = "PAUSED"
    mode: str = Mode.CLICK.value
    progress: float = 0.0
    cursor: tuple = (0.5, 0.5)
    menu_open: bool = False
    menu_hover: object = None
    flash: bool = False
    holding: bool = False
    scroll_speed: float = 0.0
    calibrated: bool = False
    probs: tuple = (0.0, 0.0)
    fps: float = 0.0
    face: bool = False
    message: str = ""
    detail: str = ""


def _fmt_detail(probs, gesture_values):
    if CONFIG.click_method == "gesture" and gesture_values:
        v = gesture_values
        return (f"mouth {v['mouth']:.2f} (click at {v['mouth_thr']:.2f})   "
                f"eyes {v['eye_a']:.2f} / {v['eye_b']:.2f}")
    return f"head up {probs[0]:.2f}  down {probs[1]:.2f}"


class Brain:
    def __init__(self):
        self.cursor = CursorController()
        self.clicks = ClickController()
        self.scroller = Scroller()
        self.dragger = Dragger()
        self.smoother = GazeSmoother()
        self.mapper = GazeMapper()
        self.mapper.load()
        self.head = HeadMapper()
        self.head.load()
        self.recenter_next = False
        self.pending_button = "left"
        self.mode = Mode.CLICK
        self.paused = True            # start paused; press Start in the panel
        self.calibrating = False
        self.menu_open = False
        self.flash_until = 0.0
        self.last_t = time.monotonic()
        self.requests = []            # things the UI thread must do ("recalibrate")

    @property
    def ready(self):
        """Head mode works with default gains; eye mode needs a calibration."""
        return CONFIG.control_mode == "head" or self.mapper.ready

    @property
    def message(self):
        if CONFIG.control_mode == "eye" and not self.mapper.ready:
            return "Eye mode is not calibrated - press Recalibrate"
        if CONFIG.control_mode == "head" and not self.head.calibrated:
            return "Head mode: using default settings. Recalibrate for best accuracy."
        return ""

    # --- controls called from the UI / hotkeys ----------------------------
    def set_paused(self, paused):
        self.paused = paused
        self.clicks.cancel()
        self.dragger.cancel(self.cursor)
        self.smoother.reset()
        if not paused and CONFIG.control_mode == "head" and not self.head.calibrated:
            self.recenter_next = True  # default gains: wherever you point at start = centre

    def recenter(self):
        self.recenter_next = True

    def toggle_menu(self):
        self.menu_open = not self.menu_open
        self.clicks.cancel()

    # --- per frame --------------------------------------------------------
    def update(self, gate, eye, probs, fps, button=None, gesture_values=None):
        """gate: confident UP/DOWN/None from the head model OR the gesture detector.
        button: which click a DOWN means ("left" / "right"); None = left."""
        now = time.monotonic()
        dt, self.last_t = now - self.last_t, now
        st = Status(calibrated=self.ready, probs=tuple(float(p) for p in probs),
                    fps=fps, face=eye is not None, detail=_fmt_detail(probs, gesture_values))

        if eye is not None and self.recenter_next and not self.calibrating:
            self.head.recenter(eye.head)
            self.smoother.reset()
            self.recenter_next = False

        if self.paused or self.calibrating or not self.ready:
            st.state = "PAUSED"
            self._fill(st, now)
            return st

        # Pointer -> smoothed normalised point (None = hold still)
        gaze = None
        if eye is not None:
            if CONFIG.control_mode == "head":
                gaze = self.smoother(*self.head.predict(eye.head), now)
            elif eye.openness >= CONFIG.blink_ratio:   # eye mode freezes on blinks
                gaze = self.smoother(*self.mapper.predict(eye.features), now)

        if gate == HEAD_DOWN and not self.clicks.armed:
            self.pending_button = button or "left"   # remember which gesture started it
        fire = self.clicks.update(gate, now, HEAD_UP, HEAD_DOWN)

        if eye is None:
            st.state = "NO_FACE"
        elif gate == HEAD_UP:
            st.state = "HOVER"
            if gaze is not None:
                if self.mode == Mode.SCROLL and not self.menu_open:
                    st.scroll_speed = self.scroller.speed(gaze[1])
                    n = self.scroller.step(gaze[1], dt)
                    if n:
                        self.cursor.scroll(n)
                else:
                    self.cursor.move(*gaze)   # only ever moves while head is confidently UP
        elif gate == HEAD_DOWN:
            st.state = "COOLDOWN" if self.clicks.need_up else "ARMING"
        else:
            st.state = "UNCERTAIN"
        if self.clicks.armed:
            st.state = "ARMING"

        st.progress = self.clicks.progress(now)
        if fire:
            nx, ny = self.cursor.position_before(CONFIG.click_lookback_s)
            self._fire(nx, ny)
            self.flash_until = now + 0.18

        self._fill(st, now)
        return st

    def _fill(self, st, now):
        st.flash = now < self.flash_until
        st.cursor = (self.cursor.nx, self.cursor.ny)
        st.mode = self.mode.value
        st.menu_open = self.menu_open
        st.holding = self.dragger.holding
        st.message = self.message
        if self.menu_open:
            st.menu_hover = menu_hit(self.cursor.nx, self.cursor.ny)

    # --- what a confirmed nod does ----------------------------------------
    def _fire(self, nx, ny):
        if self.menu_open:
            i = menu_hit(nx, ny)
            if i is not None:
                self._menu_action(MENU_ITEMS[i][0])
            return
        if inside(nx, ny, CONFIG.menu_tab):
            self.menu_open = True
            return
        if self.mode == Mode.CLICK:
            self.cursor.click(nx, ny, self.pending_button)   # mouth = left, wink = right
        elif self.mode == Mode.RIGHT:
            self.cursor.click(nx, ny, "right")
            self.mode = Mode.CLICK
        elif self.mode == Mode.DOUBLE:
            self.cursor.click(nx, ny, count=2)
            self.mode = Mode.CLICK
        elif self.mode == Mode.DRAG:
            if not self.dragger.toggle(self.cursor, nx, ny):
                self.mode = Mode.CLICK  # dropped -> back to normal
        elif self.mode == Mode.SCROLL:
            self.scroller.reset()
            self.mode = Mode.CLICK

    def _menu_action(self, item):
        c, keep_open = self.cursor, False
        modes = {"left": Mode.CLICK, "right": Mode.RIGHT, "double": Mode.DOUBLE,
                 "drag": Mode.DRAG, "scroll": Mode.SCROLL}
        if item in modes:
            self.dragger.cancel(c)
            self.mode = modes[item]
        elif item == "osk":
            c.hotkey(KEY.cmd, KEY.ctrl, "o")        # Windows on-screen keyboard
        elif item == "voice":
            c.hotkey(KEY.cmd, "h")                  # Windows voice typing
        elif item == "taskview":
            c.hotkey(KEY.cmd, KEY.tab)
        elif item == "desktop":
            c.hotkey(KEY.cmd, "d")
        elif item == "back":
            c.hotkey(KEY.alt, KEY.left)
        elif item == "copy":
            c.hotkey(KEY.ctrl, "c")
        elif item == "paste":
            c.hotkey(KEY.ctrl, "v")
        elif item == "recenter":
            self.recenter()
        elif item == "pause":
            self.requests.append("pause")
        elif item == "recal":
            self.requests.append("recalibrate")
        elif item in ("sens_dn", "sens_up"):
            step = 0.1 if item == "sens_up" else -0.1
            CONFIG.sensitivity = round(min(max(CONFIG.sensitivity + step, 0.5), 2.0), 2)
            self.requests.append("settings_changed")
            keep_open = True
        elif item in ("smooth_dn", "smooth_up"):
            step = 0.1 if item == "smooth_up" else -0.1
            CONFIG.smoothing = round(min(max(CONFIG.smoothing + step, 0.0), 1.0), 2)
            self.requests.append("settings_changed")
            keep_open = True
        self.menu_open = keep_open
