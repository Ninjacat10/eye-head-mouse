import cv2
from .config import CONFIG

class Camera:
    def __init__(self, index=CONFIG.camera_index):
        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG.frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, CONFIG.target_fps)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera {index}")

    def read(self):
        ok, frame = self.cap.read()
        if not ok:
            return None
        return cv2.flip(frame, 1)

    def release(self):
        self.cap.release()

if __name__ == "__main__":
    cam = Camera()
    while True:
        frame = cam.read()
        if frame is None:
            break
        cv2.imshow("Camera test - press Q to quit", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cam.release()
    cv2.destroyAllWindows()