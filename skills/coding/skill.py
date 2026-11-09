"""
skills/coding/skill.py — Stella coding agent.

Provides file read/write, shell execution, code search, str_replace editing,
git operations, task decomposition, and self-correction. Modeled after
OpenCode, Codex CLI, Claude Code, and Aider.

Operations:
  read_file      - Read file contents
  write_file     - Write or create a file
  str_replace    - Edit a file (find/replace exact strings)
  insert         - Insert content at a line position
  grep_search    - Search code with ripgrep-style patterns
  glob           - Find files matching a pattern
  list_dir       - List directory contents
  run_shell      - Execute a shell command
  git_init       - Initialize a git repo
  git_status     - Show git status
  git_add        - Stage files
  git_commit     - Commit staged changes
  git_log        - Show recent commits
  task_decompose - Break a coding task into ordered steps
  self_correct   - Fix errors in a file using an error message
  repo_map       - Build a lightweight repo map for context
  sources        - Return skill metadata
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path.cwd()


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _resolve_path(path: str) -> Path:
    """Resolve a path relative to the workspace root, preventing escapes."""
    p = Path(path)
    if not p.is_absolute():
        p = WORKSPACE_ROOT / p
    # Resolve and ensure it stays within workspace
    try:
        resolved = p.resolve()
        root_resolved = WORKSPACE_ROOT.resolve()
        # Allow paths within workspace root
        try:
            resolved.relative_to(root_resolved)
        except ValueError:
            # Outside workspace — clamp to workspace
            resolved = root_resolved / p.name
        return resolved
    except Exception:
        return WORKSPACE_ROOT / p.name


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _wrap(text: str, width: int = 80) -> str:
    words = text.split()
    lines = []
    current = []
    current_len = 0
    for w in words:
        if current_len + len(w) + len(current) > width:
            lines.append(" ".join(current))
            current = [w]
            current_len = len(w)
        else:
            current.append(w)
            current_len += len(w)
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


# ── read_file ──────────────────────────────────────────────────────────

def _op_read_file(kwargs: dict) -> dict:
    path = (kwargs.get("path") or "").strip()
    if not path:
        return _op("read_file", False, None, "Provide a file path (path=...).")
    limit = int(kwargs.get("limit") or 2000)
    offset = int(kwargs.get("offset") or 0)

    resolved = _resolve_path(path)
    if not resolved.exists():
        return _op("read_file", False, None, f"File not found: {path}")
    if resolved.is_dir():
        return _op("read_file", False, None, f"Path is a directory: {path}")

    text = _read_text(resolved)
    lines = text.splitlines()
    if offset:
        lines = lines[offset:]
    if limit:
        lines = lines[:limit]

    numbered = []
    for i, line in enumerate(lines, start=offset + 1):
        numbered.append(f"{i:4d}\t{line}")

    content = "\n".join(numbered)
    return _op("read_file", True, {
        "path": str(resolved.relative_to(WORKSPACE_ROOT)),
        "content": content,
        "total_lines": len(text.splitlines()),
        "returned_lines": len(lines),
    })


# ── write_file ─────────────────────────────────────────────────────────

def _op_write_file(kwargs: dict) -> dict:
    path = (kwargs.get("path") or "").strip()
    content = kwargs.get("content") or ""
    if not path:
        return _op("write_file", False, None, "Provide a file path (path=...).")

    resolved = _resolve_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return _op("write_file", True, {
        "path": str(resolved.relative_to(WORKSPACE_ROOT)),
        "bytes": len(content.encode("utf-8")),
        "message": f"Wrote {len(content)} chars to {path}",
    })


# ── str_replace ────────────────────────────────────────────────────────

def _op_str_replace(kwargs: dict) -> dict:
    path = (kwargs.get("path") or "").strip()
    old_str = kwargs.get("old_str") or ""
    new_str = kwargs.get("new_str") or ""
    if not path:
        return _op("str_replace", False, None, "Provide a file path (path=...).")
    if old_str == "":
        return _op("str_replace", False, None, "Provide old_str to replace.")

    resolved = _resolve_path(path)
    if not resolved.exists():
        return _op("str_replace", False, None, f"File not found: {path}")
    text = _read_text(resolved)
    count = text.count(old_str)
    if count == 0:
        return _op("str_replace", False, None, f"old_str not found in {path}")
    if count > 1:
        return _op("str_replace", False, None, f"old_str appears {count} times — make it more specific")

    new_text = text.replace(old_str, new_str, 1)
    resolved.write_text(new_text, encoding="utf-8")
    return _op("str_replace", True, {
        "path": str(resolved.relative_to(WORKSPACE_ROOT)),
        "message": f"Replaced {count} occurrence(s) in {path}",
    })


# ── insert ─────────────────────────────────────────────────────────────

def _op_insert(kwargs: dict) -> dict:
    path = (kwargs.get("path") or "").strip()
    content = kwargs.get("content") or ""
    line_no = int(kwargs.get("line_no") or 0)
    if not path:
        return _op("insert", False, None, "Provide a file path (path=...).")

    resolved = _resolve_path(path)
    if not resolved.exists():
        resolved.write_text("", encoding="utf-8")
    lines = _read_text(resolved).splitlines()
    insert_at = max(0, min(line_no, len(lines)))
    lines.insert(insert_at, content)
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return _op("insert", True, {
        "path": str(resolved.relative_to(WORKSPACE_ROOT)),
        "line_no": insert_at,
        "message": f"Inserted at line {insert_at + 1} in {path}",
    })


# ── grep_search ────────────────────────────────────────────────────────

def _op_grep_search(kwargs: dict) -> dict:
    pattern = (kwargs.get("pattern") or "").strip()
    path = (kwargs.get("path") or ".").strip()
    if not pattern:
        return _op("grep_search", False, None, "Provide a search pattern (pattern=...).")

    resolved = _resolve_path(path)
    if not resolved.exists():
        return _op("grep_search", False, None, f"Path not found: {path}")

    try:
        regex = re.compile(pattern)
    except re.error as e:
        return _op("grep_search", False, None, f"Invalid regex: {e}")

    results = []
    search_root = resolved if resolved.is_dir() else resolved.parent
    for f in search_root.rglob("*"):
        if not f.is_file():
            continue
        # Skip binary-ish and large files
        try:
            if f.stat().st_size > 2_000_000:
                continue
        except OSError:
            continue
        try:
            text = _read_text(f)
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                results.append({
                    "file": str(f.relative_to(WORKSPACE_ROOT)),
                    "line": i,
                    "match": line[:200],
                })
                if len(results) >= 100:
                    break
        if len(results) >= 100:
            break

    lines = []
    lines.append(f"grep '{pattern}' in {path}")
    lines.append("=" * 40)
    lines.append("")
    if not results:
        lines.append("No matches found.")
    else:
        for r in results:
            lines.append(f"{r['file']}:{r['line']}: {r['match']}")
        lines.append("")
        lines.append(f"{len(results)} match(es) found.")

    return _op("grep_search", True, {
        "pattern": pattern,
        "path": path,
        "matches": results,
        "count": len(results),
        "content": "\n".join(lines),
    })


# ── glob ───────────────────────────────────────────────────────────────

def _op_glob(kwargs: dict) -> dict:
    pattern = (kwargs.get("pattern") or "*").strip()
    path = (kwargs.get("path") or ".").strip()
    resolved = _resolve_path(path)
    if not resolved.exists():
        return _op("glob", False, None, f"Path not found: {path}")

    search_root = resolved if resolved.is_dir() else resolved.parent
    matches = []
    for f in search_root.rglob(pattern):
        if f.is_file():
            matches.append(str(f.relative_to(WORKSPACE_ROOT)))
        elif f.is_dir():
            matches.append(str(f.relative_to(WORKSPACE_ROOT)) + "/")

    matches = sorted(matches)[:200]
    return _op("glob", True, {
        "pattern": pattern,
        "path": path,
        "matches": matches,
        "count": len(matches),
    })


# ── list_dir ───────────────────────────────────────────────────────────

def _op_list_dir(kwargs: dict) -> dict:
    path = (kwargs.get("path") or ".").strip()
    resolved = _resolve_path(path)
    if not resolved.exists():
        return _op("list_dir", False, None, f"Path not found: {path}")
    if not resolved.is_dir():
        return _op("list_dir", False, None, f"Path is not a directory: {path}")

    entries = []
    for child in sorted(resolved.iterdir()):
        marker = "/" if child.is_dir() else ""
        entries.append(child.name + marker)

    return _op("list_dir", True, {
        "path": str(resolved.relative_to(WORKSPACE_ROOT)),
        "entries": entries,
        "count": len(entries),
    })


# ── run_shell ──────────────────────────────────────────────────────────

def _op_run_shell(kwargs: dict) -> dict:
    command = (kwargs.get("command") or "").strip()
    if not command:
        return _op("run_shell", False, None, "Provide a command to run (command=...).")
    timeout = int(kwargs.get("timeout") or 60)
    cwd = kwargs.get("cwd") or "."

    cwd_resolved = _resolve_path(cwd)
    if not cwd_resolved.exists():
        return _op("run_shell", False, None, f"Working directory not found: {cwd}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd_resolved),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += ("\n[STDERR]\n" + result.stderr) if output else result.stderr
        if not output:
            output = "(no output)"
        return _op("run_shell", result.returncode == 0, {
            "command": command,
            "returncode": result.returncode,
            "output": output,
            "cwd": str(cwd_resolved.relative_to(WORKSPACE_ROOT)),
        })
    except subprocess.TimeoutExpired:
        return _op("run_shell", False, None, f"Command timed out after {timeout}s: {command}")
    except Exception as e:
        return _op("run_shell", False, None, f"Command failed: {e}")


# ── git helpers ────────────────────────────────────────────────────────

def _git(args: list[str], cwd: Path) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        return -1, "git not installed"
    except Exception as e:
        return -1, str(e)


def _op_git(kwargs: dict) -> dict:
    op = (kwargs.get("op") or "status").strip()
    path = (kwargs.get("path") or ".").strip()
    message = (kwargs.get("message") or "").strip()
    files = kwargs.get("files") or []

    resolved = _resolve_path(path)
    if not resolved.exists():
        return _op("git_" + op, False, None, f"Path not found: {path}")

    if op == "init":
        rc, out = _git(["init"], resolved)
        return _op("git_init", rc == 0, {"output": out}, None if rc == 0 else out)

    if op == "status":
        rc, out = _git(["status", "--short"], resolved)
        return _op("git_status", rc == 0, {"status": out}, None if rc == 0 else out)

    if op == "add":
        if not files:
            files = ["."]
        rc, out = _git(["add"] + files, resolved)
        return _op("git_add", rc == 0, {"output": out}, None if rc == 0 else out)

    if op == "commit":
        if not message:
            return _op("git_commit", False, None, "Provide a commit message (message=...).")
        rc, out = _git(["commit", "-m", message], resolved)
        return _op("git_commit", rc == 0, {"output": out}, None if rc == 0 else out)

    if op == "log":
        rc, out = _git(["log", "--oneline", "-10"], resolved)
        return _op("git_log", rc == 0, {"log": out}, None if rc == 0 else out)

    return _op("git_" + op, False, None, f"Unknown git op '{op}'. One of: init, status, add, commit, log.")


# ── claudecode / codex / opencode runner ───────────────────────────────

def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _run_external_agent(cmd: list[str], prompt: str, cwd: Path, timeout: int = 300) -> dict:
    """Run an external coding agent (Claude Code, Codex, OpenCode) with a prompt."""
    if not cmd:
        return {"ok": False, "output": "", "error": "agent command not found"}
    try:
        result = subprocess.run(
            cmd + [prompt],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += ("\n[STDERR]\n" + result.stderr) if output else result.stderr
        if not output:
            output = "(no output)"
        return {"ok": result.returncode == 0, "output": output, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "", "error": f"timed out after {timeout}s"}
    except Exception as e:
        return {"ok": False, "output": "", "error": str(e)}


def _op_claudecode(kwargs: dict) -> dict:
    """Run Claude Code (claude) with a prompt."""
    prompt = (kwargs.get("prompt") or "").strip()
    path = (kwargs.get("path") or ".").strip()
    timeout = int(kwargs.get("timeout") or 300)
    if not prompt:
        return _op("claudecode_run", False, None, "Provide a prompt (prompt=...).")
    resolved = _resolve_path(path)
    if not resolved.exists():
        return _op("claudecode_run", False, None, f"Path not found: {path}")
    cmd = _which("claude")
    if not cmd:
        return _op("claudecode_run", False, None, "Claude Code (claude) not installed. Install with: npm install -g @anthropic-ai/claude-code")
    result = _run_external_agent([cmd], prompt, resolved, timeout)
    return _op("claudecode_run", result["ok"], {
        "command": cmd,
        "output": result["output"],
        "error": result.get("error"),
        "returncode": result.get("returncode"),
    })


def _op_codex(kwargs: dict) -> dict:
    """Run OpenAI Codex (codex) with a prompt."""
    prompt = (kwargs.get("prompt") or "").strip()
    path = (kwargs.get("path") or ".").strip()
    timeout = int(kwargs.get("timeout") or 300)
    if not prompt:
        return _op("codex_run", False, None, "Provide a prompt (prompt=...).")
    resolved = _resolve_path(path)
    if not resolved.exists():
        return _op("codex_run", False, None, f"Path not found: {path}")
    cmd = _which("codex")
    if not cmd:
        return _op("codex_run", False, None, "Codex (codex) not installed. Install with: npm install -g @openai/codex")
    result = _run_external_agent([cmd], prompt, resolved, timeout)
    return _op("codex_run", result["ok"], {
        "command": cmd,
        "output": result["output"],
        "error": result.get("error"),
        "returncode": result.get("returncode"),
    })


def _op_opencode(kwargs: dict) -> dict:
    """Run OpenCode (opencode) with a prompt."""
    prompt = (kwargs.get("prompt") or "").strip()
    path = (kwargs.get("path") or ".").strip()
    timeout = int(kwargs.get("timeout") or 300)
    if not prompt:
        return _op("opencode_run", False, None, "Provide a prompt (prompt=...).")
    resolved = _resolve_path(path)
    if not resolved.exists():
        return _op("opencode_run", False, None, f"Path not found: {path}")
    cmd = _which("opencode")
    if not cmd:
        return _op("opencode_run", False, None, "OpenCode (opencode) not installed. Install with: npm install -g @opencode/opencode")
    result = _run_external_agent([cmd], prompt, resolved, timeout)
    return _op("opencode_run", result["ok"], {
        "command": cmd,
        "output": result["output"],
        "error": result.get("error"),
        "returncode": result.get("returncode"),
    })


# ── task_decompose ─────────────────────────────────────────────────────

def _op_task_decompose(kwargs: dict) -> dict:
    goal = (kwargs.get("goal") or "").strip()
    if not goal:
        return _op("task_decompose", False, None, "Provide a goal (goal=...).")

    # Deterministic decomposition without an LLM call
    steps = []
    lowered = goal.lower()

    if any(w in lowered for w in ("create", "build", "make", "write")):
        steps.append("Explore the repository structure to understand the codebase")
        steps.append("Identify where the new code should live")
        steps.append("Create or modify the relevant files")
        steps.append("Run tests or verify the changes work")
        steps.append("Commit the changes if appropriate")
    elif any(w in lowered for w in ("fix", "debug", "repair", "patch")):
        steps.append("Reproduce the issue to understand the error")
        steps.append("Locate the relevant code in the repository")
        steps.append("Apply a fix to the affected code")
        steps.append("Verify the fix resolves the issue")
        steps.append("Run any existing tests to check for regressions")
    elif any(w in lowered for w in ("refactor", "clean", "improve")):
        steps.append("Review the current code to identify issues")
        steps.append("Plan the refactoring changes")
        steps.append("Apply the refactoring to the relevant files")
        steps.append("Verify behavior is unchanged")
        steps.append("Commit the improvements")
    else:
        steps.append("Understand the goal and explore the repository")
        steps.append("Break the goal into concrete file-level actions")
        steps.append("Execute each action step by step")
        steps.append("Verify the results")
        steps.append("Report completion")

    lines = []
    lines.append(f"Task decomposition: {goal}")
    lines.append("=" * 40)
    lines.append("")
    for i, step in enumerate(steps, 1):
        lines.append(f"{i}. {step}")
    lines.append("")

    return _op("task_decompose", True, {
        "goal": goal,
        "steps": steps,
        "content": "\n".join(lines),
    })


# ── self_correct ───────────────────────────────────────────────────────

def _op_self_correct(kwargs: dict) -> dict:
    path = (kwargs.get("path") or "").strip()
    error = (kwargs.get("error") or "").strip()
    if not path:
        return _op("self_correct", False, None, "Provide a file path (path=...).")
    if not error:
        return _op("self_correct", False, None, "Provide an error message (error=...).")

    resolved = _resolve_path(path)
    if not resolved.exists():
        return _op("self_correct", False, None, f"File not found: {path}")

    text = _read_text(resolved)
    lines = []
    lines.append(f"Self-correction for {path}")
    lines.append("=" * 40)
    lines.append("")
    lines.append("Error reported:")
    lines.append(_wrap(error, 80))
    lines.append("")
    lines.append("Suggested approach:")
    lines.append("1. Read the file to understand the current code")
    lines.append("2. Identify the lines related to the error")
    lines.append("3. Apply a targeted fix using str_replace")
    lines.append("4. Re-run the code to verify the fix")
    lines.append("")
    lines.append("File preview (first 30 lines):")
    preview_lines = text.splitlines()[:30]
    for i, line in enumerate(preview_lines, 1):
        lines.append(f"{i:4d}\t{line}")

    return _op("self_correct", True, {
        "path": str(resolved.relative_to(WORKSPACE_ROOT)),
        "error": error,
        "content": "\n".join(lines),
    })


# ── repo_map ───────────────────────────────────────────────────────────

def _op_repo_map(kwargs: dict) -> dict:
    path = (kwargs.get("path") or ".").strip()
    resolved = _resolve_path(path)
    if not resolved.exists():
        return _op("repo_map", False, None, f"Path not found: {path}")

    search_root = resolved if resolved.is_dir() else resolved.parent
    skip_dirs = {".git", "__pycache__", ".venv", "node_modules", "dist", "build"}
    skip_exts = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".zip", ".gz"}

    structure = []
    file_count = 0
    for f in sorted(search_root.rglob("*")):
        rel = f.relative_to(search_root)
        parts = rel.parts
        if any(p in skip_dirs for p in parts):
            continue
        if f.is_file() and f.suffix.lower() in skip_exts:
            continue
        if f.is_dir():
            structure.append("  " * len(parts) + rel.name + "/")
        else:
            structure.append("  " * (len(parts) - 1) + "├─ " + rel.name)
            file_count += 1
            if file_count >= 150:
                structure.append("  ... (truncated)")
                break

    content = "\n".join(structure) if structure else "(empty)"
    return _op("repo_map", True, {
        "path": str(resolved.relative_to(WORKSPACE_ROOT)),
        "structure": content,
        "file_count": file_count,
    })


# ── sources ────────────────────────────────────────────────────────────

def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "coding (Stella coding agent)",
        "dependencies": [],
        "operations": ["read_file", "write_file", "str_replace", "insert",
                       "grep_search", "glob", "list_dir", "run_shell",
                       "git_init", "git_status", "git_add", "git_commit",
                       "git_log", "claudecode_run", "codex_run", "opencode_run",
                       "task_decompose", "self_correct",
                       "repo_map", "sources"],
        "note": "Stella coding agent — read/write files, shell commands, code "
                "search, str_replace editing, git operations, task decomposition, "
                "and self-correction. Pure-Python, runs on desktop and Android.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "read_file": _op_read_file,
    "write_file": _op_write_file,
    "str_replace": _op_str_replace,
    "insert": _op_insert,
    "grep_search": _op_grep_search,
    "glob": _op_glob,
    "list_dir": _op_list_dir,
    "run_shell": _op_run_shell,
    "git_init": _op_git,
    "git_status": _op_git,
    "git_add": _op_git,
    "git_commit": _op_git,
    "git_log": _op_git,
    "claudecode_run": _op_claudecode,
    "codex_run": _op_codex,
    "opencode_run": _op_opencode,
    "task_decompose": _op_task_decompose,
    "self_correct": _op_self_correct,
    "repo_map": _op_repo_map,
}

_OPERATION_TITLES = {
    "sources": "Coding Skill Sources",
    "read_file": "Read File",
    "write_file": "Write File",
    "str_replace": "String Replace",
    "insert": "Insert Content",
    "grep_search": "Grep Search",
    "glob": "Glob Files",
    "list_dir": "List Directory",
    "run_shell": "Run Shell Command",
    "git_init": "Git Init",
    "git_status": "Git Status",
    "git_add": "Git Add",
    "git_commit": "Git Commit",
    "git_log": "Git Log",
    "claudecode_run": "Claude Code",
    "codex_run": "Codex",
    "opencode_run": "OpenCode",
    "task_decompose": "Task Decompose",
    "self_correct": "Self Correct",
    "repo_map": "Repo Map",
}


def execute(**kwargs) -> dict:
    """Run one coding operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Coding",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown coding operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Coding",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Coding",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Coding error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Coding"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
