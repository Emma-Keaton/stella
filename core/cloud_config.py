"""Cloud provider configuration — encrypted at rest, loaded by Phase 5 router.

Schema (per provider):
{
  "provider": "groq|gemini|openai|anthropic|openrouter|ollama|lmstudio|custom",
  "api_key": "***",           # masked in UI, never echoed back
  "base_url": "https://...",  # for ollama/lmstudio/custom (optional presets)
  "model": "model-name",
  "headers": {"Authorization": "Bearer ***"},  # extra headers for custom
  "params": {"temperature": 0.7, "max_tokens": 2048},
  "fallback": ["provider-id", ...]
}

Storage: %LOCALAPPDATA%/StellaAI/config/cloud_providers.json
Encrypted with Fernet (cryptography) if available, else plaintext with 0600.
"""
from __future__ import annotations

import json
import os
import stat
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.user_paths import get_user_data_dir

CONFIG_DIR = get_user_data_dir() / "config"
CLOUD_FILE = CONFIG_DIR / "cloud_providers.json"

# Try to use cryptography for encryption
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

# Key derivation salt (stored alongside encrypted data)
_SALT_FILE = CONFIG_DIR / ".cloud_salt"


def _get_or_create_key() -> bytes:
    """Derive or load encryption key from machine-specific material.

    The derivation is expensive (PBKDF2, 100k iterations) and the salt is
    stable, so the result is cached in memory. Without this, every single
    provider read cost ~200ms - on the request path.
    """
    if not _HAS_CRYPTO:
        return b""
    import platform
    try:
        user = os.getlogin()
    except Exception:
        user = os.environ.get("USERNAME", "user")
    passphrase = f"stella-{platform.node()}-{user}"
    return _derive_key(str(_SALT_FILE), passphrase)


@lru_cache(maxsize=4)
def _derive_key(salt_path: str, passphrase: str) -> bytes:
    """Derive the Fernet key from a salt file and a machine passphrase.

    Cached because PBKDF2 with 100k iterations costs ~200ms - without the
    cache, every provider read paid that cost on the request path. The cache
    key includes the salt path so a redirected config directory gets its own
    key instead of the wrong one.
    """
    salt_file = Path(salt_path)
    salt_file.parent.mkdir(parents=True, exist_ok=True)
    if salt_file.exists():
        salt = salt_file.read_bytes()
    else:
        salt = os.urandom(16)
        salt_file.write_bytes(salt)
        try:
            os.chmod(salt_file, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return key


def _reset_key_cache() -> None:
    """Drop the cached derived keys - used by tests and after a salt change."""
    _derive_key.cache_clear()


def _encrypt(data: bytes) -> bytes:
    if not _HAS_CRYPTO:
        return data
    key = _get_or_create_key()
    f = Fernet(key)
    return f.encrypt(data)


def _decrypt(data: bytes) -> bytes:
    if not _HAS_CRYPTO:
        return data
    key = _get_or_create_key()
    f = Fernet(key)
    try:
        return f.decrypt(data)
    except Exception:
        return b""


def load_providers() -> list[dict[str, Any]]:
    """Load all provider configs. Returns list of dicts with masked api_key."""
    if not CLOUD_FILE.exists():
        return []
    try:
        raw = CLOUD_FILE.read_bytes()
        decrypted = _decrypt(raw)
        providers = json.loads(decrypted.decode("utf-8"))
        if not isinstance(providers, list):
            return []
        # Mask api_key for safety
        return [_mask(p) for p in providers]
    except Exception:
        return []


def load_provider(provider_id: str, reveal: bool = False) -> dict[str, Any] | None:
    """Load a single provider config.

    The api_key is MASKED by default. Pass reveal=True only when the secret is
    genuinely needed (making a request). Use load_provider_raw() for that -
    this function exists so the masked default is the path of least resistance.
    """
    p = _find_provider(provider_id)
    if p is None:
        return None
    if reveal:
        return p
    return _mask(p)


def load_provider_raw(provider_id: str) -> dict[str, Any] | None:
    """Load a single provider config WITH the plaintext api_key (internal use)."""
    return _find_provider(provider_id)


def _find_provider(provider_id: str) -> dict[str, Any] | None:
    """Locate a provider entry by id, ignoring casing/whitespace."""
    if not provider_id:
        return None
    target = str(provider_id).strip().lower()
    for p in load_providers_raw():
        if str(p.get("provider", "")).strip().lower() == target:
            return p
    return None


def _mask(entry: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a provider entry with the api_key masked."""
    out = dict(entry)
    if out.get("api_key"):
        out["api_key"] = MASK
    return out


def save_provider(config: dict[str, Any]) -> bool:
    """Save or update a provider config. Encrypts at rest."""
    pid = str(config.get("provider", "")).strip().lower()
    if pid in NON_AI_PROVIDERS:
        raise ValueError(
            f"{pid!r} is not an AI provider and cannot be saved to the AI provider store."
        )
    providers = load_providers_raw()
    # Remove existing with same provider id
    providers = [p for p in providers if p.get("provider") != config.get("provider")]
    providers.append(config)
    return _write_providers(providers)


def delete_provider(provider_id: str) -> bool:
    """Delete a provider config."""
    providers = load_providers_raw()
    providers = [p for p in providers if p.get("provider") != provider_id]
    return _write_providers(providers)


def load_providers_raw() -> list[dict[str, Any]]:
    """Load providers with actual api_keys (internal use only)."""
    if not CLOUD_FILE.exists():
        return []
    try:
        raw = CLOUD_FILE.read_bytes()
        decrypted = _decrypt(raw)
        return json.loads(decrypted.decode("utf-8"))
    except Exception:
        return []


def _write_providers(providers: list[dict[str, Any]]) -> bool:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = json.dumps(providers, indent=2).encode("utf-8")
        encrypted = _encrypt(data)
        CLOUD_FILE.write_bytes(encrypted)
        try:
            os.chmod(CLOUD_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass
        return True
    except Exception:
        return False


# Non-AI integrations that share the provider store. They must never be
# returned by the AI routing helpers.
NON_AI_PROVIDERS: frozenset[str] = frozenset({"home_assistant"})

#: The mask shown in place of a stored API key.
MASK = "••••••••"


def is_ai_provider(provider_id: str) -> bool:
    """True if the id refers to an AI provider (not home_assistant etc.)."""
    if not provider_id:
        return False
    pid = str(provider_id).strip().lower()
    if pid in NON_AI_PROVIDERS:
        return False
    try:
        from core.providers.registry import get_provider
        return get_provider(pid) is not None
    except Exception:
        # Registry unavailable: fall back to "anything not explicitly non-AI".
        return pid not in NON_AI_PROVIDERS


def load_ai_providers() -> list[dict[str, Any]]:
    """All AI provider configs (masked), excluding non-AI integrations."""
    return [_mask(p) for p in load_providers_raw() if is_ai_provider(p.get("provider"))]


def get_active_provider() -> dict[str, Any] | None:
    """Get the first configured AI provider (for the router).

    Never returns home_assistant or any other non-AI integration.
    """
    for p in load_providers_raw():
        if is_ai_provider(p.get("provider")):
            return p
    return None


# Preset base URLs for known providers.
# Derived from the shared registry (config/providers.json) so there is exactly
# one copy - see core/providers/registry.py.
try:
    from core.providers.registry import presets as _registry_presets
    PRESETS = _registry_presets()
except Exception:  # pragma: no cover - registry unreadable at import time
    PRESETS = {
        "groq": {"base_url": "https://api.groq.com/openai/v1"},
        "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai"},
        "openai": {"base_url": "https://api.openai.com/v1"},
        "anthropic": {"base_url": "https://api.anthropic.com"},
        "openrouter": {"base_url": "https://openrouter.ai/api/v1"},
        "ollama": {"base_url": "http://localhost:11434/v1"},
        "lmstudio": {"base_url": "http://localhost:1234/v1"},
        "custom": {"base_url": ""},
    }
