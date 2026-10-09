"""
core/autonomy.py — is Stella allowed to act without asking?

Stella confirms genuinely irreversible changes by default (core/confirm.py):
deleting files, shutting the machine down, answering a phone call as you.
That is the right default, because a misunderstood voice command is one thing
but a wiped folder is another.

Sometimes you want the opposite. If you are running a long unattended task and
keep saying "yes, just do it", asking every single time is friction for no gain.
Autonomous mode is that opt-out — and it is deliberately, easily reversible:

    - It is a single boolean in app_settings.json (autonomous_mode_enabled).
    - There is a toggle in Settings > AI & Assistant right beside Offline Mode.
    - It is logged loudly every time it changes.

WHAT AUTONOMOUS MODE DOES NOT DO
    It never disables the file-system safety rails (protected folders, path
    sandboxing, the Recycle Bin). It only removes the *human confirmation
    step*, and everything autonomous mode performs is still pushed onto the
    undo stack so it can be reversed afterwards.
"""

from __future__ import annotations

import threading

_SETTING_KEY = "autonomous_mode_enabled"

# In-process cache. Reading a JSON file on every file operation would be
# wasteful; the UI writes through to disk and flips this cache in one step.
_cache: bool | None = None
_lock = threading.Lock()


def _read_setting() -> bool:
    try:
        from memory import config_manager
        return bool(config_manager.get_setting(_SETTING_KEY, False))
    except Exception:
        return False


def is_autonomous() -> bool:
    """True when the user has told Stella to act without asking."""
    global _cache
    with _lock:
        if _cache is None:
            _cache = _read_setting()
        return _cache


def set_autonomous(enabled: bool) -> None:
    """Persist the flag and update the in-process cache together."""
    global _cache
    enabled = bool(enabled)
    try:
        from memory import config_manager
        config_manager.set_setting(_SETTING_KEY, enabled)
    except Exception:
        pass
    with _lock:
        _cache = enabled


def reset_cache() -> None:
    """Force the next is_autonomous() call to re-read from disk."""
    global _cache
    with _lock:
        _cache = None
