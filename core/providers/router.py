"""core/providers/router.py - resolve a mode to an ordered provider chain.

This is the implementation behind `core.llm_router.ProviderRouter` (D11/D12):
one router, one config schema. `core/llm_router.py` is a thin re-export of
this module so both import paths keep working.

The router answers one question: *given a mode (chat/agent/voice), which
providers should be tried, in what order?* It does NOT perform requests -
`core.providers.adapters` does that.

Ordering rules:

1. An explicit selection in `app_settings.json` -> `routing[mode]` wins.
2. Otherwise the legacy `default_ai_provider` setting is used (G7).
3. Otherwise "Auto": every configured provider, ordered by `priority`, then
   by the provider's own `fallback` list.

"Local" means the local brain only - it never has a cloud fallback.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from core.user_paths import get_user_data_dir

logger = logging.getLogger("providers.router")

#: The modes the router can route.
MODES = ("chat", "agent", "voice")

#: The setting name that selects a provider when no routing entry exists.
LEGACY_SETTING = "default_ai_provider"


def app_settings_path() -> Path:
    return get_user_data_dir() / "config" / "app_settings.json"


def load_app_settings() -> dict[str, Any]:
    """Read app_settings.json, tolerating a missing or corrupt file."""
    path = app_settings_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as e:
        logger.warning("Could not read app settings: %s", e)
        return {}
    return data if isinstance(data, dict) else {}


def _auth_header_and_prefix(auth_style: str) -> tuple[str, str]:
    """Map a registry auth_style to (header name, value prefix)."""
    if auth_style == "x-api-key":
        return "x-api-key", ""
    if auth_style == "none":
        return "", ""
    return "Authorization", "Bearer "


def _configured_providers() -> list[dict[str, Any]]:
    """Saved AI provider configs, masked - never the plaintext key."""
    try:
        from core.cloud_config import load_ai_providers
        return load_ai_providers()
    except Exception as e:
        logger.warning("Could not load configured providers: %s", e)
        return []


class ProviderRouter:
    """Resolves a mode to an ordered list of provider candidates."""

    def __init__(self, settings: Optional[dict[str, Any]] = None) -> None:
        self.settings = settings if settings is not None else load_app_settings()
        self._chain_cache: dict[str, list[dict[str, Any]]] = {}

    # -- selection ---------------------------------------------------------

    def selected(self, mode: str) -> str:
        """The provider id selected for a mode, or 'auto'.

        `routing[mode]` wins; the legacy `default_ai_provider` setting is the
        fallback (G7).
        """
        mode = (mode or "chat").strip().lower()
        routing = self.settings.get("routing")
        if isinstance(routing, dict):
            raw = routing.get(mode)
            if raw:
                value = str(raw).strip().lower()
                if value and value != "auto":
                    from core.providers.registry import id_for
                    return id_for(value)

        legacy = self.settings.get(LEGACY_SETTING)
        if legacy:
            from core.providers.registry import id_for
            return id_for(str(legacy))
        return "auto"

    # -- chain -------------------------------------------------------------

    def chain(self, mode: str = "chat") -> list[dict[str, Any]]:
        """The ordered provider chain for a mode.

        Each entry is a fully resolved config, including the plaintext API
        key - treat the returned dicts as secrets.
        """
        mode = (mode or "chat").strip().lower()
        selected = self.selected(mode)

        # "Local" is the local brain only; it never has a cloud fallback.
        if selected == "local":
            return []

        saved = {p["provider"]: p for p in _configured_providers()}
        order: list[str] = []

        if selected != "auto":
            if selected in saved:
                order.append(selected)
            else:
                logger.info(
                    "Routed provider %r for mode %r is not configured; "
                    "falling back to auto.",
                    selected, mode,
                )

        # Auto: every enabled provider, by priority then name.
        if selected == "auto" or not order:
            auto = [
                p for p in _configured_providers()
                if p.get("enabled", True)
            ]
            auto.sort(key=lambda p: (int(p.get("priority", 100) or 100), p["provider"]))
            order.extend(p["provider"] for p in auto)

        # Expand each provider's own fallback list.
        expanded: list[str] = []
        for pid in order:
            if pid not in expanded:
                expanded.append(pid)
            for fb in (saved.get(pid) or {}).get("fallback") or []:
                if fb and fb not in expanded:
                    expanded.append(fb)

        return [self._entry(pid) for pid in expanded if pid in saved]

    def _entry(self, provider_id: str) -> dict[str, Any]:
        """Resolve one provider into a complete request config."""
        from core.providers.keys import resolve_provider_config

        cfg = resolve_provider_config(provider_id)
        header, prefix = _auth_header_and_prefix(cfg.get("auth_style") or "bearer")
        cfg["auth_header"] = header
        cfg["auth_prefix"] = prefix
        return cfg

    # -- convenience -------------------------------------------------------

    def resolve(self, mode: str = "chat") -> list[dict[str, Any]]:
        """Alias for chain() - the first candidate is the preferred provider."""
        return self.chain(mode)

    def first(self, mode: str = "chat") -> Optional[dict[str, Any]]:
        """The preferred provider for a mode, or None."""
        chain = self.chain(mode)
        return chain[0] if chain else None

