# Settings

Stella's settings live in `config/app_settings.json` (per-user copy under the
user data directory). The file is plain JSON and can be edited by hand; the app
re-reads it on load. `memory/config_manager.py` provides `load_settings()`,
`save_settings()`, `get_setting()`, and `set_setting()` for programmatic access.

## Common keys

| Key | Type | Meaning |
|-----|------|---------|
| `default_ai_provider` | string | `Gemini`, `OpenRouter`, `Groq`, or `Local`. |
| `auto_provider_switch` | bool | Automatically fall back between providers. |
| `local_ai_url` | string | Base URL of the local model server (e.g. `http://localhost:11434/v1`). |
| `local_ai_model` | string | Model name sent to the local server. |
| `groq_model` | string | Groq model id. |
| `offline_mode_enabled` | bool | Force fully-local operation. |
| `check_updates_on_startup` | bool | Ping the release manifest on launch. |
| `app_theme` | string | Accent color hex. |
| `models` | object | Local model management (see [Model Management](model-management.md)). |

## Audio

- `input_device` / `output_device` — selected mic and speaker names.
- `push_to_talk_enabled` — enable the push-to-talk hotkey.

## Local Models

The `models` section holds the currently selected local model and metadata.
See [Model Management](model-management.md) for details on downloading,
switching, replacing, and deleting models from the Settings UI.

## API keys

API keys live in a separate file, `config/api_keys.json`, so settings can be
shared without leaking secrets:

```json
{
  "gemini_api_key": "",
  "openrouter_api_key": "",
  "groq_api_key": ""
}
```

Only fill in the providers you use. Stella never requires a key for local
models.
