"""Finds your face and irises with MediaPipe Face Mesh (pretrained model).

Outputs a small feature vector describing WHERE you are looking:
  [iris_x, iris_y, head_x, head_y]
iris_* = iris position inside the eye socket (eye rotation)
head_* = nose position relative to the face outline (head rotation)
The gaze mapper (calibration) learns how these map to screen positions.
"""
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np

# Landmark indices in the 478-point face mesh
R_EYE = dict(c1=33, c2=133, top=159, bottom=145, iris=468)
L_EYE = dict(c1=362, c2=263, top=386, bottom=374, iris=473)
NOSE_TIP = 1
FACE_LEFT, FACE_RIGHT = 234, 454
FOREHEAD, CHIN = 10, 152


@dataclass
class EyeResult:
    features: np.ndarray      # shape (4,)
    openness: float           # eyelid gap / eye width (blink if small)
    landmarks: np.ndarray     # (478, 2) pixel coords, for drawing/debug


def _eye_features(pts, eye):
    c1, c2 = pts[eye["c1"]], pts[eye["c2"]]
    axis = c2 - c1
    width = np.linalg.norm(axis) + 1e-6
    unit = axis / width
    normal = np.array([-unit[1], unit[0]])
    mid = (c1 + c2) / 2
    iris = pts[eye["iris"]]
    # Project the iris onto the eye's own axes so head tilt does not fake eye movement
    ex = np.dot(iris - c1, unit) / width          # 0 = corner1 .. 1 = corner2
    ey = np.dot(iris - mid, normal) / width       # up/down within the socket
    openness = np.linalg.norm(pts[eye["top"]] - pts[eye["bottom"]]) / width
    return ex, ey, openness


class EyeTracker:
    def __init__(self):
        self.mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,          # adds the 10 iris landmarks
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        )

    def process(self, frame_bgr):
        """Return an EyeResult, or None if no face is visible."""
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self.mesh.process(rgb)
        if not result.multi_face_landmarks:
            return None
        lm = result.multi_face_landmarks[0].landmark
        pts = np.array([(p.x * w, p.y * h) for p in lm], dtype=np.float64)

        rx, ry, ro = _eye_features(pts, R_EYE)
        lx, ly, lo = _eye_features(pts, L_EYE)

        face_w = np.linalg.norm(pts[FACE_RIGHT] - pts[FACE_LEFT]) + 1e-6
        face_h = np.linalg.norm(pts[CHIN] - pts[FOREHEAD]) + 1e-6
        centre = (pts[FACE_LEFT] + pts[FACE_RIGHT]) / 2
        mid_y = (pts[FOREHEAD][1] + pts[CHIN][1]) / 2
        hx = (pts[NOSE_TIP][0] - centre[0]) / face_w
        hy = (pts[NOSE_TIP][1] - mid_y) / face_h

        feats = np.array([(rx + lx) / 2, (ry + ly) / 2, hx, hy])
        return EyeResult(features=feats, openness=(ro + lo) / 2, landmarks=pts)

    def close(self):
        self.mesh.close()
