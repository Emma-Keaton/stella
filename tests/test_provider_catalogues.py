"""Step 2b tests: provider catalogues, Nvidia registry entry, scheduled refresh, nvidia_api skill."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _fresh_registry():
    from core.providers import registry

    registry.reload_registry()
    yield
    registry.reload_registry()


def _load_skill():
    path = REPO_ROOT / "features" / "nvidia_api" / "skill.py"
    spec = importlib.util.spec_from_file_location("stella_skill_nvidia_api", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------------- registry

def test_nvidia_is_a_first_class_provider():
    from core.providers import registry

    nvidia = registry.get_provider("nvidia")
    assert nvidia is not None
    assert nvidia["base_url"] == "https://integrate.api.nvidia.com/v1"
    assert nvidia["models_endpoint"] == "/models"
    assert registry.requires_key("nvidia") is True


def test_nvidia_env_var_is_mapped():
    from core.providers import keys

    assert keys.ENV_VARS["nvidia"] == "NVIDIA_API_KEY"


def test_android_asset_matches_the_python_registry():
    android = json.loads(
        (REPO_ROOT / "stella-connect-android" / "app" / "src" / "main" / "assets" / "providers.json")
        .read_text(encoding="utf-8"))
    ids = [p["id"] for p in android["providers"]]
    assert "nvidia" in ids, "the Android asset copy must carry the same providers"


# ------------------------------------------------------------------ catalogue

def test_fetch_models_without_a_key_reports_no_key(monkeypatch):
    from core.providers import catalogue

    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setattr(catalogue, "_env_key", lambda pid: "" if pid == "nvidia" else "k")
    outcome = catalogue.fetch_models("nvidia")
    assert outcome["ok"] is False
    assert outcome["failure"] == catalogue.FAILURE_NO_KEY


def test_parse_models_accepts_openai_shape():
    from core.providers import catalogue

    payload = {"data": [{"id": "a"}, {"id": "b"}, {"id": "a"}]}
    assert catalogue._parse_models(payload) == ["a", "b"]
    assert catalogue._parse_models(["x", "y"]) == ["x", "y"]
    assert catalogue._parse_models({}) == []


def test_classify_errors_separates_keys_from_networks():
    from core.providers import catalogue

    class Http(Exception):
        pass

    class Boom(Exception):
        pass

    auth = Boom("401 Client Error: Unauthorized")
    quota = Boom("429 Client Error: Too Many Requests")
    net = Boom("urlopen error timed out")
    other = Boom("something else")

    assert catalogue._classify_error(auth) == catalogue.FAILURE_AUTH
    assert catalogue._classify_error(quota) == catalogue.FAILURE_QUOTA
    assert catalogue._classify_error(net) == catalogue.FAILURE_NETWORK
    assert catalogue._classify_error(other) == catalogue.FAILURE_UNKNOWN


def test_refresh_stale_contacts_only_expired_providers(monkeypatch, tmp_path):
    from core.providers import catalogue
    import core.user_paths

    monkeypatch.setattr(core.user_paths, "get_user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(catalogue, "DEFAULT_TTL_SECONDS", 60.0)

    import time as _time

    monkeypatch.setattr(catalogue, "fetch_models", lambda pid, **kw: {
        "ok": True, "models": ["m1"], "fetched_at": _time.time(), "source": "test"})

    outcomes = catalogue.refresh_stale()
    assert set(outcomes) >= {"groq", "nvidia"}
    assert outcomes["nvidia"]["models"] == ["m1"]

    monkeypatch.setattr(catalogue, "fetch_models",
                        lambda pid, **kw: pytest.fail("fresh cache must not be refetched"))
    assert catalogue.refresh_stale() == {}


def test_status_reports_the_cached_list(monkeypatch, tmp_path):
    from core.providers import catalogue
    import core.user_paths

    monkeypatch.setattr(core.user_paths, "get_user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(catalogue, "fetch_models", lambda pid, **kw: {
        "ok": True, "models": ["first", "second"], "fetched_at": 111.0, "source": "test"})

    catalogue.refresh("groq")
    info = catalogue.status("groq")
    assert info["models"] == ["first", "second"]
    assert info["fetched_at"] == 111.0


def test_list_models_falls_back_to_the_registry(monkeypatch, tmp_path):
    from core.providers import catalogue
    import core.user_paths

    monkeypatch.setattr(core.user_paths, "get_user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(catalogue, "fetch_models", lambda pid, **kw: {
        "ok": False, "failure": catalogue.FAILURE_NETWORK, "reason": "offline"})

    assert catalogue.list_models("nvidia") == catalogue.list_models("nvidia")
    assert len(catalogue.list_models("nvidia")) >= 6


def test_register_periodic_refresh_is_safe(monkeypatch):
    from core import automation
    from core.providers import catalogue

    automation.start()
    assert catalogue.register_periodic_refresh() is True
    assert "provider-model-catalogue-refresh" in automation.list_jobs()
    automation.stop()


# --------------------------------------------------------------- nvidia skill

def test_skill_package_is_valid_and_discoverable():
    from core.dynamic_registry import DynamicToolRegistry

    registry = DynamicToolRegistry()
    registry.initialize()
    skills = registry.list_skills()
    names = [s.get("name") if isinstance(s, dict) else str(s) for s in skills]
    assert "nvidia_api" in names
    assert registry.find_matching_skill("check my nvidia api key") is not None


def test_ping_without_a_key_measures_reachability(monkeypatch):
    skill = _load_skill()
    monkeypatch.setattr(skill, "_resolve_key", lambda: "")
    result = skill.execute(operation="ping")
    assert result["ok"] in (True, False)
    assert "probe" in json.dumps(result["records"])
    assert result["summary"]
    assert "latency" in result["summary"].lower() or "could not be measured" in result["summary"]


def test_models_without_a_key_reports_no_key(monkeypatch):
    skill = _load_skill()
    monkeypatch.setattr(skill, "_resolve_key", lambda: "")
    result = skill.execute(operation="models")
    assert result["ok"] is False
    assert result["records"][-1]["ok"] is False
    assert result["records"][-1]["error"]


def test_unknown_operation_is_refused(monkeypatch):
    skill = _load_skill()
    monkeypatch.setattr(skill, "_resolve_key", lambda: "nvapi-fake")
    result = skill.execute(operation="frobnicate")
    assert result["ok"] is False
    assert "Unknown operation" in result["summary"]


def test_manifest_matches_the_skill_metadata():
    manifest = json.loads((REPO_ROOT / "features" / "nvidia_api" / "manifest.json").read_text(encoding="utf-8"))
    skill = _load_skill()
    assert manifest["name"] == skill.FEATURE_METADATA["name"]
    assert set(manifest["parameters"]["properties"]) == set(
        skill.FEATURE_METADATA["parameters"]["properties"])
    cases = json.loads((REPO_ROOT / "features" / "nvidia_api" / "test_cases.json").read_text(encoding="utf-8"))
    assert isinstance(cases, list) and len(cases) >= 3
