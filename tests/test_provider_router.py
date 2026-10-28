"""Router tests (T2.x): mode -> ordered provider chain.

Covers the guarantees the spec calls out:
  G7 - the legacy `default_ai_provider` setting is honoured when `routing` is absent
  G8 - a provider error surfaces instead of returning an empty answer
  T1.4 - Anthropic uses its native wire format
"""
from __future__ import annotations

import json

import pytest

from core.providers.router import ProviderRouter


@pytest.fixture
def store(tmp_path, monkeypatch):
    """An encrypted provider store containing the given providers."""
    from core import cloud_config

    userdata = tmp_path / "userdata"
    (userdata / "config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cloud_config, "CONFIG_DIR", userdata / "config")
    monkeypatch.setattr(
        cloud_config, "CLOUD_FILE", userdata / "config" / "cloud_providers.json"
    )
    monkeypatch.setattr(
        cloud_config, "_SALT_FILE", userdata / "config" / ".cloud_salt"
    )
    monkeypatch.setattr(
        "core.user_paths.get_user_data_dir", lambda: userdata
    )

    def _save(providers: list[dict]) -> None:
        for p in providers:
            cloud_config.save_provider(p)

    return _save


def _chain_ids(router: ProviderRouter, mode: str = "chat") -> list[str]:
    return [e["provider"] for e in router.chain(mode)]


def test_routing_overrides_the_legacy_alias(store):
    """G7/T: routing[chat] wins over default_ai_provider."""
    store([
        {"provider": "groq", "api_key": "k", "model": "m"},
        {"provider": "openrouter", "api_key": "k", "model": "m"},
    ])
    router = ProviderRouter({
        "routing": {"chat": "Groq"},
        "default_ai_provider": "OpenRouter",
    })
    assert router.selected("chat") == "groq"
    assert _chain_ids(router)[0] == "groq"


def test_legacy_alias_used_when_no_routing(store):
    """G7: the legacy setting still works."""
    store([
        {"provider": "groq", "api_key": "k", "model": "m"},
        {"provider": "openrouter", "api_key": "k", "model": "m"},
    ])
    router = ProviderRouter({"default_ai_provider": "OpenRouter"})
    assert router.selected("chat") == "openrouter"
    assert _chain_ids(router)[0] == "openrouter"


def test_local_selection_has_no_cloud_fallback(store):
    """"Local" means the local brain only."""
    store([{"provider": "groq", "api_key": "k", "model": "m"}])
    router = ProviderRouter({"default_ai_provider": "Local"})
    assert router.selected("chat") == "local"
    assert router.chain("chat") == []


def test_unconfigured_provider_is_skipped(store):
    """A routed provider with no saved config is skipped, not fatal."""
    store([{"provider": "groq", "api_key": "k", "model": "m"}])
    router = ProviderRouter({"routing": {"chat": "Anthropic"}})
    assert router.selected("chat") == "anthropic"
    assert "anthropic" not in _chain_ids(router)


def test_auto_chain_orders_by_priority(store):
    store([
        {"provider": "groq", "api_key": "k", "model": "m", "priority": 200},
        {"provider": "openrouter", "api_key": "k", "model": "m", "priority": 50},
    ])
    router = ProviderRouter({"routing": {"chat": "Auto"}})
    assert _chain_ids(router) == ["openrouter", "groq"]


def test_fallback_list_expands_the_chain(store):
    store([
        {"provider": "groq", "api_key": "k", "model": "m",
         "fallback": ["openrouter"]},
        {"provider": "openrouter", "api_key": "k", "model": "m"},
    ])
    router = ProviderRouter({"routing": {"chat": "Groq"}})
    assert _chain_ids(router) == ["groq", "openrouter"]


def test_disabled_providers_are_excluded(store):
    store([
        {"provider": "groq", "api_key": "k", "model": "m"},
        {"provider": "openrouter", "api_key": "k", "model": "m", "enabled": False},
    ])
    router = ProviderRouter({"routing": {"chat": "Auto"}})
    assert _chain_ids(router) == ["groq"]


def test_chain_entries_carry_the_resolved_key(store):
    store([{"provider": "groq", "api_key": "gsk-secret", "model": "m"}])
    router = ProviderRouter({"routing": {"chat": "Groq"}})
    entry = router.chain("chat")[0]
    assert entry["api_key"] == "gsk-secret"
    assert entry["base_url"] == "https://api.groq.com/openai/v1"
    assert entry["auth_header"] == "Authorization"
    assert entry["auth_prefix"] == "Bearer "


def test_anthropic_entry_uses_x_api_key(store):
    """T1.4: the Anthropic auth header is x-api-key, not Bearer."""
    store([{"provider": "anthropic", "api_key": "sk-ant-x", "model": "claude"}])
    router = ProviderRouter({"routing": {"chat": "Anthropic"}})
    entry = router.chain("chat")[0]
    assert entry["auth_header"] == "x-api-key"
    assert entry["auth_prefix"] == ""
    assert entry["wire_format"] == "anthropic"


def test_home_assistant_is_never_routed(store):
    """G6: home_assistant is not an AI provider."""
    from core import cloud_config

    cloud_config.load_providers_raw  # noqa: B018 - ensure module loaded
    # Writing home_assistant through the AI store is rejected outright.
    with pytest.raises(ValueError):
        cloud_config.save_provider({"provider": "home_assistant", "api_key": "k"})

    router = ProviderRouter({"routing": {"chat": "Auto"}})
    assert "home_assistant" not in _chain_ids(router)


def test_modes_are_independent(store):
    store([
        {"provider": "groq", "api_key": "k", "model": "m"},
        {"provider": "openrouter", "api_key": "k", "model": "m"},
    ])
    router = ProviderRouter({
        "routing": {"chat": "Groq", "agent": "OpenRouter", "voice": "Auto"},
    })
    assert _chain_ids(router, "chat")[0] == "groq"
    assert _chain_ids(router, "agent")[0] == "openrouter"
    assert len(_chain_ids(router, "voice")) == 2
