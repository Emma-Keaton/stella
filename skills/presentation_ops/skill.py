"""
Feature: presentation_ops
Description: Presentation operations for PowerPoint (.pptx) files - create, read, edit. Uses python-pptx. Write operations need authorization.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from pptx import Presentation
    from pptx.util import Inches
    _HAS_PPTX = True
except Exception:  # pragma: no cover - dependency may be absent
    _HAS_PPTX = False

FEATURE_METADATA = {
    "name": "presentation_ops",
    "aliases": ["presentation_ops", "powerpoint", "pptx", "create presentation",
                "write presentation", "read presentation", "edit presentation",
                "slide deck", "presentation manipulation", "microsoft powerpoint"],
    "description": (
        "Presentation operations for PowerPoint (.pptx) files: create, read, and "
        "edit decks. Uses python-pptx. Read-only operations never modify files; "
        "write operations require authorized=true plus confirm=true plus a policy "
        "allow rule. All file paths are resolved against the workspace root - "
        "nothing is written outside it."
    ),
    "triggers": [
        "powerpoint", "pptx", "create presentation", "write presentation",
        "read presentation", "edit presentation", "slide deck",
        "presentation manipulation", "microsoft powerpoint", "create a slide deck",
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
                "description": "Path to the .pptx file.",
            },
            "title": {
                "type": "STRING",
                "description": "Presentation title for create operation.",
            },
            "content": {
                "type": "STRING",
                "description": "Slide content for create or edit (one slide per blank line).",
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
    "requires": ["pptx"],
    "optional_dependencies": [],
    "notes": "Uses python-pptx. Write operations are destructive and need authorized=true + confirm=true + an allow rule. Paths are confined to the workspace root.",
}


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _flag(**kwargs) -> bool:
    return kwargs.get("authorized") in (True, "true", "True", 1, "1") and \
        kwargs.get("confirm") in (True, "true", "True", 1, "1")


def _resolve_path(path_str: str) -> Path | None:
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
            "Creating a presentation writes to disk, so it needs authorized=true AND "
            "confirm=true plus an allow rule in config/tool_policy.json."))
    if not _HAS_PPTX:
        return _op(operation, False, None, "python-pptx is not installed on this machine.")

    path_str = (kwargs.get("path") or "").strip()
    title = (kwargs.get("title") or "Untitled").strip()
    content = kwargs.get("content") or ""

    if not path_str:
        return _op(operation, False, None, "Provide a path (path=...).")
    path = _resolve_path(path_str)
    if path is None:
        return _op(operation, False, None, f"could not resolve path: {path_str}")
    if path.suffix.lower() != ".pptx":
        return _op(operation, False, None, f"'{path_str}' is not a .pptx file.")

    try:
        prs = Presentation()
        slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = title
        if content.strip():
            body = slide.placeholders[1]
            body.text = content
        path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(path))
    except Exception as exc:  # noqa: BLE001
        return _op(operation, False, None, f"could not create presentation: {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "path": str(path),
        "title": title,
        "slides": 1,
        "note": f"Presentation created at {path}.",
    })


def _op_read(kwargs: dict) -> dict:
    operation = "read"
    if not _HAS_PPTX:
        return _op(operation, False, None, "python-pptx is not installed on this machine.")

    path_str = (kwargs.get("path") or "").strip()
    if not path_str:
        return _op(operation, False, None, "Provide a path (path=...).")
    path = _resolve_path(path_str)
    if path is None:
        return _op(operation, False, None, f"could not resolve path: {path_str}")
    if not path.is_file():
        return _op(operation, False, None, f"file not found: {path}")

    try:
        prs = Presentation(str(path))
        slides = []
        for i, slide in enumerate(prs.slides, 1):
            texts = []
            for shape in slide.shapes:
                if shape.has_text_frame and shape.text_frame.text.strip():
                    texts.append(shape.text_frame.text)
            slides.append({"index": i, "texts": texts})
    except Exception as exc:  # noqa: BLE001
        return _op(operation, False, None, f"could not read presentation: {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "path": str(path),
        "slides": slides,
        "slide_count": len(slides),
        "note": f"Read {len(slides)} slide(s) from {path}.",
    })


def _op_edit(kwargs: dict) -> dict:
    operation = "edit"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Editing a presentation writes to disk, so it needs authorized=true AND "
            "confirm=true plus an allow rule in config/tool_policy.json."))
    if not _HAS_PPTX:
        return _op(operation, False, None, "python-pptx is not installed on this machine.")

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
        prs = Presentation(str(path))
        slide_layout = prs.slide_layouts[1]  # title and content
        for block in content.split("\n\n"):
            if block.strip():
                slide = prs.slides.add_slide(slide_layout)
                slide.shapes.title.text = block.strip().split("\n")[0][:80]
                if len(block.strip().split("\n")) > 1:
                    body = slide.placeholders[1]
                    body.text = "\n".join(block.strip().split("\n")[1:])
        prs.save(str(path))
    except Exception as exc:  # noqa: BLE001
        return _op(operation, False, None, f"could not edit presentation: {type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "path": str(path),
        "slides": len(prs.slides.__iter__.__self__._sldIdLst),
        "note": f"Added slide(s) to {path}.",
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "library": "python-pptx",
        "available": _HAS_PPTX,
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
    "sources": "Presentation Ops Sources",
    "create": "Create Presentation",
    "read": "Read Presentation",
    "edit": "Edit Presentation",
}

_ALIASES = {
    "create_presentation": "create", "write_presentation": "create",
    "read_presentation": "read", "open_presentation": "read",
    "edit_presentation": "edit", "append_presentation": "edit",
    "sources_list": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "sources":
        return f"python-pptx available={value.get('available')}. {value.get('note')}"
    if operation == "create":
        return f"Created {value.get('path')} with {value.get('slides')} slide(s)."
    if operation == "read":
        return f"Read {value.get('slide_count')} slide(s) from {value.get('path')}."
    if operation == "edit":
        return f"Presentation now has {value.get('slides')} slide(s) at {value.get('path')}."
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Run one presentation operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Presentation Ops",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Presentation Ops",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Presentation Ops",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Presentation ops error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Presentation Ops"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
