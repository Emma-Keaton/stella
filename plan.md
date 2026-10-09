# Stella Reconstruction Plan (plan.md)

Project: **Stella** — personal AI, rebuilt from Stella-Ai-Evo.
Targets (in order): **web → desktop → Android → iOS**, each as a runnable
executable/package. Personal use first, open-source friendly.

## 1. Goals (user-confirmed)
1. All platforms: CLI + GUI launcher + full app. Bundle as executables per OS.
2. Model choice ALWAYS shown. Real-time HuggingFace search filtered by live
   device specs — never a stale cached list.
3. Contact options for upgrade/update pings (user picks). Structured feedback:
   what was encountered / what user did / how / what they need next.
4. Voice menu: user picks from available voices (gender/nationality/pitch/tone).
5. Skills: creators can propose prominent skills for core inclusion.
6. Setup wizard on first run, then press-to-start. Temporary AND permanent
   agent disable options.
7. Feedback loop: general-app feedback + "what they did instead" reports flow
   back to creator for better updates. **Secrets/passwords NEVER leave device.**
8. NEW this round:
   - Voice input active when voice-activated UNLESS user starts typing.
   - Model removal / deletion / replacement with a different model.
   - Contact detail per Stella instance for upgrade/update pings.

## 2. Architecture
- `scripts/stella_model_manager.py` — spec detect, HF live search, download
  (resume + checksum), remove, replace. CLI: `detect|search|download|remove|
  replace|list`. Importable API for GUI/app use.
- `core/voice_gate.py` — single policy: mic live when voice-activated AND
  user NOT typing. UI emits typing signals; gate pauses/resumes capture.
- `core/feedback.py` — structured report builder + scrubber + channel senders
  (local file / email / GitHub issue / webhook / off).
- `core/k2_server.py` — (exists) bundled llama.cpp server manager; reused as
  the reference "local runtime" alongside Ollama/LM Studio.
- UI: provider dropdown + model combo + Remove/Replace buttons + voice picker
  + feedback dialog + setup wizard pages + disable toggles.
- Packaging: PyInstaller (desktop), PWA wrapper (web), Termux/APK path
  (Android), Swift/GGML path (iOS) — documented in docs/STELLA_SETUP.md.

## 3. Device-spec model matching
Buckets: low_end (<=2GB free RAM or <=2 cores), mid (<=5GB / <=4 cores),
high (rest), plus arch (x86_64/ARM64) and GPU (none/iGPU/discrete).
HF search: `huggingface_hub.HfApi().list_models(filter=...)`, GGUF quants
only, public repos; rank by fit (size <= 50% free RAM, quant preference
Q4_K_M CPU / Q4_0+GPU), then likes/downloads. `psutil` for specs, no cache —
query live each time, with graceful offline fallback message.

## 4. Voice-unless-typing
- UI chat input `textChanged` → `voice_gate.set_typing(bool(text))`.
- Voice-active + typing → pause mic capture + show "typing…" indicator.
- Input cleared + idle N sec → resume mic (if voice-activated).
- PTT/wake-word paths unchanged; gate sits above them.

## 5. Model remove/replace
- `remove`: delete GGUF file + clear selection if active + confirm dialog.
- `replace`: remove old → run manager download → set new as active.
- Works for bundled `models/` dir AND Ollama (`ollama rm`) AND LM Studio dir.

## 6. Feedback ping channels (user picks ONE, default: local file)
1. **Local file only** (default, fully private): `~/.stella/feedback/*.json`.
2. **Email**: user enters creator address + their SMTP (app password);
   sends structured report as encrypted-optional body. Secrets scrubbed first.
3. **GitHub issue**: opens prefilled issue URL (user submits in browser —
   no token needed) or via `gh` CLI if present.
4. **Webhook**: user-provided HTTPS endpoint, JSON POST.
5. **Off**: no pings at all.
- Scrubber redacts: passwords, tokens, keys, emails, paths with usernames.
- Report schema: encountered / did / how / need / device-profile / app-version.

## 7. Setup wizard + disable
- Pages: welcome → voice pick → device scan → model choice → sync opt →
  wake-word name → done → press-to-start.
- Disable: session snooze (until restart / 24h / date) + permanent
  (export context first) + voice-only-off. All in settings + tray.

## 8. Lightweight plan for weak devices (this PC: i3-6006U, ~2GB free)
- Server stays UP once started (no kill/reload between chats).
- ctx 2048 default, threads=cores//2, keep-alive infinite, mmap (no mlock).
- Prefer ≤1.5B Q4_K_M models on low_end; stream tokens to UI.
- Lazy-load heavy subsystems (dashboard, sensors) after first paint.
- Documented per-device presets in setup docs.

## 9. Build order
1. plan.md (this file) ✓
2. `scripts/stella_model_manager.py` + CLI smoke test
3. `core/voice_gate.py` + UI typing hook
4. Model Remove/Replace UI + manager methods
5. `core/feedback.py` + settings channel picker + dialog
6. `docs/STELLA_SETUP.md` (web/desktop/android/ios)
7. Commit; report 100%; request repo URL for push.

## 10. Acceptance
- `python scripts/stella_model_manager.py detect` prints profile.
- `search` lists live HF GGUF models fitting this PC.
- download→remove→replace cycle works on a tiny model.
- Typing pauses mic; clearing resumes.
- Feedback dialog produces scrubbed structured JSON; channel sends (or file).
- Docs cover all four platforms. Commit pushed after URL received.
