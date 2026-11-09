"""
Feature: reverse_engineer_anything
Description: Reverse engineer shipped software with plain local tools, no MCP
server required. Explains how a feature works, extracts versions/dependencies,
compares builds, or rebuilds a feature into a user-specified destination project.
Routes by file type first, then runs the cheapest inventory before any
decompilation. Never fabricates findings; reports what can and cannot work so
the user can plan workarounds.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict

FEATURE_METADATA: Dict[str, Any] = {
    "name": "reverse_engineer_anything",
    "aliases": ["rea", "reverse engineer", "reverse-engineer-anything", "extract features", "rebuild app"],
    "description": (
        "Reverse engineer shipped software (APK, native binary, Electron app, "
        "managed assembly, firmware, website, sqlite, pcap) using only tools "
        "already on this machine. Explains features, compares versions, or "
        "rebuilds extracted features into a destination project you specify. "
        "Reports what can and cannot work so you can plan workarounds."
    ),
    "triggers": [
        "reverse engineer", "reverse-engineer", "extract features", "rebuild app",
        "decompile apk", "inspect binary", "rea ", "reverse engineer anything",
        "explain how this feature works", "compare builds",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: analyze | extract | apply | graph | backends | static_scan. Defaults to analyze.",
            },
            "target": {
                "type": "STRING",
                "description": "Path to the artefact to reverse engineer (APK, EXE, ELF, Mach-O, ASAR, zip, sqlite, pcap, etc.).",
            },
            "destination": {
                "type": "STRING",
                "description": "Explicit destination project directory for apply operations. Never inferred.",
            },
            "kind": {
                "type": "STRING",
                "description": "Extraction kind: android | native | dynamic | auto. Defaults to auto.",
            },
            "files": {
                "type": "STRING",
                "description": "JSON object mapping destination-relative paths to file contents (apply operation).",
            },
            "confirm": {
                "type": "BOOLEAN",
                "description": "Must be true to actually write files to a destination. Defaults to false (preview only).",
            },
            "script": {
                "type": "STRING",
                "description": "JavaScript snippet for dynamic (Frida) extraction.",
            },
            "device": {
                "type": "STRING",
                "description": "Remote Frida device id for dynamic extraction.",
            },
            "workdir": {
                "type": "STRING",
                "description": "Directory for intermediate extraction output.",
            },
            "patterns": {
                "type": "STRING",
                "description": "Comma-separated patterns for static_scan (default scans for common REA-relevant tokens).",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
}


def _stella_rea_available() -> bool:
    """True when the bundled stella-rea package can be imported."""
    try:
        import stella_rea  # type: ignore[import-not-found]
        return True
    except Exception:
        return False


def _import_stella_rea():
    """Import stella_rea defensively, returning (module, error_or_None)."""
    try:
        import stella_rea  # type: ignore[import-not-found]
        return stella_rea, None
    except Exception as exc:
        return None, exc


def _which(binary: str) -> str | None:
    return shutil.which(binary)


def _summarize_backends() -> list[dict[str, Any]]:
    """List available RE backends with honest availability status."""
    backends = [
        {"name": "jadx", "binary": "jadx", "kind": "static", "targets": "APK / DEX / AAB"},
        {"name": "ghidra", "binary": "analyzeHeadless", "kind": "static", "targets": "native ELF / PE / Mach-O"},
        {"name": "frida", "binary": "frida", "kind": "dynamic", "targets": "running process"},
        {"name": "static_scan", "binary": None, "kind": "static", "targets": "source tree (always available)"},
    ]
    out = []
    for b in backends:
        entry = dict(b)
        if b["binary"] is None:
            entry["available"] = True
            entry["status"] = "available"
        else:
            found = _which(b["binary"]) is not None
            entry["available"] = found
            entry["status"] = "available" if found else "not installed"
        out.append(entry)
    return out


def _op(cmd: str, ok: bool, value: Any = None, error: str | None = None) -> dict[str, Any]:
    return {"operation": cmd, "ok": ok, "value": value, "error": error}


def _static_scan(root: Path, patterns: list[str]) -> dict[str, Any]:
    """Always-available static scan; no external binary required."""
    if not root.exists():
        return _op("static_scan", False, error=f"scan root does not exist: {root}")
    if not root.is_dir():
        return _op("static_scan", False, error=f"scan root is not a directory: {root}")

    provenance = ("static_scan",)
    records = []
    for needle in patterns:
        hits: list[str] = []
        try:
            for candidate in sorted(root.rglob("*")):
                if not candidate.is_file():
                    continue
                try:
                    text = candidate.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if needle in text:
                    hits.append(str(candidate))
                    if len(hits) >= 200:
                        break
        except OSError:
            continue
        if hits:
            records.append({
                "claim": f"pattern {needle!r} appears in {len(hits)} file(s)",
                "source": "static_scan",
                "confidence": "high",
                "found": True,
                "detail": {"pattern": needle, "files": hits},
                "locator": str(root),
            })
        else:
            records.append({
                "claim": f"pattern {needle!r} was not found",
                "source": "static_scan",
                "confidence": "medium",
                "found": False,
                "detail": {"pattern": needle},
                "locator": str(root),
            })
    return _op("static_scan", True, value={
        "target": str(root),
        "records": records,
        "positives": [r for r in records if r["found"]],
        "absences": [r for r in records if not r["found"]],
    })


def _default_patterns() -> list[str]:
    return [
        "exposeInMainWorld", "ipcMain", "ipcRenderer", "contextBridge",
        "DllImport", "P/Invoke", "jadx", "ghidra", "frida",
        "AndroidManifest.xml", "classes.dex", "sourceMappingURL",
        "webpack", "vite", "asar",
    ]


def execute(**kwargs) -> Dict[str, Any]:
    """Reverse engineer a target using only tools present on this machine.

    Supported operations:
      - analyze: report destination project type + available backends
      - extract: decompile/inspect a target artefact
      - apply: write extracted features to an explicit destination (confirm required)
      - graph: build/inspect/render an stella-rea graph
      - backends: list which RE backends are installed
      - static_scan: scan a source tree for patterns (always available)
    """
    stella_rea, import_error = _import_stella_rea()

    operation = (kwargs.get("operation") or "analyze").strip().lower()
    target = kwargs.get("target")
    destination = kwargs.get("destination")
    kind = (kwargs.get("kind") or "auto").strip().lower()
    files_raw = kwargs.get("files")
    confirm = bool(kwargs.get("confirm", False))
    script = kwargs.get("script")
    device = kwargs.get("device")
    workdir = kwargs.get("workdir")
    patterns_raw = kwargs.get("patterns")

    # ------------------------------------------------------------------
    # backends — always answerable, tells the user what can/cannot work
    # ------------------------------------------------------------------
    if operation == "backends":
        return {
            "title": "REA Backends",
            "summary": "Available reverse-engineering backends on this machine.",
            "backends": _summarize_backends(),
            "stella_rea_available": bool(stella_rea),
            "import_error": str(import_error) if import_error else None,
            "spoken_narrative": "Here are the reverse-engineering backends available on this machine.",
        }

    # ------------------------------------------------------------------
    # static_scan — always available, no external binary needed
    # ------------------------------------------------------------------
    if operation == "static_scan":
        root = Path(target) if target else Path.cwd()
        patterns = [p.strip() for p in patterns_raw.split(",")] if patterns_raw else _default_patterns()
        result = _static_scan(root, patterns)
        return {
            "title": "Static Scan",
            "summary": f"Scanned {root} for {len(patterns)} pattern(s).",
            "result": result,
            "spoken_narrative": f"Static scan complete. {sum(1 for r in result.get('value', {}).get('records', []) if r['found'])} pattern(s) found.",
        }

    # ------------------------------------------------------------------
    # Everything below needs stella-rea. Report honestly if missing.
    # ------------------------------------------------------------------
    if not stella_rea:
        backends = _summarize_backends()
        return {
            "title": "REA Unavailable",
            "summary": (
                "The bundled stella-rea package is not importable on this machine, "
                "so extract/apply/graph operations cannot run. Static scan and "
                "backends listing still work."
            ),
            "backends": backends,
            "stella_rea_available": False,
            "import_error": str(import_error) if import_error else None,
            "workaround": "Ensure E:\\Projects\\stella\\stella-rea is on the Python path, or install stella-rea.",
            "spoken_narrative": "stella-rea is not importable here, so extraction and apply operations are unavailable.",
        }

    from stella_rea import (
        ProjectType,
        detect_project_type,
        open_destination,
        plan_write,
    )
    from stella_rea.extraction import (
        available_backends,
        extract_dynamic,
        extract_generic,
        static_scan,
    )
    from stella_rea.errors import (
        BackendUnavailable,
        ConfirmationRequired,
        DestinationUnknown,
        ExecutionFailed,
        PathEscape,
        StellaReaError,
        ValidationError,
    )

    # ------------------------------------------------------------------
    # analyze — report destination + backends
    # ------------------------------------------------------------------
    if operation == "analyze":
        dest_path = destination or (str(target) if target else str(Path.cwd()))
        root = Path(dest_path)
        try:
            dest = open_destination(dest_path, project_type=None)
            backend_list = available_backends()
            return {
                "title": "Analyze Destination",
                "summary": f"Destination {dest.path} is a {dest.project_type} project.",
                "destination": str(dest.path),
                "project_type": dest.project_type,
                "backends": backend_list,
                "spoken_narrative": f"Analyzed {dest.path}; it is a {dest.project_type} project with {sum(1 for b in backend_list if b.get('available'))} backend(s) available.",
            }
        except DestinationUnknown as exc:
            return {
                "title": "Analyze Destination",
                "summary": f"Could not determine project type for {dest_path}.",
                "destination": dest_path,
                "project_type": "unknown",
                "error": exc.message,
                "backends": available_backends(),
                "workaround": "Pass an explicit project type (android/kotlin, python, node/ts, rust) or add a marker file.",
                "spoken_narrative": f"Could not determine the project type for {dest_path}.",
            }
        except (ValidationError, StellaReaError) as exc:
            return _op_result("analyze", False, error=getattr(exc, "message", str(exc)))

    # ------------------------------------------------------------------
    # extract — decompile/inspect a target
    # ------------------------------------------------------------------
    if operation == "extract":
        if not target:
            return _op_result("extract", False, error="target is required for extract")
        root = Path(target)
        if not root.exists():
            return _op_result("extract", False, error=f"target does not exist: {target}")
        try:
            bundle = extract_generic(target, kind=kind, workdir=workdir)
            payload = bundle.to_dict()
            positives = [r for r in payload["records"] if r.get("found")]
            absences = [r for r in payload["records"] if not r.get("found")]
            return {
                "title": "Extract",
                "summary": f"Extracted from {target}: {len(positives)} positive finding(s), {len(absences)} absence(s).",
                "target": str(target),
                "kind": kind,
                "records": payload["records"],
                "positives": positives,
                "absences": absences,
                "warnings": payload.get("warnings", []),
                "spoken_narrative": f"Extraction complete. {len(positives)} finding(s) recorded.",
            }
        except ValidationError as exc:
            return _op_result("extract", False, error=exc.message)
        except BackendUnavailable as exc:
            return {
                "title": "Extract",
                "summary": f"Backend {exc.backend} is not installed for {target}.",
                "target": str(target),
                "error": exc.message,
                "backend": exc.backend,
                "workaround": f"Install {exc.backend} or use static_scan / a different extraction kind.",
                "spoken_narrative": f"The {exc.backend} backend is not installed.",
            }
        except ExecutionFailed as exc:
            return _op_result("extract", False, error=exc.message)

    # ------------------------------------------------------------------
    # apply — write to explicit destination (confirm required)
    # ------------------------------------------------------------------
    if operation == "apply":
        if not destination:
            return _op_result("apply", False, error="destination is required for apply")
        if not files_raw:
            return _op_result("apply", False, error="files is required for apply")
        try:
            files = json.loads(files_raw)
        except json.JSONDecodeError as exc:
            return _op_result("apply", False, error=f"files was not valid JSON: {exc}")
        if not isinstance(files, dict):
            return _op_result("apply", False, error="files must be a JSON object of path -> content")
        try:
            report = plan_write(
                destination,
                files,
                project_type=None,
                dry_run=not confirm,
                confirm=confirm,
            )
            return {
                "title": "Apply",
                "summary": f"{'Previewed' if report.dry_run else 'Wrote'} {len(report.written)} file(s) to {destination}.",
                "destination": report.destination,
                "project_type": report.project_type,
                "dry_run": report.dry_run,
                "written": report.written,
                "skipped": report.skipped,
                "diffs": report.diffs,
                "spoken_narrative": f"Apply {'preview' if report.dry_run else 'complete'}. {len(report.written)} file(s) {'would be written' if report.dry_run else 'written'}.",
            }
        except DestinationUnknown as exc:
            return {
                "title": "Apply",
                "summary": f"Could not determine project type for {destination}.",
                "destination": destination,
                "error": exc.message,
                "workaround": "Pass an explicit project type or add a marker file.",
                "spoken_narrative": f"Could not determine the project type for {destination}.",
            }
        except ConfirmationRequired as exc:
            return {
                "title": "Apply",
                "summary": "Write requires explicit confirmation (confirm=true).",
                "destination": destination,
                "error": exc.message,
                "workaround": "Set confirm=true to actually write; otherwise this previews the diff.",
                "spoken_narrative": "Apply requires confirm=true to write files.",
            }
        except (PathEscape, ValidationError, StellaReaError) as exc:
            return _op_result("apply", False, error=getattr(exc, "message", str(exc)))

    # ------------------------------------------------------------------
    # graph — build/inspect/render a graph
    # ------------------------------------------------------------------
    if operation == "graph":
        graph_cmd = (kwargs.get("graph_command") or "build").strip().lower()
        try:
            from stella_rea.graph import Graph, compile_linear
            from stella_rea.stella_adapter import graph_to_plan, bridge_available
            if graph_cmd == "backends":
                return _op_result("graph", True, value={"backends": available_backends()})
            if graph_cmd == "build":
                steps = kwargs.get("steps") or ["analyze target", "extract features", "apply to destination"]
                graph = compile_linear(steps, name="rea-plan")
                return {
                    "title": "Graph Build",
                    "summary": f"Built graph with {len(graph.nodes)} node(s) and {len(graph.wires)} wire(s).",
                    "graph": graph.to_dict(),
                    "bridge_available": bridge_available(),
                    "spoken_narrative": f"Built a {len(graph.nodes)}-node graph.",
                }
            if graph_cmd == "inspect":
                gpath = kwargs.get("path")
                if not gpath:
                    return _op_result("graph", False, error="path is required for graph inspect")
                graph = Graph.load(gpath)
                return {
                    "title": "Graph Inspect",
                    "summary": f"Graph {graph.name}: {len(graph.nodes)} node(s), {len(graph.wires)} wire(s).",
                    "graph": graph.to_dict(),
                    "diagnostics": [d.to_dict() for d in graph.validate()],
                    "spoken_narrative": f"Inspected graph {graph.name}.",
                }
            if graph_cmd == "render":
                gpath = kwargs.get("path")
                if not gpath:
                    return _op_result("graph", False, error="path is required for graph render")
                graph = Graph.load(gpath)
                return {
                    "title": "Graph Render",
                    "summary": "Rendered graph as a UI plan.",
                    "plan": graph_to_plan(graph),
                    "spoken_narrative": "Rendered the graph as a UI plan.",
                }
            return _op_result("graph", False, error=f"unknown graph command: {graph_cmd}")
        except (ValidationError, StellaReaError, ExecutionFailed) as exc:
            return _op_result("graph", False, error=getattr(exc, "message", str(exc)))

    # ------------------------------------------------------------------
    # unknown operation
    # ------------------------------------------------------------------
    return _op_result(operation, False, error=f"unknown operation: {operation}")


def _op_result(operation: str, ok: bool, value: Any = None, error: str | None = None) -> Dict[str, Any]:
    result = {"operation": operation, "ok": ok}
    if value is not None:
        result["value"] = value
    if error is not None:
        result["error"] = error
    return result


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="backends"))
