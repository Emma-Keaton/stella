"""core/tool_registry.py - unified tool registry with auto-audit."""

from typing import Any, Callable, Dict, List, Optional

from core.audit import record


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, fn: Callable, actor: str = "system", description: str = "") -> None:
        if not callable(fn):
            raise TypeError("fn must be callable")
        self._tools[name] = fn
        self._meta[name] = {"actor": actor, "description": description}

    def get(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def list(self) -> List[str]:
        return sorted(self._tools.keys())

    def describe(self, name: str) -> Optional[Dict[str, Any]]:
        return self._meta.get(name)

    def unregister(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            self._meta.pop(name, None)
            return True
        return False

    def invoke(self, name: str, actor: str, target: str, **kwargs: Any) -> Any:
        fn = self._tools.get(name)
        if fn is None:
            record(actor, name, target, {"error": "not found"})
            raise KeyError(name)
        try:
            res = fn(**kwargs)
            record(actor, name, target, {"ok": True, "result": _safe(res)})
            return res
        except Exception as e:  # noqa: BLE001
            record(actor, name, target, {"error": str(e)})
            raise

    def merge_from(self, other: "ToolRegistry") -> int:
        n = 0
        for name in other.list():
            fn = other.get(name)
            if fn is not None and name not in self._tools:
                desc = ""
                m = other.describe(name)
                if m:
                    desc = m.get("description", "")
                self.register(name, fn, description=desc)
                n += 1
        return n

    def auto_discover(self) -> int:
        total = 0
        try:
            from agent import tools as agent_tools
            legacy = getattr(agent_tools, "registry", None) or getattr(agent_tools, "TOOL_REGISTRY", None)
            if isinstance(legacy, ToolRegistry):
                total += self.merge_from(legacy)
            elif isinstance(legacy, dict):
                for k, v in legacy.items():
                    if k not in self._tools and callable(v):
                        self.register(k, v, actor="agent.tools")
                        total += 1
        except Exception:
            pass
        try:
            from core import dynamic_registry as dr
            dyn = getattr(dr, "registry", None) or getattr(dr, "REGISTRY", None)
            if isinstance(dyn, ToolRegistry):
                total += self.merge_from(dyn)
            elif isinstance(dyn, dict):
                for k, v in dyn.items():
                    if k not in self._tools and callable(v):
                        self.register(k, v, actor="core.dynamic_registry")
                        total += 1
        except Exception:
            pass
        return total


def _safe(obj: Any) -> Any:
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_safe(x) for x in obj[:20]]
    if isinstance(obj, dict):
        return {str(k): _safe(v) for k, v in list(obj.items())[:20]}
    return repr(obj)[:200]


registry = ToolRegistry()
registry.auto_discover()


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name, fn, actor="system"):
        self._tools[name] = fn

    def get(self, name):
        return self._tools.get(name)

    def list(self):
        return list(self._tools.keys())

    def invoke(self, name, actor, target, **kwargs):
        fn = self._tools.get(name)
        if fn is None:
            record(actor, name, target, {"error": "not found"})
            raise KeyError(name)
        try:
            res = fn(**kwargs)
            record(actor, name, target, {"ok": True, "result": res})
            return res
        except Exception as e:
            record(actor, name, target, {"error": str(e)})
            raise

registry = ToolRegistry()