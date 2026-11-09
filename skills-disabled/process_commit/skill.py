"""
process_commit — Fetch a GitHub commit and scan patches for secrets.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_scan(kwargs: dict) -> dict:
    repo = (kwargs.get("repo") or "").strip()
    sha = (kwargs.get("sha") or "").strip()
    if not repo or not sha:
        return _op("scan", False, None, "Missing repo or sha.")
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Authorization": f"token {token}"} if token else {}
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo}/commits/{sha}",
            headers=headers,
            timeout=20,
        )
        r.raise_for_status()
        commit = r.json()
        patches = "".join(f.get("patch", "") for f in commit.get("files", []))
        secrets = re.findall(r"(?i)(password|api_key|secret)\s*[:=]\s*\S+", patches)
        return _op("scan", True, {
            "repo": repo,
            "sha": sha,
            "commit_message": commit.get("commit", {}).get("message"),
            "secrets_found": len(secrets),
            "samples": secrets[:5],
        })
    except Exception as exc:
        return _op("scan", False, None, f"Commit scan failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["api.github.com"],
        "content": "GitHub commit scanning via GitHub API (GITHUB_TOKEN optional).",
    })


_OPERATIONS = {
    "scan": _op_scan,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "scan": "Commit Scan",
    "sources": "Commit Scan Sources",
}

_ALIASES = {
    "process_commit": "scan",
    "scan_commit": "scan",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "scan":
        return f"Commit '{value.get('commit_message')}' in {value.get('repo')} — {value.get('secrets_found')} secret(s) found."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Fetch a GitHub commit and scan patches for secrets."""
    operation = (kwargs.get("operation") or "scan").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Process Commit",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Process Commit",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Process Commit",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Commit error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Process Commit"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))