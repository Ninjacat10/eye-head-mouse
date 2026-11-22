"""Eye + Head Mouse - entry point.

Run:  python -m src.main      (or double-click run.bat)

Threads:
  UI thread      Qt windows: overlay, control panel, calibration
  Worker thread  camera -> face mesh + head CNN -> confidence gate -> Brain
"""
import os
import queue
import sys
import time
import traceback

# IMPORTANT: load the ML libraries BEFORE PyQt6. On Windows, importing Qt first
# makes MediaPipe's DLL fail with "DLL initialization routine failed".
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import cv2  # noqa: E402,F401
import mediapipe  # noqa: E402,F401
import tensorflow  # noqa: E402,F401

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

from src.eyemouse.calibration_ui import CalibrationWindow
from src.eyemouse.control_panel import ControlPanel, Hotkeys
from src.eyemouse.overlay import Overlay, set_capture_hidden


class Worker(QThread):
    status = pyqtSignal(object)        # Status, every frame
    eye_sample = pyqtSignal(object, bool)  # (EyeResult or None, head_is_down) for calibration
    request = pyqtSignal(str)          # "recalibrate", "pause", "settings_changed"
    ready = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.commands = queue.Queue()
        self.running = True

    def send(self, *cmd):
        """Thread-safe: UI thread asks the worker to do something."""
        self.commands.put(cmd)

    def run(self):
        try:
            # Heavy imports/models load here so the UI appears instantly
            from src.eyemouse.camera import Camera
            from src.eyemouse.confidence_gate import ConfidenceGate
            from src.eyemouse.eye_tracker import EyeTracker
            from src.eyemouse.head_classifier import HEAD_DOWN, HeadClassifier
            from src.eyemouse.state_manager import Brain

            clf = HeadClassifier()
            tracker = EyeTracker()
            cam = Camera()
            gate = ConfidenceGate(2)
            brain = Brain()
        except Exception as e:
            traceback.print_exc()
            self.error.emit(f"{type(e).__name__}: {e}")
            return

        self.ready.emit()
        fps, last = 0.0, time.monotonic()
        while self.running:
            self._handle_commands(brain)
            frame = cam.read()
            if frame is None:
                time.sleep(0.01)
                continue
            eye = tracker.process(frame)
            probs = clf.predict(frame)
            g = gate.update(probs)

            now = time.monotonic()
            fps = 0.9 * fps + 0.1 / max(now - last, 1e-3)
            last = now

            st = brain.update(g, eye, probs, fps)
            if brain.calibrating:
                self.eye_sample.emit(eye, g == HEAD_DOWN)
            while brain.requests:
                self.request.emit(brain.requests.pop(0))
            self.status.emit(st)

        brain.dragger.cancel(brain.cursor)  # never leave the mouse button held down
        cam.release()
        tracker.close()

    def _handle_commands(self, brain):
        while not self.commands.empty():
            cmd, *args = self.commands.get()
            if cmd == "set_paused":
                brain.set_paused(args[0])
            elif cmd == "menu":
                brain.toggle_menu()
            elif cmd == "calibrating":
                brain.calibrating = args[0]
                brain.smoother.reset()
            elif cmd == "mapper":
                brain.mapper = args[0]
                brain.message = ""
                brain.smoother.reset()

    def stop(self):
        self.running = False
        self.wait(3000)


class App:
    def __init__(self):
        self.qt = QApplication(sys.argv)
        self.overlay = Overlay()
        self.panel = ControlPanel()
        self.worker = Worker()
        self.hotkeys = Hotkeys()
        self.calib = None
        self.paused = True
        self.hide_capture = True

        w, p, h = self.worker, self.panel, self.hotkeys
        w.status.connect(self._on_status)
        w.ready.connect(p.set_ready)
        w.error.connect(p.show_error)
        w.request.connect(self._on_request)
        p.start_stop.connect(self.toggle)
        p.recalibrate.connect(self.start_calibration)
        p.menu.connect(lambda: w.send("menu"))
        p.capture_hidden.connect(self.set_capture_hidden)
        p.quit_app.connect(self.quit)
        h.toggle.connect(self.toggle)
        h.menu.connect(lambda: w.send("menu"))
        h.recal.connect(self.start_calibration)
        h.quit.connect(self.quit)

    def run(self):
        self.overlay.show()
        self.panel.show()
        self.set_capture_hidden(True)
        self.worker.start()
        return self.qt.exec()

    def _on_status(self, st):
        self.overlay.update_status(st)
        self.panel.update_status(st)

    def _on_request(self, req):
        if req == "recalibrate":
            self.start_calibration()
        elif req == "pause":
            self._set_paused(True)
        elif req == "settings_changed":
            self.panel.sync_sliders()

    def toggle(self):
        self._set_paused(not self.paused)

    def _set_paused(self, paused):
        self.paused = paused
        self.worker.send("set_paused", paused)
        self.panel.set_running(not paused)

    def set_capture_hidden(self, hidden):
        self.hide_capture = hidden
        for wdg in (self.overlay, self.panel, self.calib):
            if wdg is not None:
                set_capture_hidden(wdg, hidden)

    def start_calibration(self):
        if self.calib is not None:
            return
        self.worker.send("calibrating", True)
        self.calib = CalibrationWindow()
        self.worker.eye_sample.connect(self.calib.add_sample)
        self.calib.finished.connect(self._calibration_done)
        self.calib.show()
        self.calib.activateWindow()
        set_capture_hidden(self.calib, self.hide_capture)

    def _calibration_done(self, mapper):
        if mapper is not None:
            self.worker.send("mapper", mapper)
        self.worker.send("calibrating", False)
        try:
            self.worker.eye_sample.disconnect(self.calib.add_sample)
        except TypeError:
            pass
        self._closing_calib = self.calib  # keep alive while it shows the result
        self.calib = None

    def quit(self):
        Hotkeys.stop()
        self.worker.stop()
        self.qt.quit()


if __name__ == "__main__":
    sys.exit(App().run())
