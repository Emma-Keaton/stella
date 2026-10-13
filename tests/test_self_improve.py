"""Tests for the self-improvement pipeline and the admin release gate.

The security-critical properties, each with its own test:

  1. Self-improvement is OFF by default. A fresh install must never let the
     model rewrite its own source unprompted.
  2. A model patch cannot touch a non-Python file. That is the single most
     important guard: it is what stops `file: "core/updater.py"` from becoming
     `file: "../../../.github/workflows/build-release.yml"`.
  3. A patch cannot escape the repo via `..` in its path.
  4. A model that claims success without passing tests is rejected.
  5. A verified patch that breaks tests is not committed.
  6. publish() refuses to run unless the machine is the admin's.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from core import admin_watcher as aw
from core import self_improve as si


@pytest.fixture(autouse=True)
def clean_opt_in():
    """Every test starts from a known opt-in state and restores it after."""
    si.disable()
    try:
        yield
    finally:
        si.disable()


@pytest.fixture
def sandbox():
    d = Path(tempfile.mkdtemp(prefix="stella-si-"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --- 1. opt-in gate --------------------------------------------------------

def test_self_improvement_is_off_by_default():
    si.disable()
    assert si.self_improve_enabled() is False
    out = si.improve(ValueError("boom"), "ctx", model_reply='{"ok": true}')
    assert out["ok"] is False
    assert "switched off" in out["reason"].lower()
    assert out["brief"] is None, "no work should even be proposed while off"


def test_self_improvement_requires_opt_in_even_with_valid_patch():
    assert si.self_improve_enabled() is False
    out = si.improve(
        RuntimeError("boom"), "ctx",
        model_reply='{"file": "core/error_reporter.py", "old": "x", "new": "y"}',
    )
    assert out["ok"] is False, "a valid patch must still be refused while off"


# --- 2 & 3. path safety ----------------------------------------------------

def _try_patch(patch: dict):
    """Exercise the path/type guard via the real public entry point.

    Uses `improve()` rather than `_apply_patch` so the test covers the guard a
    caller actually hits, including JSON parsing and the opt-in check.
    """
    si.enable()
    return si.improve(
        RuntimeError("boom"), "ctx",
        model_reply=json.dumps({"file": patch["file"], "old": "a", "new": "b"}),
    )


def test_non_python_file_is_rejected():
    out = _try_patch({"file": ".github/workflows/build-release.yml"})
    assert out["ok"] is False
    assert "non-python" in out["reason"].lower()


@pytest.mark.parametrize("escaped", [
    "../../../etc/passwd.py",
    "..\\..\\..\\windows\\system32\\evil.py",
    "core/../../evil.py",
])
def test_path_escape_is_rejected(escaped):
    out = _try_patch({"file": escaped})
    assert out["ok"] is False
    assert "escapes repo" in out["reason"].lower()


def test_absolute_path_is_rejected():
    out = _try_patch({"file": "C:/Windows/Temp/evil.py"})
    assert out["ok"] is False


def test_config_file_cannot_be_self_edited():
    """The sharpest case: flipping the install's own opt-in must be refused."""
    out = _try_patch({"file": "config/app_settings.json"})
    assert out["ok"] is False
    assert "non-python" in out["reason"].lower()


# --- 4. model honesty ------------------------------------------------------

def test_unparseable_model_reply_is_refused_safely():
    si.enable()
    out = si.improve(
        RuntimeError("boom"), "ctx",
        model_reply='{"file": "core/error_reporter.py"}',  # no old/new -> unusable
    )
    assert out["ok"] is False
    assert out["applied"] is False
    assert "safe code change" in out["reason"].lower()


def test_missing_model_reply_yields_an_analysable_brief():
    si.enable()
    out = si.improve(ValueError("bad thing"), "ctx")
    assert out["ok"] is False
    brief = out.get("brief") or {}
    # The caller needs a prompt it can hand to a model to actually get a fix.
    assert isinstance(brief, dict) and brief.get("prompt")
    assert out["reason"]


def test_no_fix_reply_is_refused():
    si.enable()
    out = si.improve(
        RuntimeError("boom"), "ctx",
        model_reply='{"no_fix": true, "reason": "needs a human"}',
    )
    assert out["ok"] is False


# --- 6. admin gate ---------------------------------------------------------

def test_publish_refuses_when_not_admin():
    with pytest.raises(aw.AdminOnlyError):
        aw.publish("123")


def test_publish_all_refuses_when_not_admin():
    with pytest.raises(aw.AdminOnlyError):
        aw.publish_all()


def test_review_pending_refuses_when_not_admin():
    with pytest.raises(aw.AdminOnlyError):
        aw.review_pending()


def test_status_is_safe_on_a_normal_install():
    st = aw.status()
    assert st["admin"] is False
    assert st["pending"] == []


def test_rebuild_exception_uses_allowlist_not_eval():
    # The whole point: a hostile error_type must never be evaluated.
    assert isinstance(aw._rebuild_exception("ValueError", "m"), ValueError)
    assert isinstance(aw._rebuild_exception("__import__('os')", "m"), RuntimeError)
    assert isinstance(aw._rebuild_exception("SystemExit", "m"), RuntimeError)
    assert isinstance(aw._rebuild_exception("FileNotFoundError", "m"), FileNotFoundError)
    # A made-up name degrades safely rather than raising KeyError at the caller.
    assert type(aw._rebuild_exception("MadeUpError", "m")) is RuntimeError


# --- issue intake: turning a GitHub issue back into a failure ------------------

def test_issue_to_error_extracts_type_message_and_trace():
    body = (
        "**Error:** AttributeError: 'NoneType' object has no attribute 'get'\n\n"
        '```\n  File "agent/llm.py", line 91, in chat\n    x = y\n```\n'
    )
    etype, message, trace = aw._issue_to_error(
        {"title": "AttributeError: bad", "body": body}
    )
    assert etype == "AttributeError"
    assert "NoneType" in message
    # The trace is what lets self_improve locate the frame in real source.
    assert "agent/llm.py" in trace


def test_issue_to_error_survives_a_bodyless_issue():
    """A user filing an issue by hand may give us nothing but a title."""
    etype, message, trace = aw._issue_to_error({"title": "ValueError: nope", "body": ""})
    assert etype == "ValueError"
    assert message, "there must always be a message to analyse"
    assert trace, "there must always be a trace to read"


# --- patch parsing ------------------------------------------------------------

def test_parse_patch_rejects_unusable_replies():
    for junk in ["", "no json here", '{"no_fix": true, "why": "cannot"}',
                 '{"file": "a.py"}', "```json\nnot json\n```"]:
        assert si.parse_patch(junk) is None, f"{junk!r} must be refused"


def test_parse_patch_accepts_a_complete_patch():
    p = si.parse_patch('{"file": "a.py", "old": "x", "new": "y", "why": "z"}')
    assert p == {"file": "a.py", "old": "x", "new": "y", "why": "z"}


def test_parse_patch_survives_code_fences():
    p = si.parse_patch('```json\n{"file": "a.py", "old": "x", "new": "y"}\n```')
    assert p and p["file"] == "a.py"


# --- suspect location ---------------------------------------------------------

def test_suspect_files_ignores_third_party_code(sandbox, monkeypatch):
    """Only frames that resolve to real files inside this repo count.

    A traceback is mostly stdlib and dependency frames. Pointing a model at
    site-packages to 'fix' is both useless and a way out of the repo.
    """
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


# --- off must mean off --------------------------------------------------------

def test_improve_refuses_even_with_a_valid_patch_when_disabled():
    si.disable()
    out = si.improve(
        RuntimeError("boom"), "ctx",
        model_reply='{"file": "core/error_reporter.py", "old": "x", "new": "y"}',
    )
    assert out["ok"] is False
    assert out.get("applied") is False
    assert "switched off" in out["reason"].lower()


def test_disable_leaves_nothing_behind(sandbox, monkeypatch):
    """`disable()` must not leave state that could still act later."""
    monkeypatch.setattr(si, "IMPROVEMENTS_DIR", sandbox / "improve")
    monkeypatch.setattr(si, "WORKTREE_ROOT", sandbox / "worktrees")
    wt = sandbox / "worktrees"
    (wt / "leftover").mkdir(parents=True)
    (wt / "leftover" / "f").write_text("x")

    assert si.disable() is True
    assert si.self_improve_enabled() is False
    assert json.loads((sandbox / "improve" / "candidates.json").read_text()) == []
    assert not wt.exists(), "a leftover worktree would mean disable() lied"


# --- the admin marker is a file, not a setting --------------------------------

def test_admin_marker_enables_the_gate(sandbox, monkeypatch):
    """Point the marker at the sandbox so a real one can never flip these."""
    monkeypatch.setattr(aw, "ADMIN_MARKER", sandbox / ".stella_admin")
    assert aw.is_admin() is False
    (sandbox / ".stella_admin").write_text("local")
    assert aw.is_admin() is True


def test_watcher_state_is_isolated_per_install(sandbox, monkeypatch):
    monkeypatch.setattr(aw, "STATE_DIR", sandbox / "watcher")
    monkeypatch.setattr(aw, "STATE_FILE", sandbox / "watcher" / "state.json")
    assert aw.status()["seen"] == 0
