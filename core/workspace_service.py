"""Workspace & thread service over HTTP API.

Provides CRUD for workspaces and threads against a configurable API base URL.
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

API_BASE = os.getenv("STELLA_API_BASE", "http://localhost:8000")


def _request(method: str, path: str, data: Optional[Dict[str, Any]] = None) -> Any:
    url = API_BASE.rstrip("/") + path
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode(errors='replace')}")
    except Exception as e:
        raise RuntimeError(f"{method} {path} failed: {e}")


def list_workspaces() -> List[Dict[str, Any]]:
    return _request("GET", "/workspaces") or []


def get_workspace(workspace_id: str) -> Dict[str, Any]:
    return _request("GET", f"/workspaces/{workspace_id}")


def create_workspace(name: str, **extra: Any) -> Dict[str, Any]:
    payload = {"name": name, **extra}
    return _request("POST", "/workspaces", payload)


def update_workspace(workspace_id: str, **fields: Any) -> Dict[str, Any]:
    return _request("PATCH", f"/workspaces/{workspace_id}", fields)


def delete_workspace(workspace_id: str) -> Any:
    return _request("DELETE", f"/workspaces/{workspace_id}")


def list_threads(workspace_id: str) -> List[Dict[str, Any]]:
    return _request("GET", f"/workspaces/{workspace_id}/threads") or []


def get_thread(workspace_id: str, thread_id: str) -> Dict[str, Any]:
    return _request("GET", f"/workspaces/{workspace_id}/threads/{thread_id}")


def create_thread(workspace_id: str, title: str = "", **extra: Any) -> Dict[str, Any]:
    payload = {"title": title, **extra}
    return _request("POST", f"/workspaces/{workspace_id}/threads", payload)


def update_thread(workspace_id: str, thread_id: str, **fields: Any) -> Dict[str, Any]:
    return _request("PATCH", f"/workspaces/{workspace_id}/threads/{thread_id}", fields)



def delete_thread(workspace_id: str, thread_id: str) -> Any:
    return _request("DELETE", f"/workspaces/{workspace_id}/threads/{thread_id}")