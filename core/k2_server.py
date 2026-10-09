"""K2 Horizon local inference server manager.

Runs the bundled llama.cpp ``llama-server`` subprocess with the in-app
``models/K2-Horizon-0.9B-Q4_K_M.gguf`` model and exposes an
OpenAI-compatible API at http://127.0.0.1:<port>/v1.

The server is started automatically alongside Brahma Evo (see main.py
``runner()``) and stopped on shutdown. Thread count auto-detects from the
host CPU so it works on any system without manual tuning.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

DEFAULT_PORT = 11435
DEFAULT_CTX = 2048
MODEL_FILENAME = "K2-Horizon-0.9B-Q4_K_M.gguf"


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
SERVER_EXE = BASE_DIR / ".venv" / "llama.cpp" / "llama-server.exe"
MODEL_PATH = BASE_DIR / "models" / MODEL_FILENAME

# Fallback: model may live next to the project (user's ~/models folder)
_FALLBACK_MODEL = Path(os.path.expanduser("~")) / "models" / MODEL_FILENAME

_proc: subprocess.Popen | None = None
_lock = threading.Lock()


def _settings_path() -> Path:
    try:
        from core.user_paths import get_user_data_dir
        return get_user_data_dir() / "config" / "app_settings.json"
    except Exception:
        return BASE_DIR / "config" / "app_settings.json"


def _load_setting(key: str, default):
    try:
        with open(_settings_path(), "r", encoding="utf-8-sig") as f:
            return json.load(f).get(key, default)
    except Exception:
        return default


def port() -> int:
    try:
        return int(_load_setting("k2_port", DEFAULT_PORT))
    except Exception:
        return DEFAULT_PORT


def threads() -> int:
    try:
        t = int(_load_setting("k2_threads", 0))
        if t > 0:
            return t
    except Exception:
        pass
    return max(1, (os.cpu_count() or 2) // 2)


def ctx_size() -> int:
    try:
        return int(_load_setting("k2_ctx", DEFAULT_CTX))
    except Exception:
        return DEFAULT_CTX


def autostart_enabled() -> bool:
    return bool(_load_setting("k2_autostart", True))


def resolve_model_path() -> Path | None:
    if MODEL_PATH.exists():
        return MODEL_PATH
    if _FALLBACK_MODEL.exists():
        return _FALLBACK_MODEL
    return None


def base_url() -> str:
    return f"http://127.0.0.1:{port()}"


def is_running() -> bool:
    global _proc
    with _lock:
        if _proc is not None and _proc.poll() is None:
            return True
        _proc = None
    # Server may have been started externally; probe the port.
    try:
        req = urllib.request.Request(f"{base_url()}/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def _model_loaded() -> bool:
    """True when the server reports a loaded model (not just HTTP up)."""
    try:
        req = urllib.request.Request(f"{base_url()}/v1/models", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return bool(data.get("data"))
    except Exception:
        return False


def _wait_ready(timeout: float = 180.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_running() and _model_loaded():
            return True
        time.sleep(1.0)
    return is_running() and _model_loaded()


def start(wait: bool = True) -> bool:
    """Start the K2 llama-server subprocess. Returns True when healthy."""
    global _proc
    if is_running():
        return True
    model = resolve_model_path()
    if model is None:
        print(f"[K2] Model file not found: {MODEL_FILENAME}")
        return False
    if not SERVER_EXE.exists():
        print(f"[K2] llama-server binary not found: {SERVER_EXE}")
        return False

    args = [
        str(SERVER_EXE),
        "-m", str(model),
        "--port", str(port()),
        "-t", str(threads()),
        "-c", str(ctx_size()),
    ]
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        with _lock:
            _proc = subprocess.Popen(args, creationflags=flags)
        print(f"[K2] llama-server starting (port={port()}, threads={threads()}, ctx={ctx_size()})...")
    except Exception as exc:
        print(f"[K2] Failed to launch llama-server: {exc}")
        return False
    if wait:
        ok = _wait_ready()
        print("[K2] Server ready." if ok else "[K2] Server did not become ready in time.")
        return ok
    return True


def ensure_running() -> bool:
    """Start the server if needed. Called before every K2 inference."""
    if is_running():
        return True
    return start(wait=True)


def start_background() -> None:
    """Fire-and-forget startup for app boot (non-blocking)."""
    threading.Thread(target=start, kwargs={"wait": True}, daemon=True).start()


def stop() -> None:
    global _proc
    with _lock:
        proc, _proc = _proc, None
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        print("[K2] Server stopped.")
