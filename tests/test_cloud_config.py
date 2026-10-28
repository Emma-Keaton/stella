"""cloud_config tests (T4.3).

Encrypt/decrypt round-trip, masked vs raw accessors, home_assistant exclusion,
and schema validation of a written file.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import cloud_config


@pytest.fixture
def temp_cloud_config(tmp_path, monkeypatch):
    """Point cloud_config at a temp dir so tests never touch real keys."""
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(cloud_config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(cloud_config, "CLOUD_FILE", cfg_dir / "cloud_providers.json")
    monkeypatch.setattr(cloud_config, "_SALT_FILE", cfg_dir / ".cloud_salt")

    # Reset the derived-key cache so each test gets a fresh key for its temp dir.
    cloud_config._reset_key_cache()

    yield cfg_dir


# ---------------------------------------------------------------------------
# Encrypt/decrypt round-trip
# ---------------------------------------------------------------------------

def test_save_and_load_round_trip(temp_cloud_config):
    """A provider saved via save_provider() is recoverable via load_provider_raw()."""
    assert cloud_config.save_provider({
        "provider": "groq",
        "api_key": "sk-test-12345",
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
    })
    loaded = cloud_config.load_provider_raw("groq")
    assert loaded is not None
    assert loaded["api_key"] == "sk-test-12345"
    assert loaded["model"] == "llama-3.3-70b-versatile"


def test_load_providers_raw_returns_all(temp_cloud_config):
    """load_providers_raw() returns all saved providers with plaintext keys."""
    cloud_config.save_provider({"provider": "groq", "api_key": "key-1", "model": "m1"})
    cloud_config.save_provider({"provider": "anthropic", "api_key": "key-2", "model": "claude-3"})
    raw = cloud_config.load_providers_raw()
    assert len(raw) == 2
    pids = {p["provider"] for p in raw}
    assert pids == {"groq", "anthropic"}


# ---------------------------------------------------------------------------
# Masked vs raw accessors
# ---------------------------------------------------------------------------

def test_load_provider_masks_key_by_default(temp_cloud_config):
    """load_provider() masks the api_key unless reveal=True."""
    cloud_config.save_provider({"provider": "groq", "api_key": "secret-key", "model": "m"})
    masked = cloud_config.load_provider("groq")
    assert masked is not None
    assert masked["api_key"] == cloud_config.MASK
    assert masked["api_key"] != "secret-key"

    raw = cloud_config.load_provider_raw("groq")
    assert raw is not None
    assert raw["api_key"] == "secret-key"


def test_load_provider_reveal_returns_raw(temp_cloud_config):
    """load_provider(pid, reveal=True) returns the plaintext key."""
    cloud_config.save_provider({"provider": "groq", "api_key": "secret-key", "model": "m"})
    revealed = cloud_config.load_provider("groq", reveal=True)
    assert revealed is not None
    assert revealed["api_key"] == "secret-key"


def test_load_providers_masks_all_keys(temp_cloud_config):
    """load_providers() masks every provider's api_key."""
    cloud_config.save_provider({"provider": "groq", "api_key": "key-1", "model": "m1"})
    cloud_config.save_provider({"provider": "anthropic", "api_key": "key-2", "model": "m2"})
    providers = cloud_config.load_providers()
    for p in providers:
        assert p["api_key"] == cloud_config.MASK


def test_load_provider_unknown_returns_none(temp_cloud_config):
    """load_provider() returns None for an unknown provider."""
    assert cloud_config.load_provider("nonexistent") is None


# ---------------------------------------------------------------------------
# home_assistant exclusion
# ---------------------------------------------------------------------------

def test_save_provider_rejects_home_assistant(temp_cloud_config):
    """save_provider() rejects non-AI providers (home_assistant)."""
    with pytest.raises(ValueError, match="not an AI provider"):
        cloud_config.save_provider({
            "provider": "home_assistant",
            "api_key": "some-key",
            "model": "m",
        })


def test_load_ai_providers_excludes_home_assistant(temp_cloud_config):
    """load_ai_providers() never returns home_assistant even if somehow present."""
    cloud_config._write_providers([
        {"provider": "home_assistant", "api_key": "ha-key", "model": "m"},
        {"provider": "groq", "api_key": "gq-key", "model": "m"},
    ])
    ai_providers = cloud_config.load_ai_providers()
    pids = {p["provider"] for p in ai_providers}
    assert "home_assistant" not in pids
    assert "groq" in pids


def test_get_active_provider_never_home_assistant(temp_cloud_config):
    """get_active_provider() never returns home_assistant."""
    cloud_config._write_providers([
        {"provider": "home_assistant", "api_key": "ha-key", "model": "m"},
        {"provider": "groq", "api_key": "gq-key", "model": "m"},
    ])
    active = cloud_config.get_active_provider()
    assert active is not None
    assert active["provider"] != "home_assistant"


def test_is_ai_provider_home_assistant_false(temp_cloud_config):
    """is_ai_provider() returns False for home_assistant."""
    assert cloud_config.is_ai_provider("home_assistant") is False
    assert cloud_config.is_ai_provider("groq") is True


# ---------------------------------------------------------------------------
# Schema validation of a written file
# ---------------------------------------------------------------------------

def test_saved_file_matches_schema(temp_cloud_config):
    """A file written by save_provider() validates against cloud_providers.schema.json."""
    from jsonschema import validate

    schema_path = Path("config/cloud_providers.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    cloud_config.save_provider({
        "provider": "groq",
        "api_key": "sk-test",
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "headers": {},
        "params": {"temperature": 0.7},
        "fallback": ["openrouter"],
    })

    # load_providers_raw() decrypts the stored file, giving us what was written
    written = cloud_config.load_providers_raw()
    validate(instance=written, schema=schema)

