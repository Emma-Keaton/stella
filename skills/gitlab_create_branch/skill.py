from __future__ import annotations
from typing import Any, Dict
import os, requests

FEATURE_METADATA = {
    "name": "gitlab_create_branch",
    "aliases": ["create branch"],
    "description": "Create a new branch in GitLab or GitHub.",
    "triggers": ["create branch"],
    "parameters": {"type":"OBJECT","properties":{"provider":{"type":"STRING","default":"gitlab"},"repo":{"type":"STRING"},"branch":{"type":"STRING"},"ref":{"type":"STRING"}},"required":["repo","branch","ref"]}
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    provider = str(params.get("provider","gitlab")).lower()
    repo = params.get("repo")
    branch = params.get("branch")
    ref = params.get("ref")
    if not repo or not branch or not ref:
        return {"ok": False, "error": "Missing repo/branch/ref"}
    token = os.getenv("GITLAB_TOKEN") if provider=="gitlab" else os.getenv("GITHUB_TOKEN")
    if not token:
        return {"ok": False, "error": f"{provider.upper()}_TOKEN not set", "auth_tier":"keyed"}
    try:
        if provider=="gitlab":
            # repo format: project-id or owner/repo
            url = f"https://gitlab.com/api/v4/projects/{repo}/repository/branches"
            r = requests.post(url, headers={"PRIVATE-TOKEN": token}, json={"branch": branch, "ref": ref}, timeout=20)
        else:
            owner, name = repo.split("/")
            url = f"https://api.github.com/repos/{owner}/{name}/git/refs"
            r = requests.post(url, headers={"Authorization": f"token {token}"}, json={"ref": f"refs/heads/{branch}", "sha": ref}, timeout=20)
        r.raise_for_status()
        return {"ok": True, "provider": provider, "repo": repo, "branch": branch, "ref": ref}
    except Exception as e:
        return {"ok": False, "error": str(e)}