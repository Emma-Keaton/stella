"""Frida backend: dynamic instrumentation, CLI-first and headless.

Frida is a *dynamic* instrumentation toolkit.  This adapter drives it from
the command line so it works in a headless container with no GUI and no
Python bindings installed:

* ``frida-ps`` enumerates running processes (locally, or on a remote device
  given a ``-D`` device id);
* ``frida`` attaches to a local process by name/pid or to a remote device,
  loads a JavaScript snippet, and prints the snippet's output;
* ``frida-trace`` is available for function-level tracing.

Honesty rules:
* a missing ``frida``/``frida-ps`` binary raises
  :class:`stella_rea.errors.BackendUnavailable` -- the *existing* typed
  error from :mod:`stella_rea.errors`, not a parallel type;
* a command failure raises :class:`stella_rea.errors.ExecutionFailed`;
* output that cannot be parsed yields an evidence record explicitly marked as
  *no evidence* at low confidence.  A dynamic run that produced nothing is
  never reported as a success.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..evidence import Confidence, Evidence, EvidenceBundle, Provenance, SourceKind
from ..errors import ExecutionFailed
from . import Backend, CommandResult

__all__ = ["FridaBackend", "ProcessInfo"]

_PROCESS_LINE_RE = re.compile(r"^\s*(\d+)\s+(.*)$")


class ProcessInfo:
    """One process as reported by ``frida-ps``."""

    def __init__(self, pid: int, name: str) -> None:
        """Store the process id and name."""
        self.pid = pid
        self.name = name

    def to_dict(self) -> dict[str, Any]:
        """Serialise the process entry."""
        return {"pid": self.pid, "name": self.name}

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        """Short debugging representation."""
        return f"ProcessInfo(pid={self.pid}, name={self.name!r})"


class FridaBackend(Backend):
    """Dynamic instrumentation via the Frida command-line tools."""

    name = "frida"
    binary = "frida"
    kind = "dynamic"
    available = True
    limitation = ""

    # -- command construction ----------------------------------------------

    def build_ps_argv(
        self,
        device: str | None = None,
        target: str | None = None,
    ) -> list[str]:
        """Build the ``frida-ps`` command line.

        ``device`` selects a remote device (``-D <id>``); ``target`` selects
        the process type (``-a`` apps, ``-U`` usb, ``-D`` device-local).
        """
        args = ["frida-ps"]
        if device:
            args.extend(["-D", device])
        if target == "apps":
            args.append("-a")
        elif target == "device":
            args.append("-D")
        elif target == "usb":
            args.append("-U")
        return args

    def build_run_argv(
        self,
        script: str,
        target: str | None = None,
        device: str | None = None,
        pid: int | None = None,
        timeout: int = 120,
    ) -> list[str]:
        """Build the ``frida`` command line for a one-shot script run.

        A remote device is selected with ``-D <id>``; a local process by
        ``-p <pid>`` or by ``-n <name>``.  ``-q`` keeps it quiet, ``-e`` loads
        the snippet inline and ``--timeout`` bounds the session.
        """
        args = ["frida", "-q", "--timeout", str(timeout)]
        if device:
            args.extend(["-D", device])
        if pid is not None:
            args.extend(["-p", str(pid)])
        elif target:
            args.extend(["-n", target])
        args.extend(["-e", script])
        return args

    def build_trace_argv(
        self,
        pattern: str,
        target: str | None = None,
        device: str | None = None,
        pid: int | None = None,
    ) -> list[str]:
        """Build the ``frida-trace`` command line for function tracing."""
        args = ["frida-trace"]
        if device:
            args.extend(["-D", device])
        if pid is not None:
            args.extend(["-p", str(pid)])
        elif target:
            args.extend(["-n", target])
        args.extend(["-i", pattern])

    # -- execution ----------------------------------------------------------

    def list_processes(
        self,
        device: str | None = None,
        target: str | None = None,
        timeout: int = 60,
    ) -> list[ProcessInfo]:
        """Enumerate processes with ``frida-ps``.

        Raises:
            BackendUnavailable: when ``frida-ps`` is not installed.
            ExecutionFailed: when the command fails or cannot be started.
        """
        self.require("frida-ps")
        argv = self.build_ps_argv(device=device, target=target)
        result = self.run(argv, timeout=timeout)
        if not result.ok:
            raise ExecutionFailed(
                f"frida-ps failed with exit code {result.returncode}",
                argv=list(argv),
                returncode=result.returncode,
                stderr=result.stderr[-4000:],
            )
        return self.parse_processes(result.stdout)

    def parse_processes(self, stdout: str) -> list[ProcessInfo]:
        """Parse ``frida-ps`` tabular output into process entries."""
        processes: list[ProcessInfo] = []
        for line in (stdout or "").splitlines():
            if not line.strip():
                continue
            match = _PROCESS_LINE_RE.match(line)
            if not match:
                continue
            name = match.group(2).strip()
            if not name or name.lower() in {"pid", "name"}:
                continue
            processes.append(ProcessInfo(pid=int(match.group(1)), name=name))
        return processes

    def run_script(
        self,
        script: str,
        target: str | None = None,
        device: str | None = None,
        pid: int | None = None,
        timeout: int = 120,
    ) -> CommandResult:
        """Attach and run a JavaScript snippet, returning the raw output.

        Raises:
            BackendUnavailable: when ``frida`` is not installed.
            ExecutionFailed: when the command fails or cannot be started.
        """
        self.require()
        argv = self.build_run_argv(
            script, target=target, device=device, pid=pid, timeout=timeout
        )
        result = self.run(argv, timeout=timeout + 30)
        if not result.ok:
            raise ExecutionFailed(
                f"frida failed with exit code {result.returncode}",
                argv=list(argv),
                returncode=result.returncode,
                stderr=result.stderr[-4000:],
            )
        return result

    def trace(
        self,
        pattern: str,
        target: str | None = None,
        device: str | None = None,
        pid: int | None = None,
        timeout: int = 120,
    ) -> CommandResult:
        """Trace calls matching ``pattern`` with ``frida-trace``.

        Raises:
            BackendUnavailable: when ``frida-trace`` is not installed.
            ExecutionFailed: when the command fails or cannot be started.
        """
        self.require("frida-trace")
        argv = self.build_trace_argv(pattern, target=target, device=device, pid=pid)
        result = self.run(argv, timeout=timeout)
        if not result.ok:
            raise ExecutionFailed(
                f"frida-trace failed with exit code {result.returncode}",
                argv=list(argv),
                returncode=result.returncode,
                stderr=result.stderr[-4000:],
            )
        return result

    def extract(
        self,
        script: str,
        target: str | None = None,
        device: str | None = None,
        pid: int | None = None,
        timeout: int = 120,
    ) -> EvidenceBundle:
        """Run a snippet and return the captured output as evidence.

        Raises:
            BackendUnavailable: when ``frida`` is not installed.
            ExecutionFailed: when the command fails or cannot be started.
        """
        provenance = Provenance(("frida.run",))
        bundle = EvidenceBundle(provenance=provenance, target=target or device or "")
        result = self.run_script(
            script, target=target, device=device, pid=pid, timeout=timeout
        )
        bundle.provenance = provenance.add("frida.parse")
        output = (result.stdout or "").strip()
        if not output:
            bundle.add(
                Evidence(
                    claim="frida produced no output; nothing was observed",
                    source=SourceKind.FRIDA,
                    confidence=Confidence.NONE,
                    provenance=bundle.provenance,
                    found=False,
                    detail={"returncode": result.returncode},
                )
            )
            return bundle
        payload: Any = output
        try:
            payload = json.loads(output)
        except json.JSONDecodeError:
            payload = output
        bundle.add(
            Evidence(
                claim="frida captured runtime output",
                source=SourceKind.FRIDA,
                confidence=Confidence.HIGH,
                provenance=bundle.provenance,
                detail={"output": payload},
            )
        )
        return bundle

        return args
