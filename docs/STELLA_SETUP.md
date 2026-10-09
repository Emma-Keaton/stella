# ✦ Stella — Setup Guide (all devices)

> **"Built to assist. Engineered to evolve. Yours to shape."**

Stella runs on **web → desktop → Android → iOS**. Every device works with
**direct runtime files only** — no Ollama/LM Studio install required. Those
endpoints remain *optional*: point Stella at them only if you already serve
models that way.

Repo: **https://github.com/Emma-Keaton/stella**

---

## 1. Desktop (Windows / macOS / Linux)

```bash
git clone https://github.com/Emma-Keaton/stella.git
cd stella
python setup.py            # pip packages + Playwright + Piper voices
python main.py             # or start_brahma.bat on Windows
```

First launch opens the **setup wizard**: voice pick → device scan → model
choice (live HuggingFace search filtered to YOUR specs — never a stale list)
→ optional sync → wake-word name → press to start.

- **Add a model**: Settings → Local → *Browse .gguf* (file explorer), HF
  `repo :: file` replace, or pull via Ollama. Sources are **never deleted on
  import** — if disk is low you'll be asked before anything is removed.
- **Remove/replace**: 🗑 Remove / 🔁 Replace buttons next to the model picker.
- **Voice**: mic stays live while voice-activated **unless you start typing**;
  clearing the box resumes listening after ~2 s.
- **Packaged build**: `installer/` PyInstaller spec produces a single-folder
  executable per OS.

## 2. Web (PWA)

The dashboard (`dashboard/`) is served by `main.py` on first run. Open the
printed URL on any device on your network; install as PWA from the browser
menu. Same chat, same providers (cloud APIs + any reachable local runtime).

## 3. Android

Path A — **Termux** (no root): install Termux + `python`, clone the repo,
`python setup.py`, run `main.py` with `--no-gui` headless + dashboard, open
the dashboard URL in Chrome → Add to Home screen.

Path B — **native APK**: `brahma-connect-android/` holds the companion app
(ChatScreen talks to the same backend). Build with Android Studio → APK.

Models live in the app's `models/` dir; the manager script picks quants that
fit the phone's RAM (Q4_K_M → Q3 on tight devices).

## 4. iOS

No Python runtime — use the **web PWA** (Add to Home Screen) pointed at your
desktop Stella, or package the companion SwiftUI shell against the same
`/v1/chat/completions` API. Voice via `AVSpeechSynthesizer`; pick Piper
voices from settings to match.

## 5. Feedback → Issues → Updates loop

1. In-app: **Feedback & Updates** card → pick a channel:
   `local` (private file, default) · `email` (your SMTP, password asked once
   and never stored) · `github` (creates/prefills an issue in
   `Emma-Keaton/stella`) · `webhook` · `off`.
2. Reports are **structured** (encountered / did / how / need + device +
   version) and **scrubbed** — keys, tokens, passwords, emails are redacted
   before anything leaves the device.
3. Each release references `Closes #N` for attended issues → GitHub closes
   them automatically. The in-app updater (`core/updater.py`,
   `core/updater_ota.py`, `updater.py`) polls `Emma-Keaton/stella` hourly and
   shows the changelog of what got fixed.
4. Creators: prominent community skills get pinged for core inclusion.

## 6. Weak-device preset (e.g. 2-core CPU, ~2 GB free RAM)

- Keep the local server **up** once started — load once at boot, never
  kill between chats.
- Prefer ≤1.5B Q4_K_M; ctx 2048; threads = cores÷2; mmap (no mlock).
- Lazy-load dashboard/sensors after first paint; stream tokens to UI.
- The manager's `low_end` bucket enforces all of the above automatically.
