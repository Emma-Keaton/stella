"""core/background_services.py - the long-running services Stella starts once.

Started from `main()` after the interface is up. Everything here is best-effort:
a service that fails to start is logged and the app carries on without it,
because none of these is more important than Stella coming up.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("background_services")

_started = False


def start_background_services() -> dict:
    """Start the scheduler and register the recurring jobs.

    Idempotent: calling it twice does nothing the second time. Returns what was
    registered, so a caller can log it.
    """
    global _started
    if _started:
        return {"already_running": True}

    registered: dict = {"already_running": False}

    try:
        from core import automation

        automation.start()
        registered["scheduler"] = True
    except Exception as exc:
        registered["scheduler"] = False
        logger.warning("Automation scheduler did not start: %s", exc)

    try:
        from core.providers import catalogue

        registered["provider_catalogues"] = catalogue.register_periodic_refresh()
    except Exception as exc:
        registered["provider_catalogues"] = False
        logger.warning("Model catalogue refresh not registered: %s", exc)

    _started = True
    registered["jobs"] = []
    try:
        from core import automation

        registered["jobs"] = automation.list_jobs()
    except Exception:
        pass
    return registered


def is_running() -> bool:
    return _started
