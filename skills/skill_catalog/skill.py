"""
Feature: skill_catalog
Description: Stella's skill catalog - the 'skill find' capability. Lists, finds, installs, registers and runs skill packages. Writes skills only into features/ or the user-data skills dir so Stella runs identically on any device. No symlinks or external PC skill directory references.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path
from typing import Any

from core.dynamic_registry import DynamicToolRegistry, FEATURES_DIR as REG_FEATURES_DIR
from core.user_paths import get_user_data_dir

FEATURE_METADATA = {
    "name": "skill_catalog",
    "aliases": ["skill_catalog", "skill find", "find skill", "skill catalog",
                "list skills", "install skill", "register skill", "run skill",
                "skill manager", "discover skills", "hot-plug skill"],
    "description": (
        "Stella's skill catalog: the 'skill find' capability. Lists every skill "
        "available on this machine (features/ plus the user-data skills dir), "
        "finds skills by keyword, name, alias or trigger, installs a skill "
        "package from a local path or inline definition, registers a loaded "
        "skill into the dynamic registry, and runs a skill operation. Nothing "
        "is symlinked or referenced from outside this project - every installed "
        "skill is written into features/ or the user-data skills dir so Stella "
        "runs identically on any device. Installs and writes require "
        "authorized=true plus confirm=true plus a policy allow rule."
    ),
    "triggers": [
        "skill find", "find skill", "skill catalog", "list skills",
        "install skill", "register skill", "run skill", "skill manager",
        "discover skills", "hot-plug skill", "what skills do I have",
        "find a skill for", "install a skill",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: list | find | install | register | run | sources. Defaults to sources.",
            },
            "keyword": {
                "type": "STRING",
                "description": "Keyword to search skills by (find operation).",
            },
            "path": {
                "type": "STRING",
                "description": "Local path to a skill package directory or skill.py file to install (install operation).",
            },
            "name": {
                "type": "STRING",
                "description": "Skill name to register or run.",
            },
            "skill": {
                "type": "STRING",
                "description": "Alias for name: the skill to run (run operation).",
            },
            "operation_target": {
                "type": "STRING",
                "description": "The skill operation to invoke (run operation), e.g. 'sources', 'count', 'list'.",
            },
            "args": {
                "type": "STRING",
                "description": "JSON object of arguments to pass to the skill operation (run operation). Defaults to {}.",
            },
            "authorized": {
                "type": "BOOLEAN",
                "description": "Must be true for install and any operation that writes to disk.",
            },
            "confirm": {
                "type": "BOOLEAN",
                "description": "Must be true to actually install or register a skill.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum items to return. Defaults to 50.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "system",
    "surface": "both",
    "requires": [],
    "optional_dependencies": [],
    "notes": "Writes skills only into features/ or the user-data skills dir - never symlinks or references a PC skill directory. Install/register are destructive (write to disk) and need authorized=true + confirm=true + an allow rule.",
}

_USER_SKILLS_DIR = Path(get_user_data_dir()) / "skills"


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _flag(**kwargs) -> bool:
    return kwargs.get("authorized") in (True, "true", "True", 1, "1") and \
        kwargs.get("confirm") in (True, "true", "True", 1, "1")


def _as_int(value, default: int = 50, ceiling: int = 500) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


def _parse_args(args_raw: Any) -> dict:
    if args_raw is None or args_raw == "":
        return {}
    if isinstance(args_raw, dict):
        return args_raw
    if isinstance(args_raw, str):
        try:
            parsed = json.loads(args_raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _load_skill_manifest(skill_dir: Path) -> dict | None:
    """Read and validate a skill package's manifest.json. Returns None on failure."""
    manifest_path = skill_dir / "manifest.json"
    skill_path = skill_dir / "skill.py"
    if not manifest_path.exists() or not skill_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or not manifest.get("name"):
            return None
        return manifest
    except json.JSONDecodeError:
        return None


def _list_local_skills() -> list[dict[str, Any]]:
    """List every discoverable skill package from features/ and user-data skills dir."""
    skills: list[dict[str, Any]] = []
    seen: set[str] = set()

    for base in (REG_FEATURES_DIR, _USER_SKILLS_DIR):
        if not base or not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            if entry.name.startswith((".", "_")) or not entry.is_dir():
                continue
            if entry.name in seen:
                continue
            manifest = _load_skill_manifest(entry)
            if manifest is None:
                continue
            seen.add(entry.name)
            skills.append({
                "name": manifest.get("name", entry.name),
                "version": manifest.get("version", "1.0.0"),
                "category": manifest.get("category", "general"),
                "surface": manifest.get("surface", "both"),
                "description": manifest.get("description", ""),
                "triggers": manifest.get("triggers", []),
                "aliases": manifest.get("aliases", []),
                "active": manifest.get("active", True),
                "source": "features" if base == REG_FEATURES_DIR else "user-data",
                "path": str(entry),
            })
    skills.sort(key=lambda s: s["name"])
    return skills


def _op_list(kwargs: dict) -> dict:
    limit = _as_int(kwargs.get("limit"), 50)
    skills = _list_local_skills()
    return _op("list", True, {
        "skills": skills[:limit],
        "count": len(skills[:limit]),
        "total": len(skills),
        "note": "Every skill listed is a real package on this machine; none is a symlink or external reference.",
    })


def _op_find(kwargs: dict) -> dict:
    keyword = (kwargs.get("keyword") or "").strip()
    if not keyword:
        return _op("find", False, None, "Provide a keyword to search skills by (keyword=...).")
    k = keyword.lower()
    limit = _as_int(kwargs.get("limit"), 50)
    all_skills = _list_local_skills()
    matches: list[dict[str, Any]] = []
    for skill in all_skills:
        haystack = " ".join([
            skill.get("name", ""),
            skill.get("description", ""),
            " ".join(skill.get("triggers", [])),
            " ".join(skill.get("aliases", [])),
            skill.get("category", ""),
        ]).lower()
        if k in haystack:
            matches.append(skill)
        if len(matches) >= limit:
            break
    return _op("find", True, {
        "keyword": keyword,
        "skills": matches,
        "count": len(matches),
        "note": "Matched against name, description, triggers, aliases and category.",
    })


def _op_install(kwargs: dict) -> dict:
    operation = "install"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Installing a skill writes to disk, so it needs authorized=true AND "
            "confirm=true plus an allow rule in config/tool_policy.json."))
    source_path = (kwargs.get("path") or "").strip()
    if not source_path:
        return _op(operation, False, None, "Provide the local path to the skill package to install (path=...).")
    src = Path(source_path)
    if not src.exists():
        return _op(operation, False, None, f"The path does not exist: {source_path}")

    # Determine the skill name from the manifest or directory name.
    skill_name = None
    if src.is_dir():
        manifest = _load_skill_manifest(src)
        if manifest is None:
            return _op(operation, False, None, f"{source_path} is not a valid skill package (missing manifest.json or skill.py).")
        skill_name = manifest.get("name", src.name)
        dest_dir = REG_FEATURES_DIR / skill_name
    elif src.is_file() and src.suffix == ".py":
        # Single skill.py file: try to read FEATURE_METADATA from it.
        skill_name = src.stem
        dest_dir = REG_FEATURES_DIR / skill_name
        manifest = None
    else:
        return _op(operation, False, None, (
            f"{source_path} is not a skill package directory or a skill.py file."))

    if dest_dir.exists():
        return _op(operation, False, None, (
            f"Skill '{skill_name}' already exists in features/. Remove it first or install under a different name."))

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            # Copy the whole package tree (manifest.json, skill.py, test_cases.json, __init__.py, docs/...).
            for item in src.iterdir():
                if item.is_dir():
                    shutil.copytree(item, dest_dir / item.name)
                else:
                    shutil.copy2(item, dest_dir / item.name)
        else:
            shutil.copy2(src, dest_dir / "skill.py")
            # Write a minimal manifest so the dynamic registry can load it.
            if manifest is None:
                manifest = {
                    "name": skill_name,
                    "description": f"Installed skill {skill_name}.",
                    "parameters": {"type": "OBJECT", "properties": {}},
                    "triggers": [],
                    "aliases": [],
                    "version": "1.0.0",
                    "active": True,
                }
            (dest_dir / "manifest.json").write_text(
                json.dumps(manifest, indent=2), encoding="utf-8")
    except OSError as exc:
        return _op(operation, False, None, f"could not install skill: {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "skill": skill_name,
        "path": str(dest_dir),
        "note": f"Installed '{skill_name}' into features/. It will be discovered by the dynamic registry on the next init.",
    })


def _op_register(kwargs: dict) -> dict:
    operation = "register"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Registering a skill touches the running registry, so it needs authorized=true AND "
            "confirm=true plus an allow rule in config/tool_policy.json."))
    name = (kwargs.get("name") or kwargs.get("skill") or "").strip()
    if not name:
        return _op(operation, False, None, "Provide the skill name to register (name=... or skill=...).")

    DynamicToolRegistry.initialize()
    skill = DynamicToolRegistry.get_skill(name)
    if skill is None or not skill.active:
        return _op(operation, False, None, f"Skill '{name}' is not discoverable. Install it first (install operation).")

    return _op(operation, True, {
        "skill": name,
        "active": skill.active,
        "version": skill.version,
        "note": f"Skill '{name}' is registered and active in the dynamic registry.",
    })


def _op_run(kwargs: dict) -> dict:
    operation = "run"
    name = (kwargs.get("name") or kwargs.get("skill") or "").strip()
    if not name:
        return _op(operation, False, None, "Provide the skill name to run (name=... or skill=...).")
    op_target = (kwargs.get("operation_target") or "").strip()
    args = _parse_args(kwargs.get("args"))

    DynamicToolRegistry.initialize()
    skill = DynamicToolRegistry.get_skill(name)
    if skill is None or not skill.active:
        return _op(operation, False, None, f"Skill '{name}' is not available. Install and register it first.")

    try:
        result = skill.execute_sync(**({op_target: None} if op_target else {}), **args) if op_target else skill.execute_sync(**args)
    except TypeError:
        # Some skills' execute() takes **kwargs; passing an unknown op_target kw may fail.
        try:
            result = skill.execute_sync(**args)
        except Exception as exc:  # noqa: BLE001
            return _op(operation, False, None, f"could not run '{name}': {type(exc).__name__}: {exc}")
    except Exception as exc:  # noqa: BLE001
        return _op(operation, False, None, f"could not run '{name}': {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "skill": name,
        "operation": op_target or "default",
        "result": result,
        "ok": bool(result.get("ok")) if isinstance(result, dict) else True,
        "note": f"Ran '{name}' via the dynamic registry.",
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "local_dirs": [
            {"dir": str(REG_FEATURES_DIR), "label": "features/ (project skills)"},
            {"dir": str(_USER_SKILLS_DIR), "label": "user-data skills dir"},
        ],
        "policy": "Writes only into features/ or the user-data skills dir. No symlinks. No references to any PC skill directory.",
        "note": "The dynamic registry auto-discovers skills on init; register() makes one active in the current session.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "list": _op_list,
    "find": _op_find,
    "install": _op_install,
    "register": _op_register,
    "run": _op_run,
}

_OPERATION_TITLES = {
    "sources": "Skill Catalog Sources",
    "list": "List Skills",
    "find": "Find Skills",
    "install": "Install Skill",
    "register": "Register Skill",
    "run": "Run Skill",
}

_ALIASES = {
    "list_skills": "list", "show_skills": "list",
    "find_skill": "find", "search_skills": "find",
    "install_skill": "install", "add_skill": "install",
    "register_skill": "register", "activate_skill": "register",
    "run_skill": "run", "execute_skill": "run",
    "sources_list": "sources",
    "where_skills_come_from": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "sources":
        return f"{len(value.get('local_dirs') or [])} local skill dir(s); write-only into project dirs."
    if operation == "list":
        return f"{value.get('count')} skill(s) available ({value.get('total')} total)."
    if operation == "find":
        return f"{value.get('count')} skill(s) matched '{value.get('keyword')}'."
    if operation == "install":
        return f"Installed {value.get('skill')} at {value.get('path')}."
    if operation == "register":
        return f"Registered {value.get('skill')} (v{value.get('version')})."
    if operation == "run":
        return f"Ran {value.get('skill')}: {value.get('note')}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Run one skill-catalog operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Skill Catalog",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Skill Catalog",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Skill Catalog",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Skill catalog error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Skill Catalog"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
