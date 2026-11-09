from __future__ import annotations
from typing import Any, Dict
import os, requests, re

FEATURE_METADATA = {
    "name": "process_commit",
    "aliases": ["commit scan"],
    "description": "Fetch a GitHub commit and scan patches for secrets.",
    "triggers": ["process commit", "scan commit"],
    "parameters": {"type":"OBJECT","properties":{"repo":{"type":"STRING"},"sha":{"type":"STRING"}},"required":["repo","sha"]}
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    repo = params.get("repo")
    sha = params.get("sha")
    if not repo or not sha:
        return {"ok": False, "error": "Missing repo or sha"}
    token = os.getenv("GITHUB_TOKEN","")
    headers = {"Authorization": f"token {token}"} if token else {}
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/commits/{sha}", headers=headers, timeout=20)
        r.raise_for_status()
        commit = r.json()
        patches = "".join([f.get("patch","") for f in commit.get("files",[])])
        secrets = re.findall(r'(?i)(password|api_key|secret)\s*[:=]\s*\S+', patches)
        return {"ok": True, "commit": commit.get("commit",{}).get("message"), "secrets_found": len(secrets), "samples": secrets[:5]}
    except Exception as e:
        return {"ok": False, "error": str(e)}