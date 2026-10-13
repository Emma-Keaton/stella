# Building Stella

Stella ships as a portable, self-updating app for Windows, macOS, and Linux.
This document explains how the build pipeline works and how to produce a build
locally or via GitHub Actions.

## Editions

| Edition | Contents |
|---------|----------|
| `lite`  | Cloud AI + voice. No globe, no browser automation, no vision. |
| `core`  | Lite + local model support + offline TTS + full system control. |
| `full`  | Everything: globe, browser automation, gestures, docs. |

Editions are defined in `scripts/stella_build.py`. An edition includes its own
dependency group plus every group it depends on, which is what keeps `lite`
small.

## Building locally

```bash
python scripts/stella_build.py --edition core --os windows --release
python scripts/stella_build.py --edition lite --os linux --release
python scripts/stella_build.py --edition full --os macos --release
```

Use `--plan` to preview sizes without running PyInstaller:

```bash
python scripts/stella_build.py --edition full --plan
```

The build writes to `dist/`:
- a portable `.zip` (always)
- an installer / image when the native packager is available (`.exe` on
  Windows via Inno Setup, `.dmg` on macOS, `.AppImage` on Linux)
- `dist/manifest.json` — the self-update manifest (version, per-OS file name,
  SHA-256). The in-app updater (`core/updater.py`) reads this.

## Requirements files

| File | Purpose |
|------|---------|
| `requirements.txt` | Portable dependencies (all platforms). Installed everywhere. |
| `requirements-all.txt` | Union of every portable feature group, for dev / full CI. |
| `requirements-windows.txt` | Windows-only extras. Installed **only** on Windows. |
| `requirements-core.txt`, `-voice`, `-web`, `-vision`, `-docs` | Per-feature groups used by edition builds. |

`requirements-windows.txt` must never be installed on Linux or macOS — the
Windows-only packages (pycaw, comtypes, etc.) fail to build there.

## Self-update

`scripts/stella_build.py --release` writes `dist/manifest.json`. When a tagged
release is published to GitHub Releases, the in-app updater checks the manifest
for the host OS, downloads the matching archive, verifies its SHA-256, stages
it, and swaps it in on next launch. New Python dependencies added by a release
are installed automatically (core/desktop first, optional tiers after).
