#!/usr/bin/env python3
"""
scripts/stella_update.py — self-update a frozen Stella install.

Why not `git pull`?
    A packaged install has no `.git` and often no git at all, so the old
    updater (updater.py::update_from_github) silently never fires. This works on
    any installed copy: it reads a small `manifest.json`, compares versions, and
    if a newer one exists it downloads the matching zip, verifies it, stages it,
    and swaps it in on next launch.

How it stays safe and restartable on a bad connection:
    * The download is RESUMABLE (HTTP Range + a `.part` file), so a dropped
      connection continues from where it stopped instead of restarting.
    * The SHA-256 in the manifest is checked BEFORE anything is unpacked. A
      truncated or tampered download is rejected, never installed.
    * The new version is extracted to a *staging* dir and only swapped in after
      it fully verifies, so an interrupted update can never brick a running app.

Where does the manifest come from?
    Pass a URL (--manifest-url), a local path (--manifest), or set
    STELLA_MANIFEST_URL in the environment. The manifest shape is produced by
    scripts/stella_build.py --release:

        { "version": "1.2.0",
          "targets": { "windows": { "file": "...", "sha256": "..." } } }

Only stdlib is required. Exit code 0 = up to date or update staged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_URL = (
    "https://github.com/Emma-Keaton/stella/releases/latest/download/manifest.json"
)


def _host_os() -> str:
    s = platform.system().lower()
    return {"darwin": "macos", "windows": "windows", "linux": "linux"}.get(s, s)


def _read_version(install_dir=None) -> str:
    """Read the *installed* app version.

    Preference order:
      1. install_dir/version.txt  — the copy the user actually runs (correct
         baseline for an update; this is what a packaged install ships).
      2. REPO/version.txt         — the checkout, used when no install dir or
         when running from source.

    version.txt holds a VSVersionInfo struct (for PyInstaller), so regex out
    the first semver-looking token rather than returning the whole blob; a
    plain '1.2.3' file works too.
    """
    candidates = []
    if install_dir is not None:
        candidates.append(Path(install_dir) / "version.txt")
    candidates.append(REPO / "version.txt")
    for p in candidates:
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


def _fetch_manifest(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "stella-updater/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        # utf-8-sig transparently strips a BOM if present (Windows editors add
        # one) and behaves like utf-8 otherwise, so a hand-edited manifest.json
        # never fails to parse.
        return json.loads(r.read().decode("utf-8-sig"))

def resumable_download(url: str, dest: Path, *, timeout: int = 30,
                       max_retries: int = 8, chunk: int = 1024 * 256) -> Path:
    """Download to `dest` via a `.part` file, resuming on reconnect."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    have = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": "stella-updater/1.0"}
    if have:
        headers["Range"] = f"bytes={have}-"

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        mode = "ab" if have else "wb"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp, \
                    open(part, mode) as f:
                if have and resp.status == 200:
                    f.seek(0); have = 0
                total = int(resp.headers.get("Content-Length", 0)) + have
                while True:
                    block = resp.read(chunk)
                    if not block:
                        break
                    f.write(block)
                    have += len(block)
                    if total:
                        pct = have * 100 // total
                        sys.stdout.write(f"\r  {have/1048576:6.1f} MB ({pct:3d}%)")
                        sys.stdout.flush()
            sys.stdout.write("\n")
            os.replace(part, dest)
            return dest
        except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout,
                ConnectionError, TimeoutError, OSError) as e:
            wait = min(2 ** attempt, 30)
            print(f"\n  network hiccup ({e.__class__.__name__}); "
                  f"retry {attempt}/{max_retries} in {wait}s "
                  f"(resume from {have/1048576:.1f} MB)")
            time.sleep(wait)
    raise RuntimeError(f"Gave up after {max_retries} retries. "
                       f"Partial kept at {part}; re-run to resume.")


def _stage_and_swap(zip_path: Path, install_dir: Path, expected_sha: str) -> None:
    if _sha256(zip_path) != expected_sha:
        raise RuntimeError("SHA-256 mismatch - download corrupted, not installed.")

    staging = install_dir.parent / (install_dir.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(staging)

    # The zip was made relative to install_dir.parent, so a single top folder
    # (install_dir.name) should appear inside staging.
    inner = staging / install_dir.name
    payload = inner if inner.is_dir() else staging

    backup = install_dir.parent / (install_dir.name + ".old")
    if backup.exists():
        shutil.rmtree(backup)
    if install_dir.exists():
        os.replace(install_dir, backup)          # atomic rename on same volume
    os.replace(payload, install_dir)             # promote the new build
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)
    shutil.rmtree(staging, ignore_errors=True)


def cmd_check(manifest_url: str, install_dir: Path) -> int:
    current = _read_version(install_dir)
    print(f"Installed version: {current}  ({_host_os()})  [{install_dir}]")
    try:
        manifest = _fetch_manifest(manifest_url)
    except Exception as e:
        print(f"Could not reach manifest: {e}")
        return 1

    latest = manifest.get("version", current)
    target = manifest.get("targets", {}).get(_host_os())
    print(f"Latest version   : {latest}")
    if not target:
        print(f"No {_host_os()} build in this manifest - nothing to do.")
        return 1
    if _parse_version(latest) <= _parse_version(current):
        print("Already up to date.")
    return 0


def cmd_update(manifest_url: str, install_dir: Path) -> int:
    current = _read_version(install_dir)
    manifest = _fetch_manifest(manifest_url)
    latest = manifest.get("version", current)
    target = manifest.get("targets", {}).get(_host_os())

    if not target or _parse_version(latest) <= _parse_version(current):
        print(f"Up to date ({current}).")
        return 0

    file_url = target.get("url") or (
        manifest_url.rsplit("/", 1)[0] + "/" + target["file"])
    dest = install_dir.parent / target["file"]
    print(f"Updating {current} -> {latest} ({_host_os()})")
    print(f"Source: {file_url}")
    resumable_download(file_url, dest)
    _stage_and_swap(dest, install_dir, target["sha256"])
    dest.unlink(missing_ok=True)
    print(f"Updated to {latest}. Restart the app to run it.")
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Stella self-updater")
    ap.add_argument("--check", action="store_true",
                    help="only report versions, download nothing")
    ap.add_argument("--manifest-url",
                    default=os.environ.get("STELLA_MANIFEST_URL",
                                           DEFAULT_MANIFEST_URL))
    ap.add_argument("--install-dir", default=str(REPO),
                    help="folder the app runs from (for swap)")
    args = ap.parse_args()

    install_dir = Path(args.install_dir)
    try:
        if args.check:
            return cmd_check(args.manifest_url, install_dir)
        return cmd_update(args.manifest_url, install_dir)
    except Exception as e:
        print(f"Update failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

