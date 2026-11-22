"""Full-screen transparent overlay: edge glow, Menu tab, navigator menu.

* Click-through: the mouse passes straight through it to your apps.
* Hidden from screen capture: SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)
  means Zoom/Teams/OBS/screenshots do not see it, but you do (Windows 10 2004+).
"""
import ctypes

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget

from .config import CONFIG
from .state_manager import MENU_ITEMS, Status, menu_rect, inside

WDA_NONE = 0x0
WDA_EXCLUDEFROMCAPTURE = 0x11


def set_capture_hidden(widget: QWidget, hidden: bool) -> bool:
    """Hide/show a window from screen sharing and screenshots. Returns success."""
    hwnd = int(widget.winId())
    ok = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE if hidden else WDA_NONE)
    return bool(ok)


STATE_COLOURS = {
    "PAUSED": QColor(220, 60, 60),
    "NO_FACE": QColor(140, 140, 140),
    "UNCERTAIN": QColor(235, 170, 40),
    "HOVER": QColor(60, 140, 255),
    "ARMING": QColor(40, 200, 90),
    "COOLDOWN": QColor(40, 140, 70),
}
SCROLL_COLOUR = QColor(150, 90, 230)
DRAG_COLOUR = QColor(255, 130, 30)


class Overlay(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool
                         | Qt.WindowType.WindowTransparentForInput
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.status = Status()

    def update_status(self, status: Status):
        self.status = status
        self.update()  # schedule a repaint

    # --- drawing ----------------------------------------------------------
    def paintEvent(self, _):
        s = self.status
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        if s.menu_open:
            self._draw_menu(p, W, H, s)

        colour = STATE_COLOURS.get(s.state, STATE_COLOURS["UNCERTAIN"])
        if s.holding:
            colour = DRAG_COLOUR
        elif s.mode == "Scroll" and s.state == "HOVER":
            colour = SCROLL_COLOUR

        thick = 3 if s.state == "PAUSED" else 6
        self._edge(p, W, H, colour, thick, alpha=200)
        self._edge(p, W, H, colour, thick * 3, alpha=45)        # soft outer glow

        if s.state == "ARMING" and s.progress > 0:
            self._progress_edge(p, W, H, s.progress)
        if s.flash:
            self._edge(p, W, H, QColor(255, 255, 255), 14, alpha=230)

        if s.mode == "Scroll" and not s.menu_open and s.state != "PAUSED":
            self._draw_scroll_bands(p, W, H, s.scroll_speed)

        if s.state != "PAUSED":
            self._draw_menu_tab(p, W, H, s)
        p.end()

    def _edge(self, p, W, H, colour, width, alpha):
        c = QColor(colour)
        c.setAlpha(alpha)
        pen = QPen(c, width)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        half = width / 2
        p.drawRect(QRectF(half, half, W - width, H - width))

    def _progress_edge(self, p, W, H, progress):
        """Bright green line that fills clockwise around the screen over 0.5 s."""
        pen = QPen(QColor(120, 255, 150, 255), 10)
        p.setPen(pen)
        edges = [((0, 5), (W, 5)), ((W - 5, 0), (W - 5, H)), ((W, H - 5), (0, H - 5)), ((5, H), (5, 0))]
        lengths = [W, H, W, H]
        remaining = progress * sum(lengths)
        for ((x1, y1), (x2, y2)), L in zip(edges, lengths):
            if remaining <= 0:
                break
            f = min(remaining / L, 1.0)
            p.drawLine(int(x1), int(y1), int(x1 + (x2 - x1) * f), int(y1 + (y2 - y1) * f))
            remaining -= L

    def _draw_menu_tab(self, p, W, H, s):
        x, y, w, h = CONFIG.menu_tab
        hover = inside(*s.cursor, CONFIG.menu_tab)
        r = QRectF(x * W, y * H, w * W, h * H)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 220) if hover else QColor(20, 20, 30, 170))
        p.drawRoundedRect(r.adjusted(0, -12, 0, 0), 12, 12)
        p.setPen(QColor(20, 20, 30) if hover else QColor(255, 255, 255))
        p.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, f"Menu  |  {s.mode}")

    def _draw_scroll_bands(self, p, W, H, speed):
        band = CONFIG.scroll_band
        for top in (True, False):
            active = (speed > 0 and top) or (speed < 0 and not top)
            c = QColor(SCROLL_COLOUR)
            c.setAlpha(int(30 + 70 * abs(speed)) if active else 18)
            rect = QRectF(0, 0 if top else H * (1 - band), W, H * band)
            p.fillRect(rect, c)
            p.setPen(QColor(255, 255, 255, 160))
            p.setFont(QFont("Segoe UI", 16))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Scroll up" if top else "Scroll down")

    def _draw_menu(self, p, W, H, s):
        p.fillRect(0, 0, W, H, QColor(0, 0, 0, 150))
        p.setFont(QFont("Segoe UI", 18, QFont.Weight.DemiBold))
        for i, (_, label) in enumerate(MENU_ITEMS):
            x, y, w, h = menu_rect(i)
            r = QRectF(x * W, y * H, w * W, h * H)
            hovered = s.menu_hover == i
            p.setPen(QPen(QColor(120, 255, 150) if hovered else QColor(255, 255, 255, 90), 3 if hovered else 1))
            p.setBrush(QColor(60, 140, 255, 200) if hovered else QColor(30, 30, 40, 210))
            p.drawRoundedRect(r, 16, 16)
            p.setPen(QColor(255, 255, 255))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, label)
        # gaze dot so you can see what the nod will select
        cx, cy = s.cursor
        p.setPen(QPen(QColor(120, 255, 150), 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx * W - 14, cy * H - 14, 28, 28))
