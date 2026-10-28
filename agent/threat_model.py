"""agent/threat_model.py - threat model for a scoped engagement.

A threat model lists assets, threats, and the mitigations that apply to each.
It is a planning document, not a verdict: every threat carries a confidence
and a source, and nothing is asserted without evidence. The model is stored as
JSON under the user data dir so it survives restarts.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from core.user_paths import get_user_data_dir


THREAT_MODEL_PATH = Path(get_user_data_dir()) / "config" / "threat_model.json"


def _load() -> dict[str, Any]:
    try:
        if not THREAT_MODEL_PATH.exists():
            return {"assets": [], "threats": [], "mitigations": [], "version": 1}
        data = json.loads(THREAT_MODEL_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"assets": [], "threats": [], "mitigations": [], "version": 1}
    except Exception:
        return {"assets": [], "threats": [], "mitigations": [], "version": 1}


def _save(data: dict[str, Any]) -> None:
    try:
        THREAT_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        THREAT_MODEL_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"could not write threat model: {exc}")


def add_asset(name: str, kind: str, owner: str = "") -> dict[str, Any]:
    data = _load()
    asset = {"name": name, "kind": kind, "owner": owner, "added_at": time.time()}
    data.setdefault("assets", []).append(asset)
    _save(data)
    return asset


def add_threat(asset: str, threat: str, confidence: str = "low",
               source: str = "") -> dict[str, Any]:
    data = _load()
    entry = {
        "asset": asset,
        "threat": threat,
        "confidence": confidence,
        "source": source,
        "added_at": time.time(),
    }
    data.setdefault("threats", []).append(entry)
    _save(data)
    return entry


def add_mitigation(threat: str, mitigation: str) -> dict[str, Any]:
    data = _load()
    entry = {"threat": threat, "mitigation": mitigation, "added_at": time.time()}
    data.setdefault("mitigations", []).append(entry)
    _save(data)
    return entry


def get_model() -> dict[str, Any]:
    return _load()


def summary() -> str:
    data = _load()
    return (f"assets={len(data.get('assets', []))} "
            f"threats={len(data.get('threats', []))} "
            f"mitigations={len(data.get('mitigations', []))}")


__all__ = ["add_asset", "add_threat", "add_mitigation", "get_model", "summary",
           "THREAT_MODEL_PATH"]
