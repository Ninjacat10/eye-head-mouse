"""Runs your Teachable Machine head model (head up / head down) in Python.

Teachable Machine exported a TensorFlow.js model: model.json (the layer
layout) + weights.bin (the trained numbers). Instead of a converter tool we
rebuild the same network in Keras and copy every trained weight in by name:

    MobileNetV2 (alpha 0.35, the CNN feature extractor)
      -> GlobalAveragePooling2D
      -> Dense(100, relu)
      -> Dense(2, softmax, no bias)   -> [p_head_up, p_head_down]
"""
import json
import os
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")  # hide TF info spam

import cv2
import numpy as np
import tensorflow as tf

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "head_model_tfjs"
IMAGE_SIZE = 224

# Index of each class in the model's output (from metadata.json labels)
HEAD_UP = 0
HEAD_DOWN = 1


def _read_tfjs_weights(model_dir: Path) -> dict:
    """Return {"layer/variable": numpy array} from model.json + weights.bin."""
    manifest = json.loads((model_dir / "model.json").read_text())["weightsManifest"]
    weights = {}
    for group in manifest:
        blob = b"".join((model_dir / p).read_bytes() for p in group["paths"])
        offset = 0
        for spec in group["weights"]:
            count = int(np.prod(spec["shape"])) if spec["shape"] else 1
            arr = np.frombuffer(blob, dtype=np.float32, count=count, offset=offset)
            weights[spec["name"]] = arr.reshape(spec["shape"])
            offset += count * 4  # float32 = 4 bytes
    return weights


def _build_model(weights: dict) -> tf.keras.Model:
    base = tf.keras.applications.MobileNetV2(
        input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3),
        alpha=0.35,
        include_top=False,
        weights=None,  # we load YOUR weights below, not ImageNet
    )
    features = tf.keras.layers.GlobalAveragePooling2D()(base.output)
    hidden = tf.keras.layers.Dense(100, activation="relu", name="dense_Dense7")(features)
    probs = tf.keras.layers.Dense(2, activation="softmax", use_bias=False, name="dense_Dense8")(hidden)
    model = tf.keras.Model(base.input, probs)

    used = set()
    for layer in model.layers:
        if not layer.weights:
            continue
        values = []
        for var in layer.weights:
            short = var.name.split("/")[-1].split(":")[0]  # e.g. "kernel"
            key = f"{layer.name}/{short}"
            if key not in weights and short == "kernel":
                key = f"{layer.name}/depthwise_kernel"  # Keras 3 vs tfjs naming
            if key not in weights:
                raise KeyError(f"Model weight {key} missing from weights.bin")
            values.append(weights[key])
            used.add(key)
        layer.set_weights(values)

    unused = set(weights) - used
    if unused:
        raise ValueError(f"Unused weights (model mismatch): {sorted(unused)[:5]}")
    return model


class HeadClassifier:
    def __init__(self, model_dir: Path = MODEL_DIR):
        self.model = _build_model(_read_tfjs_weights(model_dir))
        self.labels = json.loads((model_dir / "metadata.json").read_text())["labels"]
        # tf.function compiles the forward pass once -> much faster per frame
        self._predict = tf.function(lambda x: self.model(x, training=False))
        self._predict(tf.zeros((1, IMAGE_SIZE, IMAGE_SIZE, 3)))  # warm-up

    @staticmethod
    def preprocess(frame_bgr: np.ndarray) -> np.ndarray:
        """Match Teachable Machine: centre square crop, 224x224, RGB, scale to [-1, 1]."""
        h, w = frame_bgr.shape[:2]
        side = min(h, w)
        top, left = (h - side) // 2, (w - side) // 2
        square = frame_bgr[top:top + side, left:left + side]
        small = cv2.resize(square, (IMAGE_SIZE, IMAGE_SIZE), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB).astype(np.float32)
        return (rgb / 127.0 - 1.0)[None, ...]  # TM's tfjs code divides by 127

    def predict(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Return probabilities [p_head_up, p_head_down] for one mirrored frame."""
        return self._predict(tf.constant(self.preprocess(frame_bgr))).numpy()[0]


if __name__ == "__main__":
    # Self-test: python -m src.eyemouse.head_classifier  (press Q to quit)
    from .camera import Camera

    clf = HeadClassifier()
    cam = Camera()
    while True:
        frame = cam.read()
        if frame is None:
            break
        p = clf.predict(frame)
        text = f"up {p[HEAD_UP]:.2f}  down {p[HEAD_DOWN]:.2f}"
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("Head classifier - press Q", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cam.release()
    cv2.destroyAllWindows()
