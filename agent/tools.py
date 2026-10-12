"""agent/tools.py - the tool surface the agent may call.

Design
------
Every capability is a `Tool`: a name, a JSON-schema the model fills in, and a
callable. The registry is the single source of truth for what Stella can do,
which means three things fall out for free:

* the model sees exactly the tools that exist (no hallucinated names)
* permissions are enforced in one place (`requires` + `allow_destructive`)
* adding a capability is one decorator, not edits across the codebase

Safety
------
Anything that writes to disk, shells out, or reaches the network is marked
destructive and must be explicitly allowed by the caller. The agent cannot
widen its own permissions - `Registry.allowed` is injected from the host and
never derived from model output.
"""

from __future__ import annotations

import inspect
import os
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable


@dataclass
class ToolResult:
    """Uniform tool outcome. `ok` false means the loop should reconsider."""

    ok: bool
    output: str = ""
    data: Any = None
    error: str = ""

    def as_message(self) -> str:
        return self.output if self.ok else f"ERROR: {self.error or 'tool failed'}"


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., ToolResult]
    requires: tuple[str, ...] = ()
    destructive: bool = False

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class Registry:
    """Holds tools and decides what a given caller may run."""

    def __init__(self, allowed: Iterable[str] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        # None means "no gating" (used by tests and by trusted local callers).
        self.allowed: set[str] | None = None if allowed is None else set(allowed)

    # -- registration -------------------------------------------------------

    def tool(
        self,
        name: str,
        description: str,
        parameters: dict,
        requires: tuple[str, ...] = (),
        destructive: bool = False,
    ):
        def wrap(fn: Callable[..., ToolResult]) -> Callable[..., ToolResult]:
            self.register(Tool(name, description, parameters, fn, requires, destructive))
            return fn

        return wrap

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    # -- queries ------------------------------------------------------------

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def __iter__(self):
        return iter(self._tools.values())

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def permitted(self, name: str) -> bool:
        if name not in self._tools:
            return False
        if self.allowed is None:
            return True
        return name in self.allowed

    def schemas(self) -> list[dict]:
        """OpenAI-style tool schemas for the tools this caller may use."""
        return [t.schema() for t in self._tools.values() if self.permitted(t.name)]

    # -- execution ----------------------------------------------------------

    def run(self, name: str, args: dict | None = None) -> ToolResult:
        """Execute a tool with permission + isolation guarantees."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(ok=False, error=f"unknown tool '{name}'")
        if not self.permitted(name):
            return ToolResult(
                ok=False,
                error=f"tool '{name}' is not enabled for this session",
            )
        try:
            kwargs = dict(args or {})
            sig = inspect.signature(tool.handler)
            # Drop anything the handler does not accept: models routinely
            # include extra keys, and a TypeError here would waste a turn.
            kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
            started = time.time()
            result = tool.handler(**kwargs)
            if not isinstance(result, ToolResult):
                result = ToolResult(ok=True, output=str(result))
            result.output = (result.output or "")[:8000]
            result.data = {"elapsed": round(time.time() - started, 3), **(
                result.data if isinstance(result.data, dict) else {})}
            return result
        except TypeError as exc:
            return ToolResult(ok=False, error=f"bad arguments for '{name}': {exc}")
        except Exception as exc:  # noqa: BLE001 - surfaced back to the model
            return ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Built-in tool suite
# ---------------------------------------------------------------------------

_SAFE_ROOT: Path | None = None


def set_workspace_root(root: str | Path | None) -> None:
    """Confine filesystem tools to a root directory.

    Called by the host at startup. Passing None disables the confinement,
    which is only appropriate when the user has explicitly asked for
    unrestricted access.
    """
    global _SAFE_ROOT
    _SAFE_ROOT = Path(root).expanduser().resolve() if root else None


def _resolve_in_workspace(path: str) -> Path:
    """Resolve `path`, refusing anything outside the workspace root."""
    p = Path(path).expanduser()
    p = p if p.is_absolute() else (_SAFE_ROOT or Path.cwd()) / p
    p = p.resolve()
    if _SAFE_ROOT is not None:
        root = _SAFE_ROOT
        try:
            p.relative_to(root)
        except ValueError:
            raise PermissionError(
                f"path {p} is outside the workspace ({root}); "
                "write access is confined to the workspace"
            ) from None
    return p


def build_default_registry(workspace: str | Path | None = None,
                           include_legacy: bool = True) -> Registry:
    """The standard tool suite Stella ships with.

    Two layers in one registry:

    * the core tools below (filesystem, shell, memory, reasoning) - these are
      sandboxed by the workspace root and always available
    * the legacy catalogue from `agent.tool_catalogue` - the 41 real
      capabilities (PDF, browser, Spotify, smart home, ...). They are wrapped,
      not rewritten, and carry capability tags used for consent.
    """
    reg = Registry()

    if workspace is not None:
        set_workspace_root(workspace)

    if include_legacy:
        try:
            from agent.tool_catalogue import register_legacy
            added = register_legacy(reg)
            logger_count = f" (+{added} capability tools)"
        except Exception as exc:  # noqa: BLE001 - never block on the catalogue
            logger_count = f" (capability tools unavailable: {exc})"
    else:
        logger_count = ""
    print(f"[agent] tool registry: {len(reg)} tools{logger_count}")

    # ---- filesystem -------------------------------------------------------

    @reg.tool(
        "read_file",
        "Read a UTF-8 text file. Returns the content, optionally a line range.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File to read."},
                "start_line": {"type": "integer", "description": "1-based first line."},
                "max_lines": {"type": "integer", "description": "How many lines."},
            },
            "required": ["path"],
        },
    )
    def read_file(path: str, start_line: int = 1, max_lines: int = 400) -> ToolResult:
        p = _resolve_in_workspace(path)
        if not p.is_file():
            return ToolResult(ok=False, error=f"not a file: {p}")
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        chunk = lines[max(0, start_line - 1): start_line - 1 + max_lines]
        return ToolResult(
            ok=True,
            output="\n".join(chunk) or "(empty)",
            data={"path": str(p), "lines": len(lines)},
        )

    @reg.tool(
        "write_file",
        "Create or overwrite a text file. Overwrites the whole file.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "append": {"type": "boolean", "description": "Append instead of overwrite."},
            },
            "required": ["path", "content"],
        },
        requires=("files",),
        destructive=True,
    )
    def write_file(path: str, content: str, append: bool = False) -> ToolResult:
        p = _resolve_in_workspace(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if append:
            with p.open("a", encoding="utf-8") as fh:
                fh.write(content)
        else:
            p.write_text(content, encoding="utf-8")
        return ToolResult(ok=True, output=f"wrote {len(content)} chars -> {p}",
                          data={"path": str(p)})

    @reg.tool(
        "list_dir",
        "List files and folders in a directory.",
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    )
    def list_dir(path: str = ".") -> ToolResult:
        p = _resolve_in_workspace(path)
        if not p.is_dir():
            return ToolResult(ok=False, error=f"not a directory: {p}")
        rows = []
        for child in sorted(p.iterdir(), key=lambda c: (c.is_file(), c.name))[:500]:
            kind = "d" if child.is_dir() else "f"
            size = child.stat().st_size if child.is_file() else 0
            rows.append(f"{kind} {size:>10} {child.name}")
        return ToolResult(ok=True, output="\n".join(rows) or "(empty)",
                          data={"count": len(rows)})

    @reg.tool(
        "search_text",
        "Regex search across files under a directory.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string"},
                "glob": {"type": "string", "description": "e.g. *.py"},
                "max_hits": {"type": "integer"},
            },
            "required": ["path", "pattern"],
        },
    )
    def search_text(path: str, pattern: str, glob: str = "*", max_hits: int = 60) -> ToolResult:
        import re
        root = _resolve_in_workspace(path)
        try:
            rx = re.compile(pattern)
        except re.error as exc:
            return ToolResult(ok=False, error=f"bad regex: {exc}")
        if not root.is_dir():
            return ToolResult(ok=False, error=f"not a directory: {root}")
        hits, scanned = [], 0
        for f in root.rglob(glob):
            if not f.is_file() or f.stat().st_size > 2_000_000:
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            scanned += 1
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{f}:{i}: {line.strip()[:200]}")
                    if len(hits) >= max_hits:
                        return ToolResult(ok=True, output="\n".join(hits),
                                          data={"scanned": scanned, "truncated": True})
        return ToolResult(ok=True, output="\n".join(hits) or "(no matches)",
                          data={"scanned": scanned, "hits": len(hits)})

    # ---- shell ------------------------------------------------------------

    @reg.tool(
        "run_command",
        "Run a shell command in the workspace. Returns stdout+stderr.",
        {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout_s": {"type": "integer"},
            },
            "required": ["command"],
        },
        requires=("shell",),
        destructive=True,
    )
    def run_command(command: str, timeout_s: int = 60) -> ToolResult:
        cwd = str(_SAFE_ROOT or Path.cwd())
        try:
            proc = subprocess.run(
                command, shell=True, cwd=cwd, capture_output=True,
                text=True, timeout=max(1, min(timeout_s, 300)),
            )
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, error=f"timed out after {timeout_s}s")
        body = (proc.stdout or "") + (proc.stderr or "")
        return ToolResult(
            ok=proc.returncode == 0,
            output=body[:8000] or "(no output)",
            error=f"exit code {proc.returncode}" if proc.returncode else "",
            data={"returncode": proc.returncode},
        )

    # ---- memory -----------------------------------------------------------

    @reg.tool(
        "remember",
        "Store a durable fact for later sessions.",
        {
            "type": "object",
            "properties": {
                "fact": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["fact"],
        },
        requires=("memory",),
    )
    def remember(fact: str, tags: list[str] | None = None) -> ToolResult:
        from agent.memory import remember as _remember
        return _remember(fact, tags)

    @reg.tool(
        "recall",
        "Search stored memories. Use before assuming you do not know something.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
    )
    def recall(query: str, limit: int = 8) -> ToolResult:
        from agent.memory import recall as _recall
        return _recall(query, limit)

    # ---- time / environment ------------------------------------------------

    @reg.tool(
        "current_time",
        "Current local date and time. Use before any date arithmetic.",
        {"type": "object", "properties": {}},
    )
    def current_time() -> ToolResult:
        import datetime
        now = datetime.datetime.now().astimezone()
        return ToolResult(ok=True, output=now.strftime("%Y-%m-%d %H:%M:%S %Z (%A)"))

    @reg.tool(
        "system_info",
        "Report platform, python version, and workspace location.",
        {"type": "object", "properties": {}},
    )
    def system_info() -> ToolResult:
        import platform
        import sys
        return ToolResult(
            ok=True,
            output=(f"platform={platform.platform()}\n"
                    f"python={sys.version.split()[0]}\n"
                    f"cwd={Path.cwd()}\nworkspace={_SAFE_ROOT or '(unrestricted)'}"),
        )

    @reg.tool(
        "calculate",
        "Evaluate an arithmetic expression exactly. Prefer this over mental math.",
        {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    )
    def calculate(expression: str) -> ToolResult:
        # Deliberately narrow: no names, no attribute access, no builtins.
        allowed = set("0123456789+-*/().%^ ")
        if not set(expression) <= allowed:
            return ToolResult(ok=False, error="only digits and + - * / ( ) . % ^ allowed")
        try:
            return ToolResult(ok=True, output=str(eval(expression, {"__builtins__": {}}, {})))
        except Exception as exc:
            return ToolResult(ok=False, error=f"cannot evaluate: {exc}")

    @reg.tool(
        "todo",
        "Record or update the step-by-step plan for the current task.",
        {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "description": "Full list of steps, each short.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "string"},
                            "status": {"type": "string", "enum": ["pending", "doing", "done", "failed"]},
                        },
                        "required": ["step"],
                    },
                },
                "note": {"type": "string", "description": "Why the plan changed, if it did."},
            },
            "required": ["steps"],
        },
    )
    def todo(steps: list, note: str = "") -> ToolResult:
        from agent.scratchpad import write_plan
        return write_plan(steps, note)

    # ---- device automation (Needle, rootless, reversible) --------------------
    # These give the model the same activate/scan/run/revert cycle the Settings
    # page exposes manually, as callable tools. Needle routes tool-call turns
    # here; the confidence gate decides whether its call is trusted.

    @reg.tool(
        "device_scan",
        "Rootlessly read the whole device (screens, controls, permissions, "
        "processes, network) into device_state.json. Parses every detail needed "
        "to drive the device exactly, without opening Settings.",
        {
            "type": "object",
            "properties": {
                "device": {"type": "string",
                           "description": "Device id or address (e.g. 192.168.1.50, this-pc)."},
            },
            "required": ["device"],
        },
    )
    def device_scan(device: str) -> ToolResult:
        from agent import device_automation as da
        state, err = da.scan_device(device)
        if err is not None:
            return ToolResult(ok=False, error=err)
        try:
            da.save_state(state)
        except Exception as exc:  # never fail a scan on persistence
            state.setdefault("errors", []).append({"at": "save", "error": str(exc)})
        return ToolResult(
            ok=True,
            output=(f"scanned {state.get('device')} ({state.get('platform')}): "
                    f"{len(state.get('screens', []))} screens, "
                    f"{len(state.get('controls', []))} controls, "
                    f"{len(state.get('permissions', []))} permission groups, "
                    f"{len(state.get('processes', []))} process groups, "
                    f"{len(state.get('network', []))} network groups"),
            data=state,
        )

    @reg.tool(
        "device_revert",
        "Deactivate a device automation session, reversing every change the "
        "activation made, in reverse order, at the same access level. The "
        "device returns to exactly how it was before activation.",
        {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device to roll back."},
                "goal": {"type": "string",
                         "description": "What was automated, for the audit log."},
            },
            "required": ["device"],
        },
        destructive=True,
    )
    def device_revert(device: str, goal: str = "") -> ToolResult:
        from agent import device_automation as da
        try:
            state = da.load_state()
        except Exception as exc:
            return ToolResult(ok=False, error=f"cannot read device state: {exc}")
        try:
            activation = da.activate(device, "stella", state)
        except Exception as exc:
            return ToolResult(ok=False, error=f"cannot build activation for {device}: {exc}")
        summary = activation.revert()
        line = (f"reverted {summary.get('reverted', 0)} step(s) on {device} "
                f"({summary.get('failed', 0)} failed)")
        if goal:
            line += f" for goal: {goal[:120]}"
        if summary.get("failed"):
            return ToolResult(ok=False, error=line, data=summary)
        return ToolResult(ok=True, output=line, data=summary)

    return reg