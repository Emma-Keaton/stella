"""Key-resolution contract tests (T1.11).

There must be exactly ONE place that resolves a provider API key:
`core/providers/keys.py`. Every other module has to go through
`resolve_key()`. This test fails if a new key-reading site appears.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from core.providers import keys as keys_mod

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def _user_data(tmp_path, monkeypatch):
    """Point every key source at a temp dir so tests never touch real keys."""
    userdata = tmp_path / "userdata"
    (userdata / "config").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "core.user_paths.get_user_data_dir", lambda: userdata
    )
    monkeypatch.setattr(keys_mod, "get_user_data_dir", lambda: userdata)

    # The encrypted store must point at the temp dir too, otherwise the real
    # user profile leaks into the test.
    from core import cloud_config

    monkeypatch.setattr(
        cloud_config, "CONFIG_DIR", userdata / "config"
    )
    monkeypatch.setattr(
        cloud_config, "CLOUD_FILE", userdata / "config" / "cloud_providers.json"
    )
    monkeypatch.setattr(
        cloud_config, "_SALT_FILE", userdata / "config" / ".cloud_salt"
    )

    # Clear every provider env var so the ambient environment cannot influence
    # a test.
    for var in keys_mod.ENV_VARS.values():
        monkeypatch.delenv(var, raising=False)

    return userdata


def _write_legacy(userdata: Path, data: dict) -> None:
    cfg = userdata / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "api_keys.json").write_text(json.dumps(data), encoding="utf-8")


def _point_store(monkeypatch, userdata: Path):
    """Redirect the encrypted provider store at a temp path."""
    from core import cloud_config

    monkeypatch.setattr(
        cloud_config,
        "CLOUD_FILE",
        userdata / "config" / "cloud_providers.json",
    )
    return cloud_config


def test_resolve_key_prefers_the_provider_store(_user_data, monkeypatch):
    """The Cloud Providers UI writes cloud_providers.json - that wins."""
    _write_legacy(_user_data, {"groq_api_key": "legacy-groq"})
    cloud_config = _point_store(monkeypatch, _user_data)

    assert cloud_config.save_provider(
        {"provider": "groq", "api_key": "store-groq", "model": "m"}
    )
    assert keys_mod.resolve_key("groq") == "store-groq"
    assert keys_mod.key_source("groq") == "store"


def test_resolve_key_falls_back_to_the_legacy_file(_user_data, monkeypatch):
    """Migration: a key saved before the provider store existed still works."""
    _write_legacy(_user_data, {"groq_api_key": "legacy-groq"})
    _point_store(monkeypatch, _user_data)

    assert keys_mod.resolve_key("groq") == "legacy-groq"
    assert keys_mod.key_source("groq") == "legacy"


def test_resolve_key_falls_back_to_the_environment(_user_data, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "env-groq")
    assert keys_mod.resolve_key("groq") == "env-groq"
    assert keys_mod.key_source("groq") == "env"


def test_resolve_key_returns_empty_when_unconfigured(_user_data, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert keys_mod.resolve_key("groq") == ""
    assert keys_mod.has_key("groq") is False
    assert keys_mod.key_source("groq") is None


def test_resolve_key_accepts_display_labels(_user_data, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "env-gemini")
    assert keys_mod.resolve_key("Google Gemini") == "env-gemini"
    assert keys_mod.resolve_key("gemini") == "env-gemini"


def test_key_takes_effect_without_a_restart(_user_data, monkeypatch):
    """T1.9: the key is re-read per call, not snapshotted at import time."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    cloud_config = _point_store(monkeypatch, _user_data)

    assert keys_mod.resolve_key("groq") == ""

    cloud_config.save_provider({"provider": "groq", "api_key": "fresh-key"})
    assert keys_mod.resolve_key("groq") == "fresh-key"


def test_resolve_provider_config_merges_registry_defaults(_user_data, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cloud_config = _point_store(monkeypatch, _user_data)
    cloud_config.save_provider({"provider": "anthropic", "api_key": "sk-ant-x"})

    cfg = keys_mod.resolve_provider_config("anthropic")
    assert cfg["provider"] == "anthropic"
    assert cfg["api_key"] == "sk-ant-x"
    assert cfg["base_url"] == "https://api.anthropic.com"
    assert cfg["wire_format"] == "anthropic"
    assert cfg["auth_style"] == "x-api-key"



# ---------------------------------------------------------------------------
# The "exactly one resolution path" guard.
# ---------------------------------------------------------------------------

#: Modules allowed to touch a key store directly.
ALLOWED_KEY_READERS = {
    "core/providers/keys.py",
    "core/cloud_config.py",
    "core/providers/registry.py",
    "core/providers/adapters.py",
    "core/providers/router.py",
    "core/llm_router.py",
    # Migrated to resolve keys per-request through keys.resolve_key (Stage 2).
    "groq_client.py",
    "main.py",
    "or_client.py",
    # Uses resolve_key() in CloudLLM.available() to check per-request key presence.
    "agent/llm.py",
    # Provider catalogues and the Nvidia key-test skill both resolve keys
    # through keys.resolve_key() itself (Phase K Step 2b).
    "core/providers/catalogue.py",
    "features/nvidia_api/skill.py",
}

#: Files that legitimately contain unrelated credentials (Instagram, Discord,
#: Spotify, ...) or are not part of the AI provider path.
EXEMPT_FILES = {
    "discord_bot.py",
    "actions/web_search.py",
    "actions/youtube_video.py",
    "actions/stella_dev_agent.py",
    "core/skill_forge.py",
    "core/gemini_optional.py",
    "dashboard/server.py",
    "workspace_store.py",
    "config/__init__.py",
    "ui.py",
    "ui/settings.py",
    "ui/settings_pages.py",
    "tests/test_provider_key_resolution.py",
    "tests/test_provider_registry.py",
    # Pre-existing legacy key readers outside the AI provider routing path.
    # These read api_keys.json / env directly and are not part of the
    # per-request key-resolution unification. Add to ALLOWED_KEY_READERS only
    # when migrated to keys.resolve_key().
    "actions/auto_heal_engine.py",
    "actions/call_assistant.py",
    "actions/calorie_counter.py",
    "actions/circuit_assembler.py",
    "actions/code_helper.py",
    "actions/computer_control.py",
    "actions/computer_settings.py",
    "actions/desktop_organizer_mcp.py",
    "actions/dev_agent.py",
    "actions/docx_tools.py",
    "actions/file_processor.py",
    "actions/flight_finder.py",
    "actions/instagram_chat.py",
    "actions/instagram_mcp.py",
    "actions/meeting_assistant.py",
    "actions/mobile_autopilot.py",
    "actions/office_generator.py",
    "actions/pdf_tools.py",
    "actions/screen_processor.py",
    "actions/spotify_controller.py",
    "agent/error_handler.py",
    "agent/executor.py",
    "agent/planner.py",
    "smart_home/providers/builtin.py",
    "ui/common.py",
    "ui/main_window.py",
    "ui/overlays.py",
}

#: A file that opens api_keys.json, or reads a *_api_key field, is a candidate
#: key-resolution site.
KEY_READ_PATTERN = re.compile(
    r"(api_keys\.json|_api_key|resolve_key|API_KEY_PATH|API_CONFIG_PATH)"
)


#: Directories that never contain first-party source.
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    "build",
    "dist",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "site-packages",
    "stella-connect-android",
}


def _python_sources() -> list[Path]:
    """First-party Python sources, skipping virtualenvs and build output."""
    import os

    files: list[Path] = []
    for root, dirnames, filenames in os.walk(REPO_ROOT):
        # Prune in place so the walk never descends into these trees.
        dirnames[:] = [
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".pytest")
        ]
        rel_dir = Path(root).relative_to(REPO_ROOT)
        if rel_dir.parts and rel_dir.parts[0] in {"tests", "docs"}:
            continue
        for name in filenames:
            if name.endswith(".py"):
                files.append(Path(root) / name)
    return files


def test_only_one_module_resolves_provider_keys():
    """T1.11: no new key-reading site outside core/providers/keys.py."""
    offenders: list[str] = []
    for path in _python_sources():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in ALLOWED_KEY_READERS or rel in EXEMPT_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if KEY_READ_PATTERN.search(text):
            offenders.append(rel)

    assert not offenders, (
        "These modules resolve API keys outside core/providers/keys.py: "
        + ", ".join(sorted(offenders))
        + ". Use keys.resolve_key(provider_id) instead."
    )


def test_keys_module_does_not_write_the_legacy_file():
    """T1.1: the legacy plaintext file is read-only now."""
    text = (REPO_ROOT / "core" / "providers" / "keys.py").read_text(encoding="utf-8")
    assert "write_text" not in text
    assert '"w"' not in text and "'w'" not in text
