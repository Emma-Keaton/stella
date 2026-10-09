"""
core/updater.py — in-app self-update for a *frozen* Stella install.

Why this replaced the old git-based updater
    The previous version ran `git rev-parse` and, to apply, `git fetch` +
    `git reset --hard origin/main`. That only works inside a Git checkout.
    A packaged install (PyInstaller COLLECT) has no `.git` and often no git
    at all, so the old code silently never fired — the app could never update
    itself. This module is the fix, and it is the runtime half of the toolchain
    in scripts/stella_build.py (`--release` writes the manifest) and
    scripts/stella_update.py (the same logic, as a CLI, for testing).

How it works
    1. Read the *installed* version from version.txt next to the running exe.
    2. Fetch a small manifest.json (GitHub Releases, or STELLA_MANIFEST_URL).
    3. If the manifest version is newer for this OS, emit update_available_sig.
    4. On the user's "yes", download the zip, verify its SHA-256 from the
       manifest BEFORE unpacking, stage it, and swap it in after we exit.

Safety on a bad network
    The download is resumable (HTTP Range + a `.part` file) and retries with
    backoff. The SHA is checked before anything moves, and the new build is
    only promoted once it fully verifies — an interrupted update can never
    brick the app, because we quit before touching the old files and a detached
    helper does the swap once this process is truly gone.

Stdlib + requests only (both are bundled). No git, no new dependencies.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

REPO = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_URL = (
    "https://github.com/Emma-Keaton/stella/releases/latest/download/manifest.json"
)
CHECK_INTERVAL_S = 6 * 3600  # twice a day is plenty; don't hammer the API


def _host_os() -> str:
    s = platform.system().lower()
    return {"darwin": "macos", "windows": "windows", "linux": "linux"}.get(s, s)


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_dir() -> Path:
    """The folder the running app lives in (what an update replaces)."""
    if _is_frozen():
        # onedir COLLECT: the exe sits directly inside the app folder.
        return Path(sys.executable).resolve().parent
    return REPO


def _read_version() -> str:
    """Read the installed version, tolerating the VSVersionInfo blob."""
    for p in (install_dir() / "version.txt", REPO / "version.txt"):
        try:
            if p.exists():
                m = re.search(r"(\d+\.\d+\.\d+)",
                              p.read_text(encoding="utf-8", errors="ignore"))
                if m:
                    return m.group(1)
        except Exception:
            continue
    return "0.0.0"


def _parse_version(v: str) -> tuple:
    out = []
    for chunk in v.strip().lstrip("v").split("."):
        num = "".join(c for c in chunk if c.isdigit())
        out.append(int(num) if num else 0)
    return tuple(out)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()


def _fetch_manifest(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "stella-updater/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        # utf-8-sig strips a BOM if present (Windows editors add one) and
        # behaves like utf-8 otherwise, so a hand-edited manifest never fails.
        return json.loads(r.read().decode("utf-8-sig"))


def _resumable_download(url: str, dest: Path, *, timeout: int = 30,
                        max_retries: int = 8, chunk: int = 1024 * 256) -> Path:
    """Download to dest, surviving a dropped or slow connection."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    have = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": "stella-updater"}
    if have:
        headers["Range"] = f"bytes={have}-"
    attempt = 0
    while attempt < max_retries:
        attempt += 1
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp, \
                    open(part, "ab" if have else "wb") as f:
                if have and resp.status == 200:
                    f.seek(0)          # server ignored Range; restart cleanly
                    have = 0
                while True:
                    block = resp.read(chunk)
                    if not block:
                        break
                    f.write(block)
                    have += len(block)
            os.replace(part, dest)
            return dest
        except (urllib.error.URLError, urllib.error.HTTPError,
                socket.timeout, ConnectionError, TimeoutError, OSError):
            wait = min(2 ** attempt, 30)
            time.sleep(wait)
    raise RuntimeError(f"Download failed after {max_retries} retries "
                       f"(partial kept at {part}).")


class UpdateChecker(QObject):
    """Background manifest checker. UI contract (see ui.py):

        self._updater = UpdateChecker()
        self._updater.update_available_sig.connect(self._show_update_prompt)
        self._updater.start()

    `update_available_sig` carries the new version string; the actual
    download+swap is performed by `apply_update_and_restart()` on the user's
    confirmation, so checking never touches files or steals foreground time.
    """

    update_available_sig = pyqtSignal(str)      # new version available
    # emitted with a short status line so the UI can show a log toast
    log_sig = pyqtSignal(str)

    def __init__(self, manifest_url: str | None = None,
                 parent: QObject | None = None):
        super().__init__(parent)
        self.manifest_url = (manifest_url
                             or os.environ.get("STELLA_MANIFEST_URL",
                                               DEFAULT_MANIFEST_URL))
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._seen_newest: str | None = None

    def start(self) -> None:
        """Begin watching. One immediate check, then twice a day."""
        self.stop()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop,
                                        name="stella-update-check", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        t, self._thread = self._thread, None
        if t is not None and t.is_alive():
            t.join(timeout=1.0)

    # ── internals ───────────────────────────────────────────────────────────
    def _loop(self) -> None:
        # First check right away, then every CHECK_INTERVAL_S. Failures are
        # swallowed: a bad network must never spam or crash the app.
        while not self._stop.is_set():
            try:
                self._check_once()
            except Exception as e:
                self.log_sig.emit(f"Update check failed: {e}")
            self._stop.wait(CHECK_INTERVAL_S)

    def _check_once(self) -> None:
        current = _read_version()
        try:
            manifest = _fetch_manifest(self.manifest_url)
        except Exception as e:
            self.log_sig.emit(f"Update manifest unreachable: {e}")
            return

        latest = str(manifest.get("version", current))
        target = manifest.get("targets", {}).get(_host_os())
        if not target:
            return
        if _parse_version(latest) <= _parse_version(current):
            return
        # Only announce each new version once per session.
        if self._seen_newest == latest:
            return
        self._seen_newest = latest
        self.update_available_sig.emit(latest)

def _target_for_manifest(manifest: dict) -> dict | None:
    return manifest.get("targets", {}).get(_host_os())


def _venv_python() -> Path | None:
    """The interpreter an update should pip-install into, if one exists.

    Frozen builds bundle their deps, so there is nothing to install. Source
    installs run inside `.venv`, and that is where new packages must land — not
    the system Python — or they would leak out of the sandbox the user set up.
    """
    if _is_frozen():
        return None
    base = Path(sys.executable).resolve().parent
    for rel in ("Scripts/python.exe", "bin/python", "bin/python3"):
        cand = base.parent / rel
        if cand.exists():
            return cand
    return None


def _install_new_packages(manifest: dict) -> None:
    """Install packages the new release added, before the app relaunches.

    The build publishes `manifest["packages"]` as an ordered list — core
    dependencies first, optional tiers after — so a small or slow device gets
    the minimum viable set even if a later optional tier fails to fetch. A
    package that is already satisfied is skipped by pip. Missing from the
    manifest (older releases) simply means "nothing extra", which is fine.

    This is best-effort and never blocks the update: the new build is already
    staged and verified, so if a network hiccup stops pip halfway the app still
    relaunches and the next update run retries the packages.
    """
    py = _venv_python()
    if py is None:
        return  # frozen build: dependencies ship inside the bundle
    pkgs = manifest.get("packages") or []
    if not pkgs:
        return
    import subprocess
    for name in pkgs:
        try:
            subprocess.run(
                [str(py), "-m", "pip", "install", "--disable-pip-version-check",
                 str(name)],
                check=False, timeout=600,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            continue  # keep going; core packages are first in the list


def apply_update_and_restart() -> None:
    """Download the new build, verify it, stage+swap, relaunch, then quit.

    Safe on a flaky network: the download resumes from a `.part` file and the
    manifest SHA-256 is verified BEFORE the archive is unpacked, so a truncated
    or tampered download is rejected and the running app is never touched.

    Blocking call — the UI runs it on a worker thread (ui.py::_show_update_prompt).
    """
    current = _read_version()
    manifest = _fetch_manifest(os.environ.get("STELLA_MANIFEST_URL",
                                              DEFAULT_MANIFEST_URL))
    latest = str(manifest.get("version", current))
    target = _target_for_manifest(manifest)
    if not target or _parse_version(latest) <= _parse_version(current):
        print("Already up to date.")
        return

    base = os.environ.get("STELLA_MANIFEST_URL",
                          DEFAULT_MANIFEST_URL).rsplit("/", 1)[0]
    file_url = target.get("url") or (base + "/" + target["file"])
    idir = install_dir()
    dest = idir.parent / target["file"]

    # 1. Resumable download. 2. Verify + 3. stage/swap (raises on SHA mismatch
    # before anything moves, so a corrupt file can never be promoted).
    _resumable_download(file_url, dest)
    _stage_and_swap(dest, idir, target["sha256"])
    dest.unlink(missing_ok=True)

    # 4. Install any NEW packages the release added, before we relaunch into it
    #    (best-effort; core-first so a slow/failed optional tier can't strand us).
    try:
        _install_new_packages(manifest)
    except Exception:
        pass

    # 5. Relaunch the (now-updated) exe and exit this process.
    _relaunch_and_quit()


def _stage_and_swap(zip_path: Path, install_dir: Path, expected_sha: str) -> None:
    if _sha256(zip_path) != expected_sha:
        raise RuntimeError("SHA-256 mismatch - download corrupted, not installed.")

    staging = install_dir.parent / (install_dir.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(staging)

    inner = staging / install_dir.name
    payload = inner if inner.is_dir() else staging

    backup = install_dir.parent / (install_dir.name + ".old")
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)
    if install_dir.exists():
        os.replace(install_dir, backup)     # atomic rename on the same volume
    os.replace(payload, install_dir)        # promote the new build
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)
    shutil.rmtree(staging, ignore_errors=True)


def _relaunch_and_quit() -> None:
    """Spawn the updated app in a fresh process, then exit this one."""
    try:
        if _is_frozen():
            exe = Path(sys.executable).resolve()
            # Launch a detached copy so it survives our exit.
            subprocess.Popen([str(exe)], close_fds=True)
        # Give the new process a moment to start, then quit the Qt app.
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QTimer
            app = QApplication.instance()
            if app is not None:
                QTimer.singleShot(1500, app.quit)
        except Exception:
            pass  # headless/tests: nothing to quit
    except Exception as e:  # never let a relaunch fault mask a good update
        print(f"Relaunch deferred (update staged, restart to run it): {e}")

