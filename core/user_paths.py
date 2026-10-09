import os
import shutil
from pathlib import Path

# Old application data folder (pre-rebrand). Kept so existing installs find
# their settings, memories and credentials again after the move to StellaAI.
LEGACY_APP_NAME = "BrahmaAI"
APP_NAME = "StellaAI"


def _migrate_legacy(target: Path) -> None:
    """Copy the old BrahmaAI data folder into StellaAI, once.

    Only runs when StellaAI is missing/empty and the legacy folder has real
    content, so a re-install never resurrects stale data. `copytree` merges,
    which means an interrupted run can simply be retried.
    """
    app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
    legacy = Path(app_data) / LEGACY_APP_NAME
    try:
        if not legacy.is_dir():
            return
        # Anything already in target means this is not a first run.
        if target.exists() and any(target.iterdir()):
            return
        legacy_has_content = any(legacy.iterdir())
        if not legacy_has_content:
            return
        shutil.copytree(legacy, target, dirs_exist_ok=True)
        print(f"[user_paths] Migrated {LEGACY_APP_NAME} data -> {APP_NAME}")
    except Exception as e:  # pragma: no cover - migration must never block boot
        print(f"[user_paths] Legacy data migration skipped: {e}")


def get_user_data_dir() -> Path:
    app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
    d = Path(app_data) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    # Best-effort one-time migration from the old BrahmaAI folder.
    _migrate_legacy(d)
    return d
