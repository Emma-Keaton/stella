"""core/content_boundary.py - untrusted-content boundary.

Content that arrives from outside the agent's trust boundary (web search
results, page fetches, tool outputs from untrusted sources, model-generated
text that cites external data) must be treated as untrusted until it passes a
boundary check. This module enforces:

* A deny-list of dangerous patterns (command injection, path escape, credential
  leakage, SQL, script tags) in untrusted content.
* A size cap so a single large fetch cannot inflate the context window.
* A marking: content that passes is tagged `boundary: "cleared"`; content that
  fails is tagged `boundary: "blocked"` with the reason, and never echoed back
  to the model as fact.

Honesty: blocked content is reported as blocked with the exact rule that
tripped - never sanitized silently and never spoken as verified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

DEFAULT_MAX_BYTES = 64 * 1024  # 64 KiB per untrusted content blob

# Patterns that must never appear in untrusted content passed back to the model.
DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    ("command_injection", r"(?i)(;\s*rm\s|&&\s*rm\s|\|\s*sh\s|`|\$\()"),
    ("path_escape", r"\.\./"),
    ("credential_leak", r"(?i)(api_?key|secret|password|token|Authorization:\s*Bearer)"),
    ("sql_injection", r"(?i)(;\s*drop\s|;\s*delete\s|;\s*insert\s|union\s+select)"),
    ("script_tag", r"(?i)<script\b|javascript:|onerror\s*="),
    ("shell_meta", r"(?i)(curl\s|wget\s|nc\s|netcat\s|bash\s|sh\s|powershell\s)"),
]


@dataclass
class BoundaryVerdict:
    """Result of running content through the boundary."""
    ok: bool
    boundary: str  # "cleared" | "blocked"
    reason: str = ""
    byte_size: int = 0
    rules_tripped: list[str] = field(default_factory=list)
    preview: str = ""  # first 200 chars of cleared content, else ""


@dataclass
class ContentBoundary:
    """Enforces the untrusted-content boundary: size cap + deny-list patterns."""

    max_bytes: int = DEFAULT_MAX_BYTES
    patterns: list[tuple[str, str]] = field(default_factory=lambda: list(DANGEROUS_PATTERNS))

    def check(self, content: str, source: str = "untrusted") -> BoundaryVerdict:
        """Run one blob of untrusted content through the boundary.

        Returns a verdict. `ok=True`/`boundary="cleared"` means the content is
        safe to pass back to the model. `ok=False`/`boundary="blocked"` means
        it must not be used as factual input.
        """
        byte_size = len(content.encode("utf-8", errors="replace"))
        tripped: list[str] = []

        if byte_size > self.max_bytes:
            tripped.append("size_cap")

        for rule_name, pattern in self.patterns:
            if re.search(pattern, content or ""):
                tripped.append(rule_name)

        if tripped:
            return BoundaryVerdict(
                ok=False,
                boundary="blocked",
                reason=(
                    f"Untrusted content from {source} failed the boundary: "
                    + ", ".join(tripped) + ". It was not passed to the model."
                ),
                byte_size=byte_size,
                rules_tripped=tripped,
                preview="",
            )

        preview = (content or "")[:200]
        if len(content or "") > 200:
            preview += "…"
        return BoundaryVerdict(
            ok=True,
            boundary="cleared",
            reason="within size cap and no dangerous patterns",
            byte_size=byte_size,
            rules_tripped=[],
            preview=preview,
        )

    def clear_text(self, text: str, source: str = "untrusted") -> dict[str, Any]:
        """Convenience: returns a dict the model can consume safely."""
        verdict = self.check(text, source)
        return {
            "boundary": verdict.boundary,
            "ok": verdict.ok,
            "reason": verdict.reason,
            "byte_size": verdict.byte_size,
            "rules_tripped": verdict.rules_tripped,
            "preview": verdict.preview,
            "source": source,
        }


__all__ = [
    "BoundaryVerdict", "ContentBoundary",
    "DEFAULT_MAX_BYTES", "DANGEROUS_PATTERNS",
]
