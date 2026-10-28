"""Graph engine for stella-rea: an explicit DAG of steps with typed edges.

Stella's own graph model: node kinds, pin classes,
flow roles, synthetic-trigger node ids and snake_case wire shape.

The point of the package is the *second* control-flow architecture next to
Stella's agentic loop.  A loop hides its control flow in a ``while`` and in
the model's own choices; a graph states it: which step runs after which, which
steps must all finish before a fan-in step, where a failure is routed, and
which named port a conditional takes.  That makes a run inspectable,
serializable and recoverable, and it lets a failure route somewhere specific
instead of ending the run.

Naming note: the wire shape uses ``class`` as a field name, which is a
Python keyword.  The Python dataclasses therefore use ``class_`` and
serialise back to the same ``"class"`` JSON key.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .errors import CycleDetected, ExecutionFailed, ValidationError

__all__ = [
    "TRIGGER_NODE_BASE",
    "NodeKind",
    "PinClass",
    "FlowRole",
    "GraphSeverity",
    "NodeRunState",
    "GraphPin",
    "GraphNode",
    "GraphWire",
    "GraphDiagnostic",
    "NodePosition",
    "Graph",
    "StepContext",
    "StepResult",
    "ExecutionResult",
    "Executor",
    "compile_linear",
    "resolve_bindings",
    "trigger_step",
]

#: Node-id offset for synthetic trigger nodes, keeping them disjoint from real
#: step numbers.  Trigger ``i`` gets node id ``TRIGGER_NODE_BASE + i``.
TRIGGER_NODE_BASE: int = 1_000_000

_BINDING_RE = re.compile(r"\{\{steps\.(\d+)\}\}")


class NodeKind(str, Enum):
    """Whether a node is an executable step or a synthetic trigger entry."""

    STEP = "step"
    TRIGGER = "trigger"

    @property
    def describe(self) -> str:
        """One-line human description of the kind."""
        if self is NodeKind.TRIGGER:
            return "A synthetic entry node representing one of the graph's triggers."
        return "An executable graph step."


class PinClass(str, Enum):
    """Whether a pin/edge carries execution order or typed data."""

    FLOW = "flow"
    DATA = "data"

    @property
    def describe(self) -> str:
        """One-line human description of the pin class."""
        if self is PinClass.DATA:
            return "Typed data edge derived from a {{steps.N}} binding."
        return "Execution-order edge: which step runs after which."

    @property
    def label(self) -> str:
        """Short label used in legends."""
        return self.value



class FlowRole(str, Enum):
    """Why a flow wire exists."""

    SEQUENCE = "sequence"
    DEPENDENCY = "dependency"
    FAILURE = "failure"
    SWITCH = "switch"
    TRIGGER = "trigger"

    @property
    def describe(self) -> str:
        """One-line human description of the flow role."""
        if self is FlowRole.DEPENDENCY:
            return "routing.depends_on fan-in: source must complete before target runs."
        if self is FlowRole.FAILURE:
            return "on_failure: goto recovery edge."
        if self is FlowRole.SWITCH:
            return "Named conditional port from routing.switch."
        if self is FlowRole.TRIGGER:
            return "Derived from the graph's triggers; read-only, never hand-wired."
        return "Implicit fallthrough or explicit routing.next."

    @property
    def label(self) -> str:
        """Short label used in legends."""
        return {
            FlowRole.SEQUENCE: "next step",
            FlowRole.DEPENDENCY: "waits for",
            FlowRole.FAILURE: "on failure",
            FlowRole.SWITCH: "branch",
            FlowRole.TRIGGER: "trigger",
        }[self]


class GraphSeverity(str, Enum):
    """Severity of a graph diagnostic."""

    WARNING = "warning"
    ERROR = "error"


class NodeRunState(str, Enum):
    """Run state of one node during execution."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    @property
    def describe(self) -> str:
        """One-line human description of the run state."""
        if self is NodeRunState.PENDING:
            return "Not reached yet (or the run ended before reaching it)."
        if self is NodeRunState.ACTIVE:
            return "The run's current step while the run is live."
        if self is NodeRunState.COMPLETED:
            return "The step finished successfully."


@dataclass
class GraphPin:
    """One connection point on a node.

    ``class_`` is the pin class (flow or data); it serialises to the wire key
    ``"class"``.
    """

    class_: PinClass = PinClass.FLOW
    name: str = ""
    data_type: str | None = None
    required: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialise the pin to the snake_case wire shape."""
        out: dict[str, Any] = {
            "class": self.class_.value,
            "name": self.name,
            "required": self.required,
        }
        if self.data_type is not None:
            out["data_type"] = self.data_type
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GraphPin:
        """Build a pin from the snake_case wire shape."""
        return cls(
            class_=PinClass(data.get("class", "flow")),
            name=data.get("name", ""),
            data_type=data.get("data_type"),
            required=bool(data.get("required", False)),
        )


@dataclass
class GraphNode:
    """A node in the graph: one executable step, or one synthetic trigger entry.

    ``step >= TRIGGER_NODE_BASE`` together with ``trigger_index`` marks a
    synthetic trigger node.
    """

    step: int
    title: str = ""
    kind: NodeKind = NodeKind.STEP
    subtitle: str | None = None
    trigger_index: int | None = None
    inputs: list[GraphPin] = field(default_factory=list)
    outputs: list[GraphPin] = field(default_factory=list)

    @property
    def is_trigger(self) -> bool:
        """True when this node is a synthetic trigger entry node."""
        return self.kind is NodeKind.TRIGGER or self.step >= TRIGGER_NODE_BASE

    def to_dict(self) -> dict[str, Any]:
        """Serialise the node to the snake_case wire shape."""
        out: dict[str, Any] = {
            "step": self.step,
            "title": self.title,
            "kind": self.kind.value,
            "inputs": [p.to_dict() for p in self.inputs],
            "outputs": [p.to_dict() for p in self.outputs],
        }
        if self.subtitle is not None:
            out["subtitle"] = self.subtitle
        if self.trigger_index is not None:
            out["trigger_index"] = self.trigger_index
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GraphNode:
        """Build a node from the snake_case wire shape."""
        trigger_index = data.get("trigger_index")
        return cls(
            step=int(data["step"]),
            title=data.get("title", ""),
            kind=NodeKind(data.get("kind", "step")),
            subtitle=data.get("subtitle"),
            trigger_index=int(trigger_index) if trigger_index is not None else None,
            inputs=[GraphPin.from_dict(p) for p in data.get("inputs", [])],
            outputs=[GraphPin.from_dict(p) for p in data.get("outputs", [])],
        )


@dataclass
class GraphWire:
    """A directed edge between two nodes.

    ``flow_role`` is set for flow wires; data wires carry the producer and
    consumer pin names instead.
    """

    class_: PinClass = PinClass.FLOW
    from_step: int = 0
    to_step: int = 0
    flow_role: FlowRole | None = None
    from_pin: str | None = None
    to_pin: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise the wire to the snake_case wire shape."""
        out: dict[str, Any] = {
            "class": self.class_.value,
            "from_step": self.from_step,
            "to_step": self.to_step,
        }
        if self.flow_role is not None:
            out["flow_role"] = self.flow_role.value
        if self.from_pin is not None:
            out["from_pin"] = self.from_pin
        if self.to_pin is not None:
            out["to_pin"] = self.to_pin
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GraphWire:
        """Build a wire from the snake_case wire shape."""
        role = data.get("flow_role")
        return cls(
            class_=PinClass(data.get("class", "flow")),
            from_step=int(data["from_step"]),
            to_step=int(data["to_step"]),
            flow_role=FlowRole(role) if role is not None else None,
            from_pin=data.get("from_pin"),
            to_pin=data.get("to_pin"),
        )


@dataclass
class GraphDiagnostic:
    """A validation finding anchored to a step."""

    severity: GraphSeverity = GraphSeverity.WARNING
    step: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise the diagnostic."""
        return {
            "severity": self.severity.value,
            "step": self.step,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GraphDiagnostic:
        """Build a diagnostic from the wire shape."""
        return cls(
            severity=GraphSeverity(data.get("severity", "warning")),
            step=int(data.get("step", 0)),
            message=data.get("message", ""),
        )


@dataclass
class NodePosition:
    """Grid placement for one node."""

    step: int = 0
    col: int = 0
    row: int = 0
    x: float | None = None
    y: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise the position."""
        out: dict[str, Any] = {"step": self.step, "col": self.col, "row": self.row}
        if self.x is not None:
            out["x"] = self.x
        if self.y is not None:
            out["y"] = self.y
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> NodePosition:
        """Build a position from the wire shape."""
        return cls(
            step=int(data.get("step", 0)),
            col=int(data.get("col", 0)),
            row=int(data.get("row", 0)),
            x=data.get("x"),
            y=data.get("y"),
        )

        if self is NodeRunState.FAILED:
            return "The step errored and did not complete."
        return "The step was routed around and never ran."

    @property
    def label(self) -> str:
        """Short label used in legends."""


class Graph:
    """A graph of steps and typed edges.

    The container owns the node table, the wire list, diagnostics and an
    optional layout, and knows how to serialise itself to the snake_case wire
    shape used by Stella's own canvas and by ``stella-rea``'s own CLI/MCP.
    """

    def __init__(
        self,
        nodes: Iterable[GraphNode] | None = None,
        wires: Iterable[GraphWire] | None = None,
        diagnostics: Iterable[GraphDiagnostic] | None = None,
        positions: Iterable[NodePosition] | None = None,
        name: str = "",
    ) -> None:
        """Build a graph from nodes, wires, diagnostics and positions."""
        self.name = name
        self.nodes: list[GraphNode] = list(nodes or [])
        self.wires: list[GraphWire] = list(wires or [])
        self.diagnostics: list[GraphDiagnostic] = list(diagnostics or [])
        self.positions: list[NodePosition] = list(positions or [])

    # -- queries ------------------------------------------------------------

    def node(self, step: int) -> GraphNode:
        """Return the node with the given step id.

        Raises:
            ValidationError: when no node carries that step id.
        """
        for n in self.nodes:
            if n.step == step:
                return n
        raise ValidationError(f"no node with step {step}", step=step)

    def has_node(self, step: int) -> bool:
        """True when a node with the given step id exists."""
        return any(n.step == step for n in self.nodes)

    def step_nodes(self) -> list[GraphNode]:
        """Every non-trigger node, in insertion order."""
        return [n for n in self.nodes if not n.is_trigger]

    def trigger_nodes(self) -> list[GraphNode]:
        """Every synthetic trigger node, in insertion order."""
        return [n for n in self.nodes if n.is_trigger]

    def wires_from(self, step: int, role: FlowRole | None = None) -> list[GraphWire]:
        """Flow wires leaving ``step``, optionally filtered by role."""
        out = [w for w in self.wires if w.from_step == step and w.class_ is PinClass.FLOW]
        if role is not None:
            out = [w for w in out if w.flow_role is role]
        return out

    def wires_to(self, step: int, role: FlowRole | None = None) -> list[GraphWire]:
        """Flow wires entering ``step``, optionally filtered by role."""
        out = [w for w in self.wires if w.to_step == step and w.class_ is PinClass.FLOW]
        if role is not None:
            out = [w for w in out if w.flow_role is role]
        return out

    def dependencies(self, step: int) -> list[int]:
        """Steps that must complete before ``step`` may run."""
        return [w.from_step for w in self.wires_to(step, FlowRole.DEPENDENCY)]

    def failure_targets(self, step: int) -> list[int]:
        """Recovery steps reachable from ``step`` via failure edges."""
        return [w.to_step for w in self.wires_from(step, FlowRole.FAILURE)]

    def switch_ports(self, step: int) -> dict[str, int]:
        """Named switch ports leaving ``step`` (``port name -> target step``)."""
        ports: dict[str, int] = {}
        for w in self.wires_from(step, FlowRole.SWITCH):
            ports[w.from_pin or ""] = w.to_step
        return ports

    # -- mutation -----------------------------------------------------------

    def add_node(self, node: GraphNode) -> GraphNode:
        """Add a node, replacing any node with the same step id."""
        self.nodes = [n for n in self.nodes if n.step != node.step]
        self.nodes.append(node)
        return node

    def add_wire(self, wire: GraphWire) -> GraphWire:
        """Add a wire to the graph."""
        self.wires.append(wire)
        return wire

    def remove_node(self, step: int) -> None:
        """Remove a node and every wire touching it."""
        self.nodes = [n for n in self.nodes if n.step != step]
        self.wires = [w for w in self.wires if w.from_step != step and w.to_step != step]

        return self.value


    # -- validation ---------------------------------------------------------

    def flow_edges(self) -> list[tuple[int, int, FlowRole]]:
        """All flow edges as ``(from_step, to_step, role)`` triples."""
        return [
            (w.from_step, w.to_step, w.flow_role or FlowRole.SEQUENCE)
            for w in self.wires
            if w.class_ is PinClass.FLOW
        ]

    def find_cycle(self) -> list[int]:
        """Return one cycle in the ordering edges, or an empty list.

        Failure edges are recovery routes and are allowed to point backwards
        without forming a scheduling cycle, so they are excluded.
        """
        adjacency: dict[int, list[int]] = {n.step: [] for n in self.nodes}
        for src, dst, role in self.flow_edges():
            if role is FlowRole.FAILURE:
                continue
            adjacency.setdefault(src, []).append(dst)
            adjacency.setdefault(dst, [])

        WHITE, GREY, BLACK = 0, 1, 2
        color: dict[int, int] = {s: WHITE for s in adjacency}
        path: list[int] = []

        for root in list(adjacency):
            if color.get(root, WHITE) != WHITE:
                continue
            stack: list[tuple[int, int]] = [(root, 0)]
            while stack:
                node, index = stack[-1]
                if index == 0:
                    color[node] = GREY
                    path.append(node)
                neighbours = adjacency.get(node, [])
                if index < len(neighbours):
                    stack[-1] = (node, index + 1)
                    nxt = neighbours[index]
                    state = color.get(nxt, WHITE)
                    if state == GREY:
                        return path[path.index(nxt):] + [nxt]
                    if state == WHITE:
                        stack.append((nxt, 0))
                    continue
                color[node] = BLACK
                path.pop()
                stack.pop()
        return []

    def detect_cycle(self) -> list[int]:
        """Return the cycle found in the graph, or an empty list.

        Raises:
            CycleDetected: when a cycle exists.  Detection always terminates.
        """
        cycle = self.find_cycle()
        if cycle:
            raise CycleDetected(cycle)
        return []

    def validate(self) -> list[GraphDiagnostic]:
        """Return diagnostics for the graph (dangling wires, dead steps)."""
        found: list[GraphDiagnostic] = []
        known = {n.step for n in self.nodes}
        for w in self.wires:
            if w.from_step not in known:
                found.append(
                    GraphDiagnostic(
                        severity=GraphSeverity.ERROR,
                        step=w.to_step,
                        message=f"wire source step {w.from_step} does not exist",
                    )
                )
            if w.to_step not in known:
                found.append(
                    GraphDiagnostic(
                        severity=GraphSeverity.ERROR,
                        step=w.from_step,
                        message=f"wire target step {w.to_step} does not exist",
                    )
                )
        reachable = self.reachable_steps()
        for n in self.step_nodes():
            if n.step not in reachable:
                found.append(
                    GraphDiagnostic(
                        severity=GraphSeverity.WARNING,
                        step=n.step,
                        message="step is not reachable from any entry node",
                    )
                )
        return found

    def reachable_steps(self) -> set[int]:
        """Steps reachable from a trigger node or from a root step."""
        adjacency: dict[int, list[int]] = {}
        for src, dst, role in self.flow_edges():
            if role is FlowRole.FAILURE:
                continue
            adjacency.setdefault(src, []).append(dst)
        roots = [n.step for n in self.trigger_nodes()]
        if not roots:
            targets = {w.to_step for w in self.wires if w.class_ is PinClass.FLOW}
            roots = [n.step for n in self.step_nodes() if n.step not in targets]
        seen: set[int] = set()
        stack = list(roots)
        while stack:
            step = stack.pop()
            if step in seen:
                continue
            seen.add(step)
            stack.extend(adjacency.get(step, []))

    # -- serialisation ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise the graph to the snake_case wire shape."""
        return {
            "name": self.name,
            "nodes": [n.to_dict() for n in self.nodes],
            "wires": [w.to_dict() for w in self.wires],
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "positions": [p.to_dict() for p in self.positions],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Graph:
        """Build a graph from the snake_case wire shape."""
        return cls(
            nodes=[GraphNode.from_dict(n) for n in data.get("nodes", [])],
            wires=[GraphWire.from_dict(w) for w in data.get("wires", [])],
            diagnostics=[GraphDiagnostic.from_dict(d) for d in data.get("diagnostics", [])],
            positions=[NodePosition.from_dict(p) for p in data.get("positions", [])],
            name=data.get("name", ""),
        )

    def to_json(self, indent: int = 2) -> str:
        """Serialise the graph to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> Graph:
        """Parse a graph from a JSON string."""
        return cls.from_dict(json.loads(text))

    def save(self, path: str | Path) -> Path:
        """Write the graph JSON to ``path``."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json(), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> Graph:
        """Read a graph JSON from ``path``."""
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def __len__(self) -> int:
        """Number of nodes in the graph."""
        return len(self.nodes)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        """Short debugging representation."""
        return f"Graph(name={self.name!r}, nodes={len(self.nodes)}, wires={len(self.wires)})"

        return seen



# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


@dataclass
class StepContext:
    """Everything a step handler is given when it runs.

    The context carries the node being run, the graph it belongs to, the
    results of every step that already completed, and the *resolved* text of
    the node's own prompt template (``{{steps.N}}`` bindings substituted).
    """

    node: GraphNode
    graph: Graph
    results: dict[int, StepResult] = field(default_factory=dict)
    prompt: str = ""
    variables: dict[str, Any] = field(default_factory=dict)

    @property
    def step(self) -> int:
        """Step id of the node being run."""
        return self.node.step

    def result(self, step: int) -> StepResult | None:
        """Return the result of an already-completed step, if any."""
        return self.results.get(step)

    def output(self, step: int) -> str:
        """Return the textual output of an already-completed step."""
        found = self.results.get(step)
        return found.output if found is not None else ""


@dataclass
class StepResult:
    """The outcome of one executed step."""

    ok: bool = True
    output: str = ""
    data: Any = None
    error: str = ""
    switch_port: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise the result."""
        return {
            "ok": self.ok,
            "output": self.output,
            "data": self.data,
            "error": self.error,
            "switch_port": self.switch_port,
        }


@dataclass
class ExecutionResult:
    """The outcome of a whole graph run."""

    ok: bool = True
    results: dict[int, StepResult] = field(default_factory=dict)
    states: dict[int, NodeRunState] = field(default_factory=dict)
    order: list[int] = field(default_factory=list)
    error: str = ""
    failed_step: int | None = None

    @property
    def output(self) -> str:
        """The output of the last completed step."""
        if not self.order:
            return ""
        return self.results[self.order[-1]].output

    def to_dict(self) -> dict[str, Any]:
        """Serialise the run for JSON output."""
        return {
            "ok": self.ok,
            "error": self.error,
            "failed_step": self.failed_step,
            "order": list(self.order),
            "states": {str(k): v.value for k, v in self.states.items()},
            "results": {str(k): v.to_dict() for k, v in self.results.items()},
        }


def trigger_step(index: int) -> int:
    """Return the synthetic node id for trigger ``index``."""
    if index < 0:
        raise ValidationError("trigger index must be non-negative", index=index)
    return TRIGGER_NODE_BASE + index


def resolve_bindings(text: str, results: Mapping[int, StepResult]) -> str:
    """Substitute ``{{steps.N}}`` bindings with the outputs of step ``N``.

    An unknown step reference is left untouched rather than silently blanked,
    so an unresolved binding stays visible instead of being fabricated away.
    """
    if not text:
        return text

    def replace(match: re.Match[str]) -> str:
        step = int(match.group(1))
        found = results.get(step)
        if found is None:
            return match.group(0)
        return found.output

    return _BINDING_RE.sub(replace, text)


def compile_linear(
    steps: Sequence[str] | Sequence[Mapping[str, Any]],
    name: str = "",
    start: int = 1,
) -> Graph:
    """Compile an ordered list of steps into a linear sequence graph.

    Each entry is either a title string or a mapping with ``title`` and
    ``subtitle`` keys.  Consecutive steps are joined with
    :attr:`FlowRole.SEQUENCE` wires, which is exactly the "one thing after
    the other" shape the agentic loop produces but states explicitly.
    """
    graph = Graph(name=name)
    previous: int | None = None
    number = start
    for entry in steps:
        if isinstance(entry, str):
            title = entry
            subtitle = None
        else:
            title = str(entry.get("title", ""))
            subtitle = entry.get("subtitle")
        node = GraphNode(step=number, title=title, subtitle=subtitle)
        graph.add_node(node)
        if previous is not None:
            graph.add_wire(
                GraphWire(
                    class_=PinClass.FLOW,
                    from_step=previous,
                    to_step=number,
                    flow_role=FlowRole.SEQUENCE,
                )
            )
        previous = number
        number += 1
    return graph


#: Roles that order execution: the target may only run once the source has
#: completed.
_ORDERING_ROLES = frozenset(
    {FlowRole.SEQUENCE, FlowRole.DEPENDENCY, FlowRole.TRIGGER}
)

#: Roles that can activate a target once the source has completed.
_ACTIVATING_ROLES = frozenset(
    {
        FlowRole.SEQUENCE,
        FlowRole.DEPENDENCY,
        FlowRole.TRIGGER,
        FlowRole.SWITCH,
        FlowRole.FAILURE,
    }
)


class Executor:
    """Runs a :class:`Graph`.

    The executor is deliberately explicit about *why* a step may run:

    * a step becomes **activated** when an incoming ordering edge fires
      (sequence fallthrough, dependency fan-in, trigger entry, chosen switch
      port, or a failure recovery route);
    * a step becomes **runnable** only once every incoming sequence,
      dependency and switch predecessor has completed -- this is the fan-in
      rule, and it is what makes a DAG a DAG rather than a chain;
    * a step that **fails** never activates its sequence successors; instead
      it activates its ``on_failure: goto`` recovery targets;
    * a step that **switches** activates only the port it selected.
    """

    def __init__(
        self,
        graph: Graph,
        handlers: Mapping[int, Callable[[StepContext], Any]] | None = None,
        prompts: Mapping[int, str] | None = None,
        default_handler: Callable[[StepContext], Any] | None = None,
        max_steps: int = 500,
    ) -> None:
        """Build an executor for a graph.

        Args:
            graph: the graph to run.
            handlers: optional per-step handler mapping.
            prompts: optional per-step prompt templates containing
                ``{{steps.N}}`` bindings.
            default_handler: handler used for steps with no explicit handler.
            max_steps: hard ceiling on executed steps, so a mis-specified
                graph can never run forever.
        """
        self.graph = graph
        self.handlers: dict[int, Callable[[StepContext], Any]] = dict(handlers or {})
        self.prompts: dict[int, str] = dict(prompts or {})
        self.default_handler = default_handler
        self.max_steps = max_steps

    # -- helpers ------------------------------------------------------------

    def _handler_for(self, step: int) -> Callable[[StepContext], Any] | None:
        """Return the handler for ``step``, falling back to the default."""
        handler = self.handlers.get(step)
        if handler is not None:
            return handler
        return self.default_handler

    def _prompt_for(self, node: GraphNode) -> str:
        """Return the raw prompt template for a node."""
        template = self.prompts.get(node.step)
        if template is None:
            template = node.subtitle or node.title
        return template

    def _predecessors(self, step: int) -> list[int]:
        """Steps whose completion ``step`` waits for.

        Failure edges are excluded: a recovery target does not wait for the
        failed step to complete, because it never will.
        """
        out: list[int] = []
        for w in self.graph.wires:
            if w.to_step != step or w.class_ is not PinClass.FLOW:
                continue
            if w.flow_role is FlowRole.FAILURE:
                continue
            out.append(w.from_step)
        return out

    def _outgoing(self, step: int) -> list[GraphWire]:
        """Every wire leaving ``step``."""
        return [w for w in self.graph.wires if w.from_step == step]

    @staticmethod
    def _normalise(value: Any) -> StepResult:
        """Coerce a handler's return value into a :class:`StepResult`."""
        if isinstance(value, StepResult):
            return value
        if value is None:
            return StepResult(ok=True)
        if isinstance(value, bool):
            return StepResult(ok=value)
        if isinstance(value, str):
            return StepResult(ok=True, output=value)
        if isinstance(value, dict):
            known = {"ok", "output", "data", "error", "switch_port"}
            payload = {k: v for k, v in value.items() if k in known}
            payload.setdefault("ok", True)
            return StepResult(**payload)
        return StepResult(ok=True, output=str(value), data=value)


    # -- execution ----------------------------------------------------------

    def run(self, variables: Mapping[str, Any] | None = None) -> ExecutionResult:
        """Execute the graph and return the run outcome.

        Raises:
            CycleDetected: when the graph contains a cycle.  The check runs
                before any step executes, so a cyclic graph fails loudly
                instead of hanging.
        """
        self.graph.detect_cycle()

        result = ExecutionResult()
        states: dict[int, NodeRunState] = {
            n.step: NodeRunState.PENDING for n in self.graph.nodes
        }
        completed: set[int] = set()
        failed: set[int] = set()
        skipped: set[int] = set()
        activated: set[int] = set()
        results: dict[int, StepResult] = {}
        order: list[int] = []

        # Synthetic trigger nodes are entry points: they complete immediately
        # and fire their outgoing edges.
        for node in self.graph.trigger_nodes():
            states[node.step] = NodeRunState.COMPLETED
            completed.add(node.step)
            order.append(node.step)
            for w in self._outgoing(node.step):
                if w.class_ is PinClass.FLOW and w.flow_role in _ACTIVATING_ROLES:
                    activated.add(w.to_step)

        # Roots: steps with no incoming ordering edge at all.
        if not self.graph.trigger_nodes():
            for node in self.graph.step_nodes():
                if not self._predecessors(node.step):
                    activated.add(node.step)

        executed = 0
        while True:
            progressed = False
            for node in list(self.graph.step_nodes()):
                step = node.step
                if step in completed or step in failed or step in skipped:
                    continue
                if step not in activated:
                    continue
                preds = self._predecessors(step)
                if any(p in failed or p in skipped for p in preds):
                    states[step] = NodeRunState.SKIPPED
                    skipped.add(step)
                    progressed = True
                    continue
                if not all(p in completed for p in preds):
                    continue

                executed += 1
                if executed > self.max_steps:
                    raise ExecutionFailed(
                        f"graph exceeded the {self.max_steps}-step ceiling",
                        step=step,
                    )

                states[step] = NodeRunState.ACTIVE
                outcome = self._run_step(node, results, variables or {})
                results[step] = outcome
                order.append(step)

                if outcome.ok:
                    states[step] = NodeRunState.COMPLETED
                    completed.add(step)
                    self._activate_success(node, outcome, activated)
                else:
                    states[step] = NodeRunState.FAILED
                    failed.add(step)
                    result.ok = False
                    result.failed_step = step
                    result.error = outcome.error or f"step {step} failed"
                    self._activate_failure(node, activated)
                progressed = True
            if not progressed:
                break

        # Anything still pending was never reached: mark it skipped so the
        # report is honest about what did and did not run.
        for node in self.graph.step_nodes():
            if states.get(node.step, NodeRunState.PENDING) is NodeRunState.PENDING:
                states[node.step] = NodeRunState.SKIPPED
                skipped.add(node.step)

        result.results = results
        result.states = states
        result.order = order
        if result.failed_step is not None and not result.error:
            result.error = f"step {result.failed_step} failed"
        return result

    def _run_step(
        self,
        node: GraphNode,
        results: dict[int, StepResult],
        variables: Mapping[str, Any],
    ) -> StepResult:
        """Run one node's handler and normalise the outcome."""
        prompt = resolve_bindings(self._prompt_for(node), results)
        context = StepContext(
            node=node,
            graph=self.graph,
            results=dict(results),
            prompt=prompt,
            variables=dict(variables),
        )
        handler = self._handler_for(node.step)
        if handler is None:
            return StepResult(ok=True, output=prompt)
        try:
            return self._normalise(handler(context))
        except Exception as exc:  # a step failure is data, not a crash
            return StepResult(ok=False, error=f"{type(exc).__name__}: {exc}")

    def _activate_success(
        self,
        node: GraphNode,
        outcome: StepResult,
        activated: set[int],
    ) -> None:
        """Activate the successors of a step that completed successfully."""
        for w in self._outgoing(node.step):
            if w.class_ is not PinClass.FLOW:
                continue
            role = w.flow_role
            if role is FlowRole.FAILURE:
                continue
            if role is FlowRole.SWITCH:
                port = w.from_pin or ""
                if (outcome.switch_port or "") == port:
                    activated.add(w.to_step)
                continue
            activated.add(w.to_step)

    def _activate_failure(self, node: GraphNode, activated: set[int]) -> None:
        """Activate only the recovery targets of a step that failed."""
        for w in self._outgoing(node.step):
            if w.class_ is PinClass.FLOW and w.flow_role is FlowRole.FAILURE:
                activated.add(w.to_step)
