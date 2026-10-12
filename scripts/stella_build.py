#!/usr/bin/env python3
"""
scripts/stella_build.py â€” one command to build, bundle, and release Stella
for any OS/platform, in any edition.

Why this exists
---------------
The old flow was Windows-only, always bundled every heavy dependency, and
produced a folder instead of an installable file. This script replaces it:

  * Edition-aware  â€” ship only the deps an edition actually uses
                     (lite / core / full), which is the biggest win for size
                     and cold-start time.
  * Cross-platform â€” detects the host or takes an explicit --os, and drives the
                     right packager (Inno Setup / hdiutil / appimagetool).
  * Release-ready  â€” zips the build, computes a SHA-256, and writes
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
import secrets
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
# dependency a new release added â€” core/desktop FIRST so a small or slow device
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

    Core/desktop first, optional feature tiers after â€” exactly the order the
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
         the package present â€” seen in practice).
      3. The interpreter running this script â€” GitHub Actions pip-installs
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
    print(_printable(f"  STELLA BUILD PLAN â€” edition '{edition}' â†’ {target}"))
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


def _pyinstaller_build(edition: str, target: str, k2: bool = False) -> Path:
    """Run PyInstaller for the edition, return the COLLECT output dir.

    When `k2` is true the personal K2 runtime (llama-server + GGUF) is staged
    into the bundle, driven by the STELLA_K2_* env vars the spec reads.
    """
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

    variant = "k2" if k2 else "public"
    if k2:
        model, server = _k2_payload()
        env["STELLA_K2_BUNDLE"] = "1"
        env["STELLA_K2_MODEL"] = str(model)
        env["STELLA_K2_SERVER"] = str(server)

    print(f"==> PyInstaller: edition={edition} target={target} variant={variant}")
    # `pyi` is an argv prefix (a list), so it must be unpacked, not nested --
    # a nested list makes subprocess raise "expected str ... not list".
    cmd = [*pyi, str(spec), "--noconfirm", "--distpath", str(DIST),
           "--workpath", str(REPO / "build" / f"{edition}-{variant}")]
    subprocess.run(cmd, cwd=REPO, env=env, check=True)
    out = DIST / "Stella"
    if not out.exists():
        raise RuntimeError(f"Build produced no output at {out}")
    return out


# ---------------------------------------------------------------------------
# Personal K2 payload resolution.
#
# The weights + llama-server are built locally and never committed, so we look
# for them in conventional local spots rather than a tracked config file.
# Resolution order for each file: explicit env var -> .stella-toolchain ->
# the repo's gitignored models/ dir.
# ---------------------------------------------------------------------------
K2_STAGING = Path(os.environ.get("STELLA_K2_STAGING", REPO / "build" / "k2-stage"))


def _find_local(filename: str, env_var: str) -> Path | None:
    """Locate a K2 payload file, preferring an explicit env override."""
    explicit = os.environ.get(env_var, "").strip()
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    toolchain = Path.home() / ".stella-toolchain"
    for base in (toolchain, K2_STAGING, REPO / "models"):
        direct = base / filename
        if direct.is_file():
            return direct
        # llama-server lands under the cross-compile build dirs. Only fall back
        # to globbing for it when we are actually looking for the server -
        # otherwise a model lookup would silently resolve to a llama-server
        # binary and bundle no weights at all.
        if filename.startswith("llama-server"):
            for pat in ("llama-k2/build-*/bin/llama-server*", "**/llama-server*"):
                for hit in sorted(base.glob(pat)):
                    if hit.is_file():
                        return hit
    return None


def _k2_payload() -> tuple[Path, Path]:
    """Return (model_gguf, llama_server), raising with actionable guidance."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from core import k2_runtime as kr
    model = _find_local(kr.K2_MODEL_FILENAME, "STELLA_K2_MODEL")
    server = _find_local("llama-server", "STELLA_K2_SERVER")
    if not model:
        raise RuntimeError(
            f"K2 weights not found ({kr.K2_MODEL_FILENAME}).\n"
            f"  Put it in {REPO / 'models'}/ or set STELLA_K2_MODEL."
        )
    if not server:
        raise RuntimeError(
            "llama-server not found.\n"
            "  Build it from the pinned K2 fork, or set STELLA_K2_SERVER."
        )
    return model, server

# ---------------------------------------------------------------------------
# Packaging: turn a PyInstaller COLLECT dir into something installable.
#
# Design choice: every build ALWAYS produces a portable `dist/*.zip` (works on
# any host, needs no extra tool). On top of that, if the native packager for the
# target is present (Inno Setup / hdiutil / appimagetool / Gradle) we ALSO emit
# the native installable. That way `python stella_build.py --release` never
# hard-fails just because a machine is missing one optional tool â€” it warns and
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
        print("  (Inno Setup 'ISCC' not on PATH â€” skipping .exe, zip is portable)")
        return None
    iss = REPO / "installer" / "Stella.iss"
    if not iss.exists():
        print(f"  (missing {iss} â€” skipping Inno build)")
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
        print("  (hdiutil unavailable â€” skipping .dmg)")
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
        print("  (appimagetool unavailable â€” skipping .AppImage; try .deb via dpkg-deb)")
        return None
    print("==> appimagetool: building .AppImage")
    stage = DIST / "AppDir"
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(collect, stage)
    # Minimal AppImage desktop entry.
    (stage / "Stella.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Stella\nExec=Stella\n"
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


def _ensure_signing_key() -> dict[str, str] | None:
    """Return gradle signing args, generating a local key when none exists.

    Android refuses to sideload an UNSIGNED release APK, so "no keystore"
    does not mean "ship unsigned" - it means "the build is unusable". On a
    personal machine we therefore mint a key once, stash it outside the repo,
    and reuse it forever. That keeps every rebuild installable and upgradable
    over the previous one (same signing identity = in-place update).

    Returns None only when no JDK keytool is available at all.
    """
    store = os.environ.get("STELLA_ANDROID_KEYSTORE", "").strip()
    password = os.environ.get("STELLA_ANDROID_KEYSTORE_PASSWORD", "").strip()
    alias = os.environ.get("STELLA_ANDROID_KEY_ALIAS", "stella").strip() or "stella"

    if store and password and Path(store).is_file():
        return {"store": store, "password": password, "alias": alias}

    # Otherwise look for - or create - our own key in the per-user toolchain.
    # Personal builds sign with STELLA_PERSONAL_JKS; the public APK has no key
    # (and will be unsigned), which is intentional - a public release APK can
    # only be sideloaded while the machine owns its signature.
    tc = Path.home() / ".stella-toolchain"
    tc.mkdir(parents=True, exist_ok=True)
    key = tc / "stella-personal.jks"
    meta = tc / "stella-personal.json"
    store = os.environ.get("STELLA_ANDROID_KEYSTORE", "").strip() or str(key)
    password = os.environ.get("STELLA_ANDROID_KEYSTORE_PASSWORD", "").strip() or "stella-local-personal"
    alias = os.environ.get("STELLA_ANDROID_KEY_ALIAS", "stella").strip() or "stella"

    if Path(store).is_file():
        # Trusted env path - just read it.
        return {"store": store, "password": password, "alias": alias}

    if key.is_file():
        # A keystore with no password anywhere is dead weight: Android will
        # never let us sign with it again, and `-genkeypair` cannot add a key to
        # a file it cannot read. Replace it rather than fail the build.
        print(f"  ({key.name} has no recorded password and cannot be opened - "
              f"replacing it with a fresh local key)")
        key.unlink(missing_ok=True)

    keytool = _find_keytool()
    if not keytool:
        print("  (no keytool found - release APK will be UNSIGNED and "
              "cannot be installed)")
        return None

    if not password:
        # No human-chosen password, so generate a strong one. It lives only in
        # the toolchain dir next to the key, never in the repo.
        password = secrets.token_urlsafe(24)
    print(f"==> keytool: creating release signing key {key.name}")
    try:
        subprocess.run(
            [keytool, "-genkeypair", "-v",
             "-keystore", str(key),
             "-storepass", password, "-keypass", password,
             "-alias", alias,
             "-keyalg", "RSA", "-keysize", "4096",
             "-validity", "10000",
             "-dname", f"CN=Stella Local, OU=Stella, O=Stella, L=NA, S=NA, C=NA"],
            check=True, capture_output=True, text=True, errors="replace",
        )
    except subprocess.CalledProcessError as exc:
        print(f"  (keytool failed: {(exc.stderr or '')[:200]})")
        return None
    meta.write_text(json.dumps({"password": password, "alias": alias}, indent=2),
                    encoding="utf-8")
    return {"store": str(key), "password": password, "alias": alias}


def _keystore_unlocks(keytool: str | None, store: Path, password: str) -> bool:
    """True only if `password` really opens `store`.

    Cheap `-list` probe. Guessing is not an option: a wrong password here
    surfaces much later as a Gradle failure, so we check up front.
    """
    if not keytool:
        return False
    try:
        proc = subprocess.run(
            [keytool, "-list", "-keystore", str(store), "-storepass", password],
            capture_output=True, text=True, errors="replace", timeout=60,
        )
    except Exception:
        return False
    return proc.returncode == 0 and "password was incorrect" not in (proc.stdout or "")


def _find_keytool() -> str | None:
    jh = _find_java_home() or _find_java_home(max_major=99)
    for base in ([Path(jh)] if jh else []) + [
        Path(os.environ.get("JAVA_HOME", "")),
        Path.home() / ".stella-toolchain" / "jdk17",
        Path.home() / ".stella-toolchain" / "jdk",
    ]:
        if not base or not base.is_dir():
            continue
        exe = "keytool.exe" if _host_os() == "windows" else "keytool"
        cand = base / "bin" / exe
        if cand.is_file():
            return str(cand)
    return None


def _build_android(edition: str, version: str, k2: bool = False) -> Path | None:
    gradlew = _gradlew("android")
    if not gradlew:
        print("  (Android Gradle wrapper not found â€” skipping mobile build)")
        return None
    if not (ANDROID_DIR / "gradle" / "wrapper" / "gradle-wrapper.jar").exists():
        print("  (gradle-wrapper.jar missing â€” cannot bootstrap Gradle offline)")
        return None
    variant = "k2-bundled" if k2 else "public"
    print(f"==> Gradle: assembling Android APK (release, {variant})")
    task = "assembleRelease"
    env = dict(os.environ)
    # Gradle 8.7 cannot run on brand-new JDKs (it supports up to ~22).
    # Prefer a compatible local JDK when the user has several installed.
    local_jdk = _find_java_home(max_major=22)
    if local_jdk:
        env["JAVA_HOME"] = local_jdk
        env["PATH"] = local_jdk + os.sep + "bin" + os.pathsep + env.get("PATH", "")
        print(f"  (Gradle JDK: {local_jdk})")

    extra: list[str] = []
    if k2:
        # Personal build: stage the locally-built runtime + weights into the
        # APK. The Gradle side switches applicationId to com.stella.connect.k2
        # so it installs beside the public app rather than replacing it.
        model, server = _k2_payload()
        extra = [
            "-PstellaK2Bundle=true",
            f"-PstellaK2Model={model}",
            f"-PstellaK2Server={server}",
        ]
    # Sideloading needs a signature. The personal build signs with
    # STELLA_PERSONAL_JKS; the public APK intentionally stays unsigned (no
    # keystore is bundled), which keeps it sideloadable anywhere.
    signing = None
    if k2:
        signing = _ensure_signing_key()
        if signing:
            extra += [
                f"-PstellaSigningStore={signing['store']}",
                f"-PstellaSigningPassword={signing['password']}",
                f"-PstellaSigningAlias={signing['alias']}",
            ]
    subprocess.run([gradlew, task, "-p", str(ANDROID_DIR)] + extra, check=True, env=env)

    # The two variants share one build dir, so we must pick by the exact name
    # Gradle was told to emit (see app/build.gradle.kts applicationVariants).
    # Falling back to "newest APK" used to pick the WRONG variant when both
    # were built - a stale public APK could ship as the personal one.
    out_root = ANDROID_DIR / "app" / "build" / "outputs" / "apk" / "release"
    wanted = (
        "stella-k2-bundled-arm64.apk" if k2 else "stella-connect-release.apk"
    )
    exact = out_root / wanted
    if not exact.exists():
        # Be explicit rather than guessing: a wrong APK is worse than no APK.
        found = sorted(p.name for p in out_root.rglob("*.apk")) if out_root.exists() else []
        raise FileNotFoundError(
            f"Gradle did not produce '{wanted}' in {out_root}. "
            f"Found: {found or '(nothing)'}. "
            f"The build probably failed or outputFileName changed."
        )
    return exact


def _verify_apk_signed(apk: Path) -> tuple[bool, str]:
    """Is this APK signed, and by whom? Returns (signed, description).

    An unsigned release APK cannot be sideloaded onto Android at all, so we
    check instead of handing the user a file that will fail at install time.
    """
    build_tools = _android_build_tools()
    if not build_tools:
        return False, "apksigner not found - signature unverified"
    apksigner = build_tools / "apksigner.bat"
    if not apksigner.exists():
        apksigner = build_tools / "apksigner"
    if not apksigner.exists():
        return False, "apksigner not found - signature unverified"
    proc = subprocess.run(
        [str(apksigner), "verify", "--print-certs", str(apk)],
        capture_output=True, text=True, errors="replace",
    )
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "").strip()[:300]
    certs = [ln.strip() for ln in (proc.stdout or "").splitlines()
             if "SHA-256 digest" in ln or "Signer #1 certificate DN" in ln]
    return True, "; ".join(certs[:2]) or "signed"



def _android_build_tools() -> Path | None:
    """Highest installed Android build-tools dir, or None.

    Used for apksigner/zipalign. Checks the toolchain Stella installs for
    itself first, then the standard env vars and default locations.
    """
    roots = [
        Path(os.environ.get("ANDROID_SDK_ROOT", "")),
        Path(os.environ.get("ANDROID_HOME", "")),
        Path.home() / ".stella-toolchain" / "android-sdk",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk",
        Path("/opt/android-sdk"), Path("/usr/local/lib/android/sdk"),
    ]
    for root in roots:
        if not root or not root.is_dir():
            continue
        bt = root / "build-tools"
        if not bt.is_dir():
            continue
        vers = sorted((p for p in bt.iterdir() if p.is_dir()), reverse=True)
        if vers:
            return vers[0]
    return None


def _find_java_home(max_major: int = 22) -> str | None:
    """Best installed JDK at or below max_major (Gradle 8.7 caps at ~22).

    Checks JAVA_HOME first, then the usual Windows install roots. Returns the
    home dir, or None to let Gradle pick whatever is on PATH.
    """
    cands: list[str] = []
    env_home = os.environ.get("JAVA_HOME", "").strip()
    if env_home:
        cands.append(env_home)
    for root in (r"C:\Program Files\Java", r"C:\Program Files\Eclipse Adoptium",
                 r"C:\Program Files\Microsoft"):
        try:
            kids = sorted(Path(root).iterdir(), reverse=True)
        except Exception:
            continue
        cands.extend(str(k) for k in kids if k.is_dir())
    # Stella's own toolchain. Adoptium extracts to jdk17/jdk-17.0.20.1+1, so a
    # bare `~/.stella-toolchain/jdk17` is never itself a JAVA_HOME - we have to
    # descend one level to find the real bin/. Missing this made Gradle fall
    # back to JDK 27, which Gradle 8.7 refuses to run on.
    for base in (Path.home() / ".stella-toolchain" / "jdk17",
                 Path.home() / ".stella-toolchain" / "jdk"):
        if not base.is_dir():
            continue
        try:
            kids = sorted(base.iterdir(), reverse=True)
        except Exception:
            kids = []
        # Prefer the nested Adoptium layout, but also allow the flat one.
        cands.extend(str(k) for k in kids if k.is_dir())
        cands.append(str(base))
    for cand in cands:
        java_exe = Path(cand) / "bin" / ("java.exe" if os.name == "nt" else "java")
        if not java_exe.exists():
            continue
        try:
            out = subprocess.run([str(java_exe), "-version"], capture_output=True,
                                 text=True, timeout=20)
            blob = (out.stdout or "") + (out.stderr or "")
            m = __import__("re").search(r'version "(\d+)', blob)
            if m and int(m.group(1)) <= max_major:
                return cand
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Release: write dist/manifest.json so the in-app updater can self-update a
# frozen install without git.
# ---------------------------------------------------------------------------

def _write_manifest(version: str, edition: str, artifacts: dict,
                  server_sha_android: str = "", k2_release: bool = False) -> Path:
    """Write dist/manifest.json. The `k2:` block versions the K2 runtime
    SEPARATELY from the app: core/updater.py only touches the k2/ tree when
    `k2_release` is true AND the pinned versions moved."""
    try:
        sys.path.insert(0, str(REPO))
        from core import k2_runtime as kr
        k2_block = kr.k2_manifest_block(server_sha_android)
        k2_block["k2_release"] = bool(k2_release)
    except Exception:
        k2_block = {"k2_release": bool(k2_release)}
    manifest = {
        "version": version,
        "edition": edition,
        "channel": "stable",
        "built_at": _now_iso(),
        "targets": artifacts,  # { "windows": {"file","sha256","size"}, ... }
        "k2": k2_block,
    }
    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return DIST / "manifest.json"


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def cmd_build(edition: str, target: str, release: bool, k2: bool = False) -> int:
    version = _read_version()
    DIST.mkdir(parents=True, exist_ok=True)

    # Mobile target: build the APK, done (no PyInstaller involved).
    if target == "android":
        apk = _build_android(edition, version, k2=k2)
        if not apk:
            print("FAIL: Android build produced no APK.")
            return 1
        print(f"==> APK: {apk}")
        if release:
            # Public and personal APKs differ (applicationId + K2 payload), so
            # they need distinct filenames or one overwrites the other.
            suffix = "-k2" if k2 else ""
            out_zip = DIST / f"Stella-Connect-{version}-android{suffix}.apk"
            shutil.copyfile(apk, out_zip)
            man = _write_manifest(version, edition, {
                f"android{suffix}": {"file": out_zip.name,
                                     "sha256": _sha256(out_zip),
                                     "size": out_zip.stat().st_size,
                                     "k2_bundled": k2}
            })
            print(f"==> Manifest: {man}")
        return 0

    if target == "ios":
        print("iOS: no Xcode project in this repo yet (see docs/IOS_BUILD.md).")
        print("Next steps: add a SwiftUI shell in stella-connect-ios/, then wire")
        print("  'xcodebuild -scheme Stella archive' into _build_ios() here.")
        return 2

    # Desktop: PyInstaller COLLECT -> universal zip -> native installer.
    variant = "k2" if k2 else "public"
    collect = _pyinstaller_build(edition, target, k2=k2)
    # Suffix keeps the two variants from clobbering each other in dist/.
    vsuffix = "-k2" if k2 else ""
    out_zip = _zip_dir(collect, DIST / f"Stella-{edition}-{version}-{target}{vsuffix}.zip")
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
            f"{target}{vsuffix}": {"file": out_zip.name,
                                   "sha256": _sha256(out_zip),
                                   "size": out_zip.stat().st_size,
                                   "k2_bundled": k2}
        }
        if native:
            artifacts[f"{target}{vsuffix}"]["installer"] = native.name
        man = _write_manifest(version, edition, artifacts,
                              k2_release=k2)
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
    ap.add_argument("--k2", action="store_true",
                    help="build the PERSONAL variant with the K2 runtime + weights "
                         "baked in. Omit for the public build (no K2 payload), "
                         "which is what CI and GitHub Releases ship.")
    args = ap.parse_args()

    if args.plan:
        return cmd_plan(args.edition, args.target)
    return cmd_build(args.edition, args.target, args.release, k2=args.k2)


if __name__ == "__main__":
    raise SystemExit(main())




