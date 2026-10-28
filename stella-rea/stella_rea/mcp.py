"""MCP server exposing the same operations as the CLI.

This is a plain-stdlib JSON-RPC 2.0 server speaking the Model Context
Protocol over stdio.  It exposes exactly the same operations as the CLI --
analyze, extract, apply, graph -- so an MCP client and a shell user see the
same behaviour, including the same typed errors.

The server is dependency-free: it implements the MCP handshake and the
``tools/list`` / ``tools/call`` methods directly on top of
:mod:`json` and :mod:`sys`.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable

from .apply import apply_write
from .errors import StellaReaError
from .extraction import available_backends, extract_dynamic, extract_generic
from .graph import Graph, compile_linear
from .stella_adapter import graph_to_plan

__all__ = [
    "PROTOCOL_VERSION",
    "TOOLS",
    "call_tool",
    "handle_request",
    "serve",
]

PROTOCOL_VERSION = "2024-11-05"

#: The MCP tool definitions this server exposes.
TOOLS: list[dict[str, Any]] = [
    {
        "name": "rea_analyze",
        "description": "Inspect a destination project and report its type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "project_type": {"type": "string"},
            },
            "required": ["destination"],
        },
    },
    {
        "name": "rea_extract",
        "description": "Run an extraction workflow against a target artefact.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "kind": {
                    "type": "string",
                    "enum": ["auto", "android", "native", "dynamic"],
                },
                "script": {"type": "string"},
                "device": {"type": "string"},
                "target_name": {"type": "string"},
            },
            "required": ["target"],
        },
    },
    {
        "name": "rea_apply",
        "description": "Apply extracted features to an explicit destination.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "files": {"type": "object"},
                "dry_run": {"type": "boolean"},
                "confirm": {"type": "boolean"},
                "allow": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["destination", "files"],
        },
    },
    {
        "name": "rea_graph",
        "description": "Build, inspect or render a graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["build", "inspect", "render", "backends"],
                },
                "steps": {"type": "array", "items": {"type": "string"}},
                "path": {"type": "string"},
            },
            "required": ["action"],
        },
    },
]


def _tool_analyze(args: dict[str, Any]) -> dict[str, Any]:
    """Run the analyze operation."""
    from .apply import open_destination

    destination = open_destination(
        args.get("destination", ""), project_type=args.get("project_type")
    )
    payload = destination.describe()
    payload["backends"] = available_backends()
    return payload


def _tool_extract(args: dict[str, Any]) -> dict[str, Any]:
    """Run the extract operation."""
    kind = args.get("kind", "auto")
    if kind == "dynamic":
        if not args.get("script"):
            raise ValueError("script is required for a dynamic extraction")
        bundle = extract_dynamic(
            args["script"],
            target=args.get("target_name"),
            device=args.get("device"),
        )
    else:
        bundle = extract_generic(args["target"], kind=kind)
    return bundle.to_dict()


def _tool_apply(args: dict[str, Any]) -> dict[str, Any]:
    """Run the apply operation."""
    report = apply_write(
        args.get("destination", ""),
        args.get("files", {}),
        dry_run=bool(args.get("dry_run", True)),
        confirm=bool(args.get("confirm", False)),
        allow=args.get("allow"),
    )
    return report.to_dict()


def _tool_graph(args: dict[str, Any]) -> dict[str, Any]:
    """Run the graph operation."""
    action = args.get("action", "build")
    if action == "backends":
        return {"backends": available_backends()}
    if action == "build":
        return compile_linear(args.get("steps", []), name="plan").to_dict()
    path = args.get("path")
    if not path:
        raise ValueError("path is required for this graph action")
    graph = Graph.load(path)
    if action == "inspect":
        return {
            "name": graph.name,
            "nodes": len(graph.nodes),
            "wires": len(graph.wires),
            "diagnostics": [d.to_dict() for d in graph.validate()],
        }
    return graph_to_plan(graph)


_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "rea_analyze": _tool_analyze,
    "rea_extract": _tool_extract,
    "rea_apply": _tool_apply,
    "rea_graph": _tool_graph,
}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Invoke a tool by name.

    Raises:
        ValueError: when the tool name is unknown.
        StellaReaError: when the tool fails with a typed domain error.
    """
    handler = _HANDLERS.get(name)
    if handler is None:
        known = ", ".join(sorted(_HANDLERS))
        raise ValueError(f"unknown tool {name!r}; known tools: {known}")
    return handler(arguments or {})


def handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC request and return the response, if any."""
    method = request.get("method")
    request_id = request.get("id")

    if method == "initialize":
        result: dict[str, Any] = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "stella-rea", "version": "0.1.0"},
        }
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        try:
            payload = call_tool(name, arguments)
            result = {
                "content": [
                    {"type": "text", "text": json.dumps(payload, indent=2, default=str)}
                ],
                "isError": False,
            }
        except StellaReaError as exc:
            result = {
                "content": [
                    {"type": "text", "text": json.dumps(exc.to_dict(), indent=2)}
                ],
                "isError": True,
            }
        except Exception as exc:  # an unexpected failure is still a value
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"tag": "internal", "message": f"{type(exc).__name__}: {exc}"},
                            indent=2,
                        ),
                    }
                ],
                "isError": True,
            }
    elif method in {"notifications/initialized", "initialized"}:
        return None
    elif method == "ping":
        result = {}
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"unknown method: {method}"},
        }

    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def serve(stdin: Any = None, stdout: Any = None) -> None:
    """Serve MCP over stdio until the input stream ends."""
    source = stdin if stdin is not None else sys.stdin
    sink = stdout if stdout is not None else sys.stdout
    for line in source:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle_request(request)
        if response is None:
            continue
        sink.write(json.dumps(response, default=str) + "\n")
        sink.flush()


if __name__ == "__main__":  # pragma: no cover - script entry point
    serve()
