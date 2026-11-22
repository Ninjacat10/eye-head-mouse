"""Draws the app icon (assets/icon.ico + icon.png) with Qt - no image editor needed."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QApplication

OUT = Path(__file__).resolve().parents[1] / "assets"
app = QApplication(sys.argv)
S = 256
img = QImage(S, S, QImage.Format.Format_ARGB32)
img.fill(Qt.GlobalColor.transparent)
p = QPainter(img)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
p.setPen(Qt.PenStyle.NoPen)
p.setBrush(QColor(24, 28, 40))
p.drawRoundedRect(QRectF(8, 8, S - 16, S - 16), 56, 56)
eye = QPainterPath()                       # almond eye shape
eye.moveTo(40, 128)
eye.quadTo(128, 40, 216, 128)
eye.quadTo(128, 216, 40, 128)
p.setBrush(QColor(60, 140, 255))
p.drawPath(eye)
p.setBrush(QColor(24, 28, 40))
p.drawEllipse(QPointF(128, 128), 42, 42)
p.setBrush(QColor(120, 255, 150))
p.drawEllipse(QPointF(128, 128), 22, 22)
p.setPen(QPen(QColor(255, 255, 255), 10, cap=Qt.PenCapStyle.RoundCap))  # cursor tick
p.drawLine(QPointF(176, 176), QPointF(214, 214))
p.end()
img.save(str(OUT / "icon.png"))
img.scaled(64, 64, transformMode=Qt.TransformationMode.SmoothTransformation).save(str(OUT / "icon.ico"))
print("icon written")
