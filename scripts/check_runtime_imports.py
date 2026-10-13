"""Print which of Stella's runtime imports are missing from an interpreter.

Usage: python scripts/check_runtime_imports.py [python-exe]
Exit 0 when everything imports; exit 1 + the missing list otherwise.
"""
import importlib
import subprocess
import sys

MODULES = [
    "pyperclip", "sounddevice", "google.genai", "PyQt6",
    "PyQt6.QtWebEngineCore", "mediapipe", "cv2", "instagrapi",
    "pyautogui", "keyboard", "docx", "pptx", "multipart", "passlib",
    "bcrypt", "aiohttp", "websockets", "uvicorn", "fastapi", "plyer",
    "pydantic", "requests", "bs4", "numpy", "matplotlib", "edge_tts",
    "qrcode", "psutil", "speedtest",
]

MODE = sys.argv[1] if len(sys.argv) > 1 else "inprocess"


def check_inprocess() -> list[str]:
    missing: list[str] = []
    for name in MODULES:
        try:
            mod = importlib.import_module(name)
            # Touch a real attribute so namespace-package shadowing and
            # half-written installs surface here instead of inside PyInstaller.
            getattr(mod, "__name__", name)
        except Exception as exc:
            missing.append(f"{name} ({type(exc).__name__}: {exc})".strip())
    return missing


def check_subprocess(py: str) -> list[str]:
    missing: list[str] = []
    for name in MODULES:
        proc = subprocess.run(
            [py, "-c", f"import {name}"],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            missing.append(name)
    return missing


if __name__ == "__main__":
    if MODE == "inprocess":
        missing_mods = check_inprocess()
    else:
        missing_mods = check_subprocess(MODE)
    if missing_mods:
        print("missing: " + ", ".join(missing_mods))
        raise SystemExit(1)
    print(f"all {len(MODULES)} runtime imports OK")
