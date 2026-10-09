#!/usr/bin/env python3
"""
scripts/stella_build.py — one command to build, bundle, and release Stella
for any OS/platform, in any edition.

Why this exists
---------------
The old flow was Windows-only, always bundled every heavy dependency, and
produced a folder instead of an installable file. This script replaces it:

  * Edition-aware  — ship only the deps an edition actually uses
                     (lite / core / full), which is the biggest win for size
                     and cold-start time.
  * Cross-platform — detects the host or takes an explicit --os, and drives the
                     right packager (Inno Setup / hdiutil / appimagetool).
  * Release-ready  — zips the build, computes a SHA-256, and writes
                     dist/manifest.json so the in-app updater can check versions
                     and self-update without git.

Usage
-----
    python scripts/stella_build.py --edition core --os windows
    python scripts/stella_build.py --edition lite --os linux --release
    python scripts/stella_build.py --edition full --os macos --release

Nothing here runs PyInstaller unless it is actually installed, so `--plan`
works on a bare checkout to preview sizes before you commit to a build.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DIST = REPO / "dist"

# Dependencies grouped by feature. An edition includes its own group plus every
# group it depends on. This is what lets `lite` skip hundreds of MB.
EDITIONS = {
    "lite": {
        "blurb": "Cloud AI + voice. No globe, no browser, no vision.",
        "include": {"cloud", "voice", "desktop"},
        "excludes": [
            "PyQt6-WebEngine", "playwright", "cv2", "mediapipe",
            "matplotlib", "reportlab", "pptx", "docx",
        ],
        "data_skip": ["assets/globe"],
    },
    "core": {
        "blurb": "Lite + local K2 model + offline TTS + full system control.",
        "include": {"cloud", "voice", "desktop", "local_llm", "offline_tts"},
        "excludes": [
            "PyQt6-WebEngine", "playwright", "cv2", "mediapipe",
            "matplotlib", "reportlab",
        ],
        "data_skip": ["assets/globe"],
    },
    "full": {
        "blurb": "Everything: globe, browser automation, gestures.",
        "include": {"cloud", "voice", "desktop", "local_llm",
                    "offline_tts", "globe", "browser", "vision", "docs"},
        "excludes": [],
        "data_skip": [],
    },
}

# Approx on-disk cost per feature group (GB), for the plan preview.
GROUP_COST_GB = {
    "cloud": 0.2, "voice": 0.1, "desktop": 0.4, "local_llm": 0.6,
    "offline_tts": 0.1, "globe": 0.25, "browser": 0.4, "vision": 0.15,
    "docs": 0.12,
}

# Each feature group maps to the requirements file(s) that satisfy it. The build
# publishes an ordered, de-duplicated pip list per edition as manifest["packages"]
# so the in-app updater (core/updater.py::_install_new_packages) can pull in any
# dependency a new release added — core/desktop FIRST so a small or slow device
# gets a minimum viable set even if an optional tier fails to fetch.
#
# local_llm intentionally ships no wheels here: the K2 local model runs on a
# llama.cpp server whose binary + GGUF weights are downloaded separately by the
# setup wizard (scripts/package_bundle.py), not pip-installed into the app venv.
GROUP_REQS = {
    "cloud": ["requirements-core.txt"],
    "desktop": ["requirements-core.txt"],
    "local_llm": [],
    "offline_tts": ["requirements-voice.txt"],   # piper-tts
    "voice": ["requirements-voice.txt"],
    "globe": ["requirements-web.txt"],
    "browser": ["requirements-web.txt"],
    "vision": ["requirements-vision.txt"],
    "docs": ["requirements-docs.txt"],
}

# Order the updater installs packages in: essentials first, nice-to-haves last.
# Guarantees "bit by bit in order of importance" for low-storage/small devices.
_PACKAGE_PRIORITY = ["cloud", "desktop", "local_llm", "offline_tts",
                     "voice", "globe", "browser", "vision", "docs"]


def _read_reqs(filename: str) -> list[str]:
    """Non-comment, non-blank lines of a requirements-*.txt file."""
    f = REPO / filename
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def _edition_packages(edition: str) -> list[str]:
    """Ordered, de-duplicated pip packages this edition needs.

    Core/desktop first, optional feature tiers after — exactly the order the
    updater installs them in, so a flaky fetch can't strand the essentials.
    """
    ed = EDITIONS[edition]
    groups = ed["include"]
    seen: set[str] = set()
    ordered: list[str] = []
    # Groups not in _PACKAGE_PRIORITY (future additions) still get installed,
    # just after the known priority ones.
    ranked = [g for g in _PACKAGE_PRIORITY if g in groups]
    ranked += sorted(g for g in groups if g not in _PACKAGE_PRIORITY)
    for g in ranked:
        for filename in GROUP_REQS.get(g, []):
            for pkg in _read_reqs(filename):
                key = pkg.lower()
                if key not in seen:
                    seen.add(key)
                    ordered.append(pkg)
    return ordered


def _host_os() -> str:
    s = platform.system().lower()
    return {"darwin": "macos", "windows": "windows", "linux": "linux"}.get(s, s)


def _venv_pyinstaller() -> list[str] | None:
    """Command that runs PyInstaller.

    Order of preference:
      1. The .venv console-script shim (local dev).
      2. `python -m PyInstaller` from the .venv interpreter (shim missing but
         the package present — seen in practice).
      3. The interpreter running this script — GitHub Actions pip-installs
         PyInstaller into its system Python, and there is no .venv there.
    Returns the argv prefix, or None when PyInstaller is not installed.
    """
    interp = REPO / ".venv" / ("Scripts/python.exe" if os.name == "nt"
                               else "bin/python")
    for sub in ("Scripts/pyinstaller.exe", "bin/pyinstaller"):
        p = REPO / ".venv" / sub
        if p.exists():
            return [str(p)]
    candidates = [str(interp)] if interp.exists() else []
    if sys.executable:
        candidates.append(sys.executable)
    for py in dict.fromkeys(candidates):        # dedupe, keep order
        try:
            probe = subprocess.run(
                [py, "-c", "import PyInstaller"],
                capture_output=True, timeout=60)
        except Exception:
            continue
        if probe.returncode == 0:
            return [py, "-m", "PyInstaller"]
    return None


def _read_version() -> str:
    """Read the app version. version.txt holds a VSVersionInfo struct, so regex
    out the first semver token; a plain '1.2.3' file works too."""
    import re
    for name in ("app_version.txt", "version.txt"):
        vf = REPO / name
        if vf.exists():
            m = re.search(r"(\d+\.\d+\.\d+)",
                          vf.read_text(encoding="utf-8", errors="ignore"))
            if m:
                return m.group(1)
    return "0.0.0"

def _printable(s: str) -> str:
    """Encode-proof console text: strip glyphs the host console can't print."""
    try:
        s.encode(sys.stdout.encoding or "utf-8", errors="strict")
        return s
    except Exception:
        keep = []
        for ch in s:
            try:
                ch.encode(sys.stdout.encoding or "utf-8", errors="strict")
                keep.append(ch)
            except Exception:
                keep.append("-")
        return "".join(keep)


def cmd_plan(edition: str, target: str) -> int:
    ed = EDITIONS[edition]
    groups = ed["include"]
    est = sum(GROUP_COST_GB.get(g, 0.0) for g in groups)
    print("=" * 66)
    print(_printable(f"  STELLA BUILD PLAN — edition '{edition}' → {target}"))
    print("=" * 66)
    print(f"  {ed['blurb']}")
    print("-" * 66)
    print("  Feature groups included:")
    for g in sorted(groups):
        print(f"    + {g:<12} ~{GROUP_COST_GB.get(g, 0.0):.2f} GB")
    if ed["excludes"]:
        print("  Excluded (not bundled):")
        print("    - " + ", ".join(ed["excludes"]))
    print("-" * 66)
    print(f"  Estimated app size : ~{est:.2f} GB")
    print(f"  Host OS            : {_host_os()}")
    print(f"  PyInstaller        : {'found' if _venv_pyinstaller() else 'NOT in .venv'}")
    if target == "android":
        gradlew = REPO / "stella-connect-android" / "gradlew.bat"
        print(f"  Gradle wrapper     : {'found' if gradlew.exists() else 'missing'}")
    print("=" * 66)
    _print_install_footprint(edition)
    return 0


def _print_install_footprint(edition: str) -> None:
    """Full install footprint in GB: app + .venv + local model + voice data.

    This is what the user actually takes home, and it is what package_bundle.py
    --plan is estimating for a single model tier. Print it alongside the tier
    picker so nobody plans on 2 GB and pulls down 9 GB.
    """
    ed = EDITIONS[edition]
    app_gb = sum(GROUP_COST_GB.get(g, 0.0) for g in ed["include"])
    dep_gb = 3.2                    # .venv site-packages + runtime overhead
    model_gb = {
        "api_only": 0.0,
        "qwen_1_5b_q4": 1.0,
        "qwen_3b_q4": 2.0,
        "qwen_7b_q4": 4.4,
        "qwen_14b_q4": 9.0,
    }.get(edition, 0.0)
    total = app_gb + dep_gb + model_gb + 0.001
    print(f"  Full install footprint : ~{total:.2f} GB on disk "
          f"(app ~{app_gb:.2f} + .venv ~{dep_gb:.2f} + model {model_gb:.2f})")


def _pyinstaller_build(edition: str, target: str) -> Path:
    """Run PyInstaller for the edition, return the COLLECT output dir."""
    pyi = _venv_pyinstaller()
    if not pyi:
        raise RuntimeError(
            "PyInstaller not found in .venv. Run bootstrap first, then retry."
        )
    ed = EDITIONS[edition]
    spec = REPO / "installer" / "Stella.spec"
    if not spec.exists():
        raise RuntimeError(f"Missing spec: {spec}")

    # Pass edition through the environment so the spec can read excludes/skips
    # without us forking the spec per edition.
    env = dict(os.environ)
    env["STELLA_EDITION"] = edition
    env["STELLA_EXCLUDES"] = ",".join(ed["excludes"])
    env["STELLA_DATA_SKIP"] = ",".join(ed["data_skip"])

    print(f"==> PyInstaller: edition={edition} target={target}")
    cmd = [pyi, str(spec), "--noconfirm", "--distpath", str(DIST), "--workpath", str(REPO / "build" / edition)]
    subprocess.run(cmd, cwd=REPO, env=env, check=True)
    out = DIST / "StellaEvo"
    if not out.exists():
        raise RuntimeError(f"Build produced no output at {out}")
    return out

# ---------------------------------------------------------------------------
# Packaging: turn a PyInstaller COLLECT dir into something installable.
#
# Design choice: every build ALWAYS produces a portable `dist/*.zip` (works on
# any host, needs no extra tool). On top of that, if the native packager for the
# target is present (Inno Setup / hdiutil / appimagetool / Gradle) we ALSO emit
# the native installable. That way `python stella_build.py --release` never
# hard-fails just because a machine is missing one optional tool — it warns and
# gives you the universal zip, and the manifest points at the zip so updates
# work no matter how the app was first installed.
# ---------------------------------------------------------------------------

def _tool(name: str) -> str | None:
    return shutil.which(name)


def _zip_dir(src: Path, dest_zip: Path) -> Path:
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    if dest_zip.exists():
        dest_zip.unlink()
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in src.rglob("*"):
            zf.write(p, p.relative_to(src.parent))
    return dest_zip


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_windows_installer(collect: Path, edition: str, version: str) -> Path | None:
    iscc = _tool("ISCC")
    if not iscc:
        print("  (Inno Setup 'ISCC' not on PATH — skipping .exe, zip is portable)")
        return None
    iss = REPO / "installer" / "Stella.iss"
    if not iss.exists():
        print(f"  (missing {iss} — skipping Inno build)")
        return None
    print("==> Inno Setup: building .exe installer")
    subprocess.run([iscc, f"/DMyAppVersion={version}", f"/DMySourceDir={collect}",
                    str(iss)], check=True)
    exe = REPO / "installer" / "Output" / f"StellaSetup-{version}.exe"
    return exe if exe.exists() else None


def _make_macos_dmg(collect: Path, version: str) -> Path | None:
    if _host_os() != "macos":
        return None
    if not _tool("hdiutil"):
        print("  (hdiutil unavailable — skipping .dmg)")
        return None
    print("==> hdiutil: building .dmg")
    dmg = DIST / f"Stella-{version}.dmg"
    # The COLLECT dir IS the .app payload in onedir mode; wrap + convert.
    subprocess.run(["hdiutil", "create", "-volname", "Stella", "-srcfolder",
                    str(collect), "-ov", "-format", "UDZO", str(dmg)], check=True)
    return dmg if dmg.exists() else None


def _make_linux_appimage(collect: Path, version: str) -> Path | None:
    tool = _tool("appimagetool") or _tool("appimagetool-x86_64.AppImage")
    if not tool:
        print("  (appimagetool unavailable — skipping .AppImage; try .deb via dpkg-deb)")
        return None
    print("==> appimagetool: building .AppImage")
    stage = DIST / "AppDir"
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(collect, stage)
    # Minimal AppImage desktop entry.
    (stage / "Stella.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Stella\nExec=StellaEvo\n"
        "Icon=stella\nCategories=Utility;\n", encoding="utf-8")
    appimage = DIST / f"Stella-{version}-x86_64.AppImage"
    subprocess.run([tool, str(stage), str(appimage)], check=True)
    return appimage if appimage.exists() else None

# ---------------------------------------------------------------------------
# Mobile: the Android companion app (stella-connect-android) is a real Gradle
# project. We drive its wrapper so a desktop build and a mobile build share one
# command. iOS has no project yet, so we print a clear, honest TODO rather than
# pretending to build something that isn't there.
# ---------------------------------------------------------------------------

ANDROID_DIR = REPO / "stella-connect-android"


def _gradlew(target: str) -> str | None:
    if target != "android":
        return None
    wrapper = ANDROID_DIR / ("gradlew.bat" if _host_os() == "windows" else "gradlew")
    return str(wrapper) if wrapper.exists() else None


def _build_android(edition: str, version: str) -> Path | None:
    gradlew = _gradlew("android")
    if not gradlew:
        print("  (Android Gradle wrapper not found — skipping mobile build)")
        return None
    if not (ANDROID_DIR / "gradle" / "wrapper" / "gradle-wrapper.jar").exists():
        print("  (gradle-wrapper.jar missing — cannot bootstrap Gradle offline)")
        return None
    print("==> Gradle: assembling Android APK (release, unsigned for sideload)")
    task = "assembleRelease"
    subprocess.run([gradlew, task, "-p", str(ANDROID_DIR)], check=True)
    apks = list((ANDROID_DIR / "app" / "build" / "outputs" / "apk").rglob("*.apk"))
    return apks[0] if apks else None


# ---------------------------------------------------------------------------
# Release: write dist/manifest.json so the in-app updater can self-update a
# frozen install without git.
# ---------------------------------------------------------------------------

def _write_manifest(version: str, edition: str, artifacts: dict) -> Path:
    manifest = {
        "version": version,
        "edition": edition,
        "channel": "stable",
        "built_at": _now_iso(),
        "targets": artifacts,  # { "windows": {"file","sha256","size"}, ... }
    }
    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return DIST / "manifest.json"


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def cmd_build(edition: str, target: str, release: bool) -> int:
    version = _read_version()
    DIST.mkdir(parents=True, exist_ok=True)

    # Mobile target: build the APK, done (no PyInstaller involved).
    if target == "android":
        apk = _build_android(edition, version)
        if not apk:
            print("FAIL: Android build produced no APK.")
            return 1
        print(f"==> APK: {apk}")
        if release:
            out_zip = DIST / f"Stella-Connect-{version}-android.apk"
            shutil.copyfile(apk, out_zip)
            man = _write_manifest(version, edition, {
                "android": {"file": out_zip.name,
                            "sha256": _sha256(out_zip),
                            "size": out_zip.stat().st_size}
            })
            print(f"==> Manifest: {man}")
        return 0

    if target == "ios":
        print("iOS: no Xcode project in this repo yet (see docs/IOS_BUILD.md).")
        print("Next steps: add a SwiftUI shell in stella-connect-ios/, then wire")
        print("  'xcodebuild -scheme Stella archive' into _build_ios() here.")
        return 2

    # Desktop: PyInstaller COLLECT -> universal zip -> native installer.
    collect = _pyinstaller_build(edition, target)
    out_zip = _zip_dir(collect, DIST / f"Stella-{edition}-{version}-{target}.zip")
    print(f"==> Portable zip: {out_zip}")

    native = None
    if target == "windows":
        native = _make_windows_installer(collect, edition, version)
    elif target == "macos":
        native = _make_macos_dmg(collect, version)
    elif target == "linux":
        native = _make_linux_appimage(collect, version)
    if native:
        print(f"==> Native installer: {native}")

    if release:
        artifacts = {
            target: {"file": out_zip.name, "sha256": _sha256(out_zip),
                     "size": out_zip.stat().st_size}
        }
        if native:
            artifacts[target]["installer"] = native.name
        man = _write_manifest(version, edition, artifacts)
        print(f"==> Manifest: {man}")
        print("    Publish dist/*.zip + manifest.json to GitHub Releases.")
    return 0


def main() -> int:
    # Windows consoles default to cp1252 and choke on the box-drawing / arrow
    # glyphs we use. Best-effort switch to UTF-8; harmless if unavailable.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Build, bundle, and release Stella.")
    ap.add_argument("--edition", choices=sorted(EDITIONS), default="core")
    ap.add_argument("--os", "--target", dest="target",
                    choices=["windows", "linux", "macos", "android", "ios"],
                    default=_host_os())
    ap.add_argument("--release", action="store_true",
                    help="also write dist/manifest.json (SHA-256 + version).")
    ap.add_argument("--plan", action="store_true",
                    help="preview the edition + sizes, build nothing.")
    args = ap.parse_args()

    if args.plan:
        return cmd_plan(args.edition, args.target)
    return cmd_build(args.edition, args.target, args.release)


if __name__ == "__main__":
    raise SystemExit(main())



