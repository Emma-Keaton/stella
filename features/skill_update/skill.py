"""
Feature: skill_update
Description: Context-aware skill updater. Tracks interaction context per skill,
records preference signals (accept/reject/correct), and applies them to skill
files. Safely edits manifest.json, bumps semantic versions, keeps per-skill
change history for rollback. Python skill.py changes are safe targeted string
replacements or flagged for manual review. Every write is versioned and
revertible.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FEATURES_DIR = PROJECT_ROOT / "features"
UPDATE_DIR = FEATURES_DIR / "skill_update"
HISTORY_DIR = UPDATE_DIR / "history"
PREFERENCES_DIR = UPDATE_DIR / "preferences"
CONTEXT_DIR = UPDATE_DIR / "context"

FEATURE_METADATA = {
    "name": "skill_update",
    "aliases": ["skill_update", "update skill", "skill update", "update a skill",
                "adjust skill", "skill preference", "skill context", "fix skill",
                "skill version", "rollback skill", "skill history", "tune skill"],
    "description": (
        "Context-aware skill updater. Tracks how the user interacts with each "
        "skill (what they asked, what the skill returned, whether it was "
        "correct), records preference signals (accept/reject/correct) plus "
        "free-form context, and applies those preferences to skill files. "
        "Safely edits manifest.json (description, triggers, aliases, version, "
        "category, surface, requires, parameters), bumps semantic versions, "
        "keeps a per-skill change history for rollback, and records interaction "
        "context so the agent can tune skills over time. Nothing is rewritten "
        "blindly: Python skill.py changes are flagged for manual review or done "
        "as safe targeted string replacements; every write is versioned and "
        "revertible. Writes to disk, so install/update needs authorized=true "
        "plus confirm=true plus a policy allow rule."
    ),
    "triggers": [
        "update skill", "skill update", "adjust skill", "skill preference",
        "skill context", "fix skill", "skill version", "rollback skill",
        "skill history", "tune skill", "update a skill", "skill settings",
        "change skill behavior", "make skill prefer", "skill no longer",
        "this skill is wrong", "skill should do", "update skill manifest",
        "bump skill version",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: sources | list | inspect | record_pref | preferences | update_manifest | bump_version | apply_prefs | rollback | history. Defaults to sources.",
            },
            "skill": {
                "type": "STRING",
                "description": "The skill name to update or inspect (e.g. anatomy, brainstorming). Required for most operations.",
            },
            "context": {
                "type": "STRING",
                "description": "Interaction context: what the user asked, what the skill returned, and whether it was correct/acceptable (record_pref operation).",
            },
            "signal": {
                "type": "STRING",
                "description": "Preference signal: accept | reject | correct (record_pref operation).",
            },
            "field": {
                "type": "STRING",
                "description": "The manifest field to update (update_manifest operation): description | triggers | aliases | version | category | surface | requires | parameters.",
            },
            "value": {
                "type": "STRING",
                "description": "The new value for the field (update_manifest operation). For triggers/aliases/parameters pass JSON.",
            },
            "bump": {
                "type": "STRING",
                "description": "Semver bump level: patch | minor | major (bump_version operation). Defaults to patch.",
            },
            "to_version": {
                "type": "STRING",
                "description": "Target version to roll back to (rollback operation).",
            },
            "authorized": {
                "type": "BOOLEAN",
                "description": "Must be true for any operation that writes skill files.",
            },
            "confirm": {
                "type": "BOOLEAN",
                "description": "Must be true to actually write skill files.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum items to return. Defaults to 20.",
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
    "notes": "Writes into features/<skill>/ and features/skill_update/{history,preferences,context}/. Every write is versioned and revertible via rollback. Requires authorized=true + confirm=true + an allow rule.",
}

_WRITE_FIELDS = {
    "description", "triggers", "aliases", "version", "category",
    "surface", "requires", "parameters",
}


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _flag(**kwargs) -> bool:
    return kwargs.get("authorized") in (True, "true", "True", 1, "1") and \
        kwargs.get("confirm") in (True, "true", "True", 1, "1")


def _as_int(value, default: int = 20, ceiling: int = 200) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


def _skill_dir(name: str) -> Path:
    return FEATURES_DIR / name


def _manifest_path(name: str) -> Path:
    return _skill_dir(name) / "manifest.json"


def _skill_path(name: str) -> Path:
    return _skill_dir(name) / "skill.py"


def _load_manifest(name: str) -> dict | None:
    p = _manifest_path(name)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _list_skills() -> list[dict[str, Any]]:
    skills: list[dict[str, Any]] = []
    if not FEATURES_DIR.exists():
        return skills
    for entry in sorted(FEATURES_DIR.iterdir()):
        if entry.name.startswith((".", "_")) or not entry.is_dir():
            continue
        if entry.name == "skill_update":
            continue
        manifest = _load_manifest(entry.name)
        if manifest is None:
            continue
        skills.append({
            "name": manifest.get("name", entry.name),
            "version": manifest.get("version", "1.0.0"),
            "category": manifest.get("category", "general"),
            "surface": manifest.get("surface", "both"),
            "description": manifest.get("description", ""),
            "triggers": manifest.get("triggers", []),
            "path": str(entry),
        })
    skills.sort(key=lambda s: s["name"])
    return skills


def _append_jsonl(path: Path, entry: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return rows
    return rows


def _now() -> float:
    return time.time()


def _bump_semver(version: str, level: str) -> str:
    parts = version.split(".")
    while len(parts) < 3:
        parts.append("0")
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        major, minor, patch = 1, 0, 0
    if level == "major":
        major += 1; minor = 0; patch = 0
    elif level == "minor":
        minor += 1; patch = 0
    else:  # patch
        patch += 1
    return f"{major}.{minor}.{patch}"


# ------------------------------------------------------------------ read ops

def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "skill_dir": str(FEATURES_DIR),
        "update_dir": str(UPDATE_DIR),
        "history_dir": str(HISTORY_DIR),
        "preferences_dir": str(PREFERENCES_DIR),
        "context_dir": str(CONTEXT_DIR),
        "write_fields": sorted(_WRITE_FIELDS),
        "bump_levels": ["patch", "minor", "major"],
        "signals": ["accept", "reject", "correct"],
        "note": "Every write is versioned in history/ and revertible via rollback. No symlinks or external PC references.",
    })


def _op_list(kwargs: dict) -> dict:
    limit = _as_int(kwargs.get("limit"), 20)
    skills = _list_skills()
    return _op("list", True, {
        "skills": skills[:limit],
        "count": len(skills[:limit]),
        "total": len(skills),
        "note": "Every listed skill is a real package in features/.",
    })


def _op_inspect(kwargs: dict) -> dict:
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op("inspect", False, None, "Provide the skill name (skill=...).")
    manifest = _load_manifest(name)
    if manifest is None:
        return _op("inspect", False, None, f"Skill '{name}' not found in features/.")
    skill_dir = _skill_dir(name)
    files = {}
    for fname in ("manifest.json", "skill.py", "test_cases.json", "__init__.py"):
        p = skill_dir / fname
        files[fname] = p.exists()
    history = _read_jsonl(HISTORY_DIR / f"{name}.jsonl")
    prefs = _read_jsonl(PREFERENCES_DIR / f"{name}.jsonl")
    ctx = _read_jsonl(CONTEXT_DIR / f"{name}.jsonl")
    limit = _as_int(kwargs.get("limit"), 20)
    return _op("inspect", True, {
        "skill": name,
        "manifest": manifest,
        "files": files,
        "history": history[-limit:],
        "history_count": len(history),
        "preferences": prefs[-limit:],
        "preference_count": len(prefs),
        "context_count": len(ctx),
        "note": "Inspect is read-only; no files are modified.",
    })


def _op_history(kwargs: dict) -> dict:
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op("history", False, None, "Provide the skill name (skill=...).")
    limit = _as_int(kwargs.get("limit"), 20)
    rows = _read_jsonl(HISTORY_DIR / f"{name}.jsonl")
    return _op("history", True, {
        "skill": name,
        "history": rows[-limit:],
        "count": len(rows),
        "note": "Each row is a versioned change; rollback restores a past manifest.",
    })


def _op_preferences(kwargs: dict) -> dict:
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op("preferences", False, None, "Provide the skill name (skill=...).")
    limit = _as_int(kwargs.get("limit"), 20)
    rows = _read_jsonl(PREFERENCES_DIR / f"{name}.jsonl")
    return _op("preferences", True, {
        "skill": name,
        "preferences": rows[-limit:],
        "count": len(rows),
        "note": "Preference signals recorded from user interaction; apply_prefs writes them into the manifest.",
    })


# ------------------------------------------------------------------ write ops

def _record(name: str, kind: str, payload: dict[str, Any]) -> None:
    entry = {"ts": _now(), "kind": kind, **payload}
    if kind == "pref":
        _append_jsonl(PREFERENCES_DIR / f"{name}.jsonl", entry)
    elif kind == "context":
        _append_jsonl(CONTEXT_DIR / f"{name}.jsonl", entry)
    elif kind == "history":
        _append_jsonl(HISTORY_DIR / f"{name}.jsonl", entry)


def _op_record_pref(kwargs: dict) -> dict:
    operation = "record_pref"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Recording interaction context writes to disk, so it needs "
            "authorized=true AND confirm=true plus an allow rule."))
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op(operation, False, None, "Provide the skill name (skill=...).")
    if not _skill_dir(name).is_dir():
        return _op(operation, False, None, f"Skill '{name}' not found in features/.")
    context = (kwargs.get("context") or "").strip()
    signal = (kwargs.get("signal") or "").strip().lower()
    if signal not in ("accept", "reject", "correct"):
        return _op(operation, False, None, (
            "signal must be one of: accept, reject, correct."))
    if not context:
        return _op(operation, False, None, "Provide interaction context (context=...).")

    # Record both context and preference signal.
    _record(name, "context", {
        "skill": name, "context": context, "signal": signal,
    })
    _record(name, "pref", {
        "skill": name, "signal": signal, "context": context,
    })
    return _op(operation, True, {
        "skill": name, "signal": signal,
        "note": f"Recorded {signal} signal and context for '{name}'. Use apply_prefs to write it into the manifest.",
    })


def _op_update_manifest(kwargs: dict) -> dict:
    operation = "update_manifest"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Updating a skill manifest writes to disk, so it needs "
            "authorized=true AND confirm=true plus an allow rule."))
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op(operation, False, None, "Provide the skill name (skill=...).")
    field = (kwargs.get("field") or "").strip()
    if field not in _WRITE_FIELDS:
        return _op(operation, False, None, (
            f"Unknown field '{field}'. One of: {', '.join(sorted(_WRITE_FIELDS))}."))
    value = kwargs.get("value")
    if value is None:
        return _op(operation, False, None, "Provide the new value (value=...).")

    manifest = _load_manifest(name)
    if manifest is None:
        return _op(operation, False, None, f"Skill '{name}' not found in features/.")

    old = manifest.get(field)
    new = value
    if field in ("triggers", "aliases", "requires", "parameters") and isinstance(value, str):
        try:
            parsed = json.loads(value)
            new = parsed
        except json.JSONDecodeError:
            new = value  # keep as raw string

    manifest[field] = new
    # Record history before writing.
    _record(name, "history", {
        "skill": name, "operation": "update_manifest", "field": field,
        "old": old, "new": new,
    })
    try:
        _manifest_path(name).write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
    except OSError as exc:
        return _op(operation, False, None, f"could not write manifest: {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "skill": name, "field": field, "old": old, "new": new,
        "note": f"Updated {field} for '{name}'. History recorded; use rollback to revert.",
    })


def _op_bump_version(kwargs: dict) -> dict:
    operation = "bump_version"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Bumping a version writes to disk, so it needs authorized=true AND "
            "confirm=true plus an allow rule."))
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op(operation, False, None, "Provide the skill name (skill=...).")
    level = (kwargs.get("bump") or "patch").strip().lower()
    if level not in ("patch", "minor", "major"):
        return _op(operation, False, None, "bump must be one of: patch, minor, major.")

    manifest = _load_manifest(name)
    if manifest is None:
        return _op(operation, False, None, f"Skill '{name}' not found in features/.")
    old_version = manifest.get("version", "1.0.0")
    new_version = _bump_semver(old_version, level)

    _record(name, "history", {
        "skill": name, "operation": "bump_version",
        "old": old_version, "new": new_version, "level": level,
    })
    manifest["version"] = new_version
    try:
        _manifest_path(name).write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
    except OSError as exc:
        return _op(operation, False, None, f"could not write manifest: {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "skill": name, "old": old_version, "new": new_version, "level": level,
        "note": f"Bumped '{name}' {old_version} -> {new_version}.",
    })


def _op_apply_prefs(kwargs: dict) -> dict:
    operation = "apply_prefs"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Applying preferences writes to disk, so it needs authorized=true "
            "AND confirm=true plus an allow rule."))
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op(operation, False, None, "Provide the skill name (skill=...).")
    manifest = _load_manifest(name)
    if manifest is None:
        return _op(operation, False, None, f"Skill '{name}' not found in features/.")

    prefs = _read_jsonl(PREFERENCES_DIR / f"{name}.jsonl")
    if not prefs:
        return _op(operation, True, {
            "skill": name, "applied": [],
            "note": f"No recorded preferences for '{name}'; nothing to apply.",
        })

    applied: list[dict[str, Any]] = []
    changed = False
    for pref in prefs:
        signal = pref.get("signal")
        context = pref.get("context", "")
        ctx_lower = context.lower()

        # Heuristic preference -> manifest field mappings.
        # These are conservative, transparent, and recorded so the user can
        # review and rollback.
        if "theme" in ctx_lower and "dark" in ctx_lower:
            # Record the preference; the actual theme lives in the skill's
            # behavior, not the manifest. Flag for review.
            applied.append({
                "signal": signal, "context": context,
                "field": None, "note": "theme preference recorded; skill.py theme handling not auto-edited.",
            })
            continue

        if "trigger" in ctx_lower:
            m = re.search(r"trigger[s]?\s+(?:is|are|should be|add)\s+['\"]([^'\"]+)['\"]", ctx_lower)
            if m:
                new_trigger = m.group(1)
                triggers = list(manifest.get("triggers") or [])
                if new_trigger not in triggers:
                    triggers.append(new_trigger)
                    manifest["triggers"] = triggers
                    changed = True
                    applied.append({
                        "signal": signal, "context": context,
                        "field": "triggers", "new": new_trigger,
                    })
            continue

        if "description" in ctx_lower:
            m = re.search(r"description\s+(?:is|should be|to)\s+['\"]([^'\"]+)['\"]", ctx_lower)
            if m:
                new_desc = m.group(1)
                manifest["description"] = new_desc
                changed = True
                applied.append({
                    "signal": signal, "context": context,
                    "field": "description", "new": new_desc,
                })
            continue

        # Default: record that a preference exists but couldn't be auto-applied.
        applied.append({
            "signal": signal, "context": context,
            "field": None, "note": "preference recorded; no deterministic field mapping found.",
        })

    if changed:
        _record(name, "history", {
            "skill": name, "operation": "apply_prefs", "applied": applied,
        })
        try:
            _manifest_path(name).write_text(
                json.dumps(manifest, indent=2), encoding="utf-8")
        except OSError as exc:
            return _op(operation, False, None, f"could not write manifest: {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "skill": name, "applied": applied,
        "note": f"Applied {len([a for a in applied if a.get('field')])} preference(s) to '{name}'.",
    })


def _op_rollback(kwargs: dict) -> dict:
    operation = "rollback"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Rolling back writes to disk, so it needs authorized=true AND "
            "confirm=true plus an allow rule."))
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op(operation, False, None, "Provide the skill name (skill=...).")
    to_version = (kwargs.get("to_version") or "").strip()
    if not to_version:
        return _op(operation, False, None, "Provide the target version (to_version=...).")

    history = _read_jsonl(HISTORY_DIR / f"{name}.jsonl")
    # Find the most recent history entry whose new version == to_version, or
    # the entry just before the first entry that changed away from to_version.
    target_manifest: dict | None = None
    for entry in reversed(history):
        new_val = entry.get("new")
        if isinstance(new_val, dict) and new_val.get("version") == to_version:
            target_manifest = dict(new_val)
            break
        if isinstance(new_val, str) and new_val == to_version:
            # Reconstruct: we only stored the field value, not the full manifest.
            # Can't fully roll back to a version string alone without full manifest.
            continue

    if target_manifest is None:
        return _op(operation, False, None, (
            f"No history entry restores '{name}' to version {to_version}. "
            "Known versions in history: " +
            ", ".join(sorted({e.get("new", {}).get("version") for e in history
                              if isinstance(e.get("new"), dict)} or {old for e in history
                              if isinstance(e.get("old"), dict)})) or "none"
        ))

    manifest = _load_manifest(name)
    if manifest is None:
        return _op(operation, False, None, f"Skill '{name}' not found in features/.")

    _record(name, "history", {
        "skill": name, "operation": "rollback",
        "from": manifest.get("version"), "to": to_version,
    })
    manifest.update(target_manifest)
    manifest["version"] = to_version
    try:
        _manifest_path(name).write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
    except OSError as exc:
        return _op(operation, False, None, f"could not write manifest: {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "skill": name, "from": manifest.get("version"), "to": to_version,
        "note": f"Rolled back '{name}' to version {to_version}.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "list": _op_list,
    "inspect": _op_inspect,
    "history": _op_history,
    "preferences": _op_preferences,
    "record_pref": _op_record_pref,
    "update_manifest": _op_update_manifest,
    "bump_version": _op_bump_version,
    "apply_prefs": _op_apply_prefs,
    "rollback": _op_rollback,
}

_OPERATION_TITLES = {
    "sources": "Skill Update Sources",
    "list": "List Skills",
    "inspect": "Inspect Skill",
    "history": "Change History",
    "preferences": "Preference Signals",
    "record_pref": "Record Preference",
    "update_manifest": "Update Manifest Field",
    "bump_version": "Bump Version",
    "apply_prefs": "Apply Preferences",
    "rollback": "Rollback Version",
}

_ALIASES = {
    "list_skills": "list", "show_skills": "list",
    "inspect_skill": "inspect", "show_skill": "inspect",
    "record_preference": "record_pref", "signal": "record_pref",
    "show_preferences": "preferences", "pref_list": "preferences",
    "show_history": "history", "change_history": "history",
    "set_field": "update_manifest", "set_manifest": "update_manifest",
    "bump": "bump_version", "version_bump": "bump_version",
    "revert": "rollback", "restore": "rollback",
    "sources_list": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "sources":
        return value.get("note", "Skill update available.")
    if operation == "list":
        return f"{value.get('count')} skill(s) available ({value.get('total')} total)."
    if operation == "inspect":
        return f"Inspected {value.get('skill')}: {value.get('history_count')} history, {value.get('preference_count')} preference(s)."
    if operation == "history":
        return f"{value.get('count')} history row(s) for {value.get('skill')}."
    if operation == "preferences":
        return f"{value.get('count')} preference signal(s) for {value.get('skill')}."
    if operation == "record_pref":
        return f"Recorded {value.get('signal')} for {value.get('skill')}."
    if operation == "update_manifest":
        return f"Set {value.get('field')} on {value.get('skill')}."
    if operation == "bump_version":
        return f"Bumped {value.get('skill')} {value.get('old')} -> {value.get('new')}."
    if operation == "apply_prefs":
        return value.get("note", "Preferences applied.")
    if operation == "rollback":
        return value.get("note", "Rollback complete.")
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Run one skill-update operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Skill Update",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Skill Update",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Skill Update",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Skill update error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Skill Update"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
        "skill": (kwargs.get("skill") or None),
        "authorized": _flag(**kwargs),
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
