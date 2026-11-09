"""core/llm_router.py - the public entry point for provider routing.

This module used to hold a second, parallel router with its own config schema
(`{providers: [{name, kind, model, api_key, base_url, enabled, priority}]}`)
and a plaintext key loader. It had no production consumer, and it conflicted
with `core/cloud_config.py` - two routers, two schemas, exactly the class of
bug this phase exists to fix.

D11/D12: there is now ONE router, `core/providers/router.py`, and this file is
a thin re-export so both import paths keep working:

    from core.llm_router import ProviderRouter   # still valid
    from core.providers.router import ProviderRouter  # canonical

Note that `config/providers.json` is now the shared provider *registry* (ids,
base URLs, wire formats), not a router config. Router configuration lives in
the encrypted `config/cloud_providers.json` plus `app_settings.json`.
"""
from __future__ import annotations

from core.providers.router import (  # noqa: F401
    LEGACY_SETTING,
    MODES,
    ProviderRouter,
    load_app_settings,
)

__all__ = [
    "ProviderRouter",
    "MODES",
    "LEGACY_SETTING",
    "load_app_settings",
    "load_default",
]


def load_default() -> ProviderRouter:
    """The router built from the current app settings and provider store."""
    return ProviderRouter()

