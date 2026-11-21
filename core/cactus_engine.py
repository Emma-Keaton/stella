"""core/cactus_engine.py — Cactus (cactus-compute) on-device engine adapter.

Loads the real `cactus-compute` package (Needle = the sub-50MB agentic
tool-calling model) and exposes the small engine interface
agent/needle_bridge.py expects:

    engine.complete(prompt, tools=None, max_new_tokens=...) -> envelope

The envelope uses Needle's native shape ({"type": "call", "function_calls":
[...], "confidence": ...}) which needle_bridge.from_needle_envelope converts
to an OpenAI-style chat completion.

Everything is optional: if the package, the engine binary or the bundled
weights are missing, load() returns None and the main model keeps working —
a broken Cactus can never take Stella down. Set CACTUS_TELEMETRY=0 to
disable anonymous usage counts.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

os.environ.setdefault("CACTUS_TELEMETRY", "0")
logger = logging.getLogger("CactusEngine")

DEFAULT_MODEL = "needle3"  # Cactus Needle 3 — tool calling + structured output

# Bundled model search paths (first hit wins).
_MODEL_DIRS = [
    Path(__file__).resolve().parent.parent / "models",
    Path(os.environ.get("STELLA_MODELS_DIR", "")) if os.environ.get("STELLA_MODELS_DIR") else None,
    Path.home() / ".cactus" / "models",
]

_cactus = None
_load_error: Optional[str] = None


def _find_bundled_model() -> Optional[str]:
    for d in _MODEL_DIRS:
        if d and d.is_dir():
            for p in sorted(d.glob("*.cact")):  # needle3.cact etc.
                return str(p)
    return None


def _point_at_bundled_engine() -> None:
    """If we ship the native engine next to the weights, use it (air-gapped)."""
    engine = Path(__file__).resolve().parent.parent / "models" / "engine"
    for lib in engine.glob("libcactus.*") if engine.is_dir() else []:
        os.environ.setdefault("CACTUS_LIB_PATH", str(lib))
        return


def load() -> Optional[Any]:
    """Import the cactus package. Returns the module or None."""
    global _cactus, _load_error
    if _cactus is not None or _load_error is not None:
        return _cactus
    try:
        _point_at_bundled_engine()
        import cactus  # type: ignore
        _cactus = cactus
    except Exception as e:
        _load_error = f"cactus-compute not installed ({e})"
        logger.info("[Cactus] %s", _load_error)
        _cactus = None
    return _cactus


def available() -> bool:
    return load() is not None


def last_error() -> Optional[str]:
    return _load_error


class CactusEngine:
    """Adapter exposing needle_bridge's engine interface over cactus.Cactus.

    Cactus 4 binds tools at construction (`Cactus(tools=[...])`), so agents
    are cached per toolset signature — one agent per distinct tool list.
    """

    def __init__(self, model: Optional[str] = None):
        self._cactus = load()
        self._weights = model or _find_bundled_model()
        self._agents: dict = {}  # toolset signature -> cactus.Cactus instance

    @property
    def ok(self) -> bool:
        return self._cactus is not None

    def _agent_for(self, cactus_tools: list) -> Any:
        sig = ",".join(sorted(t["name"] for t in cactus_tools)) or "__none__"
        if sig not in self._agents:
            kwargs: dict = {"tools": cactus_tools or None}
            if self._weights:
                kwargs["weights"] = self._weights
            self._agents[sig] = self._cactus.Cactus(**kwargs)
        return self._agents[sig]

    def complete(self, prompt: str, tools: Optional[list] = None,
                 max_new_tokens: int = 256) -> dict:
        """Run one tool-calling turn. Returns a Needle-shaped envelope."""
        if self._cactus is None:
            raise RuntimeError(_load_error or "cactus engine not loaded")
        cactus_tools = _to_cactus_tools(tools)
        try:
            agent = self._agent_for(cactus_tools)
            result = agent.complete(text=prompt, max_new_tokens=max_new_tokens)
        except Exception as e:
            raise RuntimeError(f"cactus complete() failed: {e}")
        return _to_needle_envelope(result)


def _to_cactus_tools(needle_tools: list) -> list:
    """Convert needle_bridge-style flat tool dicts into cactus tool callables.

    Cactus accepts either Python functions or {"name","description",
    "parameters"} dicts; we pass dicts through and let the engine bind them.
    """
    out = []
    for t in needle_tools or []:
        if isinstance(t, dict) and t.get("name"):
            out.append({
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("parameters") or {"type": "object", "properties": {}},
            })
    return out


def _to_needle_envelope(result: Any) -> dict:
    """Normalise a cactus result into Needle's envelope shape."""
    if isinstance(result, dict):
        if result.get("type") == "call" or "function_calls" in result:
            return result
        # cactus Cactus.run/complete style: {"results": [...], "message": ...}
        calls = []
        for r in result.get("results") or []:
            if isinstance(r, dict) and r.get("name"):
                calls.append({"name": r["name"], "arguments": r.get("arguments") or r.get("result") or {}})
        return {
            "type": "call" if calls else "text",
            "function_calls": calls,
            "message": result.get("message", ""),
            "confidence": result.get("confidence", 1.0 if calls else 0.0),
        }
    return {"type": "text", "message": str(result), "confidence": 0.0}


def get_engine(model: Optional[str] = None) -> Optional[CactusEngine]:
    eng = CactusEngine(model)
    return eng if eng.ok else None
