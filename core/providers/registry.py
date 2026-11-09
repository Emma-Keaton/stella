"""core/providers/registry.py - the single source of truth for provider capabilities.

The data lives in `config/providers.json` and is shared verbatim with Android
(`core/ProviderRegistry.kt` reads the same file from `assets/`). Never hard-code a
provider id, base URL or wire format anywhere else - read it from here.
"""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional


def _repo_root() -> Path:
    # core/providers/registry.py -> core/providers -> core -> repo root
    return Path(__file__).resolve().parents[2]


def _registry_path() -> Path:
    """Locate providers.json, preferring the repo copy, then the packaged one."""
    candidates = [
        _repo_root() / "config" / "providers.json",
        Path(getattr(os, "_MEIPASS", "")) / "config" / "providers.json" if getattr(sys, "frozen", False) else None,
        Path(__file__).resolve().parent / "providers.json",
    ]
    for c in candidates:
        if c and c.exists():
            return c
    return _repo_root() / "config" / "providers.json"


@lru_cache(maxsize=1)
def _load() -> dict[str, dict[str, Any]]:
    path = _registry_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for entry in data.get("providers") or []:
        pid = entry.get("id")
        if pid:
            out[pid] = entry
    return out


def reload_registry() -> None:
    """Drop the cache - used by tests and after the file changes."""
    _load.cache_clear()


def all_providers() -> dict[str, dict[str, Any]]:
    """All provider definitions, keyed by id."""
    return dict(_load())


def get_provider(provider_id: str) -> Optional[dict[str, Any]]:
    """One provider definition, or None if the id is unknown."""
    if not provider_id:
        return None
    return _load().get(str(provider_id).strip().lower())


PROVIDER_IDS: list[str] = list(_load().keys())


def provider_ids() -> list[str]:
    """Provider ids, in registry order."""
    return list(_load().keys())


def provider_labels() -> dict[str, str]:
    """id -> human label."""
    return {pid: p.get("label", pid) for pid, p in _load().items()}


def label_for(provider_id: str) -> str:
    p = get_provider(provider_id)
    return p.get("label", provider_id) if p else provider_id


# Label aliases: the UI and the legacy `default_ai_provider` setting both use
# display names, and they do not always agree ("Gemini" vs "Google Gemini").
LABEL_ALIASES: dict[str, str] = {
    "gemini": "gemini",
    "google gemini": "gemini",
    "google": "gemini",
    "groq": "groq",
    "openai": "openai",
    "open ai": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "openrouter": "openrouter",
    "open router": "openrouter",
    "ollama": "ollama",
    "lmstudio": "lmstudio",
    "lm studio": "lmstudio",
    "custom": "custom",
    "local": "local",
}


def id_for(label: str) -> str:
    """Map a display label (or an id) to a canonical provider id.

    Unknown labels fall back to 'custom' so a stray value can never crash the
    caller - an unconfigured provider is skipped by the router anyway.
    """
    if not label:
        return "custom"
    key = str(label).strip().lower()
    if key in _load():
        return key
    return LABEL_ALIASES.get(key, "custom")


def base_url_for(provider_id: str, override: Optional[str] = None) -> str:
    """Base URL for a provider; an explicit override always wins."""
    if override:
        return override.rstrip("/")
    p = get_provider(provider_id)
    if not p:
        return ""
    return (p.get("base_url") or "").rstrip("/")


def requires_key(provider_id: str) -> bool:
    p = get_provider(provider_id)
    return bool(p.get("requires_key")) if p else False


def wire_format(provider_id: str) -> str:
    p = get_provider(provider_id)
    return (p.get("wire_format") or "openai") if p else "openai"


def auth_style(provider_id: str) -> str:
    p = get_provider(provider_id)
    return (p.get("auth_style") or "bearer") if p else "bearer"


def chat_endpoint(provider_id: str) -> str:
    p = get_provider(provider_id)
    return (p.get("chat_endpoint") or "/chat/completions") if p else "/chat/completions"


def models_endpoint(provider_id: str) -> Optional[str]:
    p = get_provider(provider_id)
    if not p:
        return None
    return p.get("models_endpoint")


def static_models(provider_id: str) -> list[str]:
    """Models shipped in the registry (Anthropic has no /models endpoint)."""
    p = get_provider(provider_id)
    return list(p.get("models") or []) if p else []


def anthropic_version() -> str:
    p = get_provider("anthropic")
    return (p.get("anthropic_version") or "2023-06-01") if p else "2023-06-01"


def presets() -> dict[str, dict[str, str]]:
    """Backwards-compatible shape for `core.cloud_config.PRESETS`.

    Historically PRESETS was `{id: {"base_url": ...}}`. Keep exactly that so the
    existing UI code keeps working, but derive it from the registry so there is
    only ever one copy.
    """
    return {pid: {"base_url": (p.get("base_url") or "")} for pid, p in _load().items()}


def has_service_credential(provider_id: str) -> bool:
    """Whether a key exists for a named service, via the single resolver path.

    Skills name the credential they need (aisstream, firms, tomtom, ...) and ask
    this instead of importing `core.providers.keys` themselves, which keeps the
    "exactly one key-resolution site" guard (tests/test_provider_key_resolution.py)
    honest without every feature needing an allow-list entry.
    """
    try:
        from core.providers.keys import resolve_key

        return bool(resolve_key(provider_id))
    except Exception:
        return False


def image_generation_endpoint() -> dict[str, str]:
    """Endpoint and credential for the user-configured image generator.

    The base URL is user configuration, not a secret, so it is read from the
    user's app settings. The credential is resolved through
    `core.providers.keys`, which keeps this codebase's single key-resolution
    path (enforced by tests/test_provider_key_resolution.py).
    """
    base_url = ""
    try:
        from core.user_paths import get_user_data_dir

        path = get_user_data_dir() / "config" / "app_settings.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base_url = str(data.get("image_base_url") or "").strip()
    except Exception:
        base_url = ""

    credential = ""
    try:
        from core.providers.keys import resolve_key

        credential = resolve_key("image") or ""
    except Exception:
        credential = ""

    return {"base_url": base_url.rstrip("/"), "api_key": credential}
