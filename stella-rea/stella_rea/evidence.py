"""Evidence records: what was observed, how sure we are, and where it came from.

The central rule of this module: **never fabricate a fact that was not
observed**.  Every claim carries a source, a confidence, a provenance chain
and an observation timestamp.  Absence of evidence is recorded as evidence of
absence (an :class:`Evidence` with ``found=False`` and low confidence), never
as a silent omission and never as an invented positive.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

__all__ = [
    "Confidence",
    "SourceKind",
    "Provenance",
    "Evidence",
    "EvidenceBundle",
]


class Confidence(str, Enum):
    """How much trust a single observation deserves."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CONFIRMED = "confirmed"

    @property
    def score(self) -> float:
        """A numeric score in ``[0, 1]`` for sorting and thresholding."""
        return {
            Confidence.NONE: 0.0,
            Confidence.LOW: 0.25,
            Confidence.MEDIUM: 0.5,
            Confidence.HIGH: 0.75,
            Confidence.CONFIRMED: 1.0,
        }[self]

    def at_least(self, other: Confidence) -> bool:
        """True when this confidence is at least as strong as ``other``."""
        return self.score >= other.score


class SourceKind(str, Enum):
    """What kind of observation produced the evidence."""

    JADX = "jadx"
    GHIDRA = "ghidra"
    FRIDA = "frida"
    HOPPER = "hopper"
    STATIC_SCAN = "static_scan"
    DYNAMIC_TRACE = "dynamic_trace"
    MANUAL = "manual"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Provenance:
    """Where an observation came from, in order."""

    steps: tuple[str, ...] = ()

    def add(self, step: str) -> Provenance:
        """Return a new provenance with ``step`` appended."""
        return Provenance(self.steps + (step,))

    def to_dict(self) -> dict[str, Any]:
        """Serialise the provenance."""
        return {"steps": list(self.steps)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Provenance:
        """Build a provenance from the serialised form."""
        return cls(tuple(data.get("steps", ())))

    def __str__(self) -> str:
        """Render the chain as ``a -> b -> c``."""


@dataclass
class Evidence:
    """One observed fact.

    Attributes:
        claim: the statement that was observed, in plain language.
        source: which tool or observation produced it.
        confidence: how much trust the observation deserves.
        provenance: the chain of operations that led here.
        observed_at: when the observation was made (UTC).
        found: whether the fact was actually observed.  ``False`` means the
            search happened and did not find the thing -- which is itself a
            result worth recording.
        detail: optional structured payload.
        locator: where in the source the observation lives (file, offset,
            symbol name).
    """

    claim: str = ""
    source: SourceKind = SourceKind.UNKNOWN
    confidence: Confidence = Confidence.NONE
    provenance: Provenance = field(default_factory=Provenance)
    observed_at: str = ""
    found: bool = True
    detail: dict[str, Any] = field(default_factory=dict)
    locator: str = ""

    def __post_init__(self) -> None:
        """Stamp the observation time when the caller did not supply one."""
        if not self.observed_at:
            self.observed_at = datetime.now(timezone.utc).isoformat()

    @property
    def is_absence(self) -> bool:
        """True when this record documents a *negative* observation."""
        return not self.found

    def to_dict(self) -> dict[str, Any]:
        """Serialise the evidence."""
        return {
            "claim": self.claim,
            "source": self.source.value,
            "confidence": self.confidence.value,
            "provenance": self.provenance.to_dict(),
            "observed_at": self.observed_at,
            "found": self.found,
            "detail": dict(self.detail),
            "locator": self.locator,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Evidence:
        """Build evidence from the serialised form."""
        return cls(
            claim=data.get("claim", ""),
            source=SourceKind(data.get("source", "unknown")),
            confidence=Confidence(data.get("confidence", "none")),
            provenance=Provenance.from_dict(data.get("provenance", {})),
            observed_at=data.get("observed_at", ""),
            found=bool(data.get("found", True)),
            detail=dict(data.get("detail", {})),
            locator=data.get("locator", ""),
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        """Short debugging representation."""
        return (
            f"Evidence(claim={self.claim!r}, source={self.source.value}, "
            f"confidence={self.confidence.value}, found={self.found})"
        )



@dataclass
class EvidenceBundle:
    """A set of evidence records plus the extraction's own provenance."""

    records: list[Evidence] = field(default_factory=list)
    provenance: Provenance = field(default_factory=Provenance)
    target: str = ""
    warnings: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        """Number of records in the bundle."""
        return len(self.records)

    def __iter__(self):
        """Iterate over the records."""
        return iter(self.records)

    def add(self, record: Evidence) -> Evidence:
        """Append a record and return it."""
        self.records.append(record)
        return record

    def extend(self, records: list[Evidence]) -> None:
        """Append several records."""
        self.records.extend(records)

    def positives(self) -> list[Evidence]:
        """Only the records that observed something."""
        return [r for r in self.records if r.found]

    def absences(self) -> list[Evidence]:
        """Only the records that observed an absence."""
        return [r for r in self.records if not r.found]

    def claims(self) -> list[str]:
        """The claim text of every positive record."""
        return [r.claim for r in self.positives()]

    def to_dict(self) -> dict[str, Any]:
        """Serialise the bundle."""
        return {
            "target": self.target,
            "provenance": self.provenance.to_dict(),
            "warnings": list(self.warnings),
            "records": [r.to_dict() for r in self.records],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceBundle:
        """Build a bundle from the serialised form."""
        return cls(
            records=[Evidence.from_dict(r) for r in data.get("records", [])],
            provenance=Provenance.from_dict(data.get("provenance", {})),
            target=data.get("target", ""),
            warnings=list(data.get("warnings", [])),
        )

    def to_json(self, indent: int = 2) -> str:
        """Serialise the bundle to JSON."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

        return " -> ".join(self.steps)
