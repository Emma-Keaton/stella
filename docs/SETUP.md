# Setup — Build, Install, and Run Stella

Stella runs on desktop (Windows/macOS/Linux), web (PWA), Android, and iOS (PWA only). Every device works with direct runtime files only — no Ollama/LM Studio install required. Those endpoints remain optional; point Stella at them only if you already serve models that way.

## 1. Desktop (Windows / macOS / Linux)

```powershell
git clone https://github.com/Emma-Keaton/stella.git
cd stella
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

First launch opens the setup wizard: voice pick → device scan → model choice (live HuggingFace search filtered to YOUR specs) → optional sync → wake-word name → press to start.

- **Add a model**: Settings → Local → Browse .gguf (file explorer), HF `repo :: file` replace, or pull via Ollama. Sources are never deleted on import — if disk is low you're asked before anything is removed.
- **Remove/replace**: 🗑 Remove / 🔁 Replace buttons next to the model picker.
- **Voice**: mic stays live while voice-activated unless you start typing; clearing the box resumes listening after ~2 s.
- **Packaged build**: `installer/` PyInstaller spec produces a single-folder executable per OS.

### Requirements files

| File | Purpose |
|------|---------|
| `requirements.txt` | Portable dependencies (all platforms). |
| `requirements-all.txt` | Union of every portable feature group, for dev / full CI. |
| `requirements-windows.txt` | Windows-only extras (pycaw, comtypes, etc.) — Windows only. |
| `requirements-core.txt`, `-voice`, `-web`, `-vision`, `-docs` | Per-feature groups used by edition builds. |

`requirements-windows.txt` must never be installed on Linux or macOS — the Windows-only packages fail to build there.

## 2. Web (PWA)

The dashboard (`dashboard/`) is served by `main.py` on first run. Open the printed URL on any device on your network; install as PWA from the browser menu. Same chat, same providers (cloud APIs + any reachable local runtime).

## 3. Android

**Path A — Termux** (no root): install Termux + `python`, clone the repo, `python setup.py`, run `main.py` with `--no-gui` headless + dashboard, open the dashboard URL in Chrome → Add to Home screen.

**Path B — native APK**: `stella-connect-android/` holds the companion app. Build with Android Studio → APK. Models live in the app's `models/` dir; the manager script picks quants that fit the phone's RAM (Q4_K_M → Q3 on tight devices).

## 4. iOS

No Python runtime — use the web PWA (Add to Home Screen) pointed at your desktop Stella, or package the companion SwiftUI shell against the same `/v1/chat/completions` API. Voice via `AVSpeechSynthesizer`; pick Piper voices from settings to match.

## 5. Building locally

Stella ships as a portable, self-updating app for Windows, macOS, and Linux.

```powershell
python scripts/stella_build.py --edition core --os windows --release
python scripts/stella_build.py --edition lite --os linux --release
python scripts/stella_build.py --edition full --os macos --release
```

Use `--plan` to preview sizes without running PyInstaller.

The build writes to `dist/`:
- a portable `.zip` (always)
- an installer / image when the native packager is available (`.exe` on Windows via Inno Setup, `.dmg` on macOS, `.AppImage` on Linux)
- `dist/manifest.json` — the self-update manifest (version, per-OS file name, SHA-256). The in-app updater reads this.

### Editions

| Edition | Contents |
|---------|----------|
| `lite` | Cloud AI + voice. No globe, no browser automation, no vision. |
| `core` | Lite + local model support + offline TTS + full system control. |
| `full` | Everything: globe, browser automation, gestures, docs. |

Heavy deps (PyQt6-WebEngine, Playwright, opencv, mediapipe, piper-tts, docs libs) move behind lazy imports — a user who only wants cloud chat still gets the smallest build.

## 6. Local Models

The public build ships with no pre-loaded local model. You download models yourself, switch between them per task, and delete or replace them when you like. Everything is managed from Settings → Local Models.

- Downloaded models are stored as `.gguf` files under the user data directory's `models/` folder.
- The currently active model and its endpoint are recorded in the `models` section of `config/app_settings.json`.
- When a model is selected, Stella points its local AI client at that model's server endpoint and uses it for local reasoning tasks.

The Local Models panel shows downloaded models (size, quantization, active marker), Download (device-appropriate models only), Switch, Delete, and Replace.

### Choosing the right model

Stella's device detection buckets your machine and recommends quantizations that fit your free RAM:

- **~2 GB free RAM** — 1–3B parameter models at Q4.
- **~5 GB free RAM** — 3–8B parameter models at Q4/Q5.
- **8+ GB free RAM** — larger models; quantization matters less.

## 7. Android toolchain notes (personal builds)

Machine-specific build reference. Do **not** commit.

- **JDK 17** (Gradle 8.7 cannot run on JDK > ~22): `C:\Users\USER\.stella-toolchain\jdk17\jdk-17.0.20.1+1`
- **Android SDK**: `C:\Users\USER\.stella-toolchain\android-sdk`
- **K2 model**: `E:\Projects\stella\models\K2-Horizon-0.9B-Q4_K_M.gguf`

Every shell, first:
```powershell
$env:JAVA_HOME="C:\Users\USER\.stella-toolchain\jdk17\jdk-17.0.20.1+1"
```

Android signing credentials live in `.stella-signing.txt` (gitignored). Future updates MUST be signed with this same key, or the APK will refuse to install over the existing app.

## 8. iOS (future plan)

Status: **planned**. No Xcode project exists and no Apple toolchain runs on Windows. A real iOS app needs macOS + Xcode, a SwiftUI shell app, an Apple Developer account ($99/yr), and TestFlight or the App Store for distribution.

Checklist:
1. Shell app — new `stella-connect-ios/` SwiftUI project, reuses the same backend contract as Android.
2. Mac or CI — build with `xcodebuild` on macOS-latest.
3. Signing — Apple Developer team + provisioning profile as CI secrets.
4. Distribution — TestFlight internal track first, App Store later.
5. Wire into `stella_build.py` — replace the current `ios` guard with a `_build_ios()` that shells out to `xcodebuild`.
