"""Command-line interface for stella-rea.

``stella-rea --destination <path> <command>``

The destination is a first-class, explicit parameter: every command that
touches a project requires it, and no command ever guesses where to write.

Commands:
    analyze   inspect a destination project and report what it is
    extract   run an extraction workflow against a target
    apply     apply extracted features to the destination
    graph     build, inspect or render a graph

Global flags:
    --json      emit machine-readable JSON instead of prose
    --dry-run   preview writes instead of performing them
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .apply import ProjectType, apply_write, open_destination
from .errors import StellaReaError
from .evidence import EvidenceBundle
from .extraction import available_backends, extract_dynamic, extract_generic

__all__ = ["main", "build_parser"]

_PROG = "stella-rea"


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog=_PROG,
        description="Graph-engineered reverse engineering for Stella.",
    )
    parser.add_argument(
        "--destination",
        help="the destination project directory (explicit; never inferred)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit JSON instead of prose",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="preview writes instead of performing them",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="inspect the destination project")
    analyze.add_argument(
        "--project-type",
        help="override the detected project type",
        choices=list(ProjectType.ALL),
    )

    extract = sub.add_parser("extract", help="run an extraction workflow")
    extract.add_argument("target", help="the artefact to extract from")
    extract.add_argument(
        "--kind",
        default="auto",
        choices=("auto", "android", "native", "dynamic"),
        help="which workflow to run",
    )
    extract.add_argument("--script", help="the JavaScript snippet for dynamic runs")
    extract.add_argument("--device", help="a remote Frida device id")
    extract.add_argument("--target-name", help="the local process name to attach to")
    extract.add_argument("--workdir", help="where intermediate output goes")

    apply_cmd = sub.add_parser("apply", help="apply features to the destination")
    apply_cmd.add_argument(
        "--files",
        help="a JSON object mapping destination-relative paths to file contents",
    )
    apply_cmd.add_argument(
        "--confirm",
        action="store_true",
        help="actually write (without this, nothing is written)",
    )
    apply_cmd.add_argument(
        "--allow",
        action="append",
        help="allowlist of destination-relative paths that may be written",
    )
    apply_cmd.add_argument(
        "--project-type",
        help="override the detected project type",
        choices=list(ProjectType.ALL),
    )

    graph_cmd = sub.add_parser("graph", help="build or inspect a graph")
    graph_sub = graph_cmd.add_subparsers(dest="graph_command", required=True)
    build = graph_sub.add_parser("build", help="compile a linear plan into a graph")
    build.add_argument("steps", nargs="+", help="step titles")
    build.add_argument("--out", help="where to write the graph JSON")
    inspect = graph_sub.add_parser("inspect", help="show a graph's structure")
    inspect.add_argument("path", help="the graph JSON file")
    render = graph_sub.add_parser("render", help="render a graph as a UI plan")
    render.add_argument("path", help="the graph JSON file")
    graph_cmd.add_argument(
        "--backends",
        action="store_true",
        help="list the available reverse-engineering backends",
    )


class _UsageError(Exception):
    """Raised for a CLI misuse that is not a domain error."""


def _usage(message: str) -> _UsageError:
    """Build a usage error."""
    return _UsageError(message)


def _emit(payload: dict[str, Any], as_json: bool, prose: str) -> None:
    """Print either JSON or prose, depending on the ``--json`` flag."""
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    else:
        print(prose)


def _cmd_analyze(args: argparse.Namespace) -> int:
    """Handle the ``analyze`` command."""
    if not args.destination:
        raise _usage("--destination is required for the analyze command")
    destination = open_destination(args.destination, project_type=args.project_type)
    payload = destination.describe()
    payload["backends"] = available_backends()
    prose = (
        f"destination: {payload['path']}\n"
        f"project type: {payload['project_type']}\n"
        "backends:\n"
        + "\n".join(
            f"  {b['name']:<8} {b['kind']:<8} "
            f"{'available' if b['available'] else 'unavailable'}"
            + (f"  ({b['limitation']})" if b.get("limitation") else "")
            for b in payload["backends"]
        )
    )
    _emit(payload, args.json, prose)
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    """Handle the ``extract`` command."""
    if args.kind == "dynamic":
        if not args.script:
            raise _usage("--script is required for a dynamic extraction")
        bundle = extract_dynamic(
            args.script,
            target=args.target_name,
            device=args.device,
        )
    else:
        bundle = extract_generic(
            args.target,
            kind=args.kind,
            workdir=args.workdir,
        )
    payload = bundle.to_dict()
    prose = "\n".join(
        f"[{r['confidence']}] {r['source']}: {r['claim']}"
        + ("" if r["found"] else "  (no evidence)")
        for r in payload["records"]
    )
    _emit(payload, args.json, prose or "no evidence collected")
    return 0



def _cmd_apply(args: argparse.Namespace) -> int:
    """Handle the ``apply`` command."""
    if not args.destination:
        raise _usage("--destination is required for the apply command")
    if not args.files:
        raise _usage("--files is required for the apply command")
    try:
        files = json.loads(args.files)
    except json.JSONDecodeError as exc:
        raise _usage(f"--files was not valid JSON: {exc}") from exc
    if not isinstance(files, dict):
        raise _usage("--files must be a JSON object of path -> content")
    report = apply_write(
        args.destination,
        files,
        project_type=args.project_type,
        dry_run=not args.confirm,
        confirm=bool(args.confirm),
        allow=args.allow,
    )
    payload = report.to_dict()
    prose_parts = [
        f"destination: {report.destination}",
        f"project type: {report.project_type}",
        "dry run" if report.dry_run else "written",
    ]
    for path, diff in report.diffs.items():
        prose_parts.append(f"--- {path}\n{diff}")
    _emit(payload, args.json, "\n".join(prose_parts))
    return 0


def _cmd_graph(args: argparse.Namespace) -> int:
    """Handle the ``graph`` command."""
    if getattr(args, "backends", False):
        payload = {"backends": available_backends()}
        prose = "\n".join(
            f"{b['name']}: {b['kind']} - "
            + ("available" if b["available"] else "unavailable")
            for b in payload["backends"]
        )
        _emit(payload, args.json, prose)
        return 0

    from .graph import Graph, compile_linear
    from .stella_adapter import graph_to_plan

    command = args.graph_command
    if command == "build":
        graph = compile_linear(args.steps, name="plan")
        if args.out:
            path = graph.save(args.out)
            _emit({"saved": str(path), "graph": graph.to_dict()}, args.json, f"wrote {path}")
        else:
            _emit(graph.to_dict(), args.json, graph.to_json())
        return 0

    graph = Graph.load(args.path)
    if command == "inspect":
        payload = {
            "name": graph.name,
            "nodes": len(graph.nodes),
            "wires": len(graph.wires),
            "diagnostics": [d.to_dict() for d in graph.validate()],
            "graph": graph.to_dict(),
        }
        prose = (
            f"graph {graph.name or '(unnamed)'}: {payload['nodes']} nodes, "
            f"{payload['wires']} wires, "
            f"{len(payload['diagnostics'])} diagnostics"
        )
        _emit(payload, args.json, prose)
        return 0

    payload = graph_to_plan(graph)
    _emit(payload, args.json, json.dumps(payload, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the process exit code.

    Expected failures are reported as a typed error payload (with the tag)
    rather than as a traceback.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "analyze":
            return _cmd_analyze(args)
        if args.command == "extract":
            return _cmd_extract(args)
        if args.command == "apply":
            return _cmd_apply(args)
        if args.command == "graph":
            return _cmd_graph(args)
    except StellaReaError as exc:
        payload = {"ok": False, "error": exc.to_dict()}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"error [{exc.tag.value}]: {exc.message}", file=sys.stderr)
        return 2
    except _UsageError as exc:
        if args.json:
            print(
                json.dumps(
                    {"ok": False, "error": {"tag": "usage", "message": str(exc)}},
                    indent=2,
                )
            )
        else:
            print(f"error [usage]: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    raise SystemExit(main())
