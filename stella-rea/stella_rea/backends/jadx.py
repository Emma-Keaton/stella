"""JADX backend: Android static decompilation.

JADX decompiles DEX/APK artefacts back into readable Java.  This adapter is a
real, working integration: it invokes the ``jadx`` CLI to decompile an APK or
DEX into a directory, and then indexes the produced sources for classes,
methods and strings.

Honesty rules:
* a missing ``jadx`` binary raises
  :class:`stella_rea.errors.BackendUnavailable`;
* a non-zero exit raises :class:`stella_rea.errors.ExecutionFailed`;
* a decompilation that produced no sources yields an evidence record that is
  explicitly marked as *no evidence*, never an invented class list.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..evidence import Confidence, Evidence, EvidenceBundle, Provenance, SourceKind
from ..errors import ExecutionFailed
from . import Backend, CommandResult

__all__ = ["JadxBackend"]

_CLASS_RE = re.compile(r"^\s*(?:public\s+|final\s+|abstract\s+)*class\s+(\w+)", re.M)
_METHOD_RE = re.compile(
    r"^\s*(?:public\s+|private\s+|protected\s+|static\s+|final\s+)*"
    r"[\w<>\[\],. ]+\s+(\w+)\s*\([^)]*\)\s*\{",
    re.M,
)
_STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


class JadxBackend(Backend):
    """Static analysis of Android apps via the JADX CLI."""

    name = "jadx"
    binary = "jadx"
    kind = "static"
    available = True
    limitation = ""

    def build_argv(
        self,
        target: str | Path,
        output: str | Path,
        extra: list[str] | None = None,
    ) -> list[str]:
        """Build the ``jadx`` command line for decompiling ``target``.

        The layout is ``jadx --no-res --comments-level none -d <out> <in>``.
        """
        args = [self.binary, "--no-res", "--comments-level", "none", "-d", str(output)]
        if extra:
            args.extend(extra)
        args.append(str(target))
        return args

    def decompile(
        self,
        target: str | Path,
        output: str | Path,
        timeout: int = 900,
        extra: list[str] | None = None,
    ) -> CommandResult:
        """Decompile an APK/DEX into ``output``.

        Raises:
            BackendUnavailable: when ``jadx`` is not installed.
            ExecutionFailed: when the command fails or cannot be started.
        """
        self.require()
        out_dir = Path(output)
        out_dir.mkdir(parents=True, exist_ok=True)
        argv = self.build_argv(target, out_dir, extra)
        result = self.run(argv, timeout=timeout)
        if not result.ok:
            raise ExecutionFailed(
                f"jadx failed with exit code {result.returncode}",
                argv=list(argv),
                returncode=result.returncode,
                stderr=result.stderr[-4000:],
            )

    def index_sources(self, output: str | Path) -> list[dict[str, Any]]:
        """Index the Java sources under ``output`` into class/method/string lists."""
        root = Path(output)
        classes: list[str] = []
        methods: list[str] = []
        strings: list[str] = []
        if not root.exists():
            return []
        for java in sorted(root.rglob("*.java")):
            text = java.read_text(encoding="utf-8", errors="replace")
            for match in _CLASS_RE.finditer(text):
                classes.append(match.group(1))
            for match in _METHOD_RE.finditer(text):
                methods.append(match.group(1))
            for match in _STRING_RE.finditer(text):
                value = match.group(1)
                if value and value not in strings:
                    strings.append(value)
        return [
            {"classes": sorted(set(classes))},
            {"methods": sorted(set(methods))},
            {"strings": sorted(set(strings))},
        ]

    def extract(
        self,
        target: str | Path,
        output: str | Path,
        timeout: int = 900,
    ) -> EvidenceBundle:
        """Decompile ``target`` and return an evidence bundle describing it.

        Raises:
            BackendUnavailable: when ``jadx`` is not installed.
            ExecutionFailed: when the decompilation fails.
        """
        provenance = Provenance(("jadx.decompile",))
        bundle = EvidenceBundle(provenance=provenance, target=str(target))
        result = self.decompile(target, output, timeout=timeout)
        bundle.provenance = provenance.add("jadx.index")
        sections = self.index_sources(output)
        classes = sections[0]["classes"] if sections else []
        methods = sections[1]["methods"] if len(sections) > 1 else []
        strings = sections[2]["strings"] if len(sections) > 2 else []

        if not classes:
            bundle.add(
                Evidence(
                    claim="jadx produced no Java sources; nothing was observed",
                    source=SourceKind.JADX,
                    confidence=Confidence.NONE,
                    provenance=bundle.provenance,
                    found=False,
                    detail={"returncode": result.returncode},
                    locator=str(output),
                )
            )
            return bundle

        bundle.add(
            Evidence(
                claim=f"decompiled {len(classes)} classes",
                source=SourceKind.JADX,
                confidence=Confidence.HIGH,
                provenance=bundle.provenance,
                detail={"count": len(classes)},
                locator=str(output),
            )
        )
        bundle.add(
            Evidence(
                claim=f"recovered {len(methods)} method names",
                source=SourceKind.JADX,
                confidence=Confidence.HIGH,
                provenance=bundle.provenance,
                detail={"methods": methods[:500]},
                locator=str(output),
            )
        )
        bundle.add(
            Evidence(
                claim=f"recovered {len(strings)} string literals",
                source=SourceKind.JADX,
                confidence=Confidence.MEDIUM,
                provenance=bundle.provenance,
                detail={"strings": strings[:500]},
                locator=str(output),
            )
        )
        return bundle

        return result
