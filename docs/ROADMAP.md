# Build roadmap (10 chats)

| Chat | Step | Files |
|---|---|---|
| 1 | Environment + webcam test | camera.py, config.py |
| 2 | Head classifier (your model) | head_classifier.py |
| 3 | Confidence gate (0.95 x 5 frames) | confidence_gate.py |
| 4 | Eye tracker (MediaPipe iris) | eye_tracker.py |
| 5 | Calibration + gaze neural net | gaze_mapper.py |
| 6 | Smoothing + sensitivity | smoothing.py |
| 7 | Cursor + click (0.5 s wait, cooldown) | cursor_controller.py, click_controller.py |
| 8 | Click-drag + scroll modes | scroll_drag.py, state_manager.py |
| 9 | Overlay: edge glow, navigator menu, capture-hidden | overlay.py |
| 10 | Control panel, stop hotkey, main loop | control_panel.py, main.py |
