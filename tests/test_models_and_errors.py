"""Regression tests for local-model switching and plain-English errors.

Covers the two bugs that made the features silently useless:

  1. The Settings combo only wrote the flat `local_ai_model` string, so
     agent/llm.py never learned which endpoint to talk to and switching
     models did nothing. set_selected_model() must produce a selection the
     LLM chain can actually resolve.
  2. Errors surfaced as raw exceptions. translate_error() must always give
     the user something actionable, and ErrorReporter must be able to hand
     them a prefilled GitHub issue for the admin.
"""

import json
import pytest

from agent import model_manager as mm
from core import error_reporter as er


def test_selected_model_round_trips_with_endpoint(sandbox):
    fake = sandbox / "Qwen2.5-3B-Instruct-Q4_K_M.gguf"
    fake.write_bytes(b"\0" * (1024 * 1024))
    mm.set_selected_model({
        "name": fake.name,
        "path": str(fake.resolve()),
        "size_gb": 0.0,
    })
    try:
        sel = mm.get_selected_model()
        assert sel is not None, "selection must survive a save/load round trip"
        assert sel["path"] == str(fake.resolve())
        # This is exactly what agent/llm.py gates its backend on.
        assert sel["endpoint"], "endpoint must be resolved or the LLM chain skips it"
        assert sel["endpoint"].startswith("http")
    finally:
        mm.save_model_settings({"selected_model": None})


def test_clearing_selection_unregisters_it(sandbox):
    fake = sandbox / "m.gguf"
    fake.write_bytes(b"\0" * 64)
    mm.set_selected_model({"name": fake.name, "path": str(fake.resolve())})
    assert mm.get_selected_model() is not None
    mm.save_model_settings({"selected_model": None})
    assert mm.get_selected_model() is None


def test_deleted_model_file_is_not_reported_as_selected(sandbox):
    gone = sandbox / "deleted.gguf"
    mm.set_selected_model({"name": gone.name, "path": str(gone.resolve())})
    # File never created -> get_selected_model must not hand back a dead path,
    # otherwise the LLM chain would keep pointing at a missing model.
    assert mm.get_selected_model() is None
    mm.save_model_settings({"selected_model": None})


def test_list_downloaded_models_finds_gguf(sandbox, monkeypatch):
    monkeypatch.setattr(mm, "get_model_dir", lambda: sandbox)
    (sandbox / "a.gguf").write_bytes(b"\0" * (5 * 1024 * 1024))  # 5 MB
    models = mm.list_downloaded_models()
    assert [m["name"] for m in models] == ["a.gguf"]
    assert models[0]["size_mb"] > 0


def test_size_bytes_is_never_rounded_away(sandbox):
    """size_bytes is the authoritative field; GB/MB are display-only.

    A 2 KB file rounds to 0.00 in both units, so any partial/truncated
    download must still be detectable from size_bytes.
    """
    f = sandbox / "tiny.gguf"
    f.write_bytes(b"\0" * 2048)
    st = mm.get_model_status(f)
    assert st["exists"] is True
    assert st["size_bytes"] == 2048
    assert st["size_gb"] == 0.0
    assert st["size_mb"] == 0.0


def test_model_status_reports_bytes(sandbox):
    f = sandbox / "b.gguf"
    f.write_bytes(b"\0" * (7 * 1024 * 1024))  # 7 MB
    st = mm.get_model_status(f)
    assert st["exists"] is True
    assert st["size_bytes"] == 7 * 1024 * 1024
    assert st["size_mb"] > 0


@pytest.mark.parametrize("exc,needle", [
    (FileNotFoundError("no such file or directory: C:/x"), "find the file"),
    (TimeoutError("Read timed out"), "waited too long"),
    (PermissionError("Permission denied"), "permission"),
    (ConnectionError("connection refused"), "reach a service"),
    (ValueError("invalid tool name"), "value it could not understand"),
    (RuntimeError("out of memory"), "out of memory"),
])
def test_translate_error_is_plain_english(exc, needle):
    out = er.translate_error(exc, "ctx")
    assert needle.lower() in out["plain_to_user"].lower()
    # No raw traceback should ever leak into what the user reads.
    assert "Traceback" not in out["plain_to_user"]
    assert out["device_specs"]["os"]


def test_suggest_improvement_always_offers_a_way_forward():
    out = er.suggest_improvement(ValueError("totally novel failure"), "ctx")
    assert out["alternatives"], "user must never be left without an option"
    assert "admin" in out["global_fix"].lower()


def test_submit_issue_returns_prefilled_admin_url():
    t = er.translate_error(ValueError("boom"), "ctx")
    url = er.ErrorReporter().submit_issue(t)
    assert url.startswith("https://github.com/")
    assert "issues/new" in url
    assert "boom" in url


def test_submit_issue_persists_report():
    before = len(er.ErrorReporter()._load_bug_reports())
    t = er.translate_error(ValueError("persist me"), "ctx")
    er.ErrorReporter().submit_issue(t)
    after = er.ErrorReporter()._load_bug_reports()
    assert len(after) == before + 1
    # Clean up so the repo's feedback store is not polluted by tests.
    er.ErrorReporter()._save_bug_reports(before and after[:-1] or [])
