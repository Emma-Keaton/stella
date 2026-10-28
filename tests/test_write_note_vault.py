"""write_note must follow the Memory Vault the user picked in Settings.

Regression guard for the settings-key contract: the desktop settings page
(ui/settings_pages.py) persists `vault_enabled` / `vault_path`, while the
legacy fallback key is `memory_vault_folder`. This tool used to read a
cwd-relative config file and a key nobody wrote, so the chosen folder was
silently ignored.

Note: pytest's tmp_path fixture cannot be used in this environment - the
Windows temp directory raises PermissionError - so the sandbox is created
inside the opencode temp root instead.
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

from agent import tools
from core.user_paths import get_user_data_dir

TEMP_ROOT = Path(r"C:\Users\USER\AppData\Local\Temp\opencode")


def _write_note_handler():
    reg = tools.build_default_registry()
    tool = reg.get("write_note")
    assert tool is not None, "write_note is not registered"
    return tool.handler


def test_write_note_reads_canonical_vault_keys():
    """The tool must resolve the vault via the user-data settings file."""
    src = inspect.getsource(_write_note_handler())
    assert "get_user_data_dir" in src, (
        "write_note must read the user-data settings file, not a cwd-relative one"
    )
    assert 's.get("vault_path")' in src, (
        "write_note must honour the vault_path key written by the settings UI"
    )


def test_write_note_writes_into_the_configured_vault():
    """With vault_enabled + vault_path set, notes land in that folder."""
    sandbox = Path(tempfile.mkdtemp(dir=str(TEMP_ROOT)))
    import os

    previous = os.environ.get("LOCALAPPDATA")
    os.environ["LOCALAPPDATA"] = str(sandbox)
    try:
        settings_file = Path(get_user_data_dir()) / "config" / "app_settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(
            json.dumps(
                {"vault_enabled": True, "vault_path": str(sandbox / "my vault")}
            ),
            encoding="utf-8",
        )

        result = _write_note_handler()("My Note", "hello world")
        assert result.ok, result.error
        note = sandbox / "my vault" / "My Note.md"
        assert note.exists(), f"note not written into chosen vault: {result.output}"
        assert "hello world" in note.read_text(encoding="utf-8")
    finally:
        if previous is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = previous
