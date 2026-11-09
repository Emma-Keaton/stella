"""
Feature: skill_add
Description: Skill creator. Builds new Stella skill packages from a spec -
manifest.json, skill.py, test_cases.json, and __init__.py following Stella's
skill contract (FEATURE_METADATA + execute(**kwargs)). Supports built-in
templates (read_only_tool, read_write_tool, passive_osint, active_audit) or a
fully custom spec. Validates before writing, previews without writing, never
overwrites an existing skill.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

FEATURE_METADATA = {
    "name": "skill_add",
    "aliases": ["skill_add", "add skill", "skill add", "create skill",
                "new skill", "make skill", "build skill from spec",
                "skill creator", "add a skill", "create a skill",
                "new skill from spec", "create skill package",
                "generate skill", "scaffold skill"],
    "description": (
        "Skill creator: builds new Stella skill packages from a spec. Generates "
        "manifest.json, skill.py, test_cases.json, and __init__.py following "
        "Stella's skill contract (FEATURE_METADATA + execute(**kwargs)). "
        "Supports built-in templates (read_only_tool, read_write_tool, "
        "passive_osint, active_audit) or a fully custom spec. Validates the "
        "spec before writing, previews what will be created, and never "
        "overwrites an existing skill. Writes into features/<name>/, so "
        "creating a skill needs authorized=true plus confirm=true plus a "
        "policy allow rule. No symlinks or external PC references - everything "
        "is written fresh inside this project."
    ),
    "triggers": [
        "add skill", "skill add", "create skill", "new skill", "make skill",
        "build skill from spec", "skill creator", "add a skill",
        "create a skill", "new skill from spec", "create skill package",
        "generate skill", "scaffold skill",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: sources | list_templates | validate | preview | create. Defaults to sources.",
            },
            "name": {
                "type": "STRING",
                "description": "The new skill name (e.g. my_custom_skill). Required for create/preview/validate.",
            },
            "description": {
                "type": "STRING",
                "description": "Human-readable description of what the skill does.",
            },
            "category": {
                "type": "STRING",
                "description": "Skill category: system | security | osint | memory | docs | development | general. Defaults to general.",
            },
            "surface": {
                "type": "STRING",
                "description": "Surface: desktop | android | both. Defaults to both.",
            },
            "triggers": {
                "type": "STRING",
                "description": "JSON array of trigger phrases, or a comma-separated list.",
            },
            "parameters": {
                "type": "STRING",
                "description": "JSON object of parameter definitions for the skill's execute().",
            },
            "operations": {
                "type": "STRING",
                "description": "JSON array of operation names the skill supports (e.g. [\"sources\", \"run\"]).",
            },
            "requires": {
                "type": "STRING",
                "description": "JSON array of requirement strings (e.g. [\"docx\", \"node\"]).",
            },
            "template": {
                "type": "STRING",
                "description": "Built-in template to start from: read_only_tool | read_write_tool | passive_osint | active_audit. Overrides description/parameters/operations if given.",
            },
            "authorized": {
                "type": "BOOLEAN",
                "description": "Must be true to actually create skill files.",
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
    "notes": "Writes into features/<name>/. Validates before writing; preview shows what will be created without writing. Never overwrites an existing skill. Requires authorized=true + confirm=true + an allow rule.",
}

TEMPLATES: dict[str, dict[str, Any]] = {
    "read_only_tool": {
        "name": "read_only_tool",
        "description": "A read-only tool that inspects or reports without writing.",
        "category": "general",
        "surface": "both",
        "requires": [],
        "operations": ["sources", "run"],
        "triggers": [],
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "operation": {
                    "type": "STRING",
                    "description": "One of: sources | run. Defaults to sources.",
                },
                "target": {
                    "type": "STRING",
                    "description": "The target to inspect (run operation).",
                },
            },
            "required": [],
        },
    },
    "read_write_tool": {
        "name": "read_write_tool",
        "description": "A tool that reads and writes, needs confirmation.",
        "category": "system",
        "surface": "desktop",
        "requires": [],
        "operations": ["sources", "read", "write"],
        "triggers": [],
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "operation": {
                    "type": "STRING",
                    "description": "One of: sources | read | write. Defaults to sources.",
                },
                "path": {
                    "type": "STRING",
                    "description": "File path (read/write operation).",
                },
                "content": {
                    "type": "STRING",
                    "description": "Content to write (write operation).",
                },
            },
            "required": [],
        },
    },
    "passive_osint": {
        "name": "passive_osint",
        "description": "Passive OSINT lookup - queries public indexes, never contacts the target directly.",
        "category": "osint",
        "surface": "both",
        "requires": [],
        "operations": ["sources", "lookup"],
        "triggers": [],
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "operation": {
                    "type": "STRING",
                    "description": "One of: sources | lookup. Defaults to sources.",
                },
                "query": {
                    "type": "STRING",
                    "description": "The value to look up (lookup operation).",
                },
            },
            "required": [],
        },
    },
    "active_audit": {
        "name": "active_audit",
        "description": "Active audit - contacts a named target; needs authorization.",
        "category": "security",
        "surface": "desktop",
        "requires": [],
        "operations": ["sources", "audit"],
        "triggers": [],
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "operation": {
                    "type": "STRING",
                    "description": "One of: sources | audit. Defaults to sources.",
                },
                "target": {
                    "type": "STRING",
                    "description": "The target to audit (audit operation).",
                },
                "authorized": {
                    "type": "BOOLEAN",
                    "description": "Must be true to contact the target.",
                },
                "confirm": {
                    "type": "BOOLEAN",
                    "description": "Must be true to start the audit.",
                },
            },
            "required": [],
        },
    },
}

VALID_CATEGORIES = {
    "system", "security", "osint", "memory", "docs", "development", "general",
}
VALID_SURFACES = {"desktop", "android", "both"}


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


def _parse_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except json.JSONDecodeError:
            pass
        return [t.strip() for t in text.split(",") if t.strip()]
    return []


def _parse_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {}


def _skill_dir(name: str) -> Path:
    return Path(__file__).resolve().parent.parent.parent / "features" / name


def _list_existing_skills() -> list[str]:
    features_dir = Path(__file__).resolve().parent.parent / "features"
    if not features_dir.exists():
        return []
    out = []
    for entry in sorted(features_dir.iterdir()):
        if entry.name.startswith((".", "_")) or not entry.is_dir():
            continue
        if (entry / "manifest.json").exists() and (entry / "skill.py").exists():
            out.append(entry.name)
    return out


def _validate_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    name = (spec.get("name") or "").strip()
    if not name:
        errors.append("name is required")
    else:
        if not re.match(r"^[a-z0-9_]+$", name):
            errors.append("name must be lowercase letters, digits, and underscores only")
        if name in _list_existing_skills():
            errors.append(f"skill '{name}' already exists in features/")
    description = spec.get("description") or ""
    if not description:
        errors.append("description is required")
    category = (spec.get("category") or "general").strip()
    if category not in VALID_CATEGORIES:
        errors.append(f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
    surface = (spec.get("surface") or "both").strip()
    if surface not in VALID_SURFACES:
        errors.append(f"surface must be one of: {', '.join(sorted(VALID_SURFACES))}")
    _parse_list(spec.get("triggers"))
    _parse_dict(spec.get("parameters"))
    _parse_list(spec.get("operations"))
    _parse_list(spec.get("requires"))
    return errors


def _build_manifest(spec: dict[str, Any]) -> dict[str, Any]:
    triggers = _parse_list(spec.get("triggers"))
    parameters = _parse_dict(spec.get("parameters")) or {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: sources | run. Defaults to sources.",
            },
        },
        "required": [],
    }
    return {
        "name": spec["name"],
        "aliases": [spec["name"], spec["name"].replace("_", " ")],
        "description": spec["description"],
        "triggers": triggers,
        "parameters": parameters,
        "version": "1.0.0",
        "active": True,
        "author": "Stella",
        "category": spec.get("category", "general"),
        "surface": spec.get("surface", "both"),
        "requires": _parse_list(spec.get("requires")),
        "optional_dependencies": [],
        "notes": f"Created by skill_add. Operations: {', '.join(_parse_list(spec.get('operations')) or ['sources'])}.",
    }


def _build_skill_py(spec: dict[str, Any]) -> str:
    name = spec["name"]
    description = spec["description"]
    category = spec.get("category", "general")
    operations = _parse_list(spec.get("operations")) or ["sources"]
    parameters = _parse_dict(spec.get("parameters")) or {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: sources | run. Defaults to sources.",
            },
        },
        "required": [],
    }

    op_cases = []
    for op in operations:
        op_cases.append(f'    "{op}": _op_{op},')
    op_case_str = "\n".join(op_cases) if op_cases else '    "sources": _op_sources,'

    handler_fns = []
    handler_fns.append('''def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "name": "%s",
        "description": "%s",
        "category": "%s",
        "operations": %s,
        "note": "This skill was created by skill_add. Edit its manifest.json or re-run skill_add to change it."
    })


''' % (name, description.replace('"', '\\"'), category, json.dumps(operations)))

    for op in operations:
        handler_fns.append(f'''def _op_{op}(kwargs: dict) -> dict:
    return _op("{op}", True, {{
        "skill": "{name}",
        "operation": "{op}",
        "note": "The {op} operation for {name} was created by skill_add. Implement its behavior in this handler.",
    }})


''')

    handler_str = "\n".join(handler_fns)
    ops_registry = ",\n".join(op_cases)

    return '''"""
Feature: %s
Description: %s
Created by skill_add. Edit this file to implement each operation's behavior.
"""

from __future__ import annotations

from typing import Any

FEATURE_METADATA = %s


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


%s

_OPERATIONS = {
%s}

_OPERATION_TITLES = {
%s}

_ALIASES = {
    "sources_list": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "sources":
        return value.get("note", "Skill available.")
    return f"{value.get('skill', '%s')}: {{value.get('note', 'done')}}"


def execute(**kwargs) -> dict:
    """Run one skill operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {{
            "title": "%s",
            "summary": f"Unknown operation '{{operation}}'. One of: {{', '.join(sorted(_OPERATIONS))}}.",
            "spoken_narrative": f"Unknown operation {{operation}}.",
            "ok": False,
            "operation": operation,
        }}
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {{
            "title": "%s",
            "summary": f"Bad arguments for '{{operation}}': {{exc}}",
            "spoken_narrative": f"Bad arguments for {{operation}}.",
            "ok": False,
            "operation": operation,
        }}
    except Exception as exc:
        return {{
            "title": "%s",
            "summary": f"{{type(exc).__name__}}: {{exc}}",
            "spoken_narrative": f"{name} error: {{type(exc).__name__}}.",
            "ok": False,
            "operation": operation,
        }}
    return {{
        "title": _OPERATION_TITLES.get(operation, "%s"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }}


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
''' % (
        name,
        description.replace('"', '\\"'),
        json.dumps(_build_manifest(spec), indent=2),
        handler_str,
        ops_registry,
        ",\n".join(f'    "{op}": "{op.title()} Operation"' for op in operations),
        name,
        name,
        name,
        name,
        name,
    )


def _build_test_cases(spec: dict[str, Any]) -> dict[str, Any]:
    operations = _parse_list(spec.get("operations")) or ["sources"]
    cases = [
        {
            "name": "sources",
            "operation": "sources",
            "expect_ok": True,
            "expect_keys": ["note"],
        }
    ]
    for op in operations:
        if op == "sources":
            continue
        cases.append({
            "name": f"{op} basic",
            "operation": op,
            "expect_ok": True,
        })
    cases.append({
        "name": "unknown operation",
        "operation": "frobnicate",
        "expect_ok": False,
    })
    return {
        "name": spec["name"],
        "version": "1.0.0",
        "test_cases": cases,
    }


def _build_init(name: str) -> str:
    return '"""%s skill package.\\n\\n"""\\n' % name


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "templates": list(TEMPLATES.keys()),
        "template_details": TEMPLATES,
        "valid_categories": sorted(VALID_CATEGORIES),
        "valid_surfaces": sorted(VALID_SURFACES),
        "existing_skills": _list_existing_skills(),
        "note": "Use preview to see what will be created, then create with authorized=true + confirm=true.",
    })


def _op_list_templates(kwargs: dict) -> dict:
    limit = _as_int(kwargs.get("limit"), 20)
    items = list(TEMPLATES.items())[:limit]
    return _op("list_templates", True, {
        "templates": [{"key": k, **v} for k, v in items],
        "count": len(items),
        "total": len(TEMPLATES),
    })


def _op_validate(kwargs: dict) -> dict:
    name = (kwargs.get("name") or "").strip()
    spec = {
        "name": name,
        "description": kwargs.get("description") or "",
        "category": kwargs.get("category") or "general",
        "surface": kwargs.get("surface") or "both",
        "triggers": kwargs.get("triggers"),
        "parameters": kwargs.get("parameters"),
        "operations": kwargs.get("operations"),
        "requires": kwargs.get("requires"),
    }
    template = (kwargs.get("template") or "").strip()
    if template:
        if template not in TEMPLATES:
            return _op("validate", False, None, f"Unknown template '{template}'. Known: {', '.join(sorted(TEMPLATES))}.")
        spec = {**TEMPLATES[template], **spec}
        spec["name"] = name or TEMPLATES[template]["name"]
    errors = _validate_spec(spec)
    return _op("validate", True, {
        "valid": len(errors) == 0,
        "errors": errors,
        "spec": spec,
        "note": "Fix the errors, then preview or create.",
    })


def _op_preview(kwargs: dict) -> dict:
    name = (kwargs.get("name") or "").strip()
    if not name:
        return _op("preview", False, None, "Provide the skill name (name=...).")
    spec = {
        "name": name,
        "description": kwargs.get("description") or "",
        "category": kwargs.get("category") or "general",
        "surface": kwargs.get("surface") or "both",
        "triggers": kwargs.get("triggers"),
        "parameters": kwargs.get("parameters"),
        "operations": kwargs.get("operations"),
        "requires": kwargs.get("requires"),
    }
    template = (kwargs.get("template") or "").strip()
    if template:
        if template not in TEMPLATES:
            return _op("preview", False, None, f"Unknown template '{template}'.")
        spec = {**TEMPLATES[template], **spec}
        spec["name"] = name
    errors = _validate_spec(spec)
    if errors:
        return _op("preview", False, None, "; ".join(errors))
    skill_py = _build_skill_py(spec)
    return _op("preview", True, {
        "name": name,
        "manifest": _build_manifest(spec),
        "skill_py_preview": skill_py[:2000] + ("…" if len(skill_py) > 2000 else ""),
        "test_cases": _build_test_cases(spec),
        "init": _build_init(name),
        "note": "Preview only - nothing was written. Use create with authorized=true + confirm=true to write.",
    })


def _op_create(kwargs: dict) -> dict:
    operation = "create"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Creating a skill writes to disk, so it needs authorized=true AND "
            "confirm=true plus an allow rule."))
    name = (kwargs.get("name") or "").strip()
    if not name:
        return _op(operation, False, None, "Provide the skill name (name=...).")

    spec = {
        "name": name,
        "description": kwargs.get("description") or "",
        "category": kwargs.get("category") or "general",
        "surface": kwargs.get("surface") or "both",
        "triggers": kwargs.get("triggers"),
        "parameters": kwargs.get("parameters"),
        "operations": kwargs.get("operations"),
        "requires": kwargs.get("requires"),
    }
    template = (kwargs.get("template") or "").strip()
    if template:
        if template not in TEMPLATES:
            return _op(operation, False, None, f"Unknown template '{template}'.")
        spec = {**TEMPLATES[template], **spec}
        spec["name"] = name

    errors = _validate_spec(spec)
    if errors:
        return _op(operation, False, None, "; ".join(errors))

    skill_dir = _skill_dir(name)
    if skill_dir.exists():
        return _op(operation, False, None, f"Skill '{name}' already exists in features/.")

    try:
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "manifest.json").write_text(
            json.dumps(_build_manifest(spec), indent=2), encoding="utf-8")
        (skill_dir / "skill.py").write_text(
            _build_skill_py(spec), encoding="utf-8")
        (skill_dir / "test_cases.json").write_text(
            json.dumps(_build_test_cases(spec), indent=2), encoding="utf-8")
        (skill_dir / "__init__.py").write_text(
            _build_init(), encoding="utf-8")
    except OSError as exc:
        return _op(operation, False, None, f"could not create skill files: {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "name": name,
        "path": str(skill_dir),
        "files": ["manifest.json", "skill.py", "test_cases.json", "__init__.py"],
        "note": f"Created skill '{name}' in features/{name}/. It will be discovered by the dynamic registry on next init.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "list_templates": _op_list_templates,
    "validate": _op_validate,
    "preview": _op_preview,
    "create": _op_create,
}

_OPERATION_TITLES = {
    "sources": "Skill Add Sources",
    "list_templates": "List Templates",
    "validate": "Validate Spec",
    "preview": "Preview",
    "create": "Create Skill",
}

_ALIASES = {
    "listtemplates": "list_templates", "show_templates": "list_templates",
    "validate_spec": "validate", "check_spec": "validate",
    "preview_create": "preview", "dry_run": "preview",
    "make_skill": "create", "new_skill": "create",
    "scaffold": "create",
    "sources_list": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "sources":
        return f"{len(value.get('templates') or [])} template(s); {value.get('note')}"
    if operation == "list_templates":
        return f"{value.get('count')} template(s) of {value.get('total')}."
    if operation == "validate":
        return "valid" if value.get("valid") else f"invalid: {'; '.join(value.get('errors') or [])}"
    if operation == "preview":
        return f"Preview of {value.get('name')} ready to create."
    if operation == "create":
        return value.get("note", "Skill created.")
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Run one skill-add operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Skill Add",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Skill Add",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Skill Add",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Skill add error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Skill Add"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
        "skill": (kwargs.get("name") or None),
        "authorized": _flag(**kwargs),
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
