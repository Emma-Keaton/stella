"""core/error_reporter.py - Plain-English error reporting and self-improvement.

Every user-facing error is translated from a raw exception into a clear,
plain-English message the user can act on. The module also drives the
self-improvement workflow:

  1. Translate the raw error into plain English + what it means.
  2. "Fix it yourself" -> Stella synthesises an improvement to its codebase
     so it can handle the task better next time.
  3. If the local LLM cannot handle the task, offer alternatives and tell
     the user they can ask the admin to fix it globally.
  4. "Report to admin" -> the user pushes the error into Stella's GitHub
     repo issues. Stella (admin's agent) sees the issue, fixes it, and
     alerts the admin, who instructs it to push the update.
"""

from __future__ import annotations

import json
import platform
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).resolve().parent.parent
FEEDBACK_DIR = REPO / "feedback"
BUG_REPORTS_FILE = FEEDBACK_DIR / "bug_reports.json"
CHANGELOG_FILE = FEEDBACK_DIR / "changelog.json"

PLATFORM_NAMES = {
    "Windows": "Windows",
    "Darwin": "macOS",
    "Linux": "Linux",
    "Java": "Android",
    "OS/2": "OS/2",
    "OpenVMS": "OpenVMS",
}

GITHUB_REPO = "Emma-Keaton/stella"


def _ensure_feedback_dir() -> None:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    if not BUG_REPORTS_FILE.exists():
        BUG_REPORTS_FILE.write_text(json.dumps([], indent=2), encoding="utf-8")
    if not CHANGELOG_FILE.exists():
        CHANGELOG_FILE.write_text(json.dumps({"entries": []}, indent=2), encoding="utf-8")


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, data: Any) -> None:
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_platform_name() -> str:
    return PLATFORM_NAMES.get(sys.platform, sys.platform)


def _read_version() -> str:
    for p in (REPO / "version.txt",):
        try:
            if p.exists():
                return p.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            continue
    return "0.0.0"


def get_device_specs() -> dict[str, Any]:
    """Lightweight device profile for bug reports."""
    specs: dict[str, Any] = {
        "os": get_platform_name(),
        "arch": platform.machine(),
        "python": sys.version.split()[0],
        "app_version": _read_version(),
        "repo": GITHUB_REPO,
        "edition": "public",
    }
    try:
        import psutil
        specs["ram_total_gb"] = round(psutil.virtual_memory().total / 1024 ** 3, 2)
        specs["ram_free_gb"] = round(psutil.virtual_memory().available / 1024 ** 3, 2)
        specs["disk_free_gb"] = round(
            psutil.disk_usage(str(Path.home())).free / 1024 ** 3, 2
        )
    except Exception:
        try:
            specs["disk_free_gb"] = round(
                shutil.disk_usage(str(Path.home())).free / 1024 ** 3, 2
            )
        except Exception:
            pass
    return specs


def translate_error(
    error: Exception,
    context: str = "",
    max_trace_lines: int = 3,
) -> dict[str, Any]:
    """Translate a raw exception into plain-English + structured data."""
    etype = type(error).__name__
    message = str(error) if error else "(no error message)"
    plain = _plain_english(message, etype)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": etype,
        "message": message,
        "plain_to_user": plain,
        "context": context,
        "stack_trace": traceback.format_exc()[-max_trace_lines * 200:],
        "device_specs": get_device_specs(),
        "full_trace": traceback.format_exc(),
    }


def _plain_english(message: str, etype: str) -> str:
    """Map a raw exception to a plain-English description."""
    low = message.lower()
    if not message:
        return "Stella ran into an unexpected internal problem."
    if "no such file" in low or "does not exist" in low or "enoent" in low:
        return ("Stella could not find the file or folder it was looking for. "
                "Check the path is correct and try again.")
    if "permission denied" in low or "permissionerror" in low:
        return ("Stella does not have permission to do that. "
                "Give it permission or try a different action.")
    if "timeout" in low or "timed out" in low or "timeouterror" in low:
        return ("Stella waited too long for a response. "
                "The service may be slow or your internet connection is unstable.")
    if "connection" in low or "connectionerror" in low or "refused" in low:
        return ("Stella could not reach a service. "
                "Check the service is running and your network is working.")
    if "invalid" in low or "valueerror" in low or "invalidargument" in low:
        return ("Stella received a value it could not understand. "
                "Try a different input.")
    if "json" in low or "jsonerror" in low:
        return ("Stella found a data format it could not read. "
                "This usually means a file is corrupted or a response was cut off.")
    if "model" in low or "no model" in low:
        return ("Stella could not load the AI model it needs. "
                "Make sure the model is installed and the endpoint is correct.")
    if "tool" in low or "not supported" in low:
        return ("Stella tried to use a tool or action it does not support. "
                "Check the tool name and try a simpler command.")
    if "authentication" in low or "autherror" in low or "401" in low:
        return ("Stella could not log in to a service. "
                "Check your API key or login details.")
    if "forbidden" in low or "403" in low:
        return ("Stella is not allowed to do this. "
                "Check your account permissions and try again.")
    if "rate" in low or "429" in low:
        return ("Stella was asked to do too many things too fast. "
                "Wait a moment and try again.")
    if "http" in low or "500" in low or "502" in low or "503" in low:
        return ("The service Stella contacted did not respond normally. "
                "It may be down for maintenance or temporarily unreachable.")
    if "filesystem" in low or "ioerror" in low or "filenotfound" in low:
        return ("Stella had trouble reading or writing a file. "
                "Check the file is not in use and try again.")
    if "memory" in low or "out of memory" in low:
        return ("Stella ran out of memory. "
                "Close other apps to free up RAM and try again.")
    return f"Stella encountered a problem: {message}"


class ErrorReporter:
    """Reports errors to the user and optionally to the admin via GitHub issues."""

    def __init__(self) -> None:
        _ensure_feedback_dir()

    def report(
        self,
        error: Exception,
        context: str = "",
        *,
        ask_user: bool = True,
        user_mutable: bool = False,
    ) -> dict[str, Any]:
        """Report an error. Returns the translated error dict."""
        translated = translate_error(error, context)
        if ask_user and user_mutable:
            self._auto_report(translated)
        return translated

    def _auto_report(self, translated: dict[str, Any]) -> None:
        """Record a bug report locally (best effort, no network)."""
        reports = self._load_bug_reports()
        report = {
            **translated,
            "priority": "medium",
            "status": "open",
            "resolved": False,
            "global_fix": False,
            "created_by": "user",
        }
        reports.append(report)
        self._save_bug_reports(reports)

    def suggest_improvement(self, error: Exception, context: str = "") -> dict[str, Any]:
        """Prompt Stella to update and improve its codebase."""
        translated = translate_error(error, context)
        return {
            "decision": "synthesize_improvement",
            "plain_message": translated["plain_to_user"],
            "error_type": translated["type"],
            "error_message": translated["message"],
            "suggestion": ("Stella will analyse the issue and update its code "
                           "so it can handle this task better next time."),
            "alternatives": self._alternatives_for(translated),
            "global_fix": ("If your local AI cannot handle this, ask the admin "
                           "to fix it globally. The fix will be pushed in the "
                           "next update."),
            "translated": translated,
        }

    def _alternatives_for(self, translated: dict[str, Any]) -> list[str]:
        """Suggest alternatives when the local LLM cannot handle the task."""
        low = translated["message"].lower()
        alternatives = []
        if "model" in low or "local ai" in low or "load" in low:
            alternatives.append(
                "Switch to a cloud AI provider: open Settings, change the "
                "default AI provider, and try again."
            )
            alternatives.append(
                "Use a different, smaller local model that fits your device."
            )
        if "timeout" in low or "slow" in low:
            alternatives.append(
                "Change the timeout in Settings > Advanced so Stella waits "
                "longer for a response."
            )
            alternatives.append(
                "Use a cloud provider for faster responses."
            )
        if "tool" in low or "not supported" in low:
            alternatives.append(
                "Try a different tool or action for the same goal."
            )
        if not alternatives:
            alternatives.append(
                "Ask the admin to fix this globally. Open the bug report "
                "and mark it as 'needs global fix'."
            )
        return alternatives

    def _load_bug_reports(self) -> list[dict]:
        return _load_json(BUG_REPORTS_FILE, [])

    def _save_bug_reports(self, reports: list[dict]) -> None:
        _save_json(BUG_REPORTS_FILE, reports)

    def _load_changelog(self) -> dict[str, Any]:
        return _load_json(CHANGELOG_FILE, {"entries": []})

    def _save_changelog(self, data: dict[str, Any]) -> None:
        _save_json(CHANGELOG_FILE, data)

    def submit_issue(self, translated: dict[str, Any],
                     priority: str = "medium") -> str:
        """Record a bug report and return the GitHub issue URL the user can open."""
        reports = self._load_bug_reports()
        report = {
            **translated,
            "priority": priority,
            "status": "open",
            "resolved": False,
            "global_fix": False,
            "created_by": "user",
        }
        reports.append(report)
        self._save_bug_reports(reports)

        import urllib.parse
        title = urllib.parse.quote(f"{report['type']}: {report['message'][:60]}")
        body = urllib.parse.quote(
            f"**Error:** {report['message']}\n\n"
            f"**Plain English:** {report['plain_to_user']}\n\n"
            f"**Context:** {report['context']}\n\n"
            f"**Device:** {report['device_specs']}\n\n"
            f"**Trace:**\n```\n{report['full_trace']}\n```\n"
        )
        return (f"https://github.com/{GITHUB_REPO}/issues/new"
                f"?title={title}&body={body}")

    def admin_fixed(self, issue_id: str, fix_details: str) -> dict[str, Any]:
        """Stella admin reports that the issue was fixed and an update pushed."""
        reports = self._load_bug_reports()
        for r in reports:
            if (r.get("type") == issue_id.split(":")[0]
                    or "error" in r.get("type", "").lower()):
                r["status"] = "resolved"
                r["resolved"] = True
                r["fix_details"] = fix_details
                r["global_fix"] = True
                self._save_bug_reports(reports)
                break
        return {"ok": True, "message": "Issue marked as fixed. Update pushed."}


def create_bug_report(error: Exception, context: str = "") -> dict[str, Any]:
    return translate_error(error, context)


def push_to_admin(error: Exception, context: str = "") -> dict[str, Any]:
    translated = translate_error(error, context)
    return {
        "decision": "admin_fix",
        "plain_message": translated["plain_to_user"],
        "message": ("Ask the admin to fix this globally. The fix will be "
                    "bundled into the next update."),
        "translated": translated,
    }


def suggest_improvement(error: Exception, context: str = "") -> dict[str, Any]:
    reporter = ErrorReporter()
    return reporter.suggest_improvement(error, context)
