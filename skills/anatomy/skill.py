"""
Feature: anatomy
Description: Build crafted, highly detailed, interactive isometric SVG figures that explain a technical idea as a real physical object. Stella invokes the self-contained Node.js anatomy kit in features/anatomy/ (no external PC-directory references). The skill runs `node features/anatomy/build.mjs` to generate a standalone HTML figure with embedded SVG, returns the SVG markup, the output file path, and the isometric projection used. Read operations (sources, examples, kit, workflow, verify, figure_plan, references) are free; writing a figure file needs authorized=true plus confirm=true plus a policy allow rule.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

FEATURE_METADATA = {
    "name": "anatomy",
    "aliases": ["anatomy", "technical illustration", "isometric figure", "exploded view",
                "technical drawing", "interactive explainer", "svg figure", "webgl shader",
                "anatomy figure", "crafted diagram", "premium technical drawing"],
    "description": (
        "Anatomy: build crafted, highly detailed, interactive isometric SVG figures that "
        "explain a technical idea as a real physical object. Stella invokes the self-contained "
        "Node.js anatomy kit in features/anatomy/ (no external PC-directory references). The "
        "skill runs `node features/anatomy/build.mjs` to generate a standalone HTML figure "
        "with embedded SVG, returns the SVG markup, the output file path, and the isometric "
        "projection used. Read operations (sources, examples, kit, workflow, verify, "
        "figure_plan, references) are free; writing a figure file needs authorized=true plus "
        "confirm=true plus a policy allow rule."
    ),
    "triggers": [
        "anatomy", "technical illustration", "isometric figure", "exploded view",
        "technical drawing", "interactive explainer", "svg figure", "webgl shader",
        "anatomy figure", "crafted diagram", "premium technical drawing",
        "explain how it works", "build a figure", "isometric illustration",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: sources | examples | kit | workflow | verify | figure_plan | build | references. Defaults to sources.",
            },
            "example": {
                "type": "STRING",
                "description": "Name of an example to build (examples/build operation). Defaults to dial-indicator.",
            },
            "module": {
                "type": "STRING",
                "description": "Name of a kit module to describe (kit operation).",
            },
            "concept": {
                "type": "STRING",
                "description": "The technical idea to explain (figure_plan operation).",
            },
            "size": {
                "type": "STRING",
                "description": "Figure size tier: Figure | Hero | Epic (figure_plan operation). Defaults to Figure.",
            },
            "theme": {
                "type": "STRING",
                "description": "Figure theme: dark | light (build operation). Defaults to dark.",
            },
            "width": {
                "type": "INTEGER",
                "description": "Figure width in pixels (build operation). Defaults to 600.",
            },
            "height": {
                "type": "INTEGER",
                "description": "Figure height in pixels (build operation). Defaults to 380.",
            },
            "turn": {
                "type": "NUMBER",
                "description": "Dial turns for the needle position (dial-indicator build). Defaults to 0.9.",
            },
            "authorized": {
                "type": "BOOLEAN",
                "description": "Must be true for any operation that writes a figure file (build).",
            },
            "confirm": {
                "type": "BOOLEAN",
                "description": "Must be true to actually write a figure file (build).",
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
    "category": "development",
    "surface": "desktop",
    "requires": ["node"],
    "optional_dependencies": [],
    "notes": "Self-contained Node.js kit in features/anatomy/kit/ and features/anatomy/build.mjs. No symlinks or references to any PC skill directory. Build writes to features/anatomy/out/ and needs authorized=true + confirm=true + an allow rule.",
}

_EXAMPLES: dict[str, dict[str, Any]] = {
    "dial-indicator": {
        "name": "dial-indicator",
        "description": "A dial gauge on a surface plate with a magnetic base, post, arm and sliding carriage on gauge blocks - the smallest complete figure.",
        "parts": "~300 SVG elements",
        "best_for": "A quick explainer of a single instrument or gauge.",
        "build_ok": True,
    },
}

_KIT_MODULES: dict[str, dict[str, Any]] = {
    "iso-kit": {
        "name": "iso-kit",
        "description": "Core isometric projection + SVG primitives: cameraOf, iso, fitProjection, slabOf, cylinder, ring, sideArc, knurl, figureSvg, plateHtml.",
        "file": "features/anatomy/kit/iso-kit.mjs",
    },
    "build": {
        "name": "build",
        "description": "Entry point Stella invokes: reads a JSON spec, builds a figure, writes an HTML file, returns SVG + path.",
        "file": "features/anatomy/build.mjs",
    },
}

_WORKFLOW: list[str] = [
    "1. Size it - name the tier (Figure/Hero/Epic) and estimate before any geometry.",
    "2. Truth first - collect the real numbers and behaviour of the thing being explained.",
    "3. Invent the object - pick a machine whose mechanism maps one-to-one onto the concept.",
    "4. Parts list - write at least 40 parts grouped into base, structure, mechanism, controls and subject.",
    "5. Plan the world - world units ~1px, camera azimuth 45 deg, elevation 30-44 deg.",
    "6. Build geometry once - precompute static paths; moving parts built once at rest.",
    "7. Paint back to front, bottom to top - depth-sort; split wrapping parts into back/front halves.",
    "8. Frame it - card with Fig n, title, hint and live readout.",
    "9. Make it live - calm time-based motion, pointer/keyboard response, reduced-motion still.",
    "10. Verify like a critic - zoom in first; audit to zero, line check to zero, 4x close-ups, shaders.",
]

_VERIFY: list[str] = [
    "Run the audit to zero: node build.mjs --audit must end 'audit passed'.",
    "Run the line check to zero: scripts/lines.mjs must print 'line ends: 0'.",
    "4x close-ups of every junction in both themes (build --light too).",
    "Shaders: contact sheet slowed across every transition; nothing pops.",
    "Read every PNG you make; is it instantly a real object, rich in small parts?",
]

_REFERENCES: list[str] = [
    "kit/iso-kit.mjs - isometric projection + SVG primitives (self-contained in features/anatomy/kit/)",
    "build.mjs - entry point Stella invokes via `node`",
    "craft.md - parts vocabulary and recipes",
    "motion.md - calm time-based motion and pointer/keyboard response",
    "verify.md - verification checklist",
    "3d.md - true 3D mode",
    "print.md - A4 PDF printing",
    "publish.md - community gallery publishing",
    "webgl.md - WebGL shaders inside the drawing",
]


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


def _as_float(value, default: float = 0.9) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _node_available() -> bool:
    return shutil.which("node") is not None


def _build_mjs_path() -> Path | None:
    """Resolve build.mjs relative to this skill package - never a PC directory."""
    here = Path(__file__).resolve().parent
    build = here / "build.mjs"
    if build.exists():
        return build
    return None


def _run_node(spec: dict) -> dict:
    """Invoke `node features/anatomy/build.mjs <spec>` and return the parsed result."""
    build = _build_mjs_path()
    if build is None:
        return {"ok": False, "error": "anatomy build.mjs not found in features/anatomy/"}
    if not _node_available():
        return {"ok": False, "error": "node is not installed on this machine; anatomy figures cannot be built."}
    try:
        proc = subprocess.run(
            ["node", str(build), json.dumps(spec)],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            return {"ok": False, "error": f"node build failed (exit {proc.returncode}): {proc.stderr.strip()[:500]}"}
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "error": f"node build did not return JSON: {proc.stdout[:500]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "node build timed out after 60s"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"could not invoke node build: {type(exc).__name__}: {exc}"}


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "anatomy (self-contained Node.js kit in features/anatomy/)",
        "kit_dir": "features/anatomy/kit/",
        "build_entry": "features/anatomy/build.mjs",
        "output_dir": "features/anatomy/out/",
        "node_required": True,
        "node_available": _node_available(),
        "examples": len(_EXAMPLES),
        "kit_modules": len(_KIT_MODULES),
        "workflow_steps": len(_WORKFLOW),
        "verify_checks": len(_VERIFY),
        "note": "Stella never symlinks to or references any PC skill directory. Everything lives in features/anatomy/.",
    })


def _op_examples(kwargs: dict) -> dict:
    operation = "examples"
    limit = _as_int(kwargs.get("limit"), 20)
    name = (kwargs.get("example") or "").strip()
    if name:
        ex = _EXAMPLES.get(name.lower())
        if not ex:
            return _op(operation, False, None, f"Unknown example '{name}'. Known: {', '.join(sorted(_EXAMPLES))}.")
        return _op(operation, True, {"example": ex, "count": 1})
    items = list(_EXAMPLES.items())[:limit]
    return _op(operation, True, {
        "examples": [{**v, "key": k} for k, v in items],
        "count": len(items),
        "total": len(_EXAMPLES),
    })


def _op_kit(kwargs: dict) -> dict:
    operation = "kit"
    limit = _as_int(kwargs.get("limit"), 20)
    name = (kwargs.get("module") or "").strip()
    if name:
        mod = _KIT_MODULES.get(name.lower())
        if not mod:
            return _op(operation, False, None, f"Unknown kit module '{name}'. Known: {', '.join(sorted(_KIT_MODULES))}.")
        return _op(operation, True, {"module": mod, "count": 1})
    items = list(_KIT_MODULES.items())[:limit]
    return _op(operation, True, {
        "modules": [{**v, "key": k} for k, v in items],
        "count": len(items),
        "total": len(_KIT_MODULES),
    })


def _op_workflow(kwargs: dict) -> dict:
    return _op("workflow", True, {
        "steps": _WORKFLOW,
        "count": len(_WORKFLOW),
        "note": "Work in this order; most quality is decided before any geometry.",
    })


def _op_verify(kwargs: dict) -> dict:
    return _op("verify", True, {
        "checks": _VERIFY,
        "count": len(_VERIFY),
        "note": "Verify like a critic - zoom in first, read every PNG.",
    })


def _op_figure_plan(kwargs: dict) -> dict:
    operation = "figure_plan"
    concept = (kwargs.get("concept") or "").strip()
    if not concept:
        return _op(operation, False, None, "Provide the technical idea to explain (concept=...).")
    size = (kwargs.get("size") or "Figure").strip()
    valid_sizes = {"Figure", "Hero", "Epic"}
    if size not in valid_sizes:
        return _op(operation, False, None, f"Size must be one of {sorted(valid_sizes)}.")
    estimates = {
        "Figure": "40-80 parts, SVG with at most one WebGL layer, under an hour.",
        "Hero": "80-150 parts, several WebGL layers or one 3D subject, about 2-4 hours.",
        "Epic": "Whole vehicle/building/plant or 3D on multiple subjects, 6 hours or more.",
    }
    plan = {
        "concept": concept,
        "size": size,
        "estimate": estimates[size],
        "object_invention": "Invent a real physical thing whose working is the concept.",
        "workflow_steps": _WORKFLOW,
        "verify_checks": _VERIFY,
        "buildable_with_stella": size == "Figure",
        "note": "Read-only plan. Building a Figure needs node + authorized=true + confirm=true + an allow rule.",
    }
    if size == "Epic":
        plan["warning"] = "Epic figures need explicit authorization; propose a Hero version first."
    return _op(operation, True, plan)


def _op_references(kwargs: dict) -> dict:
    return _op("references", True, {
        "references": _REFERENCES,
        "count": len(_REFERENCES),
        "note": "Reference files live in features/anatomy/ (self-contained).",
    })


def _op_build(kwargs: dict) -> dict:
    operation = "build"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Building a figure writes an HTML file to features/anatomy/out/, so it needs "
            "authorized=true AND confirm=true plus an allow rule in config/tool_policy.json."))
    if not _node_available():
        return _op(operation, False, None, "node is not installed on this machine; anatomy figures cannot be built.")
    example = (kwargs.get("example") or "dial-indicator").strip()
    spec = {
        "example": example,
        "theme": (kwargs.get("theme") or "dark").strip(),
        "width": _as_int(kwargs.get("width"), 600),
        "height": _as_int(kwargs.get("height"), 380),
        "turn": _as_float(kwargs.get("turn"), 0.9),
        "fig": kwargs.get("fig") or "Fig 1",
        "title": kwargs.get("title") or "Dial indicator",
        "hint": kwargs.get("hint") or "Interactive isometric figure generated by Stella's anatomy skill",
        "readout": kwargs.get("readout") or "block 1 · reads 18.0 px",
        "caption": kwargs.get("caption") or "A dial indicator on a surface plate.",
    }
    result = _run_node(spec)
    if not result.get("ok"):
        return _op(operation, False, None, result.get("error", "node build failed"))
    return _op(operation, True, {
        "example": result.get("example"),
        "theme": result.get("theme"),
        "width": result.get("width"),
        "height": result.get("height"),
        "html_path": result.get("html_path"),
        "svg": result.get("svg"),
        "projection": result.get("projection"),
        "note": f"Figure '{example}' built at {result.get('html_path')}.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "examples": _op_examples,
    "kit": _op_kit,
    "workflow": _op_workflow,
    "verify": _op_verify,
    "figure_plan": _op_figure_plan,
    "references": _op_references,
    "build": _op_build,
}

_OPERATION_TITLES = {
    "sources": "Anatomy Sources",
    "examples": "Anatomy Examples",
    "kit": "Anatomy Kit Modules",
    "workflow": "Anatomy Workflow",
    "verify": "Anatomy Verification",
    "figure_plan": "Anatomy Figure Plan",
    "references": "Anatomy References",
    "build": "Anatomy Build",
}

_ALIASES = {
    "list_examples": "examples", "example_list": "examples",
    "list_modules": "kit", "kit_modules": "kit",
    "anatomy_workflow": "workflow", "anatomy_verify": "verify",
    "plan_figure": "figure_plan", "figureplan": "figure_plan",
    "references_list": "references",
    "sources_list": "sources",
    "build_figure": "build", "make_figure": "build",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "sources":
        return f"{value.get('examples')} examples, {value.get('kit_modules')} kit modules; node_available={value.get('node_available')}. {value.get('note')}"
    if operation == "examples":
        return f"{value.get('count')} example(s) of {value.get('total')}."
    if operation == "kit":
        return f"{value.get('count')} kit module(s) of {value.get('total')}."
    if operation == "workflow":
        return f"{value.get('count')} workflow step(s)."
    if operation == "verify":
        return f"{value.get('count')} verify check(s)."
    if operation == "figure_plan":
        return f"Plan for '{value.get('concept')}': {value.get('size')} - {value.get('estimate')}."
    if operation == "references":
        return f"{len(value.get('references') or [])} reference topic(s)."
    if operation == "build":
        return f"Built {value.get('example')} ({value.get('theme')}) at {value.get('html_path')}."
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Run one anatomy operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Anatomy",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Anatomy",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Anatomy",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Anatomy error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Anatomy"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
