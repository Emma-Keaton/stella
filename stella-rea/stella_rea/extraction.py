"""Reusable extraction workflows.

An extraction workflow is a small, named pipeline that turns a *target*
(an APK, a native binary, a running process) into an
:class:`~stella_rea.evidence.EvidenceBundle`.  Workflows are reusable: the
same workflow runs from the CLI, from the MCP server, or from a Stella
graph node.

Every workflow is honest.  When a backend is missing the workflow raises the
typed :class:`stella_rea.errors.BackendUnavailable`; when a backend runs but
finds nothing, the bundle says so explicitly with ``found=False``.  Nothing
is ever invented to fill a gap.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .backends import get_backend
from .errors import ValidationError
from .evidence import (
    Confidence,
    Evidence,
    EvidenceBundle,
    Provenance,
    SourceKind,
)

__all__ = [
    "extract_android",
    "extract_native",
    "extract_dynamic",
    "extract_generic",
    "static_scan",
    "available_backends",
]


def available_backends() -> list[dict[str, Any]]:
    """Describe every backend, including whether it is installed."""
    from .backends import BACKENDS

    return [backend.describe() for backend in BACKENDS.values()]


def extract_android(
    apk: str | Path,
    output: str | Path,
    timeout: int = 900,
) -> EvidenceBundle:
    """Decompile an Android APK/DEX with JADX and describe what was found.

    Args:
        apk: the APK or DEX artefact.
        output: the directory JADX should decompile into.
        timeout: how long the decompilation may take.

    Raises:
        BackendUnavailable: when JADX is not installed.
        ExecutionFailed: when the decompilation fails.
    """
    backend = get_backend("jadx")
    return backend.extract(apk, output, timeout=timeout)  # type: ignore[attr-defined]


def extract_native(
    binary: str | Path,
    project: str | Path,
    project_name: str = "stella_rea",
    timeout: int = 1800,
) -> EvidenceBundle:
    """Analyse a native binary with Ghidra's headless analyser.

    Args:
        binary: the native binary to analyse.
        project: the directory holding the temporary Ghidra project.
        project_name: the Ghidra project name.
        timeout: how long the analysis may take.

    Raises:
        BackendUnavailable: when Ghidra is not installed.
        ExecutionFailed: when the analysis fails.
    """
    backend = get_backend("ghidra")
    return backend.extract(  # type: ignore[attr-defined]
        binary, project, project_name=project_name, timeout=timeout
    )


def extract_dynamic(
    script: str,
    target: str | None = None,
    device: str | None = None,
    pid: int | None = None,
    timeout: int = 120,
) -> EvidenceBundle:
    """Run a Frida snippet against a local process or a remote device.

    Args:
        script: the JavaScript snippet to run.
        target: the local process name to attach to.
        device: a remote Frida device id to attach to.
        pid: a local pid to attach to.
        timeout: how long the session may run.

    Raises:
        BackendUnavailable: when Frida is not installed.
        ExecutionFailed: when the session fails.
    """
    backend = get_backend("frida")
    return backend.extract(  # type: ignore[attr-defined]
        script, target=target, device=device, pid=pid, timeout=timeout
    )


def extract_generic(
    target: str | Path,
    kind: str = "auto",
    workdir: str | Path | None = None,
) -> EvidenceBundle:
    """Extract from ``target`` using the backend that suits its kind.

    ``kind`` may be ``"android"``, ``"native"``, ``"dynamic"`` or ``"auto"``.
    ``auto`` picks ``android`` for ``.apk``/``.dex``/``.aab`` files and
    ``native`` otherwise.

    Raises:
        ValidationError: when ``kind`` is not recognised.
        BackendUnavailable: when the chosen backend is not installed.
        ExecutionFailed: when the backend fails.
    """
    path = Path(target)
    chosen = kind
    if kind == "auto":
        chosen = (
            "android"
            if path.suffix.lower() in {".apk", ".dex", ".aab"}
            else "native"
        )
    if chosen == "android":
        work = Path(workdir) if workdir else path.parent / "stella_rea_jadx"
        return extract_android(path, work)
    if chosen == "native":
        work = Path(workdir) if workdir else path.parent / "stella_rea_ghidra"
        return extract_native(path, work)
    if chosen == "dynamic":
        raise ValidationError(
            "the dynamic workflow needs an explicit script; call "
            "extract_dynamic directly",
            kind=kind,
        )
    raise ValidationError(
        f"unknown extraction kind {kind!r}; "
        "expected one of: android, native, dynamic, auto",
        kind=kind,
    )


def static_scan(root: str | Path, patterns: list[str] | None = None) -> EvidenceBundle:
    """Scan a source tree for literal patterns, as cheap static evidence.

    This is the always-available workflow: it needs no external binary, so it
    works everywhere.  It records both hits and the *absence* of a hit, so a
    caller can tell "not found" from "never looked".

    Raises:
        ValidationError: when the root does not exist.
    """
    base = Path(root)
    if not base.exists():
        raise ValidationError(f"scan root does not exist: {base}", root=str(base))
    needles = patterns or []
    provenance = Provenance(("static_scan",))
    bundle = EvidenceBundle(provenance=provenance, target=str(base))
    for needle in needles:
        hits: list[str] = []
        for candidate in sorted(base.rglob("*")):
            if not candidate.is_file():
                continue
            try:
                text = candidate.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if needle in text:
                hits.append(str(candidate))
        if hits:
            bundle.add(
                Evidence(
                    claim=f"pattern {needle!r} appears in {len(hits)} file(s)",
                    source=SourceKind.STATIC_SCAN,
                    confidence=Confidence.HIGH,
                    provenance=provenance,
                    detail={"pattern": needle, "files": hits[:200]},
                    locator=str(base),
                )
            )
        else:
            bundle.add(
                Evidence(
                    claim=f"pattern {needle!r} was not found",
                    source=SourceKind.STATIC_SCAN,
                    confidence=Confidence.MEDIUM,
                    provenance=provenance,
                    found=False,
                    detail={"pattern": needle},
                    locator=str(base),
                )
            )
    return bundle


