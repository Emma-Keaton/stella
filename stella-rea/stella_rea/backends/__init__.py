"""Adapters for external reverse-engineering tools.

Every adapter in this package follows the same three rules:

1. **A missing binary is a typed error, never a crash.**  The adapter raises
   :class:`stella_rea.errors.BackendUnavailable` when its tool is not
   installed.  There is no parallel error type.
2. **A failed command is a typed error.**  :class:`stella_rea.errors.
   ExecutionFailed` carries the command, exit code and captured stderr.
3. **A successful command is not automatically a positive finding.**  If the
   output cannot be parsed, the adapter returns an evidence record that is
   explicitly marked as *no evidence* at low confidence.  Nothing is ever
   fabricated.

The supported set is honest about what exists:

===========  ======  ==========  ==========================================
Backend      Status   Kind         Notes
===========  ======  ==========  ==========================================
JADX         working  static       Android DEX/APK decompilation
Ghidra       working  static       native binaries, headless
Frida        working  dynamic      CLI-first, attach to process or device
Hopper       stub     static       macOS-only, GUI-only, per-seat license
===========  ======  ==========  ==========================================
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ..errors import BackendUnavailable, ExecutionFailed

__all__ = [
    "CommandResult",
    "CommandRunner",
    "run_command",
    "which",
    "Backend",
    "BACKENDS",
    "get_backend",
]


@dataclass(frozen=True)
class CommandResult:
    """The outcome of running an external command."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        """True when the command exited with status zero."""
        return self.returncode == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialise the result."""
        return {
            "argv": list(self.argv),
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


def run_command(
    argv: Sequence[str],
    timeout: int = 300,
    cwd: str | Path | None = None,
) -> CommandResult:
    """Run an external command and capture its output.

    Raises:
        ExecutionFailed: when the command cannot be started or times out.
            A non-zero exit code is *not* raised here; the caller inspects
            :attr:`CommandResult.ok`.
    """
    args = [str(a) for a in argv]
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout)),
            cwd=str(cwd) if cwd is not None else None,
        )
    except FileNotFoundError as exc:
        raise ExecutionFailed(
            f"command not found: {args[0]}", argv=args, reason=str(exc)
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ExecutionFailed(
            f"command timed out after {timeout}s: {args[0]}",
            argv=args,
            reason=str(exc),
        ) from exc
    return CommandResult(
        argv=tuple(args),
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


#: The command runner used by every backend.  Tests monkeypatch this symbol
#: to assert on argument construction without needing the tools installed.
CommandRunner = run_command


def which(binary: str) -> str | None:
    """Return the absolute path of ``binary`` on PATH, or ``None``."""


class Backend:
    """Base class for external-tool adapters."""

    #: Stable backend name, used in error messages and evidence records.
    name: str = "backend"
    #: The executable that must be present for this backend to work.
    binary: str = ""
    #: What kind of analysis this backend performs.
    kind: str = "static"
    #: Whether the backend can actually be automated.
    available: bool = True
    #: Why the backend is a documented stub (empty when it works).
    limitation: str = ""

    def require(self, binary: str | None = None) -> str:
        """Return the path of the required binary or raise a typed error.

        Raises:
            BackendUnavailable: when the binary is not on PATH.
        """
        wanted = binary or self.binary
        found = which(wanted)
        if not found:
            raise BackendUnavailable(self.name, wanted, limitation=self.limitation)
        return found

    def is_available(self) -> bool:
        """True when this backend's binary is installed."""
        if not self.available:
            return False
        return which(self.binary) is not None

    def run(
        self,
        argv: Sequence[str],
        timeout: int = 300,
        cwd: str | Path | None = None,
    ) -> CommandResult:
        """Run a command after checking that the binary exists.

        Raises:
            BackendUnavailable: when the tool is missing.
            ExecutionFailed: when the command cannot be started.
        """
        self.require()
        return run_command(argv, timeout=timeout, cwd=cwd)

    def describe(self) -> dict[str, Any]:
        """Describe the backend for JSON output and documentation."""
        return {
            "name": self.name,
            "binary": self.binary,
            "kind": self.kind,
            "available": self.is_available(),
            "limitation": self.limitation,
        }


def _load_backends() -> dict[str, Backend]:
    """Instantiate every backend adapter lazily."""
    from .frida import FridaBackend
    from .ghidra import GhidraBackend
    from .hopper import HopperBackend
    from .jadx import JadxBackend

    return {
        "jadx": JadxBackend(),
        "ghidra": GhidraBackend(),
        "frida": FridaBackend(),
        "hopper": HopperBackend(),
    }


class _BackendRegistry(dict):
    """A dict of backends that loads them on first access."""

    def _ensure(self) -> None:
        """Populate the registry on first use."""
        if not super().__len__():
            super().update(_load_backends())

    def __getitem__(self, key: str) -> Backend:
        """Return a backend by name."""
        self._ensure()
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a backend by name, or ``default``."""
        self._ensure()
        return super().get(key, default)

    def __iter__(self):
        """Iterate over the backend names."""
        self._ensure()
        return super().__iter__()

    def items(self):
        """Iterate over ``(name, backend)`` pairs."""
        self._ensure()
        return super().items()

    def values(self):
        """Iterate over the backends."""
        self._ensure()
        return super().values()

    def keys(self):
        """Iterate over the backend names."""
        self._ensure()
        return super().keys()

    def __len__(self) -> int:
        """Number of registered backends."""
        self._ensure()
        return super().__len__()


#: Every backend adapter, keyed by name.
BACKENDS: _BackendRegistry = _BackendRegistry()


def get_backend(name: str) -> Backend:
    """Return the backend adapter with the given name.

    Raises:
        ExecutionFailed: when the name is not a known backend.
    """
    key = name.strip().lower()
    if key not in BACKENDS:
        known = ", ".join(sorted(BACKENDS.keys()))
        raise ExecutionFailed(f"unknown backend {name!r}; known backends: {known}")
    return BACKENDS[key]

    return shutil.which(binary)
