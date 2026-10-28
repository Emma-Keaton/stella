"""Bridge between the graph engine and Stella's agentic loop.

Stella already has one control-flow architecture: the agentic loop in
``agent/loop.py`` (``think -> act -> observe -> verify -> repeat``).  This
module makes the graph engine *drive* that loop instead of replacing it.

The shape of the bridge:

* :class:`AgentStepHandler` turns **one graph node** into **one agent
  step**.  The node's prompt is the agent goal; the agent runs against
  Stella's own :class:`~agent.tools.Registry` and
  :class:`~agent.llm.Backend`, so every tool the loop already knows about is
  available inside a graph.
* :func:`compile_agent_plan` turns a list of step descriptions into a
  :class:`~stella_rea.graph.Graph` whose nodes each become one agent step.
* :func:`graph_to_plan` renders a graph into the JSON plan shape the Stella
  UI already knows how to draw, so a graph can be shown as a plan.

Everything imports defensively.  ``agent/`` is Stella's own package and is
not importable from a standalone ``stella_rea`` install, so the import is
guarded and the module still imports cleanly -- it simply reports that the
bridge is unavailable when somebody asks it to run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .graph import (
    FlowRole,
    Graph,
    GraphWire,
    PinClass,
    StepContext,
    StepResult,
    compile_linear,
)

__all__ = [
    "StellaBridgeUnavailable",
    "AgentStepHandler",
    "compile_agent_plan",
    "graph_to_plan",
    "bridge_available",
]


class StellaBridgeUnavailable(RuntimeError):
    """Raised when Stella's ``agent`` package cannot be imported."""


def _load_agent_parts() -> tuple[Any, Any, Any]:
    """Import Stella's ``Agent``, ``Registry`` and ``ToolResult`` defensively.

    Raises:
        StellaBridgeUnavailable: when ``agent/`` is not importable.
    """
    try:
        from agent.llm import Backend  # type: ignore[import-not-found]
        from agent.loop import Agent  # type: ignore[import-not-found]
        from agent.tools import Registry, ToolResult  # type: ignore[import-not-found]
    except Exception as exc:  # ImportError, or a broken local install
        raise StellaBridgeUnavailable(
            "Stella's agent package is not importable from here; the graph "
            "engine can still be used on its own"
        ) from exc
    return Agent, Registry, ToolResult


def bridge_available() -> bool:
    """True when Stella's agent package can be imported."""
    try:
        _load_agent_parts()
    except StellaBridgeUnavailable:
        return False


@dataclass
class AgentStepHandler:
    """Runs one graph node as one Stella agent step.

    The handler wraps a Stella :class:`~agent.loop.Agent`.  The node's
    prompt is the goal handed to the agent; the agent's own think/act/
    observe/verify loop runs to completion *inside* the node.  The node's
    output becomes the text other nodes can bind with ``{{steps.N}}``.

    Attributes:
        agent: the Stella agent used to run the node.
        max_turns: how many turns the inner loop may take.
        workspace: optional workspace passed to the agent.
    """

    agent: Any = None
    max_turns: int = 6
    workspace: str | None = None
    progress: Any = None

    @classmethod
    def from_registry(
        cls,
        registry: Any = None,
        backend: Any = None,
        max_turns: int = 6,
        workspace: str | None = None,
    ) -> AgentStepHandler:
        """Build a handler from Stella's own registry and backend.

        When ``registry`` or ``backend`` is omitted, Stella's defaults are
        used (``agent.tools.build_default_registry`` and
        ``agent.llm.default_backend``).

        Raises:
            StellaBridgeUnavailable: when Stella's agent package is missing.
        """
        Agent, _Registry, _ToolResult = _load_agent_parts()
        if registry is None:
            from agent.tools import build_default_registry  # type: ignore[import-not-found]

            registry = build_default_registry(workspace)
        if backend is None:
            from agent.llm import default_backend  # type: ignore[import-not-found]

            backend = default_backend()
        agent = Agent(backend, registry, max_turns=max_turns)
        return cls(agent=agent, max_turns=max_turns, workspace=workspace)

    def __call__(self, context: StepContext) -> StepResult:
        """Run the agent for this node and return the step result."""
        if self.agent is None:
            return StepResult(
                ok=False,
                error="no Stella agent was attached to this handler",
            )
        goal = context.prompt or context.node.title
        try:
            run = self.agent.run(
                goal,
                progress=self.progress,
                workspace=self.workspace,
            )
        except Exception as exc:  # a failed agent step is data, not a crash
            return StepResult(ok=False, error=f"{type(exc).__name__}: {exc}")
        ok = bool(getattr(run, "ok", False))
        return StepResult(
            ok=ok,
            output=str(getattr(run, "answer", "") or ""),
            data=run,
            error=(
                str(getattr(run, "stopped_because", "") or "")
                if not ok
                else ""
            ),
        )


def compile_agent_plan(
    steps: list[str] | list[dict[str, Any]],
    name: str = "stella-plan",
    depends_on: dict[int, list[int]] | None = None,
    on_failure: dict[int, int] | None = None,
) -> Graph:
    """Compile a list of agent steps into a graph Stella can run.

    Args:
        steps: step titles, or mappings with ``title``/``subtitle`` keys.
        name: the graph name.
        depends_on: optional mapping of step id to the step ids it depends
            on.  These become :attr:`FlowRole.DEPENDENCY` edges, which is
            how a fan-in is expressed.
        on_failure: optional mapping of step id to the recovery step id.
            These become :attr:`FlowRole.FAILURE` edges.

    Returns:
        A :class:`~stella_rea.graph.Graph` whose nodes each become one
        Stella agent step.
    """
    graph = compile_linear(steps, name=name)
    for step, sources in (depends_on or {}).items():
        for source in sources:
            graph.add_wire(
                GraphWire(
                    class_=PinClass.FLOW,
                    from_step=source,
                    to_step=step,
                    flow_role=FlowRole.DEPENDENCY,
                )
            )
    for step, recovery in (on_failure or {}).items():
        graph.add_wire(
            GraphWire(
                class_=PinClass.FLOW,
                from_step=step,
                to_step=recovery,
                flow_role=FlowRole.FAILURE,
            )
        )
    return graph


def graph_to_plan(graph: Graph) -> dict[str, Any]:
    """Render a graph into the plan shape the Stella UI can display.

    The plan is a list of step dictionaries plus the edges between them, so
    the UI can draw the same graph it would draw for a linear plan.
    """
    steps: list[dict[str, Any]] = []
    for node in graph.nodes:
        steps.append(
            {
                "id": node.step,
                "title": node.title,
                "subtitle": node.subtitle or "",
                "kind": node.kind.value,
                "state": "pending",
                "inputs": [p.name for p in node.inputs],
                "outputs": [p.name for p in node.outputs],
            }
        )
    edges: list[dict[str, Any]] = []
    for wire in graph.wires:
        edges.append(
            {
                "from": wire.from_step,
                "to": wire.to_step,
                "class": wire.class_.value,
                "role": wire.flow_role.value if wire.flow_role else None,
                "port": wire.from_pin,
            }
        )
    return {"name": graph.name, "steps": steps, "edges": edges}

    return True
