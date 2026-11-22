# Eye + Head Mouse

Hands-free mouse for Windows. Two ways to point, two ways to click (pick in the control panel):

| Cursor | Click |
|---|---|
| **Head** (default): point your nose at the screen | **Gestures** (default): open mouth = left click, wink = right click |
| **Eyes**: look where you want | **Nod**: your Teachable Machine head-down model |

Head mode is far steadier than eye mode and reaches the corners easily. Gestures do not move
your head, so the cursor stays put while you click.

## Run it

Double-click `run.bat`, or in a VS Code terminal:

```powershell
.\.venv\Scripts\python.exe -m src.main
```

First time:
1. Wait for the control panel to say **Paused** (models take ~5 s to load).
2. Head mode works straight away (wherever you point when you press Start = centre).
   For best accuracy click **Recalibrate** and point your nose at the 9 dots with a relaxed face
   (this also learns your neutral eyes/mouth for the gestures). Press **Recenter** / `Ctrl+Alt+R`
   any time the cursor drifts.
3. Click **Start tracking** (or press `Ctrl+Alt+E`).

## How to use

| Do this | Result |
|---|---|
| Point your nose (head mode) or look (eye mode) | Cursor follows (blue edge glow) |
| Open mouth (or nod, in nod mode) and hold 0.5 s | Left click (green line fills around the screen, white flash) |
| Wink one eye and hold 0.5 s | Right click (gesture mode). Normal blinks are ignored |
| Relax face / lift head | Re-arms for the next click |
| Not sure (< 95 % / half-open mouth, for 5 frames) | Nothing happens, cursor frozen (amber glow) |
| Point at the **Menu** tab (top centre) + click gesture | Opens the navigator menu |

**Navigator menu:** Left / Right / Double click, Drag, Scroll, on-screen Keyboard, Voice typing,
Task view, Show desktop, Back, Copy, Paste, Recenter, Pause, Recalibrate, Sensitivity +/-, Smoothing +/-.

- **Drag:** click gesture once to grab, move the cursor, click gesture again to drop (orange glow while holding).
- **Scroll:** cursor stays put; point at the top/bottom of the screen to scroll (purple bands). Click gesture to exit.

**Hotkeys:** `Ctrl+Alt+E` start/stop, `Ctrl+Alt+M` menu, `Ctrl+Alt+C` recalibrate, `Ctrl+Alt+R` recenter, `Ctrl+Alt+Q` quit.

**Screen sharing:** the overlay, panel and calibration screen are hidden from Zoom/Teams/OBS/screenshots
(`SetWindowDisplayAffinity`, Windows 10 2004+). Untick the box in the panel to show them.
Note: the real cursor moving is still visible to viewers.

## How it works

```
webcam -> MediaPipe Face Mesh (iris + face landmarks) -> eye features -> gaze mapper -> One Euro smoothing -> cursor
       -> your Teachable Machine CNN (MobileNetV2) -> confidence gate (>=0.95 x 5 frames) -> click controller
                                     both -> state manager (Brain) -> overlay + control panel
```

| File | Job |
|---|---|
| `src/eyemouse/config.py` | All tunable numbers (thresholds, delays, sensitivity, smoothing) |
| `src/eyemouse/camera.py` | Webcam capture (mirrored) |
| `src/eyemouse/head_classifier.py` | Rebuilds your TF.js model in Keras and loads its weights |
| `src/eyemouse/confidence_gate.py` | "Only act when sure" rule |
| `src/eyemouse/head_pointer.py` | Head mode: nose direction -> screen position, recenter |
| `src/eyemouse/gestures.py` | Open-mouth / wink detection with the same "only when sure" rule |
| `src/eyemouse/eye_tracker.py` | Iris-in-socket + head-pose features from MediaPipe |
| `src/eyemouse/gaze_mapper.py` | Calibration regression: features -> screen position |
| `src/eyemouse/smoothing.py` | One Euro filter + sensitivity |
| `src/eyemouse/click_controller.py` | 0.5 s countdown, grace period, cooldown, re-arm |
| `src/eyemouse/scroll_drag.py` | Modes, scroll speed, drag hold/drop |
| `src/eyemouse/state_manager.py` | The Brain: states, modes, navigator menu actions |
| `src/eyemouse/cursor_controller.py` | Real mouse/keyboard output (pynput) |
| `src/eyemouse/overlay.py` | Edge glow, Menu tab, menu tiles, capture hiding |
| `src/eyemouse/calibration_ui.py` | 9-dot calibration screen |
| `src/eyemouse/control_panel.py` | Start/Stop, sliders, status, global hotkeys |
| `src/main.py` | Threads + wiring |

The cursor only moves while the model is confidently "head up", so it freezes as soon as you start to
nod, and the click lands where you were looking just before (`click_lookback_s`).

## Tuning

Edit `src/eyemouse/config.py`: `confidence_threshold`, `frames_required`, `click_delay_s`,
`cooldown_s`, `scroll_speed`, `blink_ratio`, `mouth_open_delta`, `eye_closed_frac`. Sensitivity and smoothing are live sliders.
