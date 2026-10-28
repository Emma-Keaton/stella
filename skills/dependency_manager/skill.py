"""
Feature: dependency_manager
Description: Provisions this machine with the tools Stella's capabilities need - reports what is missing per platform, shows the exact install command, and (with confirmation and a policy rule) installs it and reads back whether it actually became available.
Uses theme tokens from themes.json (no hardcoded colours). Install commands come only from PACKAGE_MAP in core/dependencies.py, so a machine with no package manager reports that rather than attempting something that cannot work, and every install reports `done` only after the tool is re-probed as available.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "dependency_manager",
    "aliases": ["dependency_manager", "install dependencies", "install tool", "install package",
                "what am I missing", "what do I need", "setup tools", "provision machine",
                "install aircrack", "install hashcat", "install ffmpeg"],
    "description": (
        "Provisions this machine with the tools Stella's capabilities need. Reports what is "
        "present and what is missing per platform, with the exact install command for each, and "
        "- only with an explicit confirmation and a policy rule that allows it - runs the install "
        "and reads back whether the tool actually became available. Never invents a package "
        "mapping: a name it has no command for is reported as such."
    ),
    "triggers": [
        "install", "install tool", "install package", "install dependencies",
        "what do I need", "what am I missing", "setup", "provision",
        "install aircrack", "install hashcat", "install ffmpeg", "install wireshark",
        "install vlc", "install python package", "pip install",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: status | audit | install | install_bundle | platform | bundles. Defaults to status.",
            },
            "name": {
                "type": "STRING",
                "description": "Requirement to install: hashcat, ffmpeg, matplotlib, or a bundle name such as wireless-full.",
            },
            "skill": {
                "type": "STRING",
                "description": "Skill to audit, e.g. world_watch or wireless_audit.",
            },
            "confirm": {
                "type": "BOOLEAN",
                "description": "Must be true to actually install. Defaults to false, which only reports what would run.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum items to list. Defaults to 40.",
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
    "notes": "Installing is destructive class in core/tool_policy.py: it needs a policy allow rule and confirm=true.",
}


def _deps():
    try:
        from core import dependencies
        return dependencies
    except Exception:
        return None


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _flag(**kwargs) -> bool:
    return kwargs.get("confirm") in (True, "true", "True", 1, "1")


def _as_int(value, default: int = 40, ceiling: int = 200) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


def _op_platform(kwargs: Dict[str, Any]) -> dict:
    deps = _deps()
    if deps is None:
        return _op("platform", False, None, "the dependency layer could not be loaded")
    return _op("platform", True, {
        "platform": deps.platform_tag(),
        "package_manager": deps.package_manager(),
        "python": deps.sys.executable,
        "note": ("A platform with no package manager cannot install system tools; pip still works "
                 "for Python modules, and everything else needs a manual install."),
    })


def _op_bundles(kwargs: Dict[str, Any]) -> dict:
    deps = _deps()
    if deps is None:
        return _op("bundles", False, None, "the dependency layer could not be loaded")
    limit = _as_int(kwargs.get("limit"), 40)
    bundles = {}
    for name, members in list(deps.BUNDLES.items())[:limit]:
        missing = [member for member in members if not deps.probe(member).present]
        bundles[name] = {"members": members, "missing": missing,
                         "complete": not missing}
    return _op("bundles", True, {"bundles": bundles,
                                "count": len(bundles),
                                "note": "A bundle is a word for a list of requirements; 'complete' means every member is present."})


def _op_status(kwargs: Dict[str, Any]) -> dict:
    deps = _deps()
    if deps is None:
        return _op("status", False, None, "the dependency layer could not be loaded")
    name = (kwargs.get("name") or "").strip()
    if not name:
        from core import skill_surfaces

        report = skill_surfaces.skill_surfaces()
        needed: list = []
        for skill in report.get("skills", []):
            for requirement in skill.get("required", []):
                needed.extend(deps.expand(requirement))
        for skill in report.get("skills", []):
            for item in skill.get("missing", []):
                if item.get("what"):
                    needed.append(item["what"])
        needed = sorted(set(needed))

    else:
        needed = deps.expand(name)

    report = deps.status(needed)
    return _op("status", True, report)


def _op_audit(kwargs: Dict[str, Any]) -> dict:
    deps = _deps()
    if deps is None:
        return _op("audit", False, None, "the dependency layer could not be loaded")
    skill = (kwargs.get("skill") or "").strip()
    if not skill:
        return _op("audit", False, None, "Name the skill to audit (skill=...), e.g. wireless_audit.")
    names = deps.requirement_names_for(skill)
    if not names:
        return _op("audit", True, {
            "skill": skill,
            "requirements": [],
            "missing": [],
            "note": ("That skill declares no requirements, or its manifest could not be read. "
                     "It runs on what ships with Python and the OS."),
        })
    report = deps.status(names)
    report["skill"] = skill
    return _op("audit", True, report)


def _op_install(kwargs: Dict[str, Any]) -> dict:
    deps = _deps()
    if deps is None:
        return _op("install", False, None, "the dependency layer could not be loaded")
    name = (kwargs.get("name") or "").strip()
    if not name:
        return _op("install", False, None, "Name what to install (name=...), e.g. hashcat or ffmpeg.")

    if not _flag(**kwargs):
        requirement = deps.probe(name)
        planned = requirement.installs[0] if requirement.installs else "no command for this platform"
        return _op("install", False, None, (
            f"Installing '{name}' was not started because confirm was not set. It would run: "
            f"{' '.join(planned) if isinstance(planned, list) else planned}. Installing changes "
            "the machine, so it also needs an allow rule in config/tool_policy.json."))

    outcome = deps.install(name, confirm=True)
    return _op("install", outcome.get("ok", False), outcome,
               "" if outcome.get("ok") else outcome.get("summary") or outcome.get("reason"))


def _op_install_bundle(kwargs: Dict[str, Any]) -> dict:
    deps = _deps()
    if deps is None:
        return _op("install_bundle", False, None, "the dependency layer could not be loaded")
    name = (kwargs.get("name") or "").strip()
    if not name:
        return _op("install_bundle", False, None,
                   "Name the bundle to install (name=...): " + ", ".join(sorted(deps.BUNDLES)))
    if name not in deps.BUNDLES:
        return _op("install_bundle", False, None, (
            f"'{name}' is not a bundle. Known bundles: {', '.join(sorted(deps.BUNDLES))}."))

    members = deps.expand(name)
    if not _flag(**kwargs):
        planned = []
        for member in members:
            requirement = deps.probe(member)
            if requirement.installs:
                planned.append(f"{member}: {' '.join(requirement.installs[0])}")
        return _op("install_bundle", False, None, (
            f"Installing the '{name}' bundle was not started because confirm was not set. It would "
            f"run {len(planned)} commands: " + "; ".join(planned[:6]) + "."))

    outcome = deps.install_all(members, confirm=True)
    return _op("install_bundle", True, outcome)


_OPERATIONS = {
    "platform": _op_platform,
    "bundles": _op_bundles,
    "status": _op_status,
    "audit": _op_audit,
    "install": _op_install,
    "install_bundle": _op_install_bundle,
}

_OPERATION_TITLES = {
    "platform": "Platform", "bundles": "Requirement Bundles",
    "status": "Dependency Status", "audit": "Skill Dependency Audit",
    "install": "Install Requirement", "install_bundle": "Install Bundle",
}

_ALIASES = {
    "what_am_i_missing": "status", "missing": "status", "report": "status",
    "check": "status", "what_do_i_need": "status",
    "audit_skill": "audit", "skill_requirements": "audit",
    "install_requirement": "install", "install_tool": "install", "install_package": "install",
    "bundle_install": "install_bundle", "install_group": "install_bundle",
    "platform_info": "platform", "what_platform": "platform",
    "list_bundles": "bundles", "available_bundles": "bundles",
}


def _failure(operation: str, reason: str) -> dict:
    title = _OPERATION_TITLES.get(operation, "Dependency Manager")
    return {
        "title": title,
        "summary": f"{title} unavailable: {reason}",
        "spoken_narrative": f"{title} unavailable: {reason}",
        "operation": operation,
        "ok": False,
        "record": _op(operation, False, None, reason),
    }


def execute(**kwargs) -> dict:
    """Provision this machine, with a read-back on every install."""
    operation = (kwargs.get("operation") or "status").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return _failure(operation, f"Unknown operation '{operation}'. One of: "
                                   + ", ".join(sorted(_OPERATIONS)) + ".")

    try:
        record = handler(kwargs)
    except TypeError as exc:
        return _failure(operation, f"Bad arguments for '{operation}': {exc}")
    except Exception as exc:
        return _failure(operation, f"{type(exc).__name__}: {exc}")

    return {
        "title": _OPERATION_TITLES.get(operation, "Dependency Manager"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "platform":
        return (f"Platform {value.get('platform')} with package manager "
                f"{value.get('package_manager')}, using {value.get('python')}.")
    if operation == "bundles":
        incomplete = [name for name, bundle in (value.get("bundles") or {}).items()
                      if not bundle["complete"]]
        return f"{value.get('count')} bundles defined; {len(incomplete)} are not fully installed."
    if operation == "status":
        missing = value.get("missing") or []
        present = value.get("present") or []
        return (f"{len(present)} requirement(s) present and {len(missing)} missing on "
                f"{value.get('platform')}. Missing: {', '.join(missing[:12]) or 'none'}.")
    if operation == "audit":
        missing = value.get("missing") or []
        if not missing:
            return f"{value.get('skill')} declares {len(value.get('details') or [])} requirement(s), and all are present."
        return (f"{value.get('skill')} is missing {len(missing)}: {', '.join(missing)}. "
                "Name one to install it with the install operation.")
    if operation == "install":
        if not record.get("ok"):
            return f"Not installed: {record.get('error')}"
        return value.get("summary", "Installed.")
    if operation == "install_bundle":
        results = value.get("results") or []
        installed = value.get("installed") or []
        failed = value.get("failed") or []
        return (f"Bundle install finished: {len(installed)} newly installed "
                f"({', '.join(installed[:8]) or 'none'}), {len(failed)} not installed "
                f"({', '.join(failed[:8]) or 'none'}), across {len(results)} requirements.")
    return record.get("error") or "No operation ran."
