from __future__ import annotations
from typing import Any, Dict
import os, subprocess, sys, venv, pathlib, shutil, json

FEATURE_METADATA = {
    "name": "hummingbot_installer",
    "description": "Ensure Hummingbot (and its Python deps) are installed in a dedicated venv.",
    "triggers": ["install hummingbot", "bootstrap hummingbot"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "force_reinstall": {"type": "BOOLEAN", "default": False}
        },
        "required": []
    }
}

STELLA_ROOT = pathlib.Path(r"E:\Projects\stella")
VENV_DIR    = STELLA_ROOT / "venvs" / "hummingbot"
HB_BIN      = VENV_DIR / ("Scripts" if os.name == "nt" else "bin") / ("hummingbot.exe" if os.name == "nt" else "hummingbot")

def _venv_exists() -> bool:
    return HB_BIN.exists()

def _create_venv() -> None:
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR)
    builder = venv.EnvBuilder(with_pip=True)
    builder.create(VENV_DIR)
    pip = VENV_DIR / ("Scripts" if os.name == "nt" else "bin") / ("pip.exe" if os.name == "nt" else "pip")
    subprocess.check_call([str(pip), "install", "--upgrade", "pip", "setuptools", "wheel"])
    subprocess.check_call([str(pip), "install", "hummingbot"])
    (VENV_DIR / ".stella_hummingbot").write_text(json.dumps({"version": "auto"}))

def _ensure_installed(force: bool = False) -> Dict[str, Any]:
    if not _venv_exists() or force:
        try:
            _create_venv()
        except Exception as e:
            return {"ok": False, "error": f"Failed to create/install hummingbot venv: {e}"}
    return {"ok": True, "hummingbot_bin": str(HB_BIN)}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    force = bool(params.get("force_reinstall", False))
    return _ensure_installed(force)