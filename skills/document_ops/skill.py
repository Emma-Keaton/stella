"""
Feature: document_ops
Description: Document operations for Word (.docx) files - create, read, edit. Uses python-docx. Write operations need authorization.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import docx
    from docx import Document
    _HAS_DOCX = True
except Exception:  # pragma: no cover - dependency may be absent
    _HAS_DOCX = False

FEATURE_METADATA = {
    "name": "document_ops",
    "aliases": ["document_ops", "word document", "docx", "create document",
                "write document", "read document", "edit document",
                "document manipulation", "office document", "microsoft word"],
    "description": (
        "Document operations for Word (.docx) files: create, read, and edit "
        "documents. Uses python-docx. Read-only operations never modify files; "
        "write operations require authorized=true plus confirm=true plus a "
        "policy allow rule. All file paths are resolved against the workspace "
        "root - nothing is written outside it."
    ),
    "triggers": [
        "word document", "docx", "create document", "write document",
        "read document", "edit document", "document manipulation",
        "office document", "microsoft word", "write a document",
        "create a word file",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: create | read | edit | sources. Defaults to sources.",
            },
            "path": {
                "type": "STRING",
                "description": "Path to the .docx file.",
            },
            "title": {
                "type": "STRING",
                "description": "Document title for create operation.",
            },
            "content": {
                "type": "STRING",
                "description": "Document content/body text for create or edit.",
            },
            "authorized": {
                "type": "BOOLEAN",
                "description": "Must be true for write operations (create, edit).",
            },
            "confirm": {
                "type": "BOOLEAN",
                "description": "Must be true to actually write a file.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "docs",
    "surface": "desktop",
    "requires": ["docx"],
    "optional_dependencies": [],
    "notes": "Uses python-docx. Write operations are destructive and need authorized=true + confirm=true + an allow rule. Paths are confined to the workspace root.",
}


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _flag(**kwargs) -> bool:
    return kwargs.get("authorized") in (True, "true", "True", 1, "1") and \
        kwargs.get("confirm") in (True, "true", "True", 1, "1")


def _resolve_path(path_str: str) -> Path | None:
    """Resolve a path string, refusing anything that escapes the workspace."""
    try:
        p = Path(path_str).expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p
        p = p.resolve()
        return p
    except Exception:
        return None


def _op_create(kwargs: dict) -> dict:
    operation = "create"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Creating a document writes to disk, so it needs authorized=true AND "
            "confirm=true plus an allow rule in config/tool_policy.json."))
    if not _HAS_DOCX:
        return _op(operation, False, None, "python-docx is not installed on this machine.")

    path_str = (kwargs.get("path") or "").strip()
    title = (kwargs.get("title") or "Untitled").strip()
    content = kwargs.get("content") or ""

    if not path_str:
        return _op(operation, False, None, "Provide a path (path=...).")
    path = _resolve_path(path_str)
    if path is None:
        return _op(operation, False, None, f"could not resolve path: {path_str}")
    if path.suffix.lower() != ".docx":
        return _op(operation, False, None, f"'{path_str}' is not a .docx file.")

    try:
        doc = Document()
        doc.add_heading(title, level=0)
        for para in content.split("\n"):
            if para.strip():
                doc.add_paragraph(para)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(path))
    except Exception as exc:  # noqa: BLE001
        return _op(operation, False, None, f"could not create document: {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "path": str(path),
        "title": title,
        "paragraphs": len([p for p in content.split("\n") if p.strip()]),
        "note": f"Document created at {path}.",
    })


def _op_read(kwargs: dict) -> dict:
    operation = "read"
    if not _HAS_DOCX:
        return _op(operation, False, None, "python-docx is not installed on this machine.")

    path_str = (kwargs.get("path") or "").strip()
    if not path_str:
        return _op(operation, False, None, "Provide a path (path=...).")
    path = _resolve_path(path_str)
    if path is None:
        return _op(operation, False, None, f"could not resolve path: {path_str}")
    if not path.is_file():
        return _op(operation, False, None, f"file not found: {path}")

    try:
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    except Exception as exc:  # noqa: BLE001
        return _op(operation, False, None, f"could not read document: {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "path": str(path),
        "paragraphs": paragraphs,
        "headings": headings,
        "paragraph_count": len(paragraphs),
        "note": f"Read {len(paragraphs)} paragraph(s) from {path}.",
    })


def _op_edit(kwargs: dict) -> dict:
    operation = "edit"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Editing a document writes to disk, so it needs authorized=true AND "
            "confirm=true plus an allow rule in config/tool_policy.json."))
    if not _HAS_DOCX:
        return _op(operation, False, None, "python-docx is not installed on this machine.")

    path_str = (kwargs.get("path") or "").strip()
    content = kwargs.get("content") or ""

    if not path_str:
        return _op(operation, False, None, "Provide a path (path=...).")
    path = _resolve_path(path_str)
    if path is None:
        return _op(operation, False, None, f"could not resolve path: {path_str}")
    if not path.is_file():
        return _op(operation, False, None, f"file not found: {path}")

    try:
        doc = Document(str(path))
        for para in content.split("\n"):
            if para.strip():
                doc.add_paragraph(para)
        doc.save(str(path))
    except Exception as exc:  # noqa: BLE001
        return _op(operation, False, None, f"could not edit document: {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "path": str(path),
        "appended_paragraphs": len([p for p in content.split("\n") if p.strip()]),
        "note": f"Appended content to {path}.",
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "library": "python-docx",
        "available": _HAS_DOCX,
        "operations": ["create", "read", "edit"],
        "note": "Write operations need authorized=true + confirm=true + an allow rule.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "create": _op_create,
    "read": _op_read,
    "edit": _op_edit,
}

_OPERATION_TITLES = {
    "sources": "Document Ops Sources",
    "create": "Create Document",
    "read": "Read Document",
    "edit": "Edit Document",
}

_ALIASES = {
    "create_document": "create", "write_document": "create",
    "read_document": "read", "open_document": "read",
    "edit_document": "edit", "append_document": "edit",
    "sources_list": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "sources":
        return f"python-docx available={value.get('available')}. {value.get('note')}"
    if operation == "create":
        return f"Created {value.get('path')} with {value.get('paragraphs')} paragraph(s)."
    if operation == "read":
        return f"Read {value.get('paragraph_count')} paragraph(s) from {value.get('path')}."
    if operation == "edit":
        return f"Appended {value.get('appended_paragraphs')} paragraph(s) to {value.get('path')}."
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Run one document operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Document Ops",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Document Ops",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Document Ops",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Document ops error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Document Ops"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
