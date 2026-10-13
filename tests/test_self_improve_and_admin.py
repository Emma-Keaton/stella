"""Tests for the self-improvement loop and the admin gate.

The security property under test: a non-admin install must never be able to
touch the working tree or push to origin, no matter how the functions are
called. That is enforced by the admin marker, not by hoping callers behave.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from core import admin_watcher as aw
from core import self_improve as si


@pytest.fixture(autouse=True)
def isolated_state(sandbox, monkeypatch):
    """Point both modules at a scratch dir and force admin OFF.

    Uses the `sandbox` fixture, not `tmp_path`: pytest's tmp_path cannot be
    created in some sandboxes and fails the whole module at setup.

    `self_improve_enabled` reads the *real* user settings file, so it is
    replaced wholesale. Without this a test that calls disable() would write
    into the developer's own Stella config, and a later test asserting the
    default would silently read another test's leftover value.
    """
    improve = sandbox / "improve"
    watcher = sandbox / "watcher"
    monkeypatch.setattr(si, "IMPROVEMENTS_DIR", improve)
    monkeypatch.setattr(si, "WORKTREE_ROOT", sandbox / "worktrees")
    monkeypatch.setattr(aw, "STATE_DIR", watcher)
    monkeypatch.setattr(aw, "STATE_FILE", watcher / "state.json")
    # The admin gate is a marker FILE, not a setting - point it at the sandbox
    # so a real `.stella_admin` in the repo can never flip these tests.
    monkeypatch.setattr(aw, "ADMIN_MARKER", sandbox / ".stella_admin")
    # Never touch the real repo or network in a test.
    monkeypatch.setattr(si, "REPO", sandbox / "not-a-repo")
    # Never touch the real user settings file in a test.
    _flag = {"on": False}

    class _FakeCfg:
        @staticmethod
        def get_setting(key, default=None):
            return _flag["on"] if key == "self_improve_enabled" else default

        @staticmethod
        def set_setting(key, value):
            if key == "self_improve_enabled":
                _flag["on"] = bool(value)

    monkeypatch.setattr(si, "_cfg", lambda: _FakeCfg)
    yield


# --- self_improve: disabled by default, and that means something ------------

def test_self_improve_is_off_by_default():
    assert si.self_improve_enabled() is False


CONTRACT = {"ok", "applied", "reason", "alternatives", "patch", "brief",
            "diff", "test_output"}


def test_improve_always_returns_every_key(monkeypatch):
    """Every exit path must carry the same keys.

    `admin_watcher` and the UI index these directly, so a path that drops one
    turns a handled refusal into a KeyError the user sees as a crash.
    """
    monkeypatch.setattr(si, "self_improve_enabled", lambda: False)
    assert set(si.improve(ValueError("boom"), "ctx")) >= CONTRACT

    monkeypatch.setattr(si, "self_improve_enabled", lambda: True)  # no git repo
    assert set(si.improve(ValueError("boom"), "ctx")) >= CONTRACT


def test_improve_refuses_when_disabled(monkeypatch):
    monkeypatch.setattr(si, "self_improve_enabled", lambda: False)
    out = si.improve(ValueError("boom"), "ctx")
    assert out["ok"] is False
    # The user reads this string, so it must be plain English, not a token.
    assert "switched off" in out["reason"]
    assert not out["patch"], "no patch may be produced while disabled"


def test_improve_refuses_without_git_repo(monkeypatch):
    monkeypatch.setattr(si, "self_improve_enabled", lambda: True)
    out = si.improve(ValueError("boom"), "ctx")
    assert out["ok"] is False
    assert "git checkout" in out["reason"]


def test_parse_patch_rejects_malformed_json():
    assert si.parse_patch("") is None
    assert si.parse_patch("no json here") is None
    assert si.parse_patch('{"no_fix": true, "why": "cannot"}') is None
    assert si.parse_patch('{"file": "a.py"}') is None  # missing old/new


def test_parse_patch_accepts_a_real_patch():
    p = si.parse_patch('{"file": "a.py", "old": "x", "new": "y", "why": "z"}')
    assert p == {"file": "a.py", "old": "x", "new": "y", "why": "z"}


def test_parse_patch_survives_code_fences():
    p = si.parse_patch('```json\n{"file": "a.py", "old": "x", "new": "y"}\n```')
    assert p and p["file"] == "a.py"


def test_suspect_files_ignores_site_packages(sandbox, monkeypatch):
    """Only frames that resolve to real files inside this repo count."""
    repo = sandbox / "repo"
    (repo / "core" / "agent").mkdir(parents=True)
    (repo / "core" / "agent" / "llm.py").write_text("x = 1\n")
    (sandbox / "site-packages").mkdir()
    (sandbox / "site-packages" / "lib.py").write_text("y = 2\n")
    monkeypatch.setattr(si, "REPO", repo)

    trace = (
        "Traceback (most recent call last):\n"
        f'  File "{sandbox / "site-packages" / "lib.py"}", line 1, in <module>\n'
        '  File "core/agent/llm.py", line 91, in chat\n'
    )
    rels = [f[0] for f in si.suspect_files(trace)]
    assert "core/agent/llm.py" in rels
    assert not any("site-packages" in r for r in rels)


def test_disable_clears_pending_state(sandbox, monkeypatch):
    """`disable()` must leave nothing behind that could still act."""
    monkeypatch.setattr(si, "self_improve_enabled", lambda: False)
    wt = sandbox / "worktrees"
    (wt / "leftover").mkdir(parents=True)
    (wt / "leftover" / "f").write_text("x")

    assert si.disable() is True
    assert si.self_improve_enabled() is False
    assert json.loads((sandbox / "improve" / "candidates.json").read_text()) == []
    assert not wt.exists(), "a leftover worktree would mean disable() lied"


# --- admin gate: non-admin must be inert -----------------------------------
#
# AdminOnlyError subclasses PermissionError, not RuntimeError, so callers can
# catch "you may not do that" without also swallowing genuine crashes.

def test_admin_marker_absent_by_default():
    assert aw.is_admin() is False


def test_poll_once_blocked_for_non_admin():
    with pytest.raises(aw.AdminOnlyError, match="admin"):
        aw.poll_once()


def test_publish_blocked_for_non_admin():
    with pytest.raises(aw.AdminOnlyError, match="admin"):
        aw.publish("1")


def test_publish_all_blocked_for_non_admin():
    with pytest.raises(aw.AdminOnlyError, match="admin"):
        aw.publish_all()


def test_notify_admin_blocked_for_non_admin():
    with pytest.raises(aw.AdminOnlyError, match="admin"):
        aw.notify_admin()


def test_review_pending_blocked_for_non_admin():
    with pytest.raises(aw.AdminOnlyError, match="admin"):
        aw.review_pending()


def test_admin_error_is_a_permission_error():
    """Callers must be able to distinguish 'not allowed' from 'broken'."""
    assert issubclass(aw.AdminOnlyError, PermissionError)
    assert not issubclass(aw.AdminOnlyError, RuntimeError)


def test_admin_can_read_status_without_secrets():
    st = aw.status()
    assert st["admin"] is False
    assert st["pending"] == []


def test_admin_marker_enables_gate(sandbox, monkeypatch):
    (sandbox / ".stella_admin").write_text("local")
    assert aw.is_admin() is True


def test_rebuild_exception_never_evals():
    # A payload that would run code if we eval'd the type name.
    exc = aw._rebuild_exception("__import__('os').system('echo pwned')", "m")
    assert isinstance(exc, RuntimeError)
    assert type(exc) is RuntimeError


def test_rebuild_exception_maps_known_types():
    assert type(aw._rebuild_exception("ValueError", "m")) is ValueError
    assert type(aw._rebuild_exception("FileNotFoundError", "m")) is FileNotFoundError
    assert type(aw._rebuild_exception("MadeUpError", "m")) is RuntimeError


def test_issue_to_error_extracts_trace():
    body = (
        "**Error:** AttributeError: 'NoneType' object has no attribute 'get'\n\n"
        "```\n  File \"agent/llm.py\", line 91, in chat\n    x = y\n```\n"
    )
    etype, message, trace = aw._issue_to_error({"title": "AttributeError: bad", "body": body})
    assert etype == "AttributeError"
    assert "NoneType" in message
    assert "agent/llm.py" in trace
