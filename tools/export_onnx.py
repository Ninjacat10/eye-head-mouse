"""One-time export: Teachable Machine TF.js model -> models/head_model.onnx

The packaged app runs the ONNX file with onnxruntime (~15 MB) instead of
TensorFlow (~1 GB). Re-run this after retraining in Teachable Machine:

    pip install tensorflow==2.18.0 tf2onnx==1.16.1
    python -m tools.export_onnx
    pip install "protobuf>=4.25.3,<5"   # tf2onnx downgrades it; mediapipe needs 4.x
"""
from pathlib import Path

import numpy as np
import tensorflow as tf
import tf2onnx

from src.eyemouse.head_classifier import MODEL_DIR, _build_model, _read_tfjs_weights

OUT = Path(__file__).resolve().parents[1] / "models" / "head_model.onnx"

model = _build_model(_read_tfjs_weights(MODEL_DIR))
spec = (tf.TensorSpec((None, 224, 224, 3), tf.float32, name="image"),)
tf2onnx.convert.from_keras(model, input_signature=spec, opset=13, output_path=str(OUT))

# Sanity check: ONNX output must match Keras
import onnxruntime as ort  # noqa: E402
x = np.random.uniform(-1, 1, (2, 224, 224, 3)).astype(np.float32)
sess = ort.InferenceSession(str(OUT), providers=["CPUExecutionProvider"])
diff = np.abs(sess.run(None, {sess.get_inputs()[0].name: x})[0] - model(x).numpy()).max()
print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB), max diff vs Keras = {diff:.2e}")
