"""Local llama.cpp inference server manager (architecture-sensitive).

Runs a llama.cpp ``llama-server`` subprocess around a chosen GGUF model and
exposes an OpenAI-compatible API at http://127.0.0.1:<port>/v1.

Why "server" and not "k2 server": the binary choice no longer belongs to one
model family. Every GGUF declares its ``general.architecture`` in the header
("k2-horizon", "llama", "qwen2", ...), and this module picks the llama-server
build that can load it (see ``server_binary`` / ``_runtimes_for``): a
K2-Horizon GGUF is served by the MBZUAI fork build (K2 loader + K2
pre-tokenizer), every other GGUF family by the plain upstream build. Callers
only ever see one OpenAI-compatible endpoint, so nothing else changes when
the model changes.

The server is started automatically alongside Stella (see main.py
``runner()``) and stopped on shutdown. Thread count auto-detects from the
host CPU so it works on any system without manual tuning.

Runtime resolution
------------------
The binary is resolved/provisioned cross-platform by
``core/local_runtime.py``, which also downloads and SHA-256-verifies the
correct prebuilt archive when nothing is installed yet. The active runtime
preference is the ``server_runtime`` setting (legacy name: ``k2_runtime``,
still read for existing installs). That is what lets the public build run a
local model at all.
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

from core import engine_runtime as kr

DEFAULT_PORT = kr.SERVER_PORT
DEFAULT_CTX = kr.SERVER_CTX

# Kept for backwards compatibility: this used to be a module-level constant
# that other modules and tests imported. The real resolution now goes through
# local_runtime.find_server(), which checks many more locations.
MODEL_FILENAME = kr.SERVER_MODEL_FILENAME


def _get_base_dir() -> Path:
    frozen_base = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and frozen_base:
        return Path(frozen_base)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
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


def _load_server_setting(new_key: str, legacy_key: str, default):
    """Read a ``server_*`` setting, falling back to its legacy ``k2_*`` twin.

    Settings files written before the rename still carry the old keys, and
    the existing tests monkeypatch `_load_setting` with a plain 2-arg lambda,
    so the fallback is layered here (nested calls) instead of widening the
    base loader's signature.
    """
    return _load_setting(new_key, _load_setting(legacy_key, default))


def runtime() -> str:
    """The llama.cpp runtime the user selected (upstream or the MBZUAI fork).

    Read live from settings so a switch takes effect on the next start without
    an app restart. Unknown values fall back to the default rather than
    silently disabling local inference.
    """
    chosen = _load_server_setting(kr.SERVER_RUNTIME_KEY, kr.K2_RUNTIME_KEY,
                                  kr.RUNTIME_DEFAULT)
    return chosen if chosen in kr.RUNTIMES else kr.RUNTIME_DEFAULT


def server_binary(model_path: Path | None = None) -> Path | None:
    """Resolved llama-server for the model that will actually be served.

    Architecture-sensitive: a K2-Horizon GGUF wants the MBZUAI fork build
    (K2 loader + pre-tokenizer), every other GGUF family wants plain upstream.
    The first runtime that already has a binary on disk wins; the user's
    `server_runtime` preference only breaks ties inside the preferred list.
    Offline-only here: callers about to start the server use
    `ensure_server_binary()`, which may download.
    """
    from core import local_runtime
    arch = kr.gguf_architecture(model_path) if model_path else ""
    for rt in _runtimes_for(arch):
        found = local_runtime.find_server(rt)
        if found:
            return found
    return None


def _runtimes_for(arch: str) -> list[str]:
    """Runtimes that can load `arch`, best first.

    k2-horizon: fork first (it carries the K2 pre-tokenizer parity build),
    upstream as the fallback (b11612+ also loads K2). Anything else: upstream
    first, fork last - the fork predates a year of GGUF-family fixes.
    """
    if arch == kr.K2_ARCH:
        return [kr.RUNTIME_MBZUAI, kr.RUNTIME_UPSTREAM]
    return [kr.RUNTIME_UPSTREAM, kr.RUNTIME_MBZUAI]


def ensure_server_binary(allow_download: bool = True, progress=None,
                         model_path: Path | None = None) -> Path | None:
    """Resolve (and if allowed, download) the server for the model's arch."""
    from core import local_runtime
    arch = kr.gguf_architecture(model_path) if model_path else ""
    runtimes = _runtimes_for(arch)
    # Try each runtime in order. Downloads only make sense for upstream (the
    # fork publishes no archives), so the fork attempt is offline-only.
    for rt in runtimes:
        got = local_runtime.ensure_server(
            rt, allow_download=(allow_download and rt == kr.RUNTIME_UPSTREAM),
            progress=progress,
        )
        if got:
            return got
    return None

def port() -> int:
    try:
        return int(_load_server_setting("server_port", "k2_port",
                                       DEFAULT_PORT))
    except Exception:
        return DEFAULT_PORT


def threads() -> int:
    try:
        t = int(_load_server_setting("server_threads", "k2_threads", 0))
        if t > 0:
            return t
    except Exception:
        pass
    return max(1, (os.cpu_count() or 2) // 2)


def ctx_size() -> int:
    try:
        return int(_load_server_setting("server_ctx", "k2_ctx", DEFAULT_CTX))
    except Exception:
        return DEFAULT_CTX


def autostart_enabled() -> bool:
    return bool(_load_server_setting("server_autostart", "k2_autostart",
                                     True))


def _model_search_dirs() -> list[Path]:
    """Directories that may hold the K2 weights, best first.

    The user data dir comes first: on an installed build the repo's `models/`
    folder is not writable, so a user who downloaded the weights themselves
    keeps them there across updates.
    """
    dirs: list[Path] = []
    try:
        from core.user_paths import get_user_data_dir
        dirs.append(get_user_data_dir() / "models")
    except Exception:
        pass
    dirs.append(BASE_DIR / "models")
    dirs.append(Path(os.path.expanduser("~")) / "models")
    # Bundled K2 payload: the personal build ships the weights in `k2/` next to
    # the exe (and under `_internal/k2/` when PyInstaller uses onedir). A user
    # who just installed that build has the model nowhere else, so these two
    # must be searched or the app reports "model not found" against a build
    # that literally contains it.
    dirs.append(BASE_DIR / "k2")
    dirs.append(BASE_DIR / "_internal" / "k2")
    seen: set[str] = set()
    out: list[Path] = []
    for d in dirs:
        key = str(d).lower()
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def resolve_model_path() -> Path | None:
    """Locate the K2 GGUF, accepting every documented filename spelling.

    The checkpoint ships as both ``K2-Horizon-0.9B-Q4_K_M.gguf`` and
    ``K2-Horizon-1B-Q4_K_M.gguf`` (same bytes, different name upstream). Matching
    only one spelling meant a user who already had the other got told their
    model was missing.
    """
    for directory in _model_search_dirs():
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        for name in kr.SERVER_MODEL_ALIASES:
            candidate = directory / name
            if candidate.exists():
                return candidate
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


def start(wait: bool = True, allow_download: bool = True,
          model_path: Path | None = None) -> bool:
    """Start the llama-server subprocess. Returns True when healthy.

    `model_path` lets the caller serve a *different* GGUF than K2 — that is the
    "download, load and run any model of my choice" path. Left as None it
    resolves the pinned K2 weights, preserving the previous behaviour.

    `allow_download` controls whether a missing runtime binary may be fetched.
    Callers that must not touch the network (first-run on a metered link, the
    offline build) pass False and get a clean failure instead of a hang.
    """
    global _proc
    if is_running():
        return True
    model = model_path or resolve_model_path()
    if model is None:
        print(f"[server] Model file not found: {MODEL_FILENAME}")
        return False

    server = ensure_server_binary(allow_download=allow_download,
                                  model_path=model)
    if server is None:
        rt = runtime()
        print(f"[server] No llama-server available for runtime '{rt}'.")
        print("[server] For llama.cpp it downloads automatically when online; "
              "for the MBZUAI fork, build it from source and point "
              "STELLA_SERVER at it (legacy name: STELLA_K2_SERVER).")
        return False

    from core import local_runtime
    args = local_runtime.build_command(
        server, model, port=port(), threads=threads(), ctx=ctx_size(),
    )
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        with _lock:
            _proc = subprocess.Popen(args, creationflags=flags)
        print(f"[server] llama-server starting (port={port()}, "
              f"threads={threads()}, ctx={ctx_size()})...")
    except Exception as exc:
        print(f"[server] Failed to launch llama-server: {exc}")
        return False
    if wait:
        ok = _wait_ready()
        print("[server] Server ready."
              if ok else "[server] Server did not become ready in time.")
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
        print("[server] Server stopped.")




