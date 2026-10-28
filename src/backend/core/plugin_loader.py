"""
src/backend/core/plugin_loader.py — Auto-discovery of drop-in plugins.

Each plugin is its own .py file in plugins/ with a module-level PLUGIN dict
and a run() function. Files starting with _ are skipped (template/helpers).
Enabled state is read from api_keys.json (plugins_enabled) on every call —
toggling requires no restart.

Follows Mark-LVI's core/plugin_loader.py pattern exactly.
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("stella.plugins")


class PluginRegistry:
    """Registry of discovered plugins with enablement checks and settings."""

    def __init__(self) -> None:
        self._plugins: Dict[str, dict] = {}
        self._order: List[str] = []

    def register(self, name: str, plugin: dict, module_path: str) -> None:
        if name in self._plugins:
            logger.warning("Plugin %r already registered (first wins); skipping %s", name, module_path)
            return
        self._plugins[name] = plugin
        self._order.append(name)
        logger.info("Registered plugin: %r (%s)", name, module_path)

    def names(self) -> List[str]:
        return list(self._order)

    def has(self, name: str) -> bool:
        return name in self._plugins

    def is_enabled(self, name: str, get_plugin_enabled) -> bool:
        return bool(get_plugin_enabled(name))

    def get_tool_declarations(self, get_plugin_enabled) -> List[dict]:
        """Return declarations only for enabled plugins."""
        declarations = []
        for name in self._order:
            if not self.is_enabled(name, get_plugin_enabled):
                continue
            plugin = self._plugins[name]
            declarations.append(_strip_meta(plugin))
        return declarations

    def run(self, name: str, parameters: dict, ctx: dict, get_plugin_enabled) -> str:
        """Dispatch to the plugin run() with enablement check."""
        if not self.is_enabled(name, get_plugin_enabled):
            return f"Plugin {name!r} is disabled."
        plugin = self._plugins.get(name)
        if not plugin:
            raise KeyError(f"Unknown plugin: {name}")
        run_fn = plugin.get("run")
        if not callable(run_fn):
            raise TypeError(f"Plugin {name!r} has no callable run()")
        return _invoke_handler(run_fn, parameters, ctx)

    def settings_schemas(self) -> List[dict]:
        """Per-plugin PLUGIN_SETTINGS schemas for the UI settings tab."""
        schemas = []
        seen_namespaces = set()
        for name in self._order:
            plugin = self._plugins[name]
            settings = plugin.get("PLUGIN_SETTINGS")
            if not isinstance(settings, dict):
                continue
            ns = settings.get("namespace")
            if not ns or ns in seen_namespaces:
                continue
            seen_namespaces.add(ns)
            schemas.append(settings)
        return schemas

    def list_for_ui(self, get_plugin_enabled) -> List[dict]:
        """Full listing for the plugin manager overlay (valid/invalid, enabled state)."""
        rows = []
        for name in self._order:
            plugin = self._plugins[name]
            rows.append({
                "name": name,
                "description": plugin.get("description", ""),
                "enabled": self.is_enabled(name, get_plugin_enabled),
                "parameters": plugin.get("parameters", {}),
            })
        return rows


def _strip_meta(plugin: dict) -> dict:
    """Remove meta keys before sending to any API. run is a callable."""
    return {k: v for k, v in plugin.items() if k not in ("tier", "brief", "run")}


def _invoke_handler(handler: Callable, parameters: dict, ctx: dict) -> str:
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
        logger.warning("Handler %s failed with full ctx, retrying params-only: %s", handler.__name__, e)
        result = handler(parameters=parameters)
    if result is None:
        return ""
    return str(result)


def _validate_plugin(plugin: Any, module_path: str) -> Optional[str]:
    if not isinstance(plugin, dict):
        return f"{module_path}: PLUGIN is not a dict"
    name = plugin.get("name")
    if not name or not isinstance(name, str):
        return f"{module_path}: PLUGIN.name missing or not a string"
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$", name):
        return f"{module_path}: PLUGIN.name '{name}' invalid"
    desc = plugin.get("description")
    if not desc or not isinstance(desc, str):
        return f"{module_path}: PLUGIN.description missing or not a string"
    params = plugin.get("parameters")
    if not isinstance(params, dict) or params.get("type") != "OBJECT":
        return f"{module_path}: PLUGIN.parameters must be OBJECT-typed dict"
    run_fn = plugin.get("run")
    if not callable(run_fn):
        return f"{module_path}: PLUGIN.run not callable"
    return None


def discover_plugins(
    plugins_dir: Path,
    core_tool_names: Optional[List[str]] = None,
    logger_obj: Optional[logging.Logger] = None,
) -> PluginRegistry:
    """
    Scan plugins_dir/*.py for module-level PLUGIN dicts + run() functions.

    - Skips __init__.py and _-prefixed files
    - Validates each PLUGIN dict
    - Checks name collisions against core tool names and other plugins
    - Returns PluginRegistry
    """
    log = logger_obj or logger
    registry = PluginRegistry()
    reserved = set(core_tool_names or [])

    if not plugins_dir.exists():
        log.warning("Plugins directory does not exist: %s", plugins_dir)
        return registry

    files = sorted(plugins_dir.glob("*.py"))
    for path in files:
        if path.name.startswith("_"):
            continue
        if path.name == "__init__.py":
            continue

        try:
            spec = importlib.util.spec_from_file_location(f"stella.plugins.{path.stem}", path)
            if spec is None or spec.loader is None:
                log.warning("Cannot load spec for %s", path)
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            log.error("Failed to import plugin %s: %s", path.name, e)
            continue

        plugin = getattr(module, "PLUGIN", None)
        if plugin is None:
            continue

        err = _validate_plugin(plugin, str(path))
        if err:
            log.error("Invalid PLUGIN in %s: %s", path.name, err)
            continue

        name = plugin["name"]
        if name in reserved:
            log.error("Plugin %r shadows core tool name; skipping %s", name, path.name)
            continue

        registry.register(name, plugin, str(path))

    log.info("Discovered %d plugins", len(registry._plugins))
    return registry
