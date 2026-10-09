# Supercharging Stella — Build, Bundle & Auto-Update Plan

This document explains what is missing to make Stella **light, fast, and
self-updating on every platform**, and how the scripts in this repo do it.

---

## 1. Why the current build is heavy

| Component | Cost | Only needed for |
|---|---|---|
| `PyQt6-WebEngine` | ~150–300 MB (all of Chromium) | Globe / WebEngine HUD |
| Playwright browsers | ~300–400 MB (a 2nd browser) | Web automation |
| `opencv-python` + `mediapipe` | ~100 MB + models | Hand / gesture tracking |
| `piper-tts` + voices | ~60 MB | Offline TTS |
| `matplotlib`, `reportlab`, `pptx`, `docx` | ~80 MB | Docs / charts |

Everything is bundled unconditionally, so a user who only wants cloud chat
still downloads hundreds of MB and pays a slow cold-start.

## 2. Editions (ship only what's used)

`scripts/stella_build.py --edition <lite|core|full>`:

- **lite** — cloud API (Gemini/Groq/OpenRouter), voice, no WebEngine globe,
  no Playwright, no opencv/mediapipe. Smallest + fastest cold start.
- **core** — Lite + local K2 (llama.cpp) + offline Piper TTS + system control.
  The default "desktop assistant".
- **full** — Core + WebEngine globe + Playwright + gestures. Everything.

Heavy deps move behind **lazy imports** (import inside the function that uses
them). `main.py` already does this for most; the build keeps it honest.

## 3. Native installables per OS

| OS | Tool | Output |
|---|---|---|
| Windows | PyInstaller onedir + Inno Setup | `StellaSetup-<v>.exe` (MSI-like) |
| macOS | PyInstaller onedir + `hdiutil` | `Stella-<v>.dmg` (contains `.app`) |
| Linux | PyInstaller onedir + `appimagetool`/`dpkg` | `Stella-<v>.AppImage` / `.deb` |

## 4. The release channel + auto-update

A frozen install has **no `.git`**, so the old `git pull` updater silently
never fires. The new flow:

1. `stella_build.py release` builds the edition and writes
   `dist/manifest.json`:
   ```json
   { "version": "1.2.0", "channel": "stable",
     "targets": { "windows": {"url": "...", "sha256": "..."} } }
   ```
2. `dist/*.zip` + `manifest.json` are published to **GitHub Releases**.
3. Installed app runs `scripts/stella_update.py` (or the bundled
   `updater.update_from_channel`): reads the manifest, compares versions,
   downloads the target zip **resumably**, verifies the SHA-256, extracts to a
   staging folder, relaunches the new build, and the new instance cleans up the
   old one. No git, no dirty-tree checks, atomic, cross-platform.

This is what makes *any* change updatable: edit code → `stella_build.py release`
→ publish → every install self-updates on next launch.

## 5. One command, any target

```powershell
# Windows
python scripts/stella_build.py --edition core --os windows --release
# macOS / Linux (same command)
python3 scripts/stella_build.py --edition lite --os linux --release
```

`build.ps1` / `build.sh` are thin wrappers around this so the muscle memory is
identical everywhere.

## 6. Going even faster (optional, advanced)

- **Nuitka** compiles Python to C — noticeably faster startup than PyInstaller,
  at the cost of a much longer build. Good for a final "Full" release.
- **Strip WebEngine from `lite`** by keeping the globe native-free (or dropping
  it) — the single biggest size win.
