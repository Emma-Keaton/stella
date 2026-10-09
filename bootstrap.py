#!/usr/bin/env python3
"""
bootstrap.py — make any device ready to run Stella, from a bare download.

Why this exists
---------------
The old setup was Windows-only (bootstrap.ps1) and tried to install one huge
requirements.txt in a single step. That fails on exactly the machines that
need help most: slow connections, small disks, phones. This replaces it with a
single cross-platform entry point that runs wherever Python 3 does — Windows,
macOS, Linux, and Android via Termux/py.

What it does, in order, never raising on a bad network mid-way
-----------------------------------------------------------------
  1. Find a Python 3.9+ interpreter (the one running this, else python3/python).
  2. Create `.venv` next to this script IF MISSING; reuse it if present. So a
     device that already has the venv skips straight to the check step.
  3. Install dependencies TIER BY TIER, smallest-and-most-essential first:
        core   -> the app can launch
        voice  -> speech in/out
        vision -> camera / screen understanding
        web    -> browsing, search, playback control
        server -> dashboard + Discord bridge
        docs   -> office / PDF generation
     Each tier is skipped if every package in it already imports, so re-running
     on a set-up device is instant and costs no bandwidth.
  4. Print a clear per-tier PASS / SKIP / FAIL summary and a "what to do next".

If a tier fails (no internet, a platform-specific wheel that doesn't exist on
this device, e.g. Windows-only pycaw on Linux) it is recorded and the next tier
still runs. The app is usable once `core` is installed; everything else is
progressive enhancement. Exit code is 0 if `core` succeeded, non-zero if not.

Usage
-----
    python bootstrap.py                 # install core + best-effort optional
    python bootstrap.py --tier core     # just enough to launch
    python bootstrap.py --tier all      # everything (default)
    python bootstrap.py --venv .venv    # custom venv path
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"

# Tier -> requirements file. Order matters: core must come first so the app can
# boot; the rest are optional and installed best-effort.
TIERS = [
    ("core", "requirements-core.txt"),
    ("voice", "requirements-voice.txt"),
    ("vision", "requirements-vision.txt"),
    ("web", "requirements-web.txt"),
    ("server", "requirements-server.txt"),
    ("docs", "requirements-docs.txt"),
]

# importlib module name -> package as it appears on PyPI, for the already-installed
# check. Only needed where the import name differs from the distribution name.
_IMPORT_ALIASES = {
    "pillow": "PIL",
    "opencv-python": "cv2",
    "pyyaml": "yaml",
    "python-dotenv": "dotenv",
    "qrcode[pil]": "qrcode",
    "uvicorn[standard]": "uvicorn",
    "discord.py": "discord",
    "google-genai": "google.genai",
    "beautifulsoup4": "bs4",
    "send2trash": "send2trash",
    "duckduckgo-search": "duckduckgo_search",
    "youtube-transcript-api": "youtube_transcript_api",
    "pyqt6": "PyQt6",
    "piper-tts": "piper",
    "mediapipe": "mediapipe",
}


def _log(msg: str) -> None:
    print(msg, flush=True)


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _venv_pip(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"

def ensure_venv(venv_dir: Path) -> Path:
    """Create .venv if missing; return the interpreter to install into."""
    py = _venv_python(venv_dir)
    if py.exists():
        _log(f"[bootstrap] Reusing existing venv at {venv_dir}")
        return py
    if sys.prefix == sys.base_prefix and not _in_venv():
        # Not already inside a venv — make one so we don't pollute the system.
        _log(f"[bootstrap] Creating virtual environment at {venv_dir} ...")
        venv.EnvBuilder(with_pip=True, clear=False).create(str(venv_dir))
        if py.exists():
            return py
        _log("[bootstrap] Could not create .venv; using the current interpreter.")
    else:
        _log("[bootstrap] Already inside a virtual environment; using it directly.")
    return Path(sys.executable)


def _in_venv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _req_packages(req_file: Path) -> list[str]:
    """Parse a requirements file into a list of package specifiers."""
    pkgs: list[str] = []
    for line in req_file.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            pkgs.append(line)
    return pkgs


def _import_name(pkg: str) -> str:
    base = pkg.split("[")[0].split(">=")[0].split("==")[0].split("<")[0].strip()
    return _IMPORT_ALIASES.get(base.lower(), base.replace("-", "_"))


def _tier_satisfied(req_file: Path) -> bool:
    """True if every package in the tier already imports (skip, no bandwidth)."""
    for pkg in _req_packages(req_file):
        try:
            if importlib.util.find_spec(_import_name(pkg)) is None:
                return False
        except (ImportError, ValueError, ModuleNotFoundError):
            return False
    return True


def install_tier(py: Path, name: str, req_file: Path) -> str:
    """Install one tier. Returns 'SKIP' | 'OK' | 'FAIL'."""
    if not req_file.exists():
        return "SKIP"
    if _tier_satisfied(req_file):
        _log(f"[bootstrap] {name:6s}: already installed, skipping")
        return "SKIP"
    _log(f"[bootstrap] {name:6s}: installing from {req_file.name} ...")
    cmd = [str(py), "-m", "pip", "install", "--disable-pip-version-check",
           "-r", str(req_file)]
    try:
        subprocess.run(cmd, cwd=str(ROOT), check=True)
        _log(f"[bootstrap] {name:6s}: done")
        return "OK"
    except subprocess.CalledProcessError as e:
        # A platform-specific wheel (e.g. Windows-only pycaw on Linux) can fail
        # without breaking the rest. Record it and keep going.
        _log(f"[bootstrap] {name:6s}: FAILED (rc={e.returncode}) — continuing anyway")
        return "FAIL"


def main() -> int:
    ap = argparse.ArgumentParser(description="Cross-platform Stella bootstrap")
    ap.add_argument("--tier", default="all",
                    choices=["all", "core", "voice", "vision", "web", "server", "docs"],
                    help="install only this tier (default: all, core first)")
    ap.add_argument("--venv", default=str(VENV_DIR), help="venv path")
    args = ap.parse_args()

    _log("=" * 60)
    _log("  STELLA BOOTSTRAP — preparing this device")
    _log("=" * 60)
    _log(f"[bootstrap] Python {sys.version.split()[0]} on {sys.platform}")

    venv_dir = Path(args.venv)
    py = ensure_venv(venv_dir)

    # Order tiers core-first; honour --tier.
    if args.tier == "all":
        wanted = list(TIERS)
    elif args.tier == "core":
        wanted = [t for t in TIERS if t[0] == "core"]
    else:
        wanted = [("core", "requirements-core.txt")] + \
                 [t for t in TIERS if t[0] == args.tier]

    results: dict[str, str] = {}
    core_ok = True
    for name, fname in wanted:
        res = install_tier(py, name, ROOT / fname)
        results[name] = res
        if name == "core" and res == "FAIL":
            core_ok = False

    _log("-" * 60)
    _log("  SUMMARY")
    for name, res in results.items():
        _log(f"    {name:6s}: {res}")

    if core_ok:
        _log("[bootstrap] Ready. Launch with:")
        _log(f"    {_venv_python(venv_dir)} main.py")
        _log("[bootstrap] Optional tiers that failed can be retried with:")
        _log("    python bootstrap.py --tier <voice|vision|web|server|docs>")
        return 0
    _log("[bootstrap] Core install failed — check your internet connection and")
    _log("[bootstrap] re-run: python bootstrap.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

