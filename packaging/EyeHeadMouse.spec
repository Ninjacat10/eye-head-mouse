# PyInstaller build:  pyinstaller packaging/EyeHeadMouse.spec --noconfirm
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT)],
    datas=[
        (str(ROOT / "models" / "head_model.onnx"), "models"),
        (str(ROOT / "assets" / "icon.png"), "assets"),
        *collect_data_files("mediapipe", includes=["**/*.tflite", "**/*.binarypb", "**/*.txt"]),
    ],
    binaries=collect_dynamic_libs("onnxruntime"),
    hiddenimports=["win32gui", "win32con", "pynput.keyboard._win32", "pynput.mouse._win32"],
    excludes=["tensorflow", "keras", "tensorboard", "tf_keras", "jax", "torch",
              "matplotlib", "tf2onnx", "IPython", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="EyeHeadMouse",
    icon=str(ROOT / "assets" / "icon.ico"),
    console=False,          # no black terminal window
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="EyeHeadMouse", upx=False)
