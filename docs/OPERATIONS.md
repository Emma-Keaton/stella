# Operations — Settings, Providers, Error Handling

Stella's settings live in `config/app_settings.json` (per-user copy under the user data directory). The file is plain JSON and can be edited by hand; the app re-reads it on load. `src/backend/memory/config_manager.py` provides programmatic access to `api_keys.json` (the single source of truth for provider keys, plugin enablement, voice, wake word, etc.).

## Settings reference

| Key | Type | Meaning |
|-----|------|---------|
| `default_ai_provider` | string | `Gemini`, `OpenRouter`, `Groq`, or `Local`. Legacy alias, honoured when `routing` is absent. |
| `routing` | object | Per-mode provider selection: `{"chat": "...", "agent": "...", "voice": "..."}`. |
| `auto_provider_switch` | bool | Automatically fall back between providers. |
| `local_ai_url` | string | Base URL of the local model server (e.g. `http://localhost:11434/v1`). |
| `local_ai_model` | string | Model name sent to the local server. |
| `groq_model` | string | Groq model id. |
| `offline_mode_enabled` | bool | Force fully-local operation. |
| `check_updates_on_startup` | bool | Ping the release manifest on launch. |
| `app_theme` | string | Accent color hex. |
| `models` | object | Local model management (see [Model Management](#local-models)). |

## Cloud Providers

Provisioned providers are stored encrypted at rest in `config/cloud_providers.json` (Fernet + PBKDF2). API keys are never displayed in plaintext after save.

Each provider carries: `provider`, `api_key` (encrypted), `base_url`, `model`, `headers`, `params`, `fallback[]`, `auth_style`, `wire_format`.

Supported providers: `groq`, `gemini`, `openai`, `anthropic`, `openrouter`, `ollama`, `lmstudio`, `custom`.

The `ProviderRouter` resolves the chat chain per mode: the selected provider is tried first, then its `fallback[]`, then the local engine as a safety net. Unconfigured providers are skipped, never fatal.

Provider actions: **Save** (encrypted, key not echoed back), **Test** (connection tested against the real wire format), **Fetch models** (uses the resolved key), **Forget** (removes provider, clears dangling routing selection).

## Audio

- `input_device` / `output_device` — selected mic and speaker names.
- `push_to_talk_enabled` — enable the push-to-talk hotkey.

## Local Models

The `models` section holds the currently selected local model and metadata. See [Model Management](#model-management) for details on downloading, switching, replacing, and deleting models from the Settings UI.

## API keys

API keys live encrypted in `config/cloud_providers.json`, never in plaintext. Stella never requires a key for local models.

## Plain-English errors

Every error that reaches you is written in plain English — never a raw stack trace — and offers concrete next steps.

| Underlying error | What Stella tells you |
|------------------|-----------------------|
| `FileNotFoundError` | "Stella could not find the file or folder it was looking for. Check the path is correct and try again." |
| `TimeoutError` | "Stella waited too long for a response. The service may be slow or your internet connection is unstable." |
| `ConnectionError` | "Stella could not reach a service. Check the service is running and your network is working." |
| HTTP 401 | "Stella could not log in to a service. Check your API key or login details." |

The translation lives in `core/error_reporter.py::translate_error`.

## Fix it yourself

When an error appears, Stella offers a **Fix it yourself** action. This prompts Stella to analyse the issue and update its own code so it can handle the task better next time. The response includes the plain-English description, the error type and original message, and a suggestion for how Stella will improve.

## When your local AI can't handle the task

Not every task is within reach of the model running on your device. Stella tells you plainly and offers alternatives:
- switching to a cloud AI provider (Settings → AI Provider),
- using a smaller or different local model that fits your device,
- adjusting the timeout so Stella waits longer.

## Report to admin

If the fix is beyond what your local instance can do, you can push the error into Stella's GitHub repository as an issue. Stella (the admin's agent) sees the issue, fixes the code, and alerts the admin, who then instructs it to push the update.

- `ErrorReporter.submit_issue(...)` records the report locally and returns a pre-filled GitHub issue URL (title, error, plain-English summary, device specs, and stack trace) so you can submit it with one click.
- Bug reports are stored in `feedback/bug_reports.json` with a `global_fix` flag. Resolved reports roll into the next update's changelog (`feedback/changelog.json`).

## Error recovery in the agent loop

The agentic loop treats a failed tool call as an observation, not a dead end: the error text is handed back to the model so it can adapt instead of retrying blindly. A repeat-detector stops the model from issuing the identical call more than twice. `agent/error_handler.py` classifies errors (transient / not-found / fatal) and decides whether to retry, skip, replan, or abort.

## Provider coverage gaps (known)

- **Gemini** — native `generativelanguage.googleapis.com` shape. Android's `cloudEndpoint()` has no `gemini` branch, so cloud chat silently fails for Gemini on Android.
- **Anthropic** — native `api.anthropic.com/v1/messages`, `x-api-key` header, `anthropic-version` header, different body shape. Not fully covered on either surface.
- **Home Assistant** is stored in the AI-provider store and can be returned as the "active provider" by `get_active_provider()`.

## What already exists (do not rebuild)

| Area | Status | Evidence |
|------|--------|----------|
| Provider config schema (runtime) | Exists | `src/backend/core/providers/` |
| Desktop encrypted store | Exists | Fernet, PBKDF2, `%LOCALAPPDATA%\StellaAI\config\cloud_providers.json` |
| Android encrypted store | Exists | `CloudKeyStore.kt` - AES-256-GCM, Android Keystore |
| Desktop provider UI | Exists | Settings → AI & Models → Cloud Providers |
| Android provider UI | Exists | `ProviderSelector.kt` |

## Phase 4/5 known gaps

1. Desktop provider config is write-only — saving a provider changes nothing until the router reads it.
2. Desktop chat reads `default_ai_provider` while the Routing card writes a separate `routing` block that nothing reads.
3. The runtime format and the published schema disagree — `additionalProperties: false` would reject every config the app actually writes.
4. `home_assistant` is stored in the AI-provider store and can shadow real AI providers.
