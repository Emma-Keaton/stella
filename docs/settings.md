# Settings

Stella's settings live in `config/app_settings.json` (per-user copy under the
user data directory). The file is plain JSON and can be edited by hand; the app
re-reads it on load. `memory/config_manager.py` provides `load_settings()`,
`save_settings()`, `get_setting()`, and `set_setting()` for programmatic access.

## Common keys

| Key | Type | Meaning |
|-----|------|---------|
| `default_ai_provider` | string | `Gemini`, `OpenRouter`, `Groq`, or `Local`. Legacy alias, honoured when `routing` is absent. |
| `routing` | object | Per-mode provider selection: `{"chat": "...", "agent": "...", "voice": "..."}`. Values: `Auto`, `Groq`, `Gemini`, `OpenAI`, `Anthropic`, `OpenRouter`, `Local`. |
| `auto_provider_switch` | bool | Automatically fall back between providers. |
| `local_ai_url` | string | Base URL of the local model server (e.g. `http://localhost:11434/v1`). |
| `local_ai_model` | string | Model name sent to the local server. |
| `groq_model` | string | Groq model id. |
| `offline_mode_enabled` | bool | Force fully-local operation. |
| `check_updates_on_startup` | bool | Ping the release manifest on launch. |
| `app_theme` | string | Accent color hex. |
| `models` | object | Local model management (see [Model Management](model-management.md)). |

## Cloud Providers (Phase 4/5)

The Cloud Providers card (Settings → AI & Models → Cloud Providers) now drives
chat. Provisioned providers are stored encrypted at rest in
`config/cloud_providers.json` (Fernet + PBKDF2). API keys are never displayed in
plaintext after save.

Each provider carries: `provider`, `api_key` (encrypted), `base_url`, `model`,
`headers`, `params`, `fallback[]`, `auth_style`, `wire_format`.

Supported providers: `groq`, `gemini`, `openai`, `anthropic`, `openrouter`,
`ollama`, `lmstudio`, `custom`.

The `ProviderRouter` resolves the chat chain per mode: the selected provider is
tried first, then its `fallback[]`, then the local engine as a safety net.
Unconfigured providers are skipped, never fatal.

Provider actions: **Save** (encrypted, key not echoed back), **Test**
(connection tested against the real wire format), **Fetch models** (uses the
resolved key), **Forget** (removes provider, clears dangling routing selection).

## Audio

- `input_device` / `output_device` — selected mic and speaker names.
- `push_to_talk_enabled` — enable the push-to-talk hotkey.

## Local Models

The `models` section holds the currently selected local model and metadata.
See [Model Management](model-management.md) for details on downloading,
switching, replacing, and deleting models from the Settings UI.

## API keys

API keys live encrypted in `config/cloud_providers.json`, never in plaintext.
Stella never requires a key for local models.
