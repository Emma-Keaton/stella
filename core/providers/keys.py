"""core/providers/keys.py - THE single place an API key is resolved.

Every module that needs a cloud provider key calls `resolve_key()`. Nothing
else may read `api_keys.json`, the environment, or the encrypted provider store
directly. This is enforced by `tests/test_provider_key_resolution.py` (T1.11).

Resolution order for a provider id:

1. The encrypted provider store (`config/cloud_providers.json`) - this is what
   the Cloud Providers UI writes. Highest priority, because it is the only
   source the user can change from inside the app.
2. The legacy plaintext `config/api_keys.json` (`<provider>_api_key`). Read
   only, never written by new code - it exists purely for migration (D8:
   migrate-and-leave).
3. The environment variable for the provider (e.g. `GROQ_API_KEY`).

Keys are NEVER cached. The legacy clients used to snapshot the key at import
time, which meant a key saved in the UI did not take effect until the app was
restarted (T1.9). `resolve_key()` re-reads on every call, so a save takes
effect immediately.

Nothing in this module logs, prints or returns a key to the UI. Use
`has_key()` when you only need to know whether one exists.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from core.user_paths import get_user_data_dir

logger = logging.getLogger("providers.keys")


def api_keys_path() -> Path:
    """Path of the legacy plaintext key file."""
    return get_user_data_dir() / "config" / "api_keys.json"


#: provider id -> legacy key field in api_keys.json
LEGACY_KEY_FIELDS: dict[str, str] = {
    "groq": "groq_api_key",
    "gemini": "gemini_api_key",
    "openai": "openai_api_key",
    "anthropic": "anthropic_api_key",
    "openrouter": "openrouter_api_key",
    "nvidia": "nvidia_api_key",
    "image": "image_api_key",
}


#: provider id -> environment variable holding the key
ENV_VARS: dict[str, str] = {
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "image": "IMAGE_API_KEY",
}


def normalize_id(provider_id: str) -> str:
    """Canonicalise a provider id or display label to a registry id."""
    if not provider_id:
        return ""
    key = str(provider_id).strip().lower()
    try:
        from core.providers.registry import id_for
        resolved = id_for(key)
        # id_for() maps unknown values to "custom"; prefer the literal id when
        # it is a real registry entry.
        if resolved != "custom" or key == "custom":
            return resolved
        return key
    except Exception:
        return key



def _legacy_key(provider_id: str) -> str:
    """Read the legacy plaintext key file for a provider (read-only)."""
    field = LEGACY_KEY_FIELDS.get(provider_id)
    if not field:
        return ""
    path = api_keys_path()
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Could not read legacy key file %s: %s", path, e)
        return ""
    if not isinstance(data, dict):
        return ""
    value = data.get(field) or ""
    return str(value).strip()


def _env_key(provider_id: str) -> str:
    var = ENV_VARS.get(provider_id)
    if not var:
        return ""
    return (os.environ.get(var) or "").strip()


def _store_key(provider_id: str) -> str:
    """Read the encrypted provider store for a provider."""
    try:
        from core.cloud_config import load_provider_raw
        entry = load_provider_raw(provider_id)
    except Exception as e:
        logger.warning("Could not read provider store for %s: %s", provider_id, e)
        return ""
    if not entry:
        return ""
    return str(entry.get("api_key") or "").strip()


def resolve_key(provider_id: str) -> str:
    """Resolve the API key for a provider.

    Returns an empty string when no key is configured. Never raises, never logs
    the key itself.
    """
    pid = normalize_id(provider_id)
    if not pid:
        return ""

    # 1. The provider store - what the user configured in the UI.
    key = _store_key(pid)
    if key:
        return key

    # 2. Legacy plaintext file - migration only, never written by new code.
    key = _legacy_key(pid)
    if key:
        return key

    # 3. Environment variable.
    return _env_key(pid)


def has_key(provider_id: str) -> bool:
    """True if a key is configured for this provider."""
    return bool(resolve_key(provider_id))


def key_source(provider_id: str) -> Optional[str]:
    """Where the key came from: 'store', 'legacy' or 'env'.

    Useful for diagnostics and for the UI to tell the user their legacy file
    is still in use. Never returns the key.
    """
    pid = normalize_id(provider_id)
    if not pid:
        return None
    if _store_key(pid):
        return "store"
    if _legacy_key(pid):
        return "legacy"
    if _env_key(pid):
        return "env"
    return None



def resolve_provider_config(provider_id: str) -> dict[str, Any]:
    """The saved configuration for a provider, with the key filled in.

    Merges the encrypted store with the registry defaults, so callers always
    get a usable base_url / wire_format / model. The returned dict contains the
    plaintext key - treat it as a secret.
    """
    pid = normalize_id(provider_id)
    try:
        from core.providers.registry import get_provider
        reg = get_provider(pid) or {}
    except Exception:
        reg = {}

    try:
        from core.cloud_config import load_provider_raw
        saved = load_provider_raw(pid) or {}
    except Exception:
        saved = {}

    base_url = saved.get("base_url") or reg.get("base_url") or ""
    model = saved.get("model") or ""
    if not model:
        models = reg.get("models") or []
        model = models[0] if models else ""

    return {
        "provider": pid,
        "api_key": resolve_key(pid),
        "base_url": str(base_url).rstrip("/"),
        "model": model,
        "headers": dict(saved.get("headers") or {}),
        "params": dict(saved.get("params") or {}),
        "fallback": list(saved.get("fallback") or []),
        "enabled": bool(saved.get("enabled", True)),
        "priority": int(saved.get("priority", 100) or 100),
        "wire_format": reg.get("wire_format") or "openai",
        "auth_style": reg.get("auth_style") or "bearer",
        "requires_key": bool(reg.get("requires_key")),
        "label": reg.get("label") or pid,
    }
