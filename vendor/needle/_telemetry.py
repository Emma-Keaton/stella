"""Telemetry stub - vendored by Stella.

Upstream needle reports anonymous usage counts over the network on every
call. Stella ships an air-gapped offline mode, so this module is a deliberate
no-op: nothing is collected, buffered, or transmitted.

Kept as a stub because needle/__init__.py does
`from ._telemetry import track as _track` at import time.
"""

from __future__ import annotations


def _enabled() -> bool:
    return False


def track(event: str, props=None) -> None:
    """No-op. Stella never phones home."""
    return


def _send(event: str, props=None) -> None:
    return
