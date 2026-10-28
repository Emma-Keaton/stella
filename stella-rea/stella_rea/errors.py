"""Tagged error algebra and Result type for stella-rea.

Expected failures are modelled as *values*, never as bare exceptions crossing a
module boundary.  Every error carries a stable machine-readable ``tag`` plus a
human message and an optional ``details`` mapping, so a CLI, an MCP client, or
an orchestrator can branch on the failure without parsing prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Generic, TypeVar

__all__ = [
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
]

T = TypeVar("T")
E = TypeVar("E")


class ErrorTag(str, Enum):
    """Stable machine-readable tags for every expected failure mode."""

    BACKEND_UNAVAILABLE = "backend_unavailable"
    DESTINATION_UNKNOWN = "destination_unknown"
    PATH_ESCAPE = "path_escape"
    VALIDATION = "validation"
    CYCLE_DETECTED = "cycle_detected"
    CONFIRMATION_REQUIRED = "confirmation_required"
    EXECUTION_FAILED = "execution_failed"


class StellaReaError(Exception):
    """Base class for every expected stella-rea failure.

    The error is both an ``Exception`` (so it can be raised) and a value
    (it carries ``tag``/``details`` so it can be returned inside a
    :class:`Result`).
    """

    tag: ErrorTag = ErrorTag.VALIDATION

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = dict(details)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the error for JSON output."""
        return {
            "tag": self.tag.value,
            "error": type(self).__name__,
            "message": self.message,
            "details": self.details,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"{type(self).__name__}({self.message!r}, details={self.details!r})"


class BackendUnavailable(StellaReaError):
    """An external RE tool (jadx, ghidra, frida, ...) is not installed.

    This is the *only* error type used for a missing binary; backends must
    never crash and never fabricate a successful result.
    """

    tag = ErrorTag.BACKEND_UNAVAILABLE

    def __init__(
        self,
        backend: str,
        binary: str,
        message: str | None = None,
        **details: Any,
    ) -> None:
        text = message or (
            f"backend {backend!r} is unavailable: binary {binary!r} was not found on PATH"
        )
        super().__init__(text, backend=backend, binary=binary, **details)
        self.backend = backend
        self.binary = binary


class DestinationUnknown(StellaReaError):
    """The destination project's type could not be determined."""

    tag = ErrorTag.DESTINATION_UNKNOWN

    def __init__(self, destination: str, message: str | None = None, **details: Any) -> None:
        text = message or (
            f"unknown destination project type for {destination!r}; "
            "pass an explicit project type instead of guessing"
        )
        super().__init__(text, destination=destination, **details)
        self.destination = destination


class PathEscape(StellaReaError):
    """A write target resolved outside of the destination directory."""

    tag = ErrorTag.PATH_ESCAPE

    def __init__(
        self,
        path: str,
        destination: str,
        message: str | None = None,
        **details: Any,
    ) -> None:
        text = message or (
            f"path {path!r} escapes destination {destination!r}; refusing to write"
        )
        super().__init__(text, path=path, destination=destination, **details)
        self.path = path
        self.destination = destination


class ValidationError(StellaReaError):
    """Input did not satisfy a documented invariant."""

    tag = ErrorTag.VALIDATION


class CycleDetected(StellaReaError):
    """The graph contains a cycle and therefore cannot be scheduled."""

    tag = ErrorTag.CYCLE_DETECTED

    def __init__(self, cycle: list[int], message: str | None = None, **details: Any) -> None:
        text = message or ("cycle detected in graph: " + " -> ".join(str(s) for s in cycle))
        super().__init__(text, cycle=list(cycle), **details)
        self.cycle = list(cycle)


class ConfirmationRequired(StellaReaError):
    """A mutating operation needs an explicit confirmation."""

    tag = ErrorTag.CONFIRMATION_REQUIRED


class ExecutionFailed(StellaReaError):
    """A graph step or an external command failed at run time."""

    tag = ErrorTag.EXECUTION_FAILED


@dataclass(frozen=True)
class Result(Generic[T, E]):
    """A tagged outcome: either a value or an error, never both.

    Expected failures travel as values so a caller can branch on
    ``result.error.tag`` instead of catching exceptions across a boundary.
    """

    ok: bool
    value: T | None = None
    error: E | None = None

    @property
    def is_ok(self) -> bool:
        """True when the operation succeeded."""
        return self.ok

    def unwrap(self) -> T:
        """Return the value, raising the stored error if there is one."""
        if self.error is not None:
            raise self.error
        if self.value is None:
            raise ValidationError("successful result carried no value")
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Return the value, or ``default`` when the result is an error."""
        if self.error is not None or self.value is None:
            return default
        return self.value

    def map(self, fn: Callable[[T], Any]) -> Result[Any, E]:
        """Apply ``fn`` to the value of a successful result."""
        if not self.ok or self.value is None:
            return Result(ok=False, error=self.error)
        return Result(ok=True, value=fn(self.value))

    def to_dict(self) -> dict[str, Any]:
        """Serialise the result for JSON output."""
        return {
            "ok": self.ok,
            "value": self.value,
            "error": self.error.to_dict() if self.error is not None else None,
        }


def ok(value: T) -> Result[T, StellaReaError]:
    """Build a successful :class:`Result`."""
    return Result(ok=True, value=value)


def err(error: StellaReaError) -> Result[Any, StellaReaError]:
    """Build a failed :class:`Result`."""
    return Result(ok=False, error=error)
