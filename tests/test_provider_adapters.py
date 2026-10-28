"""Adapter tests (T1.3, T1.4, T1.5) - the per-provider wire formats.

These assert the EXACT request each provider receives, without touching the
network: `requests.post` is monkeypatched and the captured url / headers /
body are checked.
"""
from __future__ import annotations

import json

import pytest

from core.providers import adapters


class _Response:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload


@pytest.fixture
def captured(monkeypatch):
    """Capture outgoing requests instead of sending them."""
    calls = []

    def _post(url, headers=None, json=None, timeout=None, **kw):
        calls.append({"url": url, "headers": headers, "body": json, "timeout": timeout})
        return _Response(
            200,
            {
                "choices": [{"message": {"content": "hello"}}],
                "content": [{"type": "text", "text": "hello"}],
            },
        )

    monkeypatch.setattr("requests.post", _post)
    return calls


@pytest.fixture
def provider_cfg(monkeypatch):
    """Feed a fixed provider config into the adapter."""
    cfg = {}

    def _resolve(provider_id):
        return dict(cfg)

    monkeypatch.setattr(
        "core.providers.keys.resolve_provider_config", _resolve
    )
    return cfg


# ---------------------------------------------------------------------------
# OpenAI-compatible providers
# ---------------------------------------------------------------------------

def test_openai_style_request(provider_cfg, captured):
    provider_cfg.update({
        "provider": "groq",
        "api_key": "gsk-test",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "headers": {},
        "params": {},
        "wire_format": "openai",
        "auth_style": "bearer",
        "requires_key": True,
    })
    out = adapters.chat("groq", [{"role": "user", "content": "hi"}])
    assert out == "hello"

    call = captured[0]
    assert call["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer gsk-test"
    assert call["body"]["model"] == "llama-3.3-70b-versatile"
    assert call["body"]["messages"] == [{"role": "user", "content": "hi"}]


def test_gemini_uses_the_openai_compat_path(provider_cfg, captured):
    """T1.5: .../v1beta/openai/chat/completions, Bearer auth."""
    provider_cfg.update({
        "provider": "gemini",
        "api_key": "AIza-test",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.5-flash",
        "headers": {},
        "params": {},
        "wire_format": "openai",
        "auth_style": "bearer",
        "requires_key": True,
    })
    adapters.chat("gemini", [{"role": "user", "content": "hi"}])
    call = captured[0]
    assert call["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    )
    assert call["headers"]["Authorization"] == "Bearer AIza-test"


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

def test_anthropic_uses_v1_messages_and_x_api_key(provider_cfg, captured):
    """T1.4: POST /v1/messages, x-api-key, anthropic-version."""
    provider_cfg.update({
        "provider": "anthropic",
        "api_key": "sk-ant-test",
        "base_url": "https://api.anthropic.com",
        "model": "claude-sonnet-4-5-20250929",
        "headers": {},
        "params": {},
        "wire_format": "anthropic",
        "auth_style": "x-api-key",
        "requires_key": True,
    })
    out = adapters.chat(
        "anthropic",
        [
            {"role": "system", "content": "be brief"},
            {"role": "user", "content": "hi"},
        ],
    )
    assert out == "hello"

    call = captured[0]
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    assert call["headers"]["x-api-key"] == "sk-ant-test"
    assert call["headers"]["anthropic-version"] == "2023-06-01"
    # Anthropic does NOT accept Bearer auth.
    assert "Authorization" not in call["headers"]
    # system is a top-level field, not a message.
    assert call["body"]["system"] == "be brief"
    assert call["body"]["messages"] == [{"role": "user", "content": "hi"}]
    assert all(m["role"] != "system" for m in call["body"]["messages"])


def test_anthropic_does_not_double_the_v1_path(provider_cfg, captured):
    """The base URL must not already contain /v1."""
    provider_cfg.update({
        "provider": "anthropic",
        "api_key": "sk-ant-test",
        "base_url": "https://api.anthropic.com",
        "model": "claude",
        "headers": {},
        "params": {},
        "wire_format": "anthropic",
        "auth_style": "x-api-key",
        "requires_key": True,
    })
    adapters.chat("anthropic", [{"role": "user", "content": "hi"}])
    assert captured[0]["url"].count("/v1/") == 1


# ---------------------------------------------------------------------------
# Errors, headers and params
# ---------------------------------------------------------------------------

def test_missing_key_raises_a_clear_error(provider_cfg, captured):
    provider_cfg.update({
        "provider": "groq",
        "api_key": "",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "m",
        "headers": {},
        "params": {},
        "wire_format": "openai",
        "auth_style": "bearer",
        "requires_key": True,
    })
    with pytest.raises(adapters.ProviderError) as exc:
        adapters.chat("groq", [{"role": "user", "content": "hi"}])
    assert "key is missing" in str(exc.value)
    assert not captured


def test_auth_failure_surfaces(provider_cfg, monkeypatch):
    monkeypatch.setattr(
        "requests.post",
        lambda url, **kw: _Response(401, {}, "unauthorized"),
    )
    provider_cfg.update({
        "provider": "groq",
        "api_key": "bad",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "m",
        "headers": {},
        "params": {},
        "wire_format": "openai",
        "auth_style": "bearer",
        "requires_key": True,
    })
    with pytest.raises(adapters.ProviderError) as exc:
        adapters.chat("groq", [{"role": "user", "content": "hi"}])
    assert "Authentication failed" in str(exc.value)


def test_error_bodies_are_truncated(provider_cfg, monkeypatch):
    monkeypatch.setattr(
        "requests.post",
        lambda url, **kw: _Response(500, {}, "x" * 5000),
    )
    provider_cfg.update({
        "provider": "groq",
        "api_key": "k",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "m",
        "headers": {},
        "params": {},
        "wire_format": "openai",
        "auth_style": "bearer",
        "requires_key": True,
    })
    with pytest.raises(adapters.ProviderError) as exc:
        adapters.chat("groq", [{"role": "user", "content": "hi"}])
    assert len(str(exc.value)) < 300


def test_custom_headers_override_the_derived_auth(provider_cfg, captured):
    provider_cfg.update({
        "provider": "custom",
        "api_key": "k",
        "base_url": "https://example.com/v1",
        "model": "m",
        "headers": {"Authorization": "Bearer custom-token", "X-Extra": "1"},
        "params": {},
        "wire_format": "openai",
        "auth_style": "custom",
        "requires_key": False,
    })
    adapters.chat("custom", [{"role": "user", "content": "hi"}])
    call = captured[0]
    assert call["headers"]["Authorization"] == "Bearer custom-token"
    assert call["headers"]["X-Extra"] == "1"


def test_params_are_merged_into_the_body(provider_cfg, captured):
    provider_cfg.update({
        "provider": "groq",
        "api_key": "k",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "m",
        "headers": {},
        "params": {"top_p": 0.9},
        "wire_format": "openai",
        "auth_style": "bearer",
        "requires_key": True,
    })
    adapters.chat("groq", [{"role": "user", "content": "hi"}])
    assert captured[0]["body"]["top_p"] == 0.9


def test_local_providers_send_no_auth_header(provider_cfg, captured):
    provider_cfg.update({
        "provider": "ollama",
        "api_key": "",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "headers": {},
        "params": {},
        "wire_format": "openai",
        "auth_style": "none",
        "requires_key": False,
    })
    adapters.chat("ollama", [{"role": "user", "content": "hi"}])
    assert "Authorization" not in captured[0]["headers"]
    assert captured[0]["url"] == "http://localhost:11434/v1/chat/completions"
