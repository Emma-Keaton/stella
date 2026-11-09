"""core/self_improve.py - Stella fixing its own code, safely.

The "Fix it myself" button in the error dialog routes here. The promise to the
user is that Stella improves its own codebase so the task works better next
time. The promise to *us* is that it can never brick someone's install.

Both promises hold by construction:

  * Nothing is edited in place. Every attempt happens in a throwaway git
    worktree, so the user's working copy is untouched until - and unless -
    the change survives its own tests.
  * Tests are the gate. An edit that fails `pytest tests/` is discarded and
    the worktree is removed. A green patch is the only kind offered back.
  * It is opt-in per install. `self_improve_enabled` defaults to False, so a
    normal user's Stella never rewrites source on its own.

What this module deliberately does NOT do: hand-roll a code edit. Guessing a
patch with string surgery and hoping pytest agrees produces plausible-looking
breakage. Instead it prepares the environment and produces a precise,
machine-readable brief that an actual model (local or cloud) fills in. The
model proposes; the test gate disposes. See `propose_patch()`.

Offline behaviour: with no LLM configured, `improve()` still succeeds. It
returns the brief and records the failure as a candidate for a global fix, so
the user is told the truth rather than shown a fake success.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
IMPROVEMENTS_DIR = REPO / "feedback" / "improvements"
WORKTREE_ROOT = REPO / ".stella_worktrees"

TEST_TARGETS = ["tests"]
GIT_TIMEOUT = 120
TEST_TIMEOUT = 900


class SelfImproveError(RuntimeError):
    """Raised when self-improvement cannot even be attempted."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    IMPROVEMENTS_DIR.mkdir(parents=True, exist_ok=True)
    WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)


def _run(cmd: list[str], cwd: Path | None = None,
         timeout: int = GIT_TIMEOUT) -> subprocess.CompletedProcess:
    """Run a git command. Defaults to the main checkout.

    `cwd` defaults to REPO so callers do not have to repeat it - and so a
    forgotten argument cannot silently run git against whatever directory the
    process happens to be sitting in.
    """
    return subprocess.run(
        cmd, cwd=str(cwd or REPO), capture_output=True, text=True,
        timeout=timeout, errors="replace",
    )


def _is_git_repo() -> bool:
    return (REPO / ".git").exists()


def _cfg():
    """memory.config_manager exposes plain module-level functions; there is no
    `config_manager` object. Importing one raised ImportError, which the old
    `except Exception` swallowed - so enable() silently did nothing and the
    feature could never be switched on.
    """
    from memory import config_manager
    return config_manager


def self_improve_enabled() -> bool:
    """Per-install opt-in. Defaults OFF."""
    try:
        return bool(_cfg().get_setting("self_improve_enabled", False))
    except Exception:
        return False


def enable() -> bool:
    """Turn self-improvement on for this install. Idempotent."""
    try:
        _cfg().set_setting("self_improve_enabled", True)
    except Exception:
        return False
    return self_improve_enabled()


def disable() -> bool:
    """Turn it off, and make sure nothing half-started is left behind.

    Off must actually mean off: a queued proposal surviving a disable would be
    a lie about what the install is doing.
    """
    try:
        _cfg().set_setting("self_improve_enabled", False)
    except Exception:
        pass
    # Drop any pending candidates so nothing resurfaces on the next enable.
    try:
        IMPROVEMENTS_DIR.mkdir(parents=True, exist_ok=True)
        (IMPROVEMENTS_DIR / "candidates.json").write_text("[]", encoding="utf-8")
    except Exception:
        pass
    # And clean any worktree we were mid-flight in.
    try:
        if WORKTREE_ROOT.exists():
            for child in WORKTREE_ROOT.iterdir():
                shutil.rmtree(child, ignore_errors=True)
            # Remove the empty root too. Leaving it behind is harmless in
            # itself, but "off" should leave the tree byte-identical to how it
            # was before the feature was ever enabled.
            WORKTREE_ROOT.rmdir()
    except Exception:
        pass
    return not self_improve_enabled()



# ---------------------------------------------------------------------------
# Where did it break?
# ---------------------------------------------------------------------------

_FRAME_RE = re.compile(r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+)', re.MULTILINE)


def suspect_files(trace_text: str) -> list[tuple[str, int]]:
    """Pull (path, line) frames out of a traceback, nearest frame first.

    Frames outside this repo are dropped - we can only improve our own code.
    """
    repo_str = str(REPO.resolve())
    hits: list[tuple[str, int]] = []
    for m in _FRAME_RE.finditer(trace_text or ""):
        raw = Path(m.group("path"))
        try:
            resolved = raw if raw.is_absolute() else (REPO / raw)
            resolved = resolved.resolve()
        except Exception:
            continue
        try:
            rel = resolved.relative_to(Path(repo_str))
        except ValueError:
            continue  # stdlib / site-packages / frozen
        if not resolved.exists():
            continue
        hits.append((str(rel).replace("\\", "/"), int(m.group("line"))))
    return list(reversed(hits))


def _read_excerpt(rel: str, line: int, radius: int = 12) -> str:
    """A numbered source excerpt around `line`, so a model sees real context."""
    try:
        lines = (REPO / rel).read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except Exception:
        return ""
    start = max(1, line - radius)
    end = min(len(lines), line + radius)
    return "\n".join(f"{i:5d} | {lines[i - 1]}" for i in range(start, end + 1))


# ---------------------------------------------------------------------------
# The brief a model fills in
# ---------------------------------------------------------------------------

def propose_patch(error: Exception, context: str = "", trace_text: str = "") -> dict[str, Any]:
    """Assemble everything a model needs to write the actual fix.

    Returns a dict the caller hands to an LLM:
      prompt     - the instruction text to send
      suspects   - (path, line) frames inside this repo, nearest first
      schema     - the exact JSON shape a usable reply must have

    Keeping the shape stable matters: `improve()` stores this dict as `brief`
    and the UI/CLI read `brief["prompt"]` to retry the fix later.
    """
    frames = suspect_files(trace_text)
    sites = []
    for rel, line in frames[:3]:
        sites.append({
            "file": rel,
            "line": line,
            "excerpt": _read_excerpt(rel, line),
        })

    try:
        from core.error_reporter import translate_error
        plain = translate_error(error, context).get("plain_to_user", "")
    except Exception:
        plain = str(error)

    prompt = f"""You are improving the Stella codebase to fix a real failure.

Failure (plain English): {plain}
Raw error: {type(error).__name__}: {error}
Where it happened: {context or "(not recorded)"}

Suspect source locations:
{json.dumps(sites, indent=2) if sites else "(no project frames in the trace)"}

Rules:
- Change the smallest amount of source that fixes the cause, not the symptom.
- Do not weaken a test, delete a check, or broaden an `except`.
- Do not add dependencies that are not already installed.
- Reply with ONLY JSON, no prose, no code fences:

{{
  "file": "<path relative to repo root>",
  "old": "<exact existing text, copied verbatim>",
  "new": "<replacement text>",
  "why": "<one sentence on the root cause>"
}}"""
    return {
        "prompt": prompt,
        "suspects": [{"file": f, "line": l} for f, l in frames[:3]],
        "schema": {
            "file": "str - path relative to repo root, .py only",
            "old": "str - exact existing text, must appear exactly once",
            "new": "str - replacement text",
            "why": "str - one sentence on the root cause",
        },
    }


# ---------------------------------------------------------------------------
# The test gate
# ---------------------------------------------------------------------------

def run_tests(cwd: Path) -> tuple[bool, str]:
    """Run the project's tests in `cwd`. Returns (passed, tail_of_output)."""
    cmd = [sys.executable, "-m", "pytest", *TEST_TARGETS,
           "-q", "--no-header", "-p", "no:cacheprovider"]
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True,
            timeout=TEST_TIMEOUT, errors="replace",
        )
    except subprocess.TimeoutExpired:
        return False, "tests timed out"
    except Exception as exc:
        return False, f"could not run tests: {exc}"
    tail = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, tail[-2000:]


def _apply_patch(cwd: Path, patch: dict[str, Any]) -> None:
    """Apply a patch. Raises if `old` is not present exactly once."""
    target = (cwd / patch["file"]).resolve()
    repo_root = cwd.resolve()

    # Python only. This is the load-bearing guard: without it a model could
    # name ".github/workflows/build-release.yml" and edit the very pipeline
    # that gates its own code, or "config/app_settings.json" to flip its own
    # opt-in. Scope of authority, not just scope of filesystem.
    if Path(patch["file"]).suffix.lower() != ".py":
        raise SelfImproveError(
            f"refusing to patch a non-Python file: {patch['file']}"
        )

    # Refuse to write outside the worktree.
    if repo_root not in target.parents and target != repo_root:
        raise SelfImproveError(f"patch target escapes repo: {patch['file']}")
    if not target.exists():
        raise SelfImproveError(f"patch target does not exist: {patch['file']}")
    text = target.read_text(encoding="utf-8-sig", errors="replace")
    if text.count(patch["old"]) != 1:
        raise SelfImproveError(
            f"`old` block appears {text.count(patch['old'])} times in {patch['file']}; "
            "refusing to guess"
        )
    target.write_text(text.replace(patch["old"], patch["new"]), encoding="utf-8")


def _git_diff(cwd: Path) -> str:
    # `cwd` is mandatory. Omitting it diffed the *main* checkout instead of the
    # worktree, which returned an empty diff and made every verified fix look
    # like it had changed nothing.
    proc = _run(["git", "diff"], cwd=cwd)
    return proc.stdout or ""


# ---------------------------------------------------------------------------
# Worktree lifecycle
# ---------------------------------------------------------------------------

class _Worktree:
    """A disposable git worktree. Removes itself on exit, always."""

    def __init__(self, label: str):
        _ensure_dirs()
        self.name = f"{label}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        self.path = WORKTREE_ROOT / self.name
        self.branch = f"stella/self-improve/{self.name}"
        self.created = False

    def __enter__(self) -> "_Worktree":
        if not _is_git_repo():
            raise SelfImproveError("not a git repository - cannot isolate a fix")
        proc = _run(["git", "worktree", "add", "--detach", str(self.path), "HEAD"],
                    cwd=REPO)
        if proc.returncode != 0:
            raise SelfImproveError(f"worktree create failed: {proc.stderr.strip()[:300]}")
        self.created = True
        _run(["git", "switch", "-c", self.branch], cwd=self.path)
        return self

    def __exit__(self, *exc_info) -> bool:
        self.cleanup()
        return False

    def cleanup(self) -> None:
        """Always tear the worktree down, even if creation half-finished.

        Without this, `with _Worktree(...)` raised AttributeError the moment it
        exited, which masked the real result of the attempt and left stray
        worktrees (and their branches) piling up under .stella/tmp.
        """
        if not self.created:
            return
        _run(["git", "worktree", "remove", "--force", str(self.path)], cwd=REPO)
        _run(["git", "branch", "-D", self.branch], cwd=REPO)
        _run(["git", "worktree", "prune"], cwd=REPO)
        shutil.rmtree(self.path, ignore_errors=True)
        self.created = False



# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def _no_change(result: dict[str, Any], reason: str, outcome: str,
               error: Exception | None = None, context: str = "",
               patch: dict[str, Any] | None = None, why: str = "") -> dict[str, Any]:
    """Uniform 'nothing was changed' result. Honest, and never silent."""
    result["ok"] = False
    result["applied"] = False
    result["reason"] = reason
    result["alternatives"] = [
        "Report it to the admin so it is fixed globally and shipped in an update.",
    ]
    if error is not None:
        _record_candidate(error, context, outcome, patch=patch, why=why)
    return result


def improve(error: Exception, context: str = "", model_reply: str = "",
            trace_text: str = "") -> dict[str, Any]:
    """Attempt to improve Stella's code so this failure cannot recur.

    `model_reply` is the JSON a model produced from `propose_patch()`'s prompt.
    With no LLM wired up the caller passes nothing and gets an honest
    "recorded for global fix" result rather than a fake success.

    The returned keys are ALWAYS present, on every path - success, refusal,
    or error. Callers index them without guarding; an intermittent key is a
    KeyError waiting for a bad day.

      ok          - a green patch was produced
      applied     - True only when ok
      reason      - what happened, plain English
      alternatives- what the user can do instead
      patch       - the verified patch, or None
      brief       - the prompt a model can retry from, or None
      diff        - unified diff, or ""
      test_output - tail of the gate run, or ""
    """
    result: dict[str, Any] = {
        "ok": False, "applied": False, "reason": "",
        "alternatives": [], "brief": None, "test_output": "", "diff": "",
        "patch": None,
    }

    if not self_improve_enabled():
        out = _no_change(
            result,
            "Self-improvement is switched off for this install, so Stella did not "
            "change any code.",
            "disabled", error=error, context=context,
        )
        out["alternatives"] = [
            "Turn on Developer Mode, then enable 'Let Stella improve its own code'.",
            "Report it to the admin so it is fixed globally and shipped in an update.",
        ]
        return out

    if not _is_git_repo():
        return _no_change(
            result,
            "Stella can only rewrite its own code when running from a git "
            "checkout, so nothing was changed.",
            "no_git", error=error, context=context,
        )

    brief = propose_patch(error, context, trace_text)
    result["brief"] = brief

    if not model_reply:
        return _no_change(
            result,
            "No AI on this device was able to work out a safe fix, so Stella did "
            "not change any code.",
            "no_model", error=error, context=context,
        )

    patch = parse_patch(model_reply)
    if patch is None:
        return _no_change(
            result,
            "Stella could not turn its idea into a safe code change, so nothing "
            "was changed.",
            "unparseable", error=error, context=context,
        )

    try:
        with _Worktree("fix") as wt:
            _apply_patch(wt.path, patch)
            passed, output = run_tests(wt.path)
            result["test_output"] = output
            if not passed:
                return _no_change(
                    result,
                    "Stella worked out a fix but it broke the test suite, so it "
                    "was thrown away instead of risking your install.",
                    "tests_failed", error=error, context=context,
                    patch=patch, why=patch.get("why", ""),
                )
            result["diff"] = _git_diff(wt.path)
    except SelfImproveError as exc:
        return _no_change(
            result,
            f"Stella could not apply its own fix safely ({exc}), so nothing was "
            "changed.",
            "unsafe", error=error, context=context, patch=patch, why=str(exc),
        )
    except Exception as exc:
        result["reason"] = f"Something went wrong while improving ({exc})."
        return result

    # The gate passed: the patch applied cleanly and the suite is green.
    # This has to be explicit. Falling off the end of the function used to
    # leave ok=False, so a perfectly good verified fix was reported as a
    # failure and thrown away - the feature could never once succeed.
    result["ok"] = True
    result["applied"] = True
    result["reason"] = (
        "Stella found a fix, proved it against the test suite in a throwaway "
        "copy, and queued it for you to release."
    )
    result["patch"] = patch
    return result


def apply_verified_patch(patch: dict[str, Any]) -> dict[str, Any]:
    """Apply an already-verified patch to the live checkout, then re-test.

    Only ever call this with a patch whose diff passed the gate above. The
    tests run again here because the live tree may have moved since.
    """
    try:
        _apply_patch(REPO, patch)
    except SelfImproveError as exc:
        return {"ok": False, "reason": str(exc)}
    passed, output = run_tests(REPO)
    if not passed:
        # Undo rather than leave the tree broken.
        _run(["git", "checkout", "--", patch.get("file", "")])
        return {"ok": False,
                "reason": "The patch broke the test suite and was reverted.",
                "test_output": output}
    return {"ok": True, "reason": "Applied and all tests pass.", "test_output": output}


def _record_candidate(error: Exception, context: str, outcome: str,
                      patch: dict[str, Any] | None = None, why: str = "") -> None:
    """Keep every attempt - successful or not - as a global-fix candidate."""
    try:
        _ensure_dirs()
        record = {
            "created": _now(),
            "outcome": outcome,
            "error_type": type(error).__name__,
            "error_message": str(error)[:500],
            "context": context,
            "why": why[:500],
            "needs_global_fix": True,
        }
        if patch:
            record["patch"] = patch
        path = IMPROVEMENTS_DIR / f"candidate-{outcome}.json"
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        existing.append(record)
        path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    except Exception:
        pass  # recording must never break the caller


def status() -> dict[str, Any]:
    """Summary for the UI: is self-improvement available on this install?"""
    return {
        "enabled": self_improve_enabled(),
        "git_repo": _is_git_repo(),
        "ready": self_improve_enabled() and _is_git_repo(),
        "worktrees_pending": (
            len(list(WORKTREE_ROOT.iterdir())) if WORKTREE_ROOT.exists() else 0
        ),
    }


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_patch(reply: str) -> dict[str, Any] | None:
    """Extract a patch dict from a model reply. Returns None if unusable."""
    if not reply:
        return None
    text = re.sub(r"```(?:json)?", "", reply).strip()
    m = _JSON_RE.search(text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("no_fix"):
        return None
    if not (data.get("file") and data.get("old") is not None and data.get("new") is not None):
        return None
    return data
