"""
Feature: skill_build
Description: Skill builder. Validates, compiles, and runs test_cases for a
Stella skill package. Checks manifest.json validity, FEATURE_METADATA/manifest
agreement, compiles skill.py with py_compile, and runs the skill's
test_cases.json against its execute(). Reports per-test pass/fail with reasons.
Reads only - never writes to skill files. Use skill_add to create and
skill_update to modify; skill_build is the verify step in the add → build →
update lifecycle. No symlinks or external PC references.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

FEATURE_METADATA = {
    "name": "skill_build",
    "aliases": ["skill_build", "build skill", "skill build", "validate skill",
                "check skill", "compile skill", "test skill", "skill test",
                "skill checker", "build a skill", "verify skill",
                "run skill tests", "skill test cases", "compile skill.py"],
    "description": (
        "Skill builder: validates, compiles, and runs test_cases for a Stella "
        "skill package. Checks manifest.json validity, FEATURE_METADATA/"
        "manifest agreement, compiles skill.py with py_compile, and runs the "
        "skill's test_cases.json against its execute(). Reports per-test "
        "pass/fail with reasons. Reads only - never writes to skill files. "
        "Use skill_add to create and skill_update to modify; skill_build is "
        "the verify step in the add → build → update lifecycle. No symlinks "
        "or external PC references."
    ),
    "triggers": [
        "build skill", "skill build", "validate skill", "check skill",
        "compile skill", "test skill", "skill test", "skill checker",
        "build a skill", "verify skill", "run skill tests",
        "skill test cases", "compile skill.py",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: sources | list | inspect | validate | compile | test | build. Defaults to sources.",
            },
            "skill": {
                "type": "STRING",
                "description": "The skill name to build/validate/test (e.g. anatomy, brainstorming). Required for inspect/validate/compile/test/build.",
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
    "notes": "Read-only: compiles skill.py and runs test_cases.json against execute(). Never writes to skill files.",
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FEATURES_DIR = PROJECT_ROOT / "features"


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


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


def _list_skills() -> list[dict[str, Any]]:
    skills: list[dict[str, Any]] = []
    if not FEATURES_DIR.exists():
        return skills
    for entry in sorted(FEATURES_DIR.iterdir()):
        if entry.name.startswith((".", "_")) or not entry.is_dir():
            continue
        manifest = entry / "manifest.json"
        skill_py = entry / "skill.py"
        if manifest.exists() and skill_py.exists():
            skills.append({
                "name": entry.name,
                "path": str(entry),
                "has_manifest": True,
                "has_skill_py": True,
                "has_test_cases": (entry / "test_cases.json").exists(),
                "has_init": (entry / "__init__.py").exists(),
            })
    skills.sort(key=lambda s: s["name"])
    return skills


def _load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_module(name: str):
    skill_py = _skill_dir(name) / "skill.py"
    spec = importlib.util.spec_from_file_location(
        f"stella_skill_build_{name}", str(skill_py))
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    return module


# ------------------------------------------------------------------ read ops

def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "skill_dir": str(FEATURES_DIR),
        "operations": ["sources", "list", "inspect", "validate", "compile",
                       "test", "build"],
        "note": "Read-only: never writes to skill files. Use skill_add to create and skill_update to modify.",
    })


def _op_list(kwargs: dict) -> dict:
    limit = _as_int(kwargs.get("limit"), 20)
    skills = _list_skills()
    return _op("list", True, {
        "skills": skills[:limit],
        "count": len(skills[:limit]),
        "total": len(skills),
        "note": "Every listed skill is a real package in features/ with manifest.json + skill.py.",
    })


def _op_inspect(kwargs: dict) -> dict:
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op("inspect", False, None, "Provide the skill name (skill=...).")
    skill_dir = _skill_dir(name)
    if not skill_dir.is_dir():
        return _op("inspect", False, None, f"Skill '{name}' not found in features/.")
    files = {}
    for fname in ("manifest.json", "skill.py", "test_cases.json", "__init__.py"):
        files[fname] = (skill_dir / fname).exists()
    manifest = _load_json(skill_dir / "manifest.json")
    test_cases = _load_json(skill_dir / "test_cases.json")
    test_count = len(test_cases.get("test_cases", [])) if isinstance(test_cases, dict) else 0
    return _op("inspect", True, {
        "skill": name,
        "files": files,
        "manifest": manifest,
        "test_case_count": test_count,
        "note": "Inspect is read-only.",
    })


# ------------------------------------------------------------------ validate

def _op_validate(kwargs: dict) -> dict:
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op("validate", False, None, "Provide the skill name (skill=...).")
    skill_dir = _skill_dir(name)
    if not skill_dir.is_dir():
        return _op("validate", False, None, f"Skill '{name}' not found in features/.")

    errors: list[str] = []
    manifest_path = skill_dir / "manifest.json"
    skill_py_path = skill_dir / "skill.py"

    if not manifest_path.exists():
        errors.append("manifest.json is missing")
    if not skill_py_path.exists():
        errors.append("skill.py is missing")

    manifest = _load_json(manifest_path)
    if manifest is None:
        errors.append("manifest.json is not valid JSON")
    else:
        if not isinstance(manifest, dict):
            errors.append("manifest.json is not a JSON object")
        else:
            if not manifest.get("name"):
                errors.append("manifest.json: name is missing or empty")
            if not manifest.get("version"):
                errors.append("manifest.json: version is missing or empty")
            params = manifest.get("parameters")
            if not isinstance(params, dict) or params.get("type") != "OBJECT":
                errors.append("manifest.json: parameters must be an object with type OBJECT")
            if not isinstance(manifest.get("triggers"), list):
                errors.append("manifest.json: triggers must be a list")
            if manifest.get("surface") not in ("desktop", "android", "both"):
                errors.append("manifest.json: surface must be desktop, android, or both")
            if not isinstance(manifest.get("requires"), list):
                errors.append("manifest.json: requires must be a list")

    module = _load_module(name)
    if module is None:
        errors.append("skill.py could not be loaded as a module")
    else:
        metadata = getattr(module, "FEATURE_METADATA", None)
        if manifest is not None and isinstance(manifest, dict) and isinstance(metadata, dict):
            if manifest.get("name") != metadata.get("name"):
                errors.append("manifest name != FEATURE_METADATA name")
            mprops = set((manifest.get("parameters") or {}).get("properties", {}).keys())
            fprops = set((metadata.get("parameters") or {}).get("properties", {}).keys())
            if mprops != fprops:
                errors.append("manifest parameters != FEATURE_METADATA parameters")
            surface = manifest.get("surface")
            if surface not in ("desktop", "android", "both"):
                errors.append("manifest surface invalid")

    return _op("validate", True, {
        "skill": name,
        "valid": len(errors) == 0,
        "errors": errors,
        "error_count": len(errors),
        "note": "Validate is read-only; no files are modified.",
    })


# ------------------------------------------------------------------ compile

def _op_compile(kwargs: dict) -> dict:
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op("compile", False, None, "Provide the skill name (skill=...).")
    skill_py_path = _skill_dir(name) / "skill.py"
    if not skill_py_path.exists():
        return _op("compile", False, None, f"Skill '{name}' skill.py not found.")

    import py_compile
    try:
        py_compile.compile(str(skill_py_path), doraise=True)
    except py_compile.PyCompileError as exc:
        return _op("compile", False, None, {
            "skill": name,
            "file": str(skill_py_path),
            "error": str(exc),
        })
    except Exception as exc:  # noqa: BLE001
        return _op("compile", False, None, f"could not compile: {type(exc).__name__}: {exc}")

    return _op("compile", True, {
        "skill": name,
        "file": str(skill_py_path),
        "note": "skill.py compiles cleanly.",
    })


# ------------------------------------------------------------------ test

def _run_test_case(module, test_case: dict) -> dict[str, Any]:
    name = test_case.get("name", "unnamed")
    operation = test_case.get("operation") or "sources"
    expect_ok = test_case.get("expect_ok", True)
    expect_keys = test_case.get("expect_keys") or []
    kwargs = {k: v for k, v in test_case.items()
              if k not in ("name", "operation", "expect_ok", "expect_keys")}

    try:
        result = module.execute(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return {
            "name": name,
            "operation": operation,
            "passed": False,
            "reason": f"execute() raised {type(exc).__name__}: {exc}",
            "expect_ok": expect_ok,
            "actual_ok": None,
        }

    if not isinstance(result, dict):
        return {
            "name": name,
            "operation": operation,
            "passed": False,
            "reason": "execute() did not return a dict",
            "expect_ok": expect_ok,
            "actual_ok": None,
        }

    actual_ok = bool(result.get("ok"))
    passed = actual_ok == expect_ok
    missing_keys = [k for k in expect_keys if k not in result]
    if missing_keys:
        passed = False

    reason_parts = []
    if actual_ok != expect_ok:
        reason_parts.append(f"expected ok={expect_ok}, got ok={actual_ok}")
    if missing_keys:
        reason_parts.append(f"missing keys: {', '.join(missing_keys)}")
    reason = "; ".join(reason_parts) if reason_parts else "all checks passed"

    return {
        "name": name,
        "operation": operation,
        "passed": passed,
        "reason": reason,
        "expect_ok": expect_ok,
        "actual_ok": actual_ok,
        "missing_keys": missing_keys,
        "result_keys": sorted(result.keys()),
    }


def _op_test(kwargs: dict) -> dict:
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op("test", False, None, "Provide the skill name (skill=...).")
    skill_dir = _skill_dir(name)
    if not skill_dir.is_dir():
        return _op("test", False, None, f"Skill '{name}' not found in features/.")

    test_cases_path = skill_dir / "test_cases.json"
    if not test_cases_path.exists():
        return _op("test", False, None, f"Skill '{name}' has no test_cases.json.")

    test_cases_data = _load_json(test_cases_path)
    if not isinstance(test_cases_data, dict):
        return _op("test", False, None, "test_cases.json is not a JSON object.")
    test_cases = test_cases_data.get("test_cases") or []
    if not isinstance(test_cases, list):
        return _op("test", False, None, "test_cases.json: test_cases is not a list.")

    module = _load_module(name)
    if module is None:
        return _op("test", False, None, f"Skill '{name}' skill.py could not be loaded.")

    results: list[dict[str, Any]] = []
    passed = 0
    for tc in test_cases:
        r = _run_test_case(module, tc)
        results.append(r)
        if r["passed"]:
            passed += 1

    limit = _as_int(kwargs.get("limit"), 20)
    return _op("test", True, {
        "skill": name,
        "results": results[:limit],
        "count": len(results[:limit]),
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "note": f"{passed}/{len(results)} test(s) passed.",
    })


# ------------------------------------------------------------------ build (all)

def _op_build(kwargs: dict) -> dict:
    name = (kwargs.get("skill") or "").strip()
    if not name:
        return _op("build", False, None, "Provide the skill name (skill=...).")
    skill_dir = _skill_dir(name)
    if not skill_dir.is_dir():
        return _op("build", False, None, f"Skill '{name}' not found in features/.")

    validate = _op_validate({"skill": name})
    compile_res = _op_compile({"skill": name})
    test_res = _op_test({"skill": name})

    all_ok = (
        validate.get("ok", False)
        and compile_res.get("ok", False)
        and test_res.get("ok", False)
    )
    errors = []
    if not validate.get("ok", False):
        errors.append("validation failed")
    if not compile_res.get("ok", False):
        errors.append("compile failed")
    if not test_res.get("ok", False):
        errors.append("tests failed")

    return _op("build", all_ok, {
        "skill": name,
        "valid": all_ok,
        "validation": validate.get("value", {}),
        "compile": compile_res.get("value", {}),
        "test": test_res.get("value", {}),
        "errors": errors,
        "note": f"Build {'passed' if all_ok else 'failed'} for '{name}': " +
                f"{test_res.get('value', {}).get('passed', 0)}/{test_res.get('value', {}).get('total', 0)} tests passed.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "list": _op_list,
    "inspect": _op_inspect,
    "validate": _op_validate,
    "compile": _op_compile,
    "test": _op_test,
    "build": _op_build,
}

_OPERATION_TITLES = {
    "sources": "Skill Build Sources",
    "list": "List Skills",
    "inspect": "Inspect Skill",
    "validate": "Validate Skill",
    "compile": "Compile Skill",
    "test": "Test Skill",
    "build": "Build Skill",
}

_ALIASES = {
    "list_skills": "list", "show_skills": "list",
    "inspect_skill": "inspect", "show_skill": "inspect",
    "validate_skill": "validate", "check_manifest": "validate",
    "compile_skill": "compile", "py_compile": "compile",
    "run_tests": "test", "skill_test": "test",
    "full_build": "build", "build_all": "build",
    "sources_list": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "sources":
        return value.get("note", "Skill build available.")
    if operation == "list":
        return f"{value.get('count')} skill(s) available ({value.get('total')} total)."
    if operation == "inspect":
        return f"Inspected {value.get('skill')}: {value.get('test_case_count')} test case(s)."
    if operation == "validate":
        return "valid" if value.get("valid") else f"invalid: {value.get('error_count')} error(s)"
    if operation == "compile":
        return value.get("note", "Compiles cleanly.")
    if operation == "test":
        return f"{value.get('passed')}/{value.get('total')} test(s) passed."
    if operation == "build":
        return value.get("note", "Build complete.")
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Run one skill-build operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Skill Build",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Skill Build",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Skill Build",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Skill build error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Skill Build"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
        "skill": (kwargs.get("skill") or None),
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
