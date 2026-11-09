"""
src/backend/core/engine.py — Stella engine main loop.

Follows Mark-LVI's JarvisLive pattern: init discovers actions/plugins/skills,
binds UI callbacks (via emit), run() enters the reconnect loop with background
tasks. The engine touches the frontend through exactly one callback: emit().
This means the backend can be rewritten without touching the frontend.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..memory.config_manager import config_manager
from .action_loader import discover_actions, ActionRegistry
from .plugin_loader import discover_plugins, PluginRegistry
from ..agent.tools import Registry as ToolRegistry, BUILTIN_TOOLS
from ..agent.executor import AgentExecutor
from ..agent.integration import AgentIntegration
from ..agent.evolution.engine import EvolutionEngine
from ..agent.frontier_router import FrontierRouter, LOCAL, FRONTIER

logger = logging.getLogger("stella.engine")


class StellaEngine:
    """
    Stella engine: the core assistant runtime.

    Constructor:
      - Discovers actions from actions/ (TOOL dicts)
      - Discovers plugins from plugins/ (PLUGIN dicts)
      - Loads skills from skills/ (SKILL.md + skill.py)
      - Binds UI callbacks via emit() — the ONLY frontend touchpoint
      - Initializes wake word, system monitor, proactive engine

    run():
      - Async reconnect loop: pick LLM → resolve caps → build config → open
        session → background tasks → on error: reconnect / step model / backoff
    """

    def __init__(
        self,
        emit: Callable[[str, Any], None],
        actions_dir=None,
        plugins_dir=None,
        skills_dir=None,
        skills_lock_file=None,
    ) -> None:
        self.emit = emit
        self._running = False
        self._session = None
        self._provider = None

        # Resolve directories relative to repo root
        import os
        repo_root = Path(__file__).resolve().parents[3]  # src/backend/core/engine.py -> stella/
        if actions_dir is None:
            actions_dir = repo_root / "actions"
        if plugins_dir is None:
            plugins_dir = repo_root / "plugins"
        if skills_dir is None:
            skills_dir = repo_root / "skills"
        if skills_lock_file is None:
            skills_lock_file = skills_dir / "skills-lock.json"

        # ── Layer 1: Built-in tools ──
        self.tool_registry = ToolRegistry()
        for tool in BUILTIN_TOOLS:
            self.tool_registry.register(tool)

        # ── Layer 2: Actions (auto-discovered TOOL dicts) ──
        self.action_registry = discover_actions(
            actions_dir,
            reserved_names=[t.name for t in BUILTIN_TOOLS],
            logger_obj=logger,
        )

        # ── Layer 3: Plugins (auto-discovered PLUGIN dicts) ──
        self.plugin_registry = discover_plugins(
            plugins_dir,
            core_tool_names=[t.name for t in BUILTIN_TOOLS] + list(self.action_registry.names()),
            logger_obj=logger,
        )

        # ── Layer 4: Skills (SKILL.md + skill.py) ──
        from ..agent.skill_loader import SkillLoader
        self.skill_loader = SkillLoader(skills_dir, skills_lock_file)

        # ── Phase 5: Frontier router (local-by-default, frontier on opt-in) ──
        self.frontier_router = FrontierRouter()
        self._last_route_decision: Optional[RouteDecision] = None

        # ── Agent integration (loop → planner → executor) ──
        self.integration = AgentIntegration(
            llm=None,  # set in run() after provider resolution
            tool_registry=self.tool_registry,
            action_registry=self.action_registry,
            plugin_registry=self.plugin_registry,
            skill_loader=self.skill_loader,
            get_plugin_enabled=config_manager.get_plugin_enabled,
            frontier_router=self.frontier_router,
        )

        # ── Dr. Zero self-evolution engine ──
        self.evolution = EvolutionEngine(
            integration=self.integration,
            emit=self._emit_evolution_event,
            enabled=config_manager.get_app_setting("evolution_enabled", True),
        )

        # State
        self.state = {
            "connected": False,
            "provider_mode": config_manager.get_provider_mode(),
            "wake_word": config_manager.get_wake_word_enabled(),
            "push_to_talk": config_manager.get_push_to_talk_enabled(),
            "audio_level": 0.0,
            "speaking": False,
            "listening": False,
        }

    # ── UI callback (the one frontend touchpoint) ──

    def _emit_state(self) -> None:
        self.emit("state", self.state)

    def _emit_log(self, level: str, message: str, source: str = "engine") -> None:
        self.emit("log", {"level": level, "message": message, "source": source})

    def _emit_evolution_event(self, event_type: str, payload: Any) -> None:
        self.emit(event_type, payload)

    # ── Phase 5: Frontier routing ──
    def route_goal(self, goal: str, frontier: bool = False,
                   user_opted_frontier: bool = False) -> dict:
        """Classify a goal as local or frontier and record the decision.

        Returns a dict with: backend, reason, confidence, forced_local,
        opted_into_frontier. The decision is stored in engine state so the
        frontend can display it and the audit trail can record it.
        """
        decision = self.frontier_router.route(goal, frontier, user_opted_frontier)
        self._last_route_decision = decision
        self.state["last_route"] = {
            "backend": decision.backend,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "forced_local": decision.forced_local,
            "opted_into_frontier": decision.opted_into_frontier,
            "goal": goal[:120],
        }
        self._emit_state()
        return self.state["last_route"]

    def get_last_route(self) -> Optional[dict]:
        """Return the most recent routing decision, or None."""
        return self.state.get("last_route")


    # ── Provider resolution ──

    def _resolve_provider(self):
        """Resolve the LLM provider from api_keys.json config.

        Default mode is "gemini". In pipeline mode, builds a local
        STT→LLM→TTS pipeline. Providers are built lazily — never imported
        at startup unless the user selects pipeline mode.
        """
        mode = config_manager.get_provider_mode()
        self.state["provider_mode"] = mode

        if mode == "gemini":
            # Lazy import to avoid requiring google-genai at startup
            from llm_client import LLMClient
            self._provider = LLMClient()
            self._emit_log("info", "Provider: Gemini Live (default)")
        elif mode == "pipeline":
            from ..core.providers.registry import provider_registry
            pipeline = config_manager.get_pipeline() or {}
            llm_id = pipeline.get("llm", "custom")
            self._provider = provider_registry.build(llm_id, config_manager.get_provider_config(llm_id))
            self._emit_log("info", f"Provider: pipeline LLM={llm_id}")
        else:
            # local mode — user-managed models via download hub
            from llm_client import LLMClient
            self._provider = LLMClient()
            self._emit_log("info", "Provider: local (user-managed models)")

        self.integration = AgentIntegration(
            llm=self._provider,
            tool_registry=self.tool_registry,
            action_registry=self.action_registry,
            plugin_registry=self.plugin_registry,
            skill_loader=self.skill_loader,
            get_plugin_enabled=config_manager.get_plugin_enabled,
            frontier_router=self.frontier_router,
        )

    # ── Build tool declarations (all layers) ──

    def _build_config(self) -> List[dict]:
        """Build the full tool declaration list from all layers."""
        declarations = self.integration.get_tools()
        import json as _json
        try:
            _json.dumps(declarations)
        except Exception as _je:
            logger.error("_build_config JSON error: %s", _je)
            for i, d in enumerate(declarations):
                try:
                    _json.dumps(d)
                except Exception as _de:
                    logger.error("  Declaration %d (%s): %s", i, d.get('name', 'unknown') if isinstance(d, dict) else 'not-dict', _de)
                    for k, v in (d.items() if isinstance(d, dict) else []):
                        if not isinstance(v, (str, int, float, bool, list, dict, type(None))):
                            logger.error("    Key %s: type=%s", k, type(v).__name__)
        self._emit_log("debug", f"Tool declarations: {len(declarations)}")
        return declarations

    # ── Startup / shutdown ──

    def start(self) -> None:
        """Start the engine (called from main.py)."""
        self._running = True
        self._emit_log("info", "Stella engine starting")
        self._emit_state()
        # Start evolution engine after provider is resolved (in run())

    def stop(self) -> None:
        """Stop the engine."""
        self._running = False
        if self.evolution:
            try:
                # Evolution is async; we schedule stop but don't await here
                asyncio.ensure_future(self.evolution.stop())
            except Exception:
                pass
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
        self._emit_log("info", "Stella engine stopped")

    # ── Main reconnect loop (Mark-LVI JarvisLive.run() pattern) ──

    async def run(self) -> None:
        """
        Main engine loop. Runs forever until stop() is called.

        Sequence:
          1. Resolve provider
          2. Build tool config
          3. Open session
          4. Start background tasks (audio, system monitor, etc.)
          5. On error: reconnect with backoff, step model, degrade tuning
        """
        self._resolve_provider()
        declarations = self._build_config()
        self.state["connected"] = True
        self._emit_state()
        self._emit_log("info", "Stella engine connected")

        # Start evolution engine now that provider/integration are ready
        if self.evolution.enabled:
            try:
                # Rebind evolution to the provider-resolved integration
                self.evolution.integration = self.integration
                self.evolution.start()
                self._emit_log("info", "Evolution engine started")
            except Exception as e:
                logger.error("Failed to start evolution engine: %s", e)
                self._emit_log("error", f"Evolution start failed: {e}")

        backoff = 1.0
        max_backoff = 60.0

        while self._running:
            try:
                await self._run_session(declarations)
                backoff = 1.0  # reset on clean exit
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Session error: %s", e)
                self._emit_log("error", f"Session error: {e}")
                self.state["connected"] = False
                self._emit_state()

                if not self._running:
                    break

                # Reconnect with backoff
                await asyncio.sleep(min(backoff, max_backoff))
                backoff = min(backoff * 2, max_backoff)

                try:
                    self._resolve_provider()
                    declarations = self._build_config()
                except Exception as e2:
                    logger.error("Reconnect failed: %s", e2)
                    self._emit_log("error", f"Reconnect failed: {e2}")

    async def _run_session(self, declarations: List[dict]) -> None:
        """Run a single LLM session with background tasks."""
        # Open session (provider-specific)
        if hasattr(self._provider, "open_session"):
            self._session = await self._provider.open_session(declarations)
        else:
            self._session = self._provider

        # Start background tasks in a task group
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._watch_stall())
            tg.create_task(self._audio_loop())
            tg.create_task(self._system_monitor_loop())

            # Main receive loop
            await self._receive_loop()

    async def _receive_loop(self) -> None:
        """Main message receive loop from the LLM session."""
        while self._running:
            try:
                if hasattr(self._session, "receive"):
                    event = await asyncio.wait_for(self._session.receive(), timeout=1.0)
                else:
                    await asyncio.sleep(0.1)
                    continue

                if event is None:
                    continue

                await self._handle_event(event)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("Receive error: %s", e)
                raise

    async def _handle_event(self, event: dict) -> None:
        """Handle an event from the LLM session."""
        event_type = event.get("type", "unknown")

        if event_type == "tool_call":
            await self._handle_tool_call(event)
        elif event_type == "text":
            self._emit_log("info", f"LLM: {event.get('content', '')[:100]}")
        elif event_type == "audio":
            self.state["speaking"] = True
            self._emit_state()
        elif event_type == "done":
            self.state["speaking"] = False
            self._emit_state()

    async def _handle_tool_call(self, event: dict) -> None:
        """Handle a tool call from the LLM."""
        tool_name = event.get("tool", "")
        parameters = event.get("parameters", {})

        self._emit_log("info", f"Tool call: {tool_name}")
        result = self.integration.executor.execute(tool_name, parameters, self.state)

        self._emit_log("info", f"Tool result: {result[:100]}")

        # Send result back to session
        if self._session and hasattr(self._session, "send_tool_result"):
            await self._session.send_tool_result(tool_name, result)

    # ── Background tasks ──

    async def _watch_stall(self) -> None:
        """Watch for stalled sessions."""
        while self._running:
            await asyncio.sleep(5)
            # Stall detection logic

    async def _audio_loop(self) -> None:
        """Audio processing loop (STT → TTS)."""
        while self._running:
            await asyncio.sleep(0.1)
            # Audio processing

    async def _system_monitor_loop(self) -> None:
        """System telemetry loop (CPU, RAM, battery)."""
        while self._running:
            await asyncio.sleep(5)
            self.state["audio_level"] = 0.0  # placeholder
            self._emit_state()
