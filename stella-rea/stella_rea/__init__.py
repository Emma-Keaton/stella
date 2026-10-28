"""stella-rea: graph-engineered reverse engineering for Stella.

Two ideas live in this package.

**A graph instead of a loop.**  Stella's agentic loop
(``agent/loop.py``: think -> act -> observe -> verify -> repeat) is a loop:
its control flow is implicit, decided at run time by the model, and
unrecoverable once a step goes wrong.  :mod:`stella_rea.graph` adds the
second architecture model: an explicit DAG of steps with typed edges --
dependency fan-in, failure recovery routes, named switch ports, synthetic
trigger entries and ``{{steps.N}}`` data bindings.  A graph is inspectable
before it runs, serialisable between runs, and recoverable when a step
fails.

**Explicit destinations.**  :mod:`stella_rea.apply` never guesses where to
write.  The destination project is always named by the caller, its type is
detected (or declared) rather than assumed, writes need confirmation, and
every write path is checked for containment.

The package is stdlib-only in its core.  The external reverse-engineering
tools (JADX, Ghidra, Frida) are reached through thin adapters that raise
typed errors rather than crashing when a tool is missing.
"""

from __future__ import annotations

from .apply import (
    ApplyReport,
    Destination,
    ProjectType,
    apply_write,
    detect_project_type,
    open_destination,
    plan_write,
)
from .errors import (
    BackendUnavailable,
    ConfirmationRequired,
    CycleDetected,
    DestinationUnknown,
    ErrorTag,
    ExecutionFailed,
    PathEscape,
    Result,
    StellaReaError,
    ValidationError,
    err,
    ok,
)
from .evidence import (
    Confidence,
    Evidence,
    EvidenceBundle,
    Provenance,
    SourceKind,
)
from .graph import (
    TRIGGER_NODE_BASE,
    Executor,
    ExecutionResult,
    FlowRole,
    Graph,
    GraphDiagnostic,
    GraphNode,
    GraphPin,
    GraphSeverity,
    GraphWire,
    NodeKind,
    NodePosition,
    NodeRunState,
    PinClass,
    StepContext,
    StepResult,
    compile_linear,
    resolve_bindings,
    trigger_step,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # graph
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
    # errors
    "ErrorTag",
    "StellaReaError",
    "BackendUnavailable",
    "DestinationUnknown",
    "PathEscape",
    "ValidationError",
    "CycleDetected",
    "ConfirmationRequired",
    "ExecutionFailed",
    "Result",
    "ok",
    "err",
    # evidence
    "Confidence",
    "SourceKind",
    "Provenance",
    "Evidence",
    "EvidenceBundle",
    # apply
    "ProjectType",
    "Destination",
    "ApplyReport",
    "detect_project_type",
    "open_destination",
    "plan_write",
    "apply_write",
]
