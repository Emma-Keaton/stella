"""Registry contract tests (T0.7).

The provider registry is shared between desktop (Python) and Android (Kotlin).
These tests pin the Python side and check that the Kotlin asset copy is in
sync, so a registry change that is not mirrored on both sides fails CI.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.providers import registry

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_FILE = REPO_ROOT / "config" / "providers.json"
ANDROID_ASSET = (
    REPO_ROOT
    / "stella-connect-android"
    / "app"
    / "src"
    / "main"
    / "assets"
    / "providers.json"
)


@pytest.fixture(autouse=True)
def _fresh_registry():
    registry.reload_registry()
    yield
    registry.reload_registry()


def test_registry_file_exists():
    assert REGISTRY_FILE.exists(), "config/providers.json is the single source of truth"


def test_registry_has_the_eight_providers():
    assert registry.provider_ids() == [
        "groq",
        "gemini",
        "openai",
        "anthropic",
        "openrouter",
        "nvidia",
        "ollama",
        "lmstudio",
        "custom",
    ]


def test_nvidia_entry_points_at_the_nim_endpoint():
    nvidia = registry.get_provider("nvidia")
    assert nvidia is not None
    assert nvidia["base_url"] == "https://integrate.api.nvidia.com/v1"
    assert nvidia["models_endpoint"] == "/models"
    assert nvidia["chat_endpoint"] == "/chat/completions"
    assert nvidia["requires_key"] is True
    assert nvidia.get("models"), "NIM ships a static fallback model list"


def test_every_provider_has_the_required_fields():
    required = (
        "id",
        "label",
        "auth_style",
        "wire_format",
        "base_url",
        "requires_key",
        "chat_endpoint",
    )
    for pid, entry in registry.all_providers().items():
        for field in required:
            assert field in entry, f"{pid} is missing '{field}'"


def test_home_assistant_is_not_an_ai_provider():
    assert "home_assistant" not in registry.provider_ids()
    assert registry.get_provider("home_assistant") is None


def test_anthropic_uses_its_native_wire_format():
    """T1.4: Anthropic is not OpenAI-compatible."""
    assert registry.wire_format("anthropic") == "anthropic"
    assert registry.auth_style("anthropic") == "x-api-key"
    assert registry.chat_endpoint("anthropic") == "/v1/messages"
    # The base URL must NOT include /v1, or the request would become /v1/v1/messages.
    assert registry.base_url_for("anthropic") == "https://api.anthropic.com"
    assert registry.anthropic_version() == "2023-06-01"


def test_openai_compatible_providers_use_bearer():
    for pid in ("groq", "gemini", "openai", "openrouter"):
        assert registry.wire_format(pid) == "openai"
        assert registry.auth_style(pid) == "bearer"
        assert registry.chat_endpoint(pid) == "/chat/completions"


def test_gemini_uses_the_openai_compat_base():
    """T1.5: Gemini's OpenAI-compat base, without a trailing slash."""
    base = registry.base_url_for("gemini")
    assert base == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert not base.endswith("/")


def test_local_providers_do_not_require_a_key():
    for pid in ("ollama", "lmstudio"):
        assert registry.requires_key(pid) is False
        assert registry.auth_style(pid) == "none"


def test_id_for_maps_display_labels():
    assert registry.id_for("Groq") == "groq"
    assert registry.id_for("Google Gemini") == "gemini"
    assert registry.id_for("Gemini") == "gemini"
    assert registry.id_for("Claude") == "anthropic"
    assert registry.id_for("openrouter") == "openrouter"


def test_id_for_unknown_label_falls_back_to_custom():
    assert registry.id_for("Totally Unknown") == "custom"
    assert registry.id_for("") == "custom"


def test_presets_are_derived_from_the_registry():
    presets = registry.presets()
    assert set(presets) == set(registry.provider_ids())
    assert presets["anthropic"]["base_url"] == registry.base_url_for("anthropic")


def test_cloud_config_presets_match_the_registry():
    """core/cloud_config.PRESETS must not drift from the registry."""
    from core.cloud_config import PRESETS

    assert set(PRESETS) == set(registry.provider_ids())
    for pid in registry.provider_ids():
        assert PRESETS[pid]["base_url"] == registry.base_url_for(pid)


def test_android_asset_matches_the_registry():
    """The Kotlin side reads the same file - it must be byte-identical."""
    if not ANDROID_ASSET.exists():
        pytest.skip("Android asset not present in this checkout")
    assert (
        ANDROID_ASSET.read_text(encoding="utf-8")
        == REGISTRY_FILE.read_text(encoding="utf-8")
    ), (
        "config/providers.json and the Android asset have diverged. "
        "Copy the registry file to stella-connect-android/app/src/main/assets/."
    )


def test_registry_file_is_valid_json_with_a_version():
    data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert isinstance(data["providers"], list)
