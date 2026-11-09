from __future__ import annotations
from typing import Any, Dict
import os, subprocess, sys, venv, pathlib, shutil, json

FEATURE_METADATA = {
    "name": "hummingbot_installer",
    "description": "Ensure Hummingbot (and its Python deps) are installed in a dedicated venv.",
    "triggers": ["install hummingbot", "bootstrap hummingbot"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "force_reinstall": {"type": "BOOLEAN", "default": False}
        },
        "required": []
    }
}

STELLA_ROOT = pathlib.Path(r"E:\Projects\stella")
VENV_DIR    = STELLA_ROOT / "venvs" / "hummingbot"
HB_BIN      = VENV_DIR / ("Scripts" if os.name == "nt" else "bin") / ("hummingbot.exe" if os.name == "nt" else "hummingbot")

def _venv_exists() -> bool:
    return HB_BIN.exists()

def _create_venv() -> None:
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR)
    builder = venv.EnvBuilder(with_pip=True)
    builder.create(VENV_DIR)
    pip = VENV_DIR / ("Scripts" if os.name == "nt" else "bin") / ("pip.exe" if os.name == "nt" else "pip")
    subprocess.check_call([str(pip), "install", "--upgrade", "pip", "setuptools", "wheel"])
    subprocess.check_call([str(pip), "install", "hummingbot"])
    (VENV_DIR / ".stella_hummingbot").write_text(json.dumps({"version": "auto"}))

def _ensure_installed(force: bool = False) -> Dict[str, Any]:
    if not _venv_exists() or force:
        try:
            _create_venv()
        except Exception as e:
            return {"ok": False, "error": f"Failed to create/install hummingbot venv: {e}"}
    return {"ok": True, "hummingbot_bin": str(HB_BIN)}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    force = bool(params.get("force_reinstall", False))
    return _ensure_installed(force)


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_install(kwargs: dict) -> dict:
    force = bool(kwargs.get("force_reinstall", False))
    return _op("install", True, _ensure_installed(force))


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["hummingbot"],
        "content": "Hummingbot installation via venv (hummingbot.org).",
    })


_OPERATIONS = {
    "install": _op_install,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "install": "Hummingbot Installer",
    "sources": "Hummingbot Sources",
}

_ALIASES = {
    "install": "install",
    "bootstrap": "install",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "install":
        return f"Hummingbot installed: {value.get('hummingbot_bin', 'N/A')}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Ensure Hummingbot (and its Python deps) are installed in a dedicated venv."""
    operation = (kwargs.get("operation") or "install").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Hummingbot Installer",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Hummingbot Installer",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Hummingbot Installer",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Installer error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Hummingbot Installer"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))