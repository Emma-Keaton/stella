"""core/admin_watcher.py - the admin's side of the self-healing loop.

A user hits a failure, taps "Report to admin", and a GitHub issue lands in
Emma-Keaton/stella. This module is what the *admin's* Stella does next:

  1. Poll the repo for issues carrying the `stella-autofix` label.
  2. Feed each one to core.self_improve to produce a candidate fix.
  3. Verify the candidate in an isolated worktree (tests must pass).
  4. Notify the admin with the diff and wait.
  5. Push only when the admin says so.

The last step is the whole design. Step 4 stops and asks. Nothing here has
write access to the network - `publish()` exists but is only reachable through
an explicit admin call, never from the polling loop. An unattended agent that
can open its own pull requests is not a feature, it is an incident waiting for
a bad afternoon.

Admin-only by construction: every entry point checks for a local marker file
that is never shipped, never bundled, and gitignored. A user's install cannot
run this code even if they edit their settings.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
GITHUB_REPO = "Emma-Keaton/stella"
AUTOFIX_LABEL = "stella-autofix"
STATE_DIR = REPO / "feedback" / "admin"
STATE_FILE = STATE_DIR / "watcher_state.json"

# Presence of this file - never committed, never bundled - marks the admin's
# own machine. Absent means this code does nothing at all.
ADMIN_MARKER = REPO / ".stella_admin"


class AdminOnlyError(PermissionError):
    """Raised when a non-admin install tries to drive the watcher."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_admin() -> bool:
    """True only on the admin's own checkout.

    Deliberately NOT a setting. A gitignored file cannot be flipped by a user
    editing config, and cannot survive into a shipped build.
    """
    return ADMIN_MARKER.exists()


def _require_admin() -> None:
    if not is_admin():
        raise AdminOnlyError(
            "The admin watcher only runs on the admin's own checkout "
            f"(missing {ADMIN_MARKER.name})."
        )


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def _load_state() -> dict[str, Any]:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"seen": {}, "pending": [], "history": []}


def _save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# GitHub access
# ---------------------------------------------------------------------------

def _gh(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["gh", *args], cwd=str(REPO), capture_output=True,
        text=True, timeout=120, errors="replace",
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def gh_available() -> bool:
    """True when the `gh` CLI is installed AND authenticated."""
    code, out, _ = _gh(["auth", "status"])
    return code == 0


def fetch_autofix_issues(limit: int = 25) -> list[dict[str, Any]]:
    """Open issues carrying the autofix label, oldest first."""
    code, out, err = _gh([
        "issue", "list",
        "--repo", GITHUB_REPO,
        "--label", AUTOFIX_LABEL,
        "--state", "open",
        "--limit", str(limit),
        "--json", "number,title,body,createdAt,labels,author",
    ])
    if code != 0:
        raise RuntimeError(f"could not list issues: {err.strip()[:300]}")
    try:
        issues = json.loads(out) if out.strip() else []
    except Exception as exc:
        raise RuntimeError(f"unreadable issue list: {exc}")
    # Oldest first, so long-standing breakage gets attention before noise.
    return sorted(issues, key=lambda i: i.get("createdAt", ""))


def _issue_to_error(issue: dict[str, Any]) -> tuple[str, str, str]:
    """Best-effort reconstruction of the original failure from an issue body.

    We never get a live exception object back from a text field, so we rebuild
    an equivalent one. That is enough for self_improve's brief, which only
    needs a type, a message, and a trace to locate the suspect source.
    """
    body = issue.get("body") or ""
    title = issue.get("title") or ""
    error_type = title.split(":")[0].strip() or "RuntimeError"

    message = ""
    for line in body.splitlines():
        if line.strip().lower().startswith("**error:**"):
            message = line.split(":", 1)[1].strip().strip("*").strip()
            break
    if not message:
        message = title

    # Pull the fenced trace block, which carries the real frame locations.
    trace = ""
    if "```" in body:
        blocks = body.split("```")
        for i in range(1, len(blocks), 2):
            if "File \"" in blocks[i]:
                trace = blocks[i].strip()
                break
    if not trace:
        trace = f'  File "<unknown>", line 1, in <module>\n{error_type}: {message}'
    return error_type, message, trace




# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------

def poll_once(model_reply_for=None) -> dict[str, Any]:
    """One pass: fetch labelled issues, attempt a fix for each, notify.

    Never pushes. Verified fixes are queued as `pending` for the admin to
    review and release with `publish()`.

    `model_reply_for` is an injectable callable(issue_dict) -> str that returns
    the model's JSON patch. Keeping it injectable means this function is fully
    testable without a network or an LLM, and the caller decides which model
    to use (local, cloud, or none).
    """
    _require_admin()

    summary: dict[str, Any] = {
        "checked": _now(),
        "gh_available": gh_available(),
        "new": [], "fixed": [], "unfixed": [], "pending": [],
    }
    if not summary["gh_available"]:
        summary["note"] = "`gh` is not authenticated - run `gh auth login`."
        return summary

    state = _load_state()
    try:
        issues = fetch_autofix_issues()
    except Exception as exc:
        summary["note"] = f"could not reach GitHub: {exc}"
        return summary

    from core import self_improve

    for issue in issues:
        num = str(issue.get("number"))
        if num in state["seen"]:
            continue

        error_type, message, trace = _issue_to_error(issue)
        # Rebuild a real exception of the recorded type so self_improve sees a
        # genuine object rather than a stringly-typed impostor.
        err = _rebuild_exception(error_type, message)
        who = (issue.get("author") or {}).get("login") or "unknown"
        context = f"github-issue #{num} by {who}"

        reply = ""
        if model_reply_for is not None:
            try:
                reply = model_reply_for(issue) or ""
            except Exception:
                reply = ""

        outcome = self_improve.improve(err, context, model_reply=reply, trace_text=trace)
        entry = {
            "issue": num,
            "title": issue.get("title"),
            "url": f"https://github.com/{GITHUB_REPO}/issues/{num}",
            "found": _now(),
            "reason": outcome.get("reason", ""),
            "diff": outcome.get("diff", ""),
            "patch": outcome.get("patch"),
        }

        state["seen"][num] = {"first_seen": _now(), "verified": bool(outcome.get("ok"))}
        if outcome.get("ok"):
            state["pending"].append(entry)
            summary["fixed"].append(num)
        else:
            summary["unfixed"].append(num)
        summary["new"].append(num)

    _save_state(state)
    summary["pending"] = [e["issue"] for e in state["pending"]]
    return summary


_EXCEPTION_TYPES = {
    "ValueError", "TypeError", "KeyError", "AttributeError", "IndexError",
    "RuntimeError", "FileNotFoundError", "PermissionError", "NotImplementedError",
    "ImportError", "OSError", "TimeoutError", "ConnectionError", "ZeroDivisionError",
}


# ---------------------------------------------------------------------------
# The release step - admin only, explicit, and never automatic
# ---------------------------------------------------------------------------

def review_pending() -> list[dict[str, Any]]:
    """Verified fixes waiting on the admin's decision."""
    _require_admin()
    return _load_state()["pending"]


def notify_admin() -> str:
    """A plain-English briefing of what is waiting, for the admin to read."""
    _require_admin()
    pending = review_pending()
    if not pending:
        return "No fixes are waiting on your decision."
    lines = [f"{len(pending)} fix(es) are ready for you to release:"]
    for e in pending:
        files = []
        if e.get("patch"):
            files = [e["patch"].get("file", "")]
        lines.append(
            f"\n  #{e['issue']}  {e['title']}\n"
            f"  {e['url']}\n"
            f"  touches: {', '.join(f for f in files if f) or '(unknown)'}\n"
            f"  why: {e['reason']}"
        )
    lines.append("\nRun publish('<issue>') to push one, or publish_all() for all.")
    return "\n".join(lines)


def _commit_and_push(issue: str, diff: str) -> dict[str, Any]:
    """Apply, commit, and push a verified fix. Explicit admin action only."""
    from core import self_improve

    state = _load_state()
    entry = next((e for e in state["pending"] if e["issue"] == str(issue)), None)
    if entry is None:
        return {"ok": False, "reason": f"No pending fix for issue #{issue}."}
    if not entry.get("patch"):
        return {"ok": False, "reason": f"Fix for #{issue} has no patch to apply."}

    # Re-verify against the live tree before touching it. The gate may have
    # passed hours ago in a worktree that no longer exists.
    applied = self_improve.apply_verified_patch(entry["patch"])
    if not applied.get("ok"):
        return {"ok": False, "reason": applied.get("reason", "apply failed"),
                "test_output": applied.get("test_output", "")}

    branch = f"fix/issue-{issue}"
    steps = [
        ["git", "switch", "-c", branch],
        ["git", "add", "-A"],
        ["git", "commit", "-m",
         f"fix: {entry['title']}\n\nCloses #{issue}\n\n"
         f"Proposed by Stella, verified by the test suite, released by admin."],
        ["git", "push", "-u", "origin", branch],
    ]
    log = []
    for cmd in steps:
        proc = self_improve._run(cmd, self_improve.REPO)
        log.append({"cmd": " ".join(cmd[1:4]), "code": proc.returncode})
        if proc.returncode != 0:
            # Leave the tree exactly as we found it.
            self_improve._run(["git", "switch", "-"], self_improve.REPO)
            self_improve._run(["git", "reset", "--hard", "HEAD"], self_improve.REPO)
            return {"ok": False, "reason": f"`{' '.join(cmd[:2])}` failed: "
                                           f"{proc.stderr.strip()[:300]}", "log": log}

    state["pending"] = [e for e in state["pending"] if e["issue"] != str(issue)]
    state.setdefault("history", []).append(
        {"issue": issue, "pushed": _now(), "branch": branch}
    )
    _save_state(state)
    return {
        "ok": True,
        "branch": branch,
        "pr_url": f"https://github.com/{GITHUB_REPO}/compare/main...{branch}?expand=1",
        "reason": f"Pushed fix for #{issue} on {branch}. Open the PR to merge.",
        "log": log,
    }


def publish(issue: str) -> dict[str, Any]:
    """Push ONE verified fix. Requires the admin marker, every time."""
    _require_admin()
    return _commit_and_push(issue, "")


def publish_all() -> dict[str, Any]:
    """Push every verified fix, stopping at the first failure."""
    _require_admin()
    results = {}
    for e in list(review_pending()):
        results[e["issue"]] = publish(e["issue"])
        if not results[e["issue"]].get("ok"):
            break  # stop rather than stack failures on a broken tree
    return results


def status() -> dict[str, Any]:
    """UI-facing summary. Safe to call on any install."""
    st = _load_state()
    return {
        "admin": is_admin(),
        "gh_available": gh_available() if is_admin() else False,
        "seen": len(st["seen"]),
        "pending": [e["issue"] for e in st["pending"]],
        "history": st.get("history", [])[-10:],
    }



def _rebuild_exception(error_type: str, message: str) -> BaseException:
    """Build an exception of the recorded type, falling back to RuntimeError.

    We never `eval` a type name from user input - that is arbitrary code
    execution wearing a hat. Only names on an explicit allowlist are honoured.
    """
    import builtins
    cls = getattr(builtins, error_type, None)
    if not (isinstance(cls, type) and issubclass(cls, BaseException)
            and error_type in _EXCEPTION_TYPES):
        return RuntimeError(message)
    return cls(message)
