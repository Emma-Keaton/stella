"""Tests for the graph engine: model fidelity, execution, cycle detection."""

from __future__ import annotations

import json

import pytest

from stella_rea.errors import CycleDetected, ValidationError
from stella_rea.graph import (
    TRIGGER_NODE_BASE,
    Executor,
    FlowRole,
    Graph,
    GraphNode,
    GraphPin,
    GraphWire,
    NodeKind,
    NodeRunState,
    PinClass,
    StepResult,
    compile_linear,
    resolve_bindings,
    trigger_step,
)


def _wire(src: int, dst: int, role: FlowRole, port: str | None = None) -> GraphWire:
    """Build a flow wire for a test."""
    return GraphWire(
        class_=PinClass.FLOW,
        from_step=src,
        to_step=dst,
        flow_role=role,
        from_pin=port,
    )


def test_trigger_node_base_matches_the_zeroclaw_constant() -> None:
    """The synthetic trigger id offset is ported verbatim."""
    assert TRIGGER_NODE_BASE == 1_000_000
    assert trigger_step(0) == 1_000_000
    assert trigger_step(3) == 1_000_003


def test_pin_and_wire_round_trip_through_the_snake_case_shape() -> None:
    """Pins and wires serialise to the same wire shape as zeroclaw."""
    node = GraphNode(
        step=1,
        title="publish",
        kind=NodeKind.STEP,
        subtitle=None,
        trigger_index=None,
        inputs=[GraphPin(PinClass.DATA, "calls.0.body", "string", True)],
        outputs=[GraphPin(PinClass.FLOW, "out", None, False)],
    )
    wire = GraphWire(
        class_=PinClass.DATA,
        from_step=1,
        to_step=2,
        flow_role=None,
        from_pin="result",
        to_pin="calls.0.body",
    )
    graph = Graph(nodes=[node], wires=[wire])
    payload = graph.to_dict()

    assert payload["nodes"][0]["inputs"][0]["class"] == "data"
    assert payload["nodes"][0]["outputs"][0]["class"] == "flow"
    assert "data_type" not in payload["nodes"][0]["outputs"][0]
    assert payload["wires"][0]["class"] == "data"

    back = Graph.from_dict(payload)
    assert back.nodes[0].inputs[0].data_type == "string"
    assert back.wires[0].from_pin == "result"


def test_graph_json_round_trip_is_stable() -> None:
    """A graph survives a JSON round trip unchanged."""
    graph = compile_linear(["one", "two", "three"], name="plan")
    text = graph.to_json()
    back = Graph.from_json(text)
    assert back.to_dict() == graph.to_dict()
    assert json.loads(text)["name"] == "plan"


def test_flow_role_values_are_snake_case() -> None:
    """Every flow role serialises to its zeroclaw wire value."""
    assert FlowRole.SEQUENCE.value == "sequence"
    assert FlowRole.DEPENDENCY.value == "dependency"
    assert FlowRole.FAILURE.value == "failure"
    assert FlowRole.SWITCH.value == "switch"
    assert FlowRole.TRIGGER.value == "trigger"


def test_compile_linear_builds_a_sequence_chain() -> None:
    """A linear plan compiles to sequence wires."""
    graph = compile_linear(["a", "b", "c"])
    assert [n.step for n in graph.step_nodes()] == [1, 2, 3]
    assert all(w.flow_role is FlowRole.SEQUENCE for w in graph.wires)


def test_executor_runs_a_linear_graph_in_order() -> None:
    """A linear graph runs its steps in order."""
    graph = compile_linear(["a", "b", "c"])
    seen: list[int] = []

    def handler(ctx):
        seen.append(ctx.step)
        return ctx.node.title

    result = Executor(graph, default_handler=handler).run()
    assert result.ok
    assert seen == [1, 2, 3]


def test_executor_waits_for_every_dependency_before_running_a_fan_in() -> None:
    """A dependency fan-in runs only after both sources complete."""
    graph = Graph(name="fanin")
    graph.add_node(GraphNode(step=1, title="a"))
    graph.add_node(GraphNode(step=2, title="b"))
    graph.add_node(GraphNode(step=3, title="join"))
    graph.add_wire(_wire(1, 3, FlowRole.DEPENDENCY))
    graph.add_wire(_wire(2, 3, FlowRole.DEPENDENCY))

    order: list[int] = []

    def handler(ctx):
        order.append(ctx.step)
        return ctx.step

    result = Executor(graph, default_handler=handler).run()
    assert order[-1] == 3
    assert order.index(3) == 2
    assert result.ok


def test_failure_edge_routes_to_the_recovery_node_and_skips_the_sequence() -> None:
    """A failed step routes to its recovery target, not down the sequence."""
    graph = Graph(name="recovery")
    graph.add_node(GraphNode(step=1, title="risky"))
    graph.add_node(GraphNode(step=2, title="after"))
    graph.add_node(GraphNode(step=3, title="recover"))
    graph.add_wire(_wire(1, 2, FlowRole.SEQUENCE))
    graph.add_wire(_wire(1, 3, FlowRole.FAILURE))

    ran: list[int] = []

    def handler(ctx):
        ran.append(ctx.step)
        if ctx.step == 1:
            raise RuntimeError("boom")
        return "ok"

    result = Executor(graph, default_handler=handler).run()
    assert 3 in ran
    assert 2 not in ran
    assert result.states[2] is NodeRunState.SKIPPED
    assert result.states[3] is NodeRunState.COMPLETED


def test_switch_activates_only_the_chosen_port() -> None:
    """A switch step activates only the port it selected."""
    graph = Graph(name="switch")
    graph.add_node(GraphNode(step=1, title="branch"))
    graph.add_node(GraphNode(step=2, title="yes"))
    graph.add_node(GraphNode(step=3, title="no"))
    graph.add_wire(_wire(1, 2, FlowRole.SWITCH, port="yes"))
    graph.add_wire(_wire(1, 3, FlowRole.SWITCH, port="no"))

    ran: list[int] = []

    def handler(ctx):
        ran.append(ctx.step)
        if ctx.step == 1:
            return StepResult(ok=True, output="branched", switch_port="no")
        return "ok"

    result = Executor(graph, default_handler=handler).run()
    assert 2 not in ran
    assert 3 in ran


def test_trigger_node_is_a_synthetic_entry_point() -> None:
    """A trigger node enters the graph and fires its outgoing edge."""
    graph = Graph(name="triggered")
    graph.add_node(
        GraphNode(
            step=trigger_step(0),
            title="on-start",
            kind=NodeKind.TRIGGER,
            trigger_index=0,
        )
    )
    graph.add_node(GraphNode(step=1, title="work"))
    graph.add_wire(_wire(trigger_step(0), 1, FlowRole.TRIGGER))

    ran: list[int] = []

    def handler(ctx):
        ran.append(ctx.step)
        return "done"

    result = Executor(graph, default_handler=handler).run()
    assert ran == [1]
    assert result.ok


def test_data_binding_resolves_a_previous_step_output() -> None:
    """``{{steps.N}}`` binds the output of step N into a later prompt."""
    graph = compile_linear(["first", "second"])
    prompts = {2: "use {{steps.1}} please"}

    seen: list[str] = []

    def handler(ctx):
        seen.append(ctx.prompt)
        return "value"

    Executor(graph, prompts=prompts, default_handler=handler).run()
    assert seen[1] == "use value please"


def test_resolve_bindings_leaves_unknown_steps_untouched() -> None:
    """An unresolved binding stays visible rather than being blanked."""
    assert resolve_bindings("x {{steps.9}} y", {}) == "x {{steps.9}} y"


def test_cycle_detection_raises_instead_of_hanging() -> None:
    """A cyclic graph fails clearly and terminates."""
    graph = Graph(name="cyclic")
    graph.add_node(GraphNode(step=1, title="a"))
    graph.add_node(GraphNode(step=2, title="b"))
    graph.add_wire(_wire(1, 2, FlowRole.SEQUENCE))
    graph.add_wire(_wire(2, 1, FlowRole.SEQUENCE))

    assert graph.find_cycle()

    with pytest.raises(CycleDetected) as excinfo:
        graph.detect_cycle()
    assert excinfo.value.cycle

    with pytest.raises(CycleDetected):
        Executor(graph, default_handler=lambda ctx: "x").run()


def test_failure_edges_do_not_create_a_scheduling_cycle() -> None:
    """A backwards recovery edge is not a cycle."""
    graph = Graph(name="recover")
    graph.add_node(GraphNode(step=1, title="a"))
    graph.add_node(GraphNode(step=2, title="b"))
    graph.add_wire(_wire(1, 2, FlowRole.SEQUENCE))
    graph.add_wire(_wire(2, 1, FlowRole.FAILURE))
    assert graph.find_cycle() == []


def test_missing_node_raises_a_validation_error() -> None:
    """Looking up a node that does not exist is a typed failure."""
    graph = Graph()
    with pytest.raises(ValidationError):
        graph.node(7)
