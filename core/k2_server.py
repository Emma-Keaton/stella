# -*- coding: utf-8 -*-
"""Deprecated module path for the local llama.cpp server manager.

The canonical home is now ``core.server`` (the server stopped being
K2-specific when selection went architecture-sensitive — it now resolves a
llama-server per model family). All public names are re-exported here so old
``from core import k2_server`` imports keep working; new code should import
``core.server`` directly.
"""
from __future__ import annotations

from core.server import (
    BASE_DIR,
    DEFAULT_CTX,
    DEFAULT_PORT,
    MODEL_FILENAME,
    MODEL_PATH,
    _FALLBACK_MODEL,
    _load_server_setting,
    _load_setting,
    _lock,
    _model_loaded,
    _model_search_dirs,
    _proc,
    _runtimes_for,
    _settings_path,
    _wait_ready,
    autostart_enabled,
    base_url,
    ctx_size,
    ensure_running,
    ensure_server_binary,
    is_running,
    port,
    resolve_model_path,
    runtime,
    server_binary,
    start,
    start_background,
    stop,
    threads,
)

__all__ = [
    "BASE_DIR", "DEFAULT_CTX", "DEFAULT_PORT", "MODEL_FILENAME",
    "MODEL_PATH", "_FALLBACK_MODEL", "_load_server_setting", "_load_setting",
    "_lock", "_model_loaded", "_model_search_dirs", "_proc", "_runtimes_for",
    "_settings_path", "_wait_ready", "autostart_enabled", "base_url",
    "ctx_size", "ensure_running", "ensure_server_binary", "is_running",
    "port", "resolve_model_path", "runtime", "server_binary", "start",
    "start_background", "stop", "threads",
]
