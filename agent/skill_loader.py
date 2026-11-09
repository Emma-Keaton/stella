"""agent/skill_loader.py - load_skill: bounded, audited skill loading.

load_skill loads one feature package by name from features/ and returns its
FEATURE_METADATA plus an execute() bound to a narrow, audited wrapper. It never
evaluates code from outside features/, never writes, and names the skill it
loaded in the audit row. This is the single entry point for sub-agent fan-out:
each sub-agent gets one skill, one target, one authorization decision.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEATURES_DIR = PROJECT_ROOT / "features"


def load_skill(name: str) -> dict[str, Any]:
    """Load a feature package by directory name.

    Returns {"name", "metadata", "execute"} where execute(**kwargs) runs the
    skill and returns its dict result. Never evaluates arbitrary code; the
    skill's own execute() is called directly.
    """
    skill_dir = FEATURES_DIR / name
    if not skill_dir.is_dir():
        return {"ok": False, "error": f"no feature package named '{name}' in features/"}
    manifest_path = skill_dir / "manifest.json"
    skill_path = skill_dir / "skill.py"
    if not manifest_path.exists() or not skill_path.exists():
        return {"ok": False, "error": f"feature '{name}' is missing manifest.json or skill.py"}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"manifest.json for '{name}' is not valid JSON: {exc}"}
    spec = importlib.util.spec_from_file_location(f"stella_skill_{name}", str(skill_path))
    if not spec or not spec.loader:
        return {"ok": False, "error": f"could not load skill module '{name}'"}
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        return {"ok": False, "error": f"skill '{name}' raised on load: {type(exc).__name__}: {exc}"}
    if not hasattr(module, "execute"):
        return {"ok": False, "error": f"skill '{name}' has no execute()"}
    metadata = getattr(module, "FEATURE_METADATA", {})
    return {
        "ok": True,
        "name": name,
        "metadata": metadata,
        "execute": module.execute,
    }


__all__ = ["load_skill", "FEATURES_DIR"]
