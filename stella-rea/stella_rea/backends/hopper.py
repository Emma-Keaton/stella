"""Hopper backend: a DOCUMENTED STUB.

Hopper Disassembler is deliberately **not** automated by this package, and
this is a considered decision rather than a missing feature.  The reasons:

1. **macOS-only.**  Hopper ships as a macOS application.  There is no Linux
   or Windows build, so it cannot be installed on the Linux hosts where
   Stella's analysis pipeline actually runs, and it cannot be installed on
   the Windows workstation used for development.
2. **GUI-only.**  Hopper is an interactive reverse-engineering application.
   It has no supported headless mode and no documented command-line
   scripting surface comparable to Ghidra's ``analyzeHeadless`` or JADX's
   batch decompilation.  Driving it would mean screen-scraping the GUI.
3. **Commercial per-seat licensing.**  Hopper requires a paid, per-seat
   licence, and the licence is bound to the person using the GUI.  A
   containerised or unattended analysis agent has no legitimate way to use
   it, and automating a GUI under someone else's seat is a licensing
   violation.

Given all three, automating Hopper is impractical, and pretending otherwise
would mean shipping a backend that cannot work.  The stub therefore:

* documents the limitation in its docstring, in ``describe()``, in the
  evidence it produces, and in ``docs/GRAPH_MODEL.md``;
* raises the existing typed :class:`stella_rea.errors.BackendUnavailable`
  error rather than pretending to work;
* never returns fabricated findings.

If Hopper is ever needed, the right integration is a human-driven export
that a human imports as evidence -- not an automated adapter.
"""

from __future__ import annotations

from pathlib import Path

from ..evidence import Confidence, Evidence, EvidenceBundle, Provenance, SourceKind
from ..errors import BackendUnavailable, ExecutionFailed
from . import Backend

__all__ = ["HopperBackend", "HOPPER_LIMITATION"]

#: The single source of truth for why Hopper is not automated.
HOPPER_LIMITATION = (
    "Hopper is macOS-only (no Linux or Windows build), is a GUI-only "
    "application with no supported headless or command-line scripting "
    "surface, and requires a commercial per-seat licence bound to the "
    "person using the GUI.  Automating it from an unattended agent is "
    "therefore impractical and is deliberately not attempted."
)


class HopperBackend(Backend):
    """Documented stub for Hopper Disassembler.

    Every entry point raises :class:`stella_rea.errors.BackendUnavailable`.
    """

    name = "hopper"
    binary = "hopper"
    kind = "static"
    available = False
    limitation = HOPPER_LIMITATION

    def require(self, binary: str | None = None) -> str:
        """Always raise: Hopper cannot be automated.

        Raises:
            BackendUnavailable: always.
        """
        raise BackendUnavailable(
            self.name,
            binary or self.binary,
            message=(
                "the Hopper backend is a documented stub: "
                + self.limitation
            ),
            limitation=self.limitation,
        )

    def is_available(self) -> bool:
        """Always False: the Hopper adapter cannot be used."""
        return False

    def describe(self) -> dict[str, object]:
        """Describe the stub, including the reason it is a stub."""
        data = super().describe()
        data["status"] = "stub"
        data["reason"] = self.limitation
        return data

    def extract(
        self,
        target: str | Path,
        *args: object,
        **kwargs: object,
    ) -> EvidenceBundle:
        """Return an evidence bundle documenting that Hopper was not used.

        This never fabricates findings: the bundle contains exactly one
        record, stating that Hopper was not run and why.

        Raises:
            BackendUnavailable: never -- the stub reports honestly instead
                of raising, so a caller can record *why* Hopper contributed
                nothing.
        """
        provenance = Provenance(("hopper.stub",))
        bundle = EvidenceBundle(provenance=provenance, target=str(target))
        bundle.add(
            Evidence(
                claim="hopper was not run: the backend is a documented stub",
                source=SourceKind.HOPPER,
                confidence=Confidence.NONE,
                provenance=provenance,
                found=False,
                detail={"reason": self.limitation},
                locator=str(target),
            )
        )
        return bundle
