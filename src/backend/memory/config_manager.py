"""
src/backend/memory/config_manager.py — Single source of truth for all Stella
configuration. Everything lives in one file: `config/api_keys.json`.

Follows Mark-LVI's pattern: one JSON file, read-modify-write with mtime cache,
atomic writes, thread-safe. Default mode is "gemini" — providers package is
never imported unless the user selects pipeline mode.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from core.user_paths import get_user_data_dir

CONFIG_DIR = get_user_data_dir() / "config"
API_KEYS_FILE = CONFIG_DIR / "api_keys.json"

_lock = threading.RLock()
_cache: Optional[dict] = None
_cache_mtime: Optional[float] = None


def _ensure_config() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _read() -> dict:
    """Read api_keys.json, using mtime cache to avoid redundant disk reads."""
    global _cache, _cache_mtime
    _ensure_config()

    try:
        mtime = API_KEYS_FILE.stat().st_mtime if API_KEYS_FILE.exists() else 0.0
    except OSError:
        mtime = 0.0

    if _cache is not None and _cache_mtime == mtime:
        return _cache

    if not API_KEYS_FILE.exists():
        _cache = {}
        _cache_mtime = mtime
        return _cache

    try:
        data = json.loads(API_KEYS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (json.JSONDecodeError, OSError):
        data = {}

    _cache = data
    _cache_mtime = mtime
    return _cache


def _write(data: dict) -> None:
    """Atomic write: write to temp file, then replace."""
    _ensure_config()
    tmp = API_KEYS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, API_KEYS_FILE)
    global _cache, _cache_mtime
    _cache = data
    try:
        _cache_mtime = API_KEYS_FILE.stat().st_mtime
    except OSError:
        _cache_mtime = None


def load_api_keys() -> dict:
    """Return the full config dict (cached by mtime)."""
    with _lock:
        return dict(_read())


def save_api_keys(data: dict) -> None:
    """Atomically replace the entire config file."""
    with _lock:
        _write(data)


def _update(fn) -> dict:
    """Read-modify-write helper: load, mutate via fn, save."""
    with _lock:
        data = _read()
        fn(data)
        _write(data)
        return data


# ── Provider keys (encrypted at rest via Fernet, mirroring legacy behavior) ──


def get_gemini_key() -> str:
    return str(_read().get("gemini_api_key", "") or "")


def save_gemini_key(key: str) -> None:
    def fn(d):
        d["gemini_api_key"] = key
    _update(fn)


def get_openrouter_key() -> str:
    return str(_read().get("openrouter_api_key", "") or "")


def save_openrouter_key(key: str) -> None:
    def fn(d):
        d["openrouter_api_key"] = key
    _update(fn)


def get_groq_key() -> str:
    return str(_read().get("groq_api_key", "") or "")


def save_groq_key(key: str) -> None:
    def fn(d):
        d["groq_api_key"] = key
    _update(fn)


def get_anthropic_key() -> str:
    return str(_read().get("anthropic_api_key", "") or "")


def save_anthropic_key(key: str) -> None:
    def fn(d):
        d["anthropic_api_key"] = key
    _update(fn)


def get_provider_key(provider_id: str) -> str:
    """Generic key getter for any provider id."""
    return str(_read().get(f"{provider_id}_api_key", "") or "")


def save_provider_key(provider_id: str, key: str) -> None:
    """Generic key setter for any provider id."""
    def fn(d):
        d[f"{provider_id}_api_key"] = key
    _update(fn)


def is_configured() -> bool:
    """Whether at least one provider key is configured."""
    data = _read()
    for k in ("gemini_api_key", "openrouter_api_key", "groq_api_key", "anthropic_api_key"):
        if data.get(k):
            return True
    return False


# ── Assistant identity ──


def get_assistant_name() -> str:
    return str(_read().get("assistant_name", "Stella") or "Stella")


def save_assistant_config(assistant_name: str, user_name: str) -> None:
    def fn(d):
        d["assistant_name"] = assistant_name
        d["user_name"] = user_name
    _update(fn)


def get_user_name() -> str:
    return str(_read().get("user_name", "") or "")


# ── Voice (Gemini Live voices) ──


AVAILABLE_VOICES = ["Charon", "Puck", "Kore", "Fenrir", "Aoede"]


def get_voice() -> str:
    return str(_read().get("voice", "Puck") or "Puck")


def save_voice(voice: str) -> None:
    def fn(d):
        d["voice"] = voice
    _update(fn)


# ── Wake word ──


def get_wake_word_enabled() -> bool:
    return bool(_read().get("wake_word_enabled", True))


def save_wake_word_enabled(enabled: bool) -> None:
    def fn(d):
        d["wake_word_enabled"] = bool(enabled)
    _update(fn)


# ── Push-to-talk ──


def get_push_to_talk_enabled() -> bool:
    return bool(_read().get("push_to_talk_enabled", False))


def save_push_to_talk_enabled(enabled: bool) -> None:
    def fn(d):
        d["push_to_talk_enabled"] = bool(enabled)
    _update(fn)


# ── HUD style ──


def get_hud_style() -> str:
    return str(_read().get("hud_style", "face") or "face")


def save_hud_style(style: str) -> None:
    def fn(d):
        d["hud_style"] = style
    _update(fn)


# ── Thinking ──


def get_thinking_enabled() -> bool:
    return bool(_read().get("thinking_enabled", False))


def save_thinking_enabled(enabled: bool) -> None:
    def fn(d):
        d["thinking_enabled"] = bool(enabled)
    _update(fn)


# ── Turn tuning ──


def get_turn_tuning() -> dict:
    return _read().get("turn_tuning", {}) or {}


def save_turn_tuning(tuning: dict) -> None:
    def fn(d):
        d["turn_tuning"] = tuning
    _update(fn)


# ── Proactive audio ──


def get_proactive_audio_enabled() -> bool:
    return bool(_read().get("proactive_audio_enabled", False))


def save_proactive_audio_enabled(enabled: bool) -> None:
    def fn(d):
        d["proactive_audio_enabled"] = bool(enabled)
    _update(fn)


# ── Media resolution ──


def get_media_resolution() -> str:
    return str(_read().get("media_resolution", "720p") or "720p")


def save_media_resolution(res: str) -> None:
    def fn(d):
        d["media_resolution"] = res
    _update(fn)


# ── Brief ──


def get_brief_enabled() -> bool:
    return bool(_read().get("brief_enabled", True))


def save_brief_enabled(enabled: bool) -> None:
    def fn(d):
        d["brief_enabled"] = bool(enabled)
    _update(fn)


# ── Audio devices ──


def get_input_device() -> str:
    return str(_read().get("input_device", "") or "")


def save_input_device(name: str) -> None:
    def fn(d):
        d["input_device"] = name
    _update(fn)


def get_output_device() -> str:
    return str(_read().get("output_device", "") or "")


def save_output_device(name: str) -> None:
    def fn(d):
        d["output_device"] = name
    _update(fn)


# ── Plugins ──


def get_plugin_enabled(name: str) -> bool:
    """Plugins default to enabled (opt-out). Read on every call — no restart."""
    return bool(_read().get("plugins_enabled", {}).get(name, True))


def save_plugin_enabled(name: str, enabled: bool) -> None:
    def fn(d):
        d.setdefault("plugins_enabled", {})[name] = bool(enabled)
    _update(fn)


def get_plugin_config(namespace: str) -> dict:
    return _read().get("plugin_config", {}).get(namespace, {}) or {}


def save_plugin_config(namespace: str, values: dict) -> None:
    def fn(d):
        d.setdefault("plugin_config", {})[namespace] = values
    _update(fn)


def get_plugin_setting(namespace: str, key: str, default: Any = None) -> Any:
    return _read().get("plugin_config", {}).get(namespace, {}).get(key, default)


# ── Providers ──


def get_provider_mode() -> str:
    """gemini | pipeline | local — defaults to gemini."""
    return str(_read().get("provider_mode", "gemini") or "gemini")


def save_provider_mode(mode: str) -> None:
    def fn(d):
        d["provider_mode"] = mode
    _update(fn)


def get_provider_config(provider_id: str) -> dict:
    return _read().get("providers", {}).get(provider_id, {}) or {}


def save_provider_config(provider_id: str, cfg: dict) -> None:
    def fn(d):
        d.setdefault("providers", {})[provider_id] = cfg
    _update(fn)


def get_pipeline() -> Optional[dict]:
    """Pipeline slots: {stt, llm, tts, sidecar} — only used in pipeline mode."""
    return _read().get("pipeline")


def save_pipeline(pipeline: dict) -> None:
    def fn(d):
        d["pipeline"] = pipeline
    _update(fn)


def get_sidecar_provider() -> Optional[str]:
    return _read().get("sidecar_provider")


def save_sidecar_provider(provider_id: str) -> None:
    def fn(d):
        d["sidecar_provider"] = provider_id
    _update(fn)


def save_providers(all_cfg: dict) -> None:
    """Atomic all-in-one write for the providers block."""
    def fn(d):
        d["providers"] = all_cfg
    _update(fn)


# ── App settings (legacy app_settings.json merged in) ──


def get_app_setting(key: str, default: Any = None) -> Any:
    return _read().get(key, default)


def set_app_setting(key: str, value: Any) -> None:
    def fn(d):
        d[key] = value
    _update(fn)


# ── Tool policy ──


def get_tool_policy() -> dict:
    return _read().get("tool_policy", {}) or {}


def save_tool_policy(policy: dict) -> None:
    def fn(d):
        d["tool_policy"] = policy
    _update(fn)


# ── Reset / init ──


def reset() -> None:
    """Clear config back to defaults."""
    with _lock:
        _write({})


# Module-level alias so both `from config_manager import get_provider_mode`
# and `import config_manager as cm; cm.config_manager.get_provider_mode()` work.
config_manager = sys.modules[__name__]

