"""Small always-on-top window: Start/Stop, Recalibrate, sliders, live status.

Global hotkeys (work even when the cursor is out of control):
  Ctrl+Alt+E  start / stop tracking      Ctrl+Alt+M  open / close menu
  Ctrl+Alt+C  recalibrate                Ctrl+Alt+R  recenter (head mode)
  Ctrl+Alt+Q  quit
"""
import keyboard
from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel,
                             QPushButton, QSlider, QVBoxLayout, QWidget)

from .config import CONFIG, save_settings

POINTER_MODES = [("head", "Head - point with your nose"), ("eye", "Eyes - look where you want")]
CLICK_METHODS = [("gesture", "Open mouth = click, wink = right click"), ("nod", "Head-down nod (your model)")]
from .state_manager import Status

STATE_TEXT = {
    "PAUSED": ("Paused", "#dc3c3c"),
    "NO_FACE": ("No face", "#8c8c8c"),
    "UNCERTAIN": ("Not sure - doing nothing", "#ebaa28"),
    "HOVER": ("Hovering", "#3c8cff"),
    "ARMING": ("Clicking...", "#28c85a"),
    "COOLDOWN": ("Lift head to re-arm", "#288c46"),
}


class Hotkeys(QObject):
    """Bridges the keyboard library thread to Qt signals (thread-safe)."""
    toggle = pyqtSignal()
    menu = pyqtSignal()
    recal = pyqtSignal()
    recenter = pyqtSignal()
    quit = pyqtSignal()

    def __init__(self):
        super().__init__()
        keyboard.add_hotkey("ctrl+alt+e", self.toggle.emit)
        keyboard.add_hotkey("ctrl+alt+m", self.menu.emit)
        keyboard.add_hotkey("ctrl+alt+c", self.recal.emit)
        keyboard.add_hotkey("ctrl+alt+r", self.recenter.emit)
        keyboard.add_hotkey("ctrl+alt+q", self.quit.emit)

    @staticmethod
    def stop():
        keyboard.unhook_all()


class ControlPanel(QWidget):
    start_stop = pyqtSignal()
    recalibrate = pyqtSignal()
    recenter = pyqtSignal()
    menu = pyqtSignal()
    settings_changed = pyqtSignal()
    capture_hidden = pyqtSignal(bool)
    quit_app = pyqtSignal()

    def __init__(self):
        super().__init__(None, Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Eye + Head Mouse")
        self.setFixedWidth(380)

        self.pointer_box = self._combo(POINTER_MODES, CONFIG.control_mode, "control_mode")
        self.click_box = self._combo(CLICK_METHODS, CONFIG.click_method, "click_method")
        form = QFormLayout()
        form.addRow("Cursor:", self.pointer_box)
        form.addRow("Click:", self.click_box)

        self.state_lbl = QLabel("Loading models...")
        self.state_lbl.setStyleSheet("font-size:16px; font-weight:600;")
        self.detail_lbl = QLabel("")
        self.detail_lbl.setStyleSheet("color:#666;")
        self.msg_lbl = QLabel("")
        self.msg_lbl.setWordWrap(True)
        self.msg_lbl.setStyleSheet("color:#b05a00;")

        self.start_btn = QPushButton("Start tracking")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.setStyleSheet("font-size:15px; font-weight:600;")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_stop.emit)

        recal_btn = QPushButton("Recalibrate")
        recal_btn.clicked.connect(self.recalibrate.emit)
        recenter_btn = QPushButton("Recenter")
        recenter_btn.setToolTip("Head mode: point your nose at the screen centre, then press")
        recenter_btn.clicked.connect(self.recenter.emit)
        menu_btn = QPushButton("Menu")
        menu_btn.clicked.connect(self.menu.emit)
        row = QHBoxLayout()
        row.addWidget(recal_btn)
        row.addWidget(recenter_btn)
        row.addWidget(menu_btn)

        self.sens = self._slider(50, 200, int(CONFIG.sensitivity * 100), self._on_sens)
        self.smooth = self._slider(0, 100, int(CONFIG.smoothing * 100), self._on_smooth)
        self.sens_lbl, self.smooth_lbl = QLabel(), QLabel()
        self._on_sens(self.sens.value())
        self._on_smooth(self.smooth.value())

        hide = QCheckBox("Hide overlay from screen sharing")
        hide.setChecked(True)
        hide.toggled.connect(self.capture_hidden.emit)

        keys = QLabel("Ctrl+Alt+E start/stop   Ctrl+Alt+M menu   Ctrl+Alt+R recenter\n"
                      "Ctrl+Alt+C recalibrate   Ctrl+Alt+Q quit")
        keys.setStyleSheet("color:#888; font-size:11px;")
        quit_btn = QPushButton("Quit")
        quit_btn.clicked.connect(self.quit_app.emit)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        for w in (self.state_lbl, self.detail_lbl, self.msg_lbl, self.start_btn):
            lay.addWidget(w)
        lay.addLayout(row)
        for w in (self.sens_lbl, self.sens, self.smooth_lbl, self.smooth, hide, keys, quit_btn):
            lay.addWidget(w)

    def _combo(self, options, current, attr):
        box = QComboBox()
        for key, label in options:
            box.addItem(label, key)
        box.setCurrentIndex(max(0, [k for k, _ in options].index(current)))

        def changed(_i):
            setattr(CONFIG, attr, box.currentData())
            save_settings()
            self.settings_changed.emit()
        box.currentIndexChanged.connect(changed)
        return box

    @staticmethod
    def _slider(lo, hi, val, cb):
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        s.valueChanged.connect(cb)
        return s

    def _on_sens(self, v):
        CONFIG.sensitivity = v / 100
        self.sens_lbl.setText(f"Sensitivity: {CONFIG.sensitivity:.2f}x")

    def _on_smooth(self, v):
        CONFIG.smoothing = v / 100
        self.smooth_lbl.setText(f"Smoothing: {CONFIG.smoothing:.2f}")

    def sync_sliders(self):
        """Menu tiles can change the settings; reflect them here."""
        self.sens.setValue(int(round(CONFIG.sensitivity * 100)))
        self.smooth.setValue(int(round(CONFIG.smoothing * 100)))

    def set_ready(self):
        self.start_btn.setEnabled(True)

    def set_running(self, running):
        self.start_btn.setText("STOP tracking" if running else "Start tracking")

    def update_status(self, s: Status):
        text, colour = STATE_TEXT.get(s.state, (s.state, "#000"))
        self.state_lbl.setText(f"<span style='color:{colour}'>●</span> {text}")
        self.detail_lbl.setText(
            f"Mode: {s.mode}{'  (holding)' if s.holding else ''}   |   {s.fps:.0f} fps\n{s.detail}")
        self.msg_lbl.setText(s.message)

    def show_error(self, text):
        self.state_lbl.setText("Error")
        self.msg_lbl.setText(text)

    def closeEvent(self, e):
        self.quit_app.emit()
        e.accept()
