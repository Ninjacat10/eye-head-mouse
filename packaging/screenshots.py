"""Renders README screenshots of the real UI widgets (no camera needed).

    python packaging/screenshots.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtGui import QColor, QPainter, QLinearGradient  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
from src.eyemouse.control_panel import ControlPanel  # noqa: E402
from src.eyemouse.overlay import Overlay  # noqa: E402
from src.eyemouse.state_manager import Status  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "docs" / "images"
W, H = 1600, 900


def desktop_bg():
    """A neutral fake desktop so the transparent overlay has something behind it."""
    from PyQt6.QtGui import QImage
    img = QImage(W, H, QImage.Format.Format_ARGB32)
    p = QPainter(img)
    g = QLinearGradient(0, 0, W, H)
    g.setColorAt(0, QColor(36, 52, 88))
    g.setColorAt(1, QColor(18, 22, 34))
    p.fillRect(0, 0, W, H, g)
    p.fillRect(220, 160, 1160, 600, QColor(245, 246, 250))
    p.fillRect(220, 160, 1160, 44, QColor(225, 228, 236))
    for i in range(9):
        p.fillRect(270, 250 + i * 52, 700 - (i % 3) * 140, 18, QColor(200, 205, 215))
    p.end()
    return img


def overlay_shot(name, status):
    o = Overlay()
    o.resize(W, H)
    o.status = status
    img = desktop_bg()
    p = QPainter(img)
    o.render(p)
    p.end()
    img.save(str(OUT / name))


overlay_shot("overlay_hover.png", Status(state="HOVER", cursor=(0.6, 0.5)))
overlay_shot("overlay_clicking.png", Status(state="ARMING", progress=0.65))
overlay_shot("overlay_menu.png", Status(state="HOVER", menu_open=True, menu_hover=6, cursor=(0.36, 0.42)))
overlay_shot("overlay_scroll.png", Status(state="HOVER", mode="Scroll", scroll_speed=0.8))

panel = ControlPanel()
panel.set_ready()
panel.set_running(True)
panel.update_status(Status(state="HOVER", fps=30, detail="mouth 0.01 (click at 0.28)   eyes 0.27 / 0.26"))
panel.adjustSize()
panel.grab().save(str(OUT / "control_panel.png"))
print("screenshots written to", OUT)
