"""
src/backend/core/action_loader.py — Auto-discovery of built-in actions.

Each action is its own .py file in actions/ with a module-level TOOL dict.
Files starting with _ are skipped (helpers). Discovered at startup via glob,
sorted by name for determinism. Errors are logged, never raised.

Follows Mark-LVI's core/action_loader.py pattern exactly.
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("stella.actions")


class ActionRegistry:
    """Registry of discovered actions with validation and dispatch."""

    def __init__(self) -> None:
        self._actions: Dict[str, dict] = {}
        self._order: List[str] = []

    def register(self, name: str, tool: dict, module_path: str) -> None:
        if name in self._actions:
            logger.warning("Action %r already registered (first wins); skipping %s", name, module_path)
            return
        self._actions[name] = tool
        self._order.append(name)
        logger.info("Registered action: %r (%s)", name, module_path)

    def names(self) -> List[str]:
        return list(self._order)

    def has(self, name: str) -> bool:
        return name in self._actions

    def scheduling(self, name: str) -> Optional[str]:
        return self._actions[name].get("scheduling")

    def get_tool(self, name: str) -> Optional[dict]:
        return self._actions.get(name)

    def get_tool_declarations(self) -> List[dict]:
        """Return declarations for the LLM (meta keys stripped)."""
        declarations = []
        for name in self._order:
            tool = self._actions[name]
            declarations.append(_strip_meta(tool))
        return declarations

    def run(self, name: str, parameters: dict, ctx: dict) -> str:
        """Dispatch to the action handler with introspected context kwargs."""
        tool = self._actions.get(name)
        if not tool:
            raise KeyError(f"Unknown action: {name}")
        handler = tool.get("handler")
        if not callable(handler):
            raise TypeError(f"Action {name!r} has no callable handler")
        return _invoke_handler(handler, parameters, ctx)


def _strip_meta(tool: dict) -> dict:
    """Remove meta keys before sending to any API (Gemini rejects unknown fields).
    handler is a callable and not JSON serializable."""
    return {k: v for k, v in tool.items() if k not in ("tier", "brief", "handler")}


def _invoke_handler(handler: Callable, parameters: dict, ctx: dict) -> str:
    """Call handler with only the context kwargs it actually declares."""
    sig = inspect.signature(handler)
    kwargs: Dict[str, Any] = {"parameters": parameters}
    for param_name in sig.parameters:
        if param_name == "parameters":
            continue
        if param_name in ctx:
            kwargs[param_name] = ctx[param_name]
    try:
        result = handler(**kwargs)
    except TypeError as e:
        # Fallback: pass only parameters if handler signature is incompatible
        logger.warning("Handler %s failed with full ctx, retrying params-only: %s", handler.__name__, e)
        result = handler(parameters=parameters)
    if result is None:
        return ""
    return str(result)


def _validate_tool(tool: Any, module_path: str) -> Optional[str]:
    """Validate a TOOL dict. Returns error message or None."""
    if not isinstance(tool, dict):
        return f"{module_path}: TOOL is not a dict"
    name = tool.get("name")
    if not name or not isinstance(name, str):
        return f"{module_path}: TOOL.name missing or not a string"
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$", name):
        return f"{module_path}: TOOL.name '{name}' invalid (must match ^[a-zA-Z_][a-zA-Z0-9_]{{0,63}}$)"
    desc = tool.get("description")
    if not desc or not isinstance(desc, str):
        return f"{module_path}: TOOL.description missing or not a string"
    params = tool.get("parameters")
    if not isinstance(params, dict) or params.get("type") != "OBJECT":
        return f"{module_path}: TOOL.parameters must be OBJECT-typed dict"
    handler = tool.get("handler")
    if not callable(handler):
        return f"{module_path}: TOOL.handler not callable"
    return None


def discover_actions(
    actions_dir: Path,
    reserved_names: Optional[List[str]] = None,
    logger_obj: Optional[logging.Logger] = None,
) -> ActionRegistry:
    """
    Scan actions_dir/*.py for module-level TOOL dicts.

    - Skips __init__.py and _-prefixed files
    - Validates each TOOL dict
    - Checks name collisions against reserved_names and previously discovered
    - Returns ActionRegistry with valid actions only
    """
    log = logger_obj or logger
    registry = ActionRegistry()
    reserved = set(reserved_names or [])

    if not actions_dir.exists():
        log.warning("Actions directory does not exist: %s", actions_dir)
        return registry

    files = sorted(actions_dir.glob("*.py"))
    for path in files:
        if path.name.startswith("_"):
            continue
        if path.name == "__init__.py":
            continue

        try:
            spec = importlib.util.spec_from_file_location(f"stella.actions.{path.stem}", path)
            if spec is None or spec.loader is None:
                log.warning("Cannot load spec for %s", path)
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            log.error("Failed to import action %s: %s", path.name, e)
            continue

        tool = getattr(module, "TOOL", None)
        if tool is None:
            continue  # silently skip modules without TOOL

        err = _validate_tool(tool, str(path))
        if err:
            log.error("Invalid TOOL in %s: %s", path.name, err)
            continue

        name = tool["name"]
        if name in reserved:
            log.error("Action %r shadows reserved name; skipping %s", name, path.name)
            continue

        registry.register(name, tool, str(path))

    log.info("Discovered %d actions", len(registry._actions))
    return registry
