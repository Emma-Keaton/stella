"""Applying extracted features to a USER-SPECIFIED destination project.

The destination is always an **explicit parameter**.  Nothing in this module
infers a destination from the current working directory, from an environment
variable, or from "wherever the tool happens to live".  The caller names the
project; this module checks that it exists, works out what kind of project
it is, and refuses to write unless the write is explicitly confirmed.

Three guarantees:

* **Unknown project types fail loudly.**  A destination whose type cannot be
  determined raises :class:`stella_rea.errors.DestinationUnknown` rather
  than being guessed at.
* **Writes need confirmation.**  A mutating call without ``confirm=True``
  raises :class:`stella_rea.errors.ConfirmationRequired`.
* **Writes stay inside the destination.**  Every target path is resolved and
  checked for containment; an escape raises
  :class:`stella_rea.errors.PathEscape`.
"""

from __future__ import annotations

import difflib
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import (
    ConfirmationRequired,
    DestinationUnknown,
    PathEscape,
    ValidationError,
)

__all__ = [
    "ProjectType",
    "Destination",
    "detect_project_type",
    "open_destination",
    "plan_write",
    "apply_write",
    "diff_preview",
    "ApplyReport",
]


class ProjectType:
    """The recognised destination project types."""

    ANDROID_KOTLIN = "android/kotlin"
    PYTHON = "python"
    NODE_TS = "node/ts"
    RUST = "rust"
    UNKNOWN = "unknown"

    ALL = (ANDROID_KOTLIN, PYTHON, NODE_TS, RUST)


#: Marker files that identify each project type.  The first match wins, in
#: the order of this mapping.
_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (ProjectType.ANDROID_KOTLIN, ("build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts")),
    (ProjectType.PYTHON, ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")),
    (ProjectType.NODE_TS, ("package.json", "tsconfig.json")),
    (ProjectType.RUST, ("Cargo.toml",)),
)


def detect_project_type(destination: str | Path) -> str:
    """Return the project type of ``destination``.

    Returns:
        One of the :class:`ProjectType` constants, or
        ``"unknown"`` when nothing identifies the project.

    Raises:
        ValidationError: when the destination does not exist or is not a
            directory.
    """
    root = Path(destination)
    if not root.exists():
        raise ValidationError(f"destination does not exist: {root}", destination=str(root))
    if not root.is_dir():
        raise ValidationError(f"destination is not a directory: {root}", destination=str(root))
    for kind, markers in _MARKERS:
        for marker in markers:
            if (root / marker).exists():
                return kind
    return ProjectType.UNKNOWN


@dataclass
class Destination:
    """A validated destination project."""

    path: Path
    project_type: str

    @property
    def root(self) -> Path:
        """The resolved destination root."""
        return self.path

    def resolve(self, relative: str | Path) -> Path:
        """Resolve ``relative`` inside the destination.

        Raises:
            PathEscape: when the resolved path leaves the destination.
            ValidationError: when the path is absolute.
        """
        candidate = Path(relative)
        if candidate.is_absolute():
            raise ValidationError(
                f"apply targets must be relative to the destination: {candidate}",
                path=str(candidate),
            )
        resolved = (self.path / candidate).resolve()
        root = self.path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            raise PathEscape(str(candidate), str(root)) from None
        return resolved

    def describe(self) -> dict[str, Any]:
        """Describe the destination for JSON output."""
        return {"path": str(self.path), "project_type": self.project_type}


def open_destination(
    destination: str | Path,
    project_type: str | None = None,
) -> Destination:
    """Validate a destination and determine its project type.

    Args:
        destination: the destination project directory.  Required.
        project_type: an explicit project type.  When given it is trusted
            (after validation); when omitted the type is detected.

    Raises:
        DestinationUnknown: when the type cannot be determined and was not
            supplied explicitly.
        ValidationError: when the destination does not exist.
    """
    root = Path(destination).expanduser()
    if not root.exists():
        raise ValidationError(f"destination does not exist: {root}", destination=str(root))
    if not root.is_dir():
        raise ValidationError(f"destination is not a directory: {root}", destination=str(root))
    if project_type:
        if project_type not in ProjectType.ALL:
            raise ValidationError(
                f"unknown project type {project_type!r}; "
                f"known types: {', '.join(ProjectType.ALL)}",
                project_type=project_type,
            )
        return Destination(path=root.resolve(), project_type=project_type)
    detected = detect_project_type(root)
    if detected == ProjectType.UNKNOWN:
        raise DestinationUnknown(str(root.resolve()))
    return Destination(path=root.resolve(), project_type=detected)


@dataclass
class ApplyReport:
    """What an apply run did (or would have done)."""

    destination: str = ""
    project_type: str = ""
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    diffs: dict[str, str] = field(default_factory=dict)
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialise the report."""
        return {
            "destination": self.destination,
            "project_type": self.project_type,
            "written": list(self.written),
            "skipped": list(self.skipped),
            "diffs": dict(self.diffs),
            "dry_run": self.dry_run,
        }


def diff_preview(path: Path, content: str) -> str:
    """Return a unified diff between a file's current content and ``content``.

    A file that does not exist yet diffs against an empty file, so the
    preview shows exactly what would be added.
    """
    existing = ""
    if path.exists() and path.is_file():
        existing = path.read_text(encoding="utf-8", errors="replace")
    return "".join(
        difflib.unified_diff(
            existing.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"a/{path.name}",
            tofile=f"b/{path.name}",
        )
    )


def plan_write(
    destination: str | Path,
    files: dict[str, str],
    project_type: str | None = None,
    dry_run: bool = True,
    confirm: bool = False,
    allow: list[str] | None = None,
) -> ApplyReport:
    """Plan (and optionally perform) writes into a destination project.

    Args:
        destination: the destination project directory.  Required.
        files: mapping of destination-relative path to new file content.
        project_type: an explicit project type; detected when omitted.
        dry_run: when True (the default) nothing is written and the report
            contains diffs.
        confirm: must be True for a non-dry-run write to proceed.
        allow: optional allowlist of destination-relative paths (or path
            prefixes) that may be written.  When given, any target outside
            the allowlist is refused.

    Raises:
        DestinationUnknown: when the project type cannot be determined.
        ConfirmationRequired: when ``dry_run`` is False and ``confirm`` is
            not True.
        PathEscape: when a target path leaves the destination.
        ValidationError: when a target is outside the allowlist.
    """
    target = open_destination(destination, project_type=project_type)
    if not dry_run and not confirm:
        raise ConfirmationRequired(
            "writing to the destination requires confirm=True (or --confirm "
            "on the command line); use dry_run to preview the diff instead",
            destination=str(target.path),
        )
    report = ApplyReport(
        destination=str(target.path),
        project_type=target.project_type,
        dry_run=dry_run,
    )
    for relative, content in files.items():
        if allow is not None and not _is_allowed(relative, allow):
            raise ValidationError(
                f"write target {relative!r} is not in the allowlist",
                path=str(relative),
                allow=list(allow),
            )
        resolved = target.resolve(relative)
        diff = diff_preview(resolved, content)
        report.diffs[str(relative)] = diff
        if dry_run:
            report.skipped.append(str(relative))
            continue
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        report.written.append(str(relative))
    return report


def _is_allowed(relative: str, allow: list[str]) -> bool:
    """True when ``relative`` is covered by the allowlist."""
    candidate = Path(relative).as_posix()
    for entry in allow:
        prefix = Path(entry).as_posix()
        if candidate == prefix or candidate.startswith(prefix.rstrip("/") + "/"):
            return True
    return False


def apply_write(
    destination: str | Path,
    files: dict[str, str],
    project_type: str | None = None,
    dry_run: bool = True,
    confirm: bool = False,
) -> ApplyReport:
    """Apply extracted features to a destination project.

    This is the explicit-destination entry point.  The destination is a
    required argument; there is no default and no implicit "current
    directory" behaviour.

    Args:
        destination: the destination project directory.  Required.
        files: mapping of destination-relative path to new file content.
        project_type: an explicit project type; detected when omitted.
        dry_run: when True nothing is written and diffs are returned.
        confirm: must be True for a non-dry-run write to proceed.

    Returns:
        An :class:`ApplyReport` describing what was written or previewed.

    Raises:
        DestinationUnknown: when the project type cannot be determined.
        ConfirmationRequired: when writing without explicit confirmation.
        PathEscape: when a target path leaves the destination.
    """
    return plan_write(
        destination,
        files,
        project_type=project_type,
        dry_run=dry_run,
        confirm=confirm,
    )

    return Destination(path=root.resolve(), project_type=detected)
