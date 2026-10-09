# K2 Horizon 0.9B Local Integration Design

## Goal
Run the user's K2-Horizon-0.9B-Q4_K_M GGUF inside Brahma Evo via llama.cpp,
selectable as "K2 Horizon" in the provider dropdown, autostarted with the app.

## Key finding: NO fork needed
- K2-Horizon GGUFs carry the `k2-horizon` arch token. HF docs (Sept 2026) said
  vanilla llama.cpp lacks support and pointed at MBZUAI-IFM/llama.cpp branch
  `model/K2Horizon` (this is the "Mazda" fork the user meant — MBZUAI).
- Tested upstream `ggml-org/llama.cpp` release **b11514** (Oct 2026): loads the
  model fine ("model loaded", /health 200). K2 support has since been merged
  upstream. MBZUAI-IFM publishes no prebuilt binaries, so upstream is used.
- Binary: `llama-b11514-bin-win-cpu-x64.zip` (19.5 MB) extracted to
  `.venv/llama.cpp/` (gitignored via `.venv/`).
- Model copied to `models/K2-Horizon-0.9B-Q4_K_M.gguf` (635 MB, gitignored via
  `models/` + `*.gguf`). Fallback path: `~/models/` (original location).

## Model quirks handled
1. **Inline thinking**: model emits `<ifm|think>...</ifm|think>` inside `content`
   (`--reasoning-format none` does NOT strip it). Client strips via regex and
   appends a "do not think, answer directly" suffix to the system prompt.
2. **Slowing lies**: with short `max_tokens`, the think trace eats the budget
   (`finish_reason: length`, empty content). Use generous `max_tokens` (>=256).
3. **Cold-start 503**: server reports healthy before model finishes loading.
   `k2_server._wait_ready()` polls `/v1/models` until non-empty, and the
   client retries 503s for up to 180 s.

## Architecture
- `core/k2_server.py` (new): subprocess manager. `start()` / `ensure_running()`
  / `start_background()` / `stop()` / `is_running()`. Threads default to
  `cpu_count//2` (override via `k2_threads`), port `k2_port` (11435), ctx
  `k2_ctx` (2048), autostart flag `k2_autostart` (true). All read live from
  `app_settings.json` (utf-8-sig tolerant).
- `llm_client.py`: `UnifiedAIClient` routes `"K2"` in `chat()`, `chat_json()`,
  `multi_turn()` via `_k2_chat_completion()` (OpenAI-compatible POST to
  127.0.0.1:11435). Vision falls through to OpenRouter (0.9B is text-only).
- `ui.py`: "K2 Horizon" in provider dropdown (after Groq); `_set_default_provider`
  handles `k2` and autostarts the server; refresh shows "K2 Horizon".
- `main.py` `runner()`: `k2_server.start_background()` at boot when autostart
  enabled (non-blocking; ~10 s load on healthy disks).
- Settings: `k2_port`, `k2_threads`, `k2_ctx`, `k2_autostart` in
  `config/app_settings.json` + `_default_app_settings()`.

## Performance notes (this PC)
- Test machine: i3-6006U (2C/4T), 8 GB RAM (~2.2 free), very slow disk
  (~5 MB/s reads). Measured: ~3.3 tok/s gen, ~7 tok/s prompt when warm.
- Cold load dominates wall time here; `--mlock` makes it worse (forces full
  635 MB read upfront). mmap (default) is correct for this hardware.
- Keep the server persistent (autostart, never kill between chats) so load
  happens once at boot. On a healthy machine: ~10 s load, faster tokens.
