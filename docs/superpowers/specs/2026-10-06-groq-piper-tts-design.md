# Groq + Piper TTS Integration Design

## Goal
Add Groq as an LLM provider with tested free models, and replace Edge TTS fallback with local Piper TTS.

## LLM — Groq Provider

### Files
- `groq_client.py` (new): OpenAI-compatible client hitting `https://api.groq.com/openai/v1`
- `config/api_keys.json`: add `groq_api_key`
- `config/app_settings.json`: add `"groq_model": "openai/gpt-oss-120b"`
- `llm_client.py`: add `"Groq"` branch in `chat()`, `chat_json()`, `vision()`, `multi_turn()`
- `ui.py`: add "Groq" to provider dropdown, populate model dropdown when selected

### Models (tested, in order)
1. `openai/gpt-oss-120b` (default)
2. `openai/gpt-oss-20b`
3. `qwen/qwen3.8-27b`
4. `allam-2-7b`

### Architecture
`UnifiedAIClient` routes to `GroqClient` when `default_ai_provider == "Groq"`. Same pattern as Local branch — reads `groq_api_key` from `api_keys.json` and `groq_model` from `app_settings.json`.

## TTS — Piper

### Files
- `actions/attention_monitor.py`: add `PiperTTS` class, route fallback from Edge TTS → Piper
- `config/app_settings.json`: add `"tts_voice": "en_US-lessac-medium"`
- `ui.py`: add TTS voice dropdown in settings
- `setup.py`: auto-download Piper binary + voice models

### Voices (female)
- `en_US-lessac-medium` (default)
- `en_US-amy-medium`
- `en_US-kathleen`

### Architecture
`PiperTTS.synthesize(text)` runs Piper binary as subprocess → WAV file → playback. Replaces `_speak_edge_native()` as the fallback tier. Gemini Live remains primary, SAPI remains offline.

### Setup
Download Piper Windows release zip + voice `.onnx` + `.onnx.json` files from Hugging Face to `.venv/piper/`. Idempotent — skip if already present.

## Fallback Chain (updated)
1. Gemini Live (primary, if session active)
2. Piper TTS (fallback, replaces Edge TTS)
3. Windows SAPI (offline mode)

## Provider Switching
Settings UI dropdown: Gemini | OpenRouter | Local | Groq
Model dropdown populates based on selected provider.
