"""Regression tests for agent/device_automation.py.

Covers the two things the module promises: reversible activation (deactivation
mirrors activation at the same access level) and rootless scan dispatch without
touching Settings.
"""

from pathlib import Path

from agent import device_automation as da


def test_empty_state_defaults(monkeypatch, tmp_path=None):
    # Point STATE_FILE at a guaranteed-absent path so this test never depends
    # on (or pollutes) the real user dir - device_scan tool tests write state.
    import tempfile, os
    d = Path(tempfile.mkdtemp(prefix="stella-da-empty-"))
    monkeypatch.setattr(da, "STATE_FILE", d / "never-written.json")
    s = da.load_state()
    assert s["device"] == ""
    assert s["platform"] == "unknown"
    assert "collected_at" in s and "errors" in s


def test_save_load_round_trip(monkeypatch):
    # Redirect the state file into a sandbox so tests never touch the user dir.
    import tempfile, os, shutil
    d = Path(tempfile.mkdtemp(prefix="stella-da-"))
    target = d / "state.json"
    monkeypatch.setattr(da, "STATE_FILE", target)
    try:
        assert da.save_state({"device": "phone", "platform": "android"}) == target
        s = da.load_state()
        assert s["device"] == "phone" and s["platform"] == "android"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_revert_is_reversible_and_counts_steps():
    a = da.PCActivation("pc", "stella")
    a.record("scan", {"screens": 3})
    a.record("run", {"ok": True})
    summary = a.revert()
    # Every step gets reversed, at the same access level it was recorded.
    assert summary["reverted"] == 2
    assert summary["failed"] == 0
    assert "start" in summary and "end" in summary


def test_base_activation_refuses_to_silently_revert():
    # The abstract _step_revert raises, so a bare Activation must report a
    # failure rather than pretend the rollback succeeded.
    c = da.Activation("pc", "stella")
    c.record("x", {})
    summary = c.revert()
    assert summary["failed"] == 1 and summary["reverted"] == 0


def test_unsupported_activation_never_fails_revert():
    u = da.UnsupportedActivation("unknown-dev", {})
    assert u.revert()["failed"] == 0
    assert u.summary()["status"] == "unsupported"


def test_scan_dispatch_rootless():
    state, err = da.scan_device("192.168.1.1")
    assert err is None and state["platform"] == "android"
    state2, err2 = da.scan_device("my-pc")
    assert err2 is None and state2["platform"] == "windows"
    # Scanners populate every required detail bucket without opening Settings.
    for key in ("screens", "controls", "permissions", "processes", "network"):
        assert isinstance(state[key], list)


def test_run_script_guards_missing_file():
    import tempfile, os
    from pathlib import Path
    d = Path(tempfile.mkdtemp(prefix="stella-da-"))
    assert da.run_script(d / "missing.txt")["ok"] is False
