"""core/user_paths.py - canonical on-disk locations for Stella's own data.

Everything Stella persists (memories, credentials, workspace state, logs)
lives under a single per-user directory so an uninstall or a repo wipe can
never take user data with it.
"""

import os
from pathlib import Path

APP_NAME = "StellaAI"


def get_user_data_dir() -> Path:
    """Return (and create) the Stella user-data directory."""
    app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
    d = Path(app_data) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d