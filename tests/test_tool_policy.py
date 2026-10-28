"""Step 2 tests: tool policy, approvals, outcome vocabulary, audit, registry gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent import tools as tools_mod
from agent.outcome import ASK, DONE, FAILED, STARTED, UNVERIFIED, from_tool_result, instruction
from core import tool_policy
from core.tool_policy import PolicyDecision, allow, evaluate


@pytest.fixture(autouse=True)
def isolated_policy(monkeypatch, tmp_path):
    """Point the policy loader at a temp repo root and user data dir."""
    repo_config = tmp_path / "config"
    repo_config.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tool_policy, "_repo_root", lambda: tmp_path)

    user_dir = tmp_path / "userdata"
    (user_dir / "config").mkdir(parents=True, exist_ok=True)

    import core.user_paths

    monkeypatch.setattr(core.user_paths, "get_user_data_dir", lambda: user_dir)
    yield repo_config


def _write_rules(path: Path, rules: list) -> None:
    path.write_text(json.dumps({"version": 1, "rules": rules}), encoding="utf-8")


# --------------------------------------------------------------- policy engine

def test_default_rules_deny_active_work(tmp_path):
    _write_rules(tmp_path / "config" / "tool_policy.json", [
        {"name": "allow-passive", "allow": ["*"], "activity": ["passive"], "reason": "ok"},
        {"name": "deny-active", "deny": ["*"], "activity": ["active", "dns"], "reason": "no"},
    ])
    d = evaluate("port_scan", "active", "10.0.0.1")
    assert isinstance(d, PolicyDecision)
    assert d.allowed is False
    assert d.rule == "deny-active"


def test_deny_is_evaluated_before_allow(tmp_path):
    _write_rules(tmp_path / "config" / "tool_policy.json", [
        {"name": "deny-wins", "deny": ["port_scan"], "activity": ["active"], "reason": "no"},
        {"name": "allow-also", "allow": ["port_scan"], "activity": ["active"], "reason": "yes"},
    ])
    assert evaluate("port_scan", "active", "10.0.0.1").allowed is False


def test_missing_policy_permits_passive_and_refuses_gated(tmp_path):
    d = evaluate("read_file", "passive", "notes.txt")
    assert d.allowed is True
    assert d.rule == "passive-observation-stays-open"

    gated = evaluate("sqlmap", "active", "example.com")
    assert gated.allowed is False
    assert gated.rule in {"gated-class-default-deny", "no-active-probing-by-default"}


def test_broken_policy_refuses_and_names_the_file(tmp_path):
    (tmp_path / "config" / "tool_policy.json").write_text("{not json", encoding="utf-8")
    d = evaluate("port_scan", "active", "10.0.0.1")
    assert d.allowed is False
    assert d.rule == "policy-unreadable"


def test_target_glob_patterns_match(tmp_path):
    _write_rules(tmp_path / "config" / "tool_policy.json", [
        allow("lab-only", ["port_scan"], ["active"], ["*.lab.internal"], "lab traffic only"),
    ])
    assert evaluate("port_scan", "active", "host.lab.internal").allowed is True
    assert evaluate("port_scan", "active", "example.com").allowed is False


def test_deny_rule_still_beats_a_broader_allow(tmp_path):
    _write_rules(tmp_path / "config" / "tool_policy.json", [
        allow("everything-active", ["*"], ["active"], reason="wide open"),
        {"name": "never-this-host", "deny": ["*"], "activity": ["active"],
         "targets": ["prod.example.com"], "reason": "production is off limits"},
    ])
    assert evaluate("port_scan", "active", "staging.example.com").allowed is True
    refused = evaluate("port_scan", "active", "prod.example.com")
    assert refused.allowed is False
    assert refused.rule == "never-this-host"


def test_unknown_activity_class_is_refused():
    d = evaluate("port_scan", "sideways", "10.0.0.1")
    assert d.allowed is False
    assert d.rule == "unknown-activity"


def test_explain_lists_rules_and_gated_classes(tmp_path):
    info = tool_policy.explain()
    assert info["gated_classes"] == ["active", "destructive", "dns"]
    assert any(r.get("name") for r in info["rules"])


# -------------------------------------------------------------------- approvals

def test_approval_grant_and_expiry(tmp_path, monkeypatch):
    import core.approvals as approvals
    import core.user_paths

    user_dir = tmp_path / "userdata"
    monkeypatch.setattr(core.user_paths, "get_user_data_dir", lambda: user_dir)

    approvals.grant("pulse", ["port_scan"], ["active"], ["10.0.0.1"], ttl_seconds=60)
    assert approvals.is_approved("pulse", "port_scan", "active", "10.0.0.1") is True
    assert approvals.is_approved("other", "port_scan", "active", "10.0.0.1") is False
    assert approvals.is_approved("pulse", "port_scan", "active", "8.8.8.8") is False
    assert approvals.is_approved("pulse", "port_scan", "passive", "10.0.0.1") is False

    approvals.grant("gone", ["port_scan"], ["active"], ["10.0.0.1"], ttl_seconds=-1)
    assert approvals.is_approved("gone", "port_scan", "active", "10.0.0.1") is False

    approvals.grant("persist", ["nmap"], ["active"])
    assert approvals.is_approved("persist", "nmap", "active") is True
    approvals.revoke("persist")
    assert approvals.is_approved("persist", "nmap", "active") is False

    live = approvals.list_approvals()
    assert "pulse" in live and "gone" not in live


# --------------------------------------------------------------- outcome vocab

def test_outcome_vocabulary_is_five_words():
    assert {DONE, UNVERIFIED, FAILED, ASK, STARTED} == {
        "done", "unverified", "failed", "ask", "started"}
    assert "never" in instruction().lower()


def test_from_tool_result_mapping():
    assert from_tool_result(True, "done", confirmed=True) == DONE
    assert from_tool_result(True, "done", confirmed=False) == UNVERIFIED
    assert from_tool_result(False, "done") == FAILED
    assert from_tool_result(True, "garbage") == UNVERIFIED


# --------------------------------------------------------------- registry gate

def _build_registry():
    return tools_mod.build_default_registry()


def test_registry_refuses_active_tool_without_a_rule(isolated_policy, tmp_path):
    _write_rules(tmp_path / "config" / "tool_policy.json", [
        allow("allow-listed-shell", ["run_command"], ["active"], ["notes.txt"]),
        {"name": "deny-rest", "deny": ["*"], "activity": ["active"], "reason": "no"},
    ])
    reg = _build_registry()
    result = reg.run("run_command", {"command": "echo hi", "target": "other.txt"})
    assert result.ok is False
    assert result.honesty == tools_mod.Honesty.ASK
    assert "tool policy" in result.error


def test_registry_runs_passive_commands(isolated_policy):
    reg = _build_registry()
    assert reg.run("current_time").ok is True


def test_registry_audits_refusals(isolated_policy, tmp_path, monkeypatch):
    _write_rules(tmp_path / "config" / "tool_policy.json", [
        {"name": "deny-all-active", "deny": ["*"], "activity": ["active"], "reason": "no"},
    ])
    monkeypatch.chdir(tmp_path)
    reg = _build_registry()
    reg.run("run_command", {"command": "echo hi"})

    from core import audit

    rows = audit.tail(10)
    assert any(r["tool"] == "run_command" and r["result"] == "refused" for r in rows)
    refused = [r for r in rows if r["result"] == "refused"][-1]
    assert refused["rule"] == "deny-all-active"
    assert refused["activity"] == "active"


def test_registry_honesty_extends_to_ask_and_started():
    reg = tools_mod.Registry()

    @reg.tool("needs_a_guess", "Does nothing.", {})
    def _needs_a_guess() -> tools_mod.ToolResult:
        return tools_mod.ToolResult(ok=False, error="no", honesty=tools_mod.Honesty.ASK)

    @reg.tool("long_running", "Starts something.", {})
    def _long_running() -> tools_mod.ToolResult:
        return tools_mod.ToolResult(ok=True, output="started", honesty=tools_mod.Honesty.STARTED)

    assert reg.run("needs_a_guess").honesty == tools_mod.Honesty.ASK
    assert reg.run("long_running").honesty == tools_mod.Honesty.STARTED
