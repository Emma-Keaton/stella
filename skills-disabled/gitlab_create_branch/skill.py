"""
gitlab_create_branch — Create a new branch in GitLab or GitHub via REST API.
"""

from __future__ import annotations

from typing import Any, Dict

import os
import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_create_branch(kwargs: dict) -> dict:
    provider = str(kwargs.get("provider", "gitlab")).strip().lower()
    repo = (kwargs.get("repo") or "").strip()
    branch = (kwargs.get("branch") or "").strip()
    ref = (kwargs.get("ref") or "").strip()
    if not repo or not branch or not ref:
        return _op("create_branch", False, None, "Missing repo/branch/ref.")
    token = os.getenv("GITLAB_TOKEN") if provider == "gitlab" else os.getenv("GITHUB_TOKEN")
    if not token:
        return _op("create_branch", False, None, f"{provider.upper()}_TOKEN not set.")
    try:
        if provider == "gitlab":
            url = f"https://gitlab.com/api/v4/projects/{repo}/repository/branches"
            r = requests.post(
                url,
                headers={"PRIVATE-TOKEN": token},
                json={"branch": branch, "ref": ref},
                timeout=20,
            )
        else:
            if "/" not in repo:
                return _op("create_branch", False, None, "GitHub repo must be 'owner/name'.")
            owner, name = repo.split("/", 1)
            url = f"https://api.github.com/repos/{owner}/{name}/git/refs"
            r = requests.post(
                url,
                headers={"Authorization": f"token {token}"},
                json={"ref": f"refs/heads/{branch}", "sha": ref},
                timeout=20,
            )
        r.raise_for_status()
        return _op("create_branch", True, {
            "provider": provider,
            "repo": repo,
            "branch": branch,
            "ref": ref,
        })
    except Exception as exc:
        return _op("create_branch", False, None, f"Branch creation failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["gitlab.com", "github.com"],
        "content": "Branch creation via GitLab API (GITLAB_TOKEN) or GitHub API (GITHUB_TOKEN).",
    })


_OPERATIONS = {
    "create_branch": _op_create_branch,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "create_branch": "Create Branch",
    "sources": "Git Sources",
}

_ALIASES = {
    "create_branch": "create_branch",
    "new_branch": "create_branch",
    "branch": "create_branch",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "create_branch":
        return f"Created branch '{value.get('branch')}' in {value.get('provider')} repo '{value.get('repo')}' from {value.get('ref')}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Create a new branch in GitLab or GitHub via REST API."""
    operation = (kwargs.get("operation") or "create_branch").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "GitLab Create Branch",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "GitLab Create Branch",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "GitLab Create Branch",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Git error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "GitLab Create Branch"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="create_branch", provider="github", repo="owner/repo", branch="feature-x", ref="main"))