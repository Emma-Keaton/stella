# Phase 4 / 5 - Implementation Task List (derived from `phase4-5-provider-spec.md`)

Status: **READY FOR REVIEW** - ordered, dependency-sorted, every task cites exact code locations.
Every task is independently shippable and independently revertable.

Notation: `T<track>.<n>` | `[BUG]` a defect | `[GAP]` a missing capability | `[REFACTOR]` cleanup | `[NEW]` newly found

---

## Corrections to the earlier spec (read this first)

Five findings in this task list **contradict or extend** `phase4-5-provider-spec.md`. The spec was
written from a config-file audit; this list was written from a **data-flow** audit and found more.

### CORRECTION 1 - the desktop has THREE separate key stores, not one

The spec assumed `config/cloud_providers.json` was the desktop's provider store. It is - but the
desktop **chat path never reads it**. The real desktop chat reads a *different, plaintext* file:

| Store | Written by | Read by chat? |
|---|---|---|
| `config/api_keys.json` (plaintext) | legacy key editor | **YES - this is what actually runs** |
| `config/cloud_providers.json` (encrypted) | the Cloud Providers UI (`settings_pages.py`) | **NO - nothing in the chat path reads it** |
| `config/app_settings.json` | Routing card | `default_ai_provider` only; `routing` is **never read** |

Evidence:
- `main.py:124` `API_CONFIG_PATH = .../config/api_keys.json`; `main.py:136` `_get_api_key()` reads
  `json.load(f)["gemini_api_key"]`.
- `or_client.py:22-28` reads `api_keys.json["openrouter_api_key"]`.
- `groq_client.py:22-28` reads `api_keys.json["groq_api_key"]`.
- `core/cloud_config.py` (`cloud_providers.json`) has **no importer** in the chat path.

**Consequence:** the desktop Cloud Providers UI writes an encrypted file that the app never
consults, while the chat uses an unrelated plaintext key file. This is a *worse* break than the
spec described, and it is the highest-priority fix (Track 1). The desktop Anthropic/OpenAI/
Ollama/LM Studio/Custom entries have **no chat implementation at all** - `main.py:3775-3811`
handles only Gemini, OpenRouter and Local.

### CORRECTION 2 - Android already has the desktop-parity form; the problem is a second, older UI

The spec (6.3) proposed *building* an Android provider form. It **already exists**:
`ui/CloudProviderEditor.kt` (347 lines) has provider dropdown, masked key, model + Fetch, base
URL, headers, params, Save/Test/Forget - and it is rendered by `SettingsSections.kt:101`, reached
from `SettingsScreen.kt:88`.

But a **second, older UI** - `ui/ProviderSelector.kt` - is still rendered by the **onboarding**
flow (`StellaConnectApp.kt:243`, route `"providers"`). It:
- pre-fills the **decrypted** key into its dialog (`ProviderSelector.kt:50`), and
- calls `.copy(provider = name, apiKey = ...)` (`ProviderSelector.kt:77`), which **rewrites the
  provider id while keeping the previous provider's `base_url`/`model`/`headers`**, producing a
  config that points a Gemini key at Groq's endpoint.

So the task is **not** "build the Android form" - it is "delete/redirect the duplicate onboarding
UI and fix the form's data-flow bugs". Track 3 reflects this.

### CORRECTION 3 - `todo.md` is stale in four places that change the plan

`todo.md` is the project's own Phase 4/5 tracker. Four of its statements no longer match the
code, and one of them contradicts this task list:

| `todo.md` says | Reality | Consequence |
|---|---|---|
| `:129` "test-connection removed per user (errors surface during model load)" | The desktop **has** a Test Connection button (`settings_pages.py:279-280`, handler `:550`) and Android has a "Test" button (`CloudProviderEditor.kt:226-246`) | The Test-Connection decision (D5) is **live**, not settled. Must be re-decided. |
| `:129` "Android `ProviderSelector.kt` integrated into `SettingsScreen.kt`" | `SettingsScreen.kt:88` routes to `CloudProvidersDetail` -> `CloudProviderEditor`. `ProviderSelector.kt` is **not** in Settings; it is only in onboarding | The *right* form is already live in Settings. T3.7 should only redirect onboarding. |
| `:129` "desktop parity scaffold `ui/provider_selector.py`" | It is a 38-line stub with **no importer anywhere** (grep for `provider_selector` returns nothing) | Gate A is safe to delete immediately - it is dead code. |
| `:132` "Actions: Test connection Â· Save Â· Forget" | Already implemented on both surfaces | Not a task; a verification item |

### CORRECTION 4 - there are SIX LLM paths, not five, and one of them reads env vars

`todo.md:151` says the router "kills 5 LLM paths" (`llm_client.py`, `or_client.py`,
`groq_client.py`, `agent/llm.py`, `core/local_brain.py`). There is a sixth, and it is the odd
one out:

`agent/llm.py:186-200` builds its own backend chain and resolves keys from **environment
variables** (`os.environ`, lowercased) - not from `api_keys.json`, not from the encrypted store.
So `agent/llm.py` needs a **fourth** key source, and `agent/llm.py:198` hard-codes
`llama-3.3-70b-versatile` and the Groq URL, ignoring the provider config entirely.

(`agent/router_policy.py` was checked - it is a routing-*target* helper used by
`needle_bridge.py`, not an LLM path.)

### CORRECTION 5 - the legacy clients snapshot the key at import time

`or_client.py:349` (`client = OpenRouterClient()`) and `groq_client.py` do the same. The key is
read in `__init__` (`:85`) and frozen into `self._headers`. Consequences:
- A key saved **after** startup is not used until the app restarts.
- Simply changing `_load_api_key()` to read the encrypted store (T1.2) is **not sufficient** -
  the clients must re-read the key per request, or expose a `reload()`.

This is why "the provider UI does nothing" is so hard to notice: the UI writes a file, and the
chat reads a *different* file, snapshotted at startup.

### CORRECTION 6 - a `ProviderRouter` already exists, unused, with a conflicting schema

`core/llm_router.py` (104 lines) already defines a `ProviderRouter` class. It is **not** the
module the spec planned, and it must be reconciled rather than duplicated:

| Aspect | `core/llm_router.py` (existing) | The spec's planned router |
|---|---|---|
| Config shape | `{"providers": [{name, kind, model, api_key, base_url, enabled, priority}], "fallback_chain": [...]}` | The Phase 1.6 contract: `{provider, api_key, base_url, model, headers, params, fallback[]}` |
| Key source | `api_key` inline in the config file | Encrypted `cloud_providers.json` via `core/cloud_config.py` |
| Extra fields | ignores `headers`, `params`, `fallback` | uses all of them |
| Config path | `~/.stella/providers.json`, `config/providers.json`, `config/cloud_providers.json` (`:91-98`) | `config/cloud_providers.json` |
| Adapter | falls back to a raw `urllib` OpenAI-only call (`:77-88`) because `core/llm_adapter.py` **does not exist** | `core/providers/adapters.py` (T1.3) |
| Consumers | **none** - grep for `llm_router` / `ProviderRouter` returns only its own definition | wired into 6 LLM paths |

Two concrete hazards:
- `load_default()` at `:95` reads `config/cloud_providers.json` **in plaintext** - it would
  bypass the Fernet encryption in `core/cloud_config.py` and fail on the encrypted file.
- It is OpenAI-only (`:79` builds `base + "/chat/completions"` with `Authorization: Bearer`),
  so it reproduces the Anthropic and Gemini bugs rather than fixing them.

Decision needed (D11): **evolve `core/llm_router.py` in place** (recommended - it is the name
the spec already uses) or **replace it** with `core/providers/router.py` and delete it. Either
way it must not sit there unused with a second config schema.

---


## Track 0 - Foundation (no behaviour change; unblocks everything)

| ID | Type | Task | Files / locations | Done when |
|---|---|---|---|---|
| T0.1 | [NEW] | Create the single provider registry as data: `config/providers.json` - id, label, auth_style, wire_format, base_url, requires_key, models_endpoint, chat_endpoint | `config/providers.json` (new) | 8 entries: groq, gemini, openai, anthropic, openrouter, ollama, lmstudio, custom |
| T0.2 | [NEW] | Python registry loader; `PROVIDER_IDS`, `PROVIDER_LABELS`, `label_for(id)`, `id_for(label)`, `PRESETS` derived from T0.1 | `core/providers/registry.py` (new), `core/providers/__init__.py` | `core/cloud_config.py:170-179` `PRESETS` becomes a thin alias, not a second copy |
| T0.3 | [NEW] | Kotlin registry loader reading the same `config/providers.json` (ship it in `assets/`) | `core/ProviderRegistry.kt` (new), `app/src/main/assets/providers.json` | Kotlin ids == Python ids (asserted by T0.7) |
| T0.4 | [BUG] | Rewrite the schema to describe the **runtime array**, not the old `{name, auth_type, endpoint, models, key_env, status}` object | `config/cloud_providers.schema.json` | `jsonschema.validate` passes on a real file written by `save_provider`; schema `type` is `array` |
| T0.5 | [BUG] | Exclude `home_assistant` at the accessor level | `core/cloud_config.py:163-166` `get_active_provider()` | `get_active_provider()` can never return `home_assistant`; add `is_ai_provider()`, `load_ai_providers()` |
| T0.6 | [BUG] | Fix the masked/raw API inconsistency: `load_providers()` masks (`cloud_config.py:96-99`) but `load_provider()` returns the **raw key** (`:104-117`) | `core/cloud_config.py:104-117` | New explicit pair: `load_provider(pid, reveal=False)` (masked, default) + `load_provider_raw(pid)`; update the one legit raw caller |
| T0.7 | [NEW] | Registry parity contract test (mirrors the existing `ThemeContractTest.kt` pattern at `app/src/test/java/com/stella/connect/ui/theme/ThemeContractTest.kt`) | `tests/test_provider_registry.py` + `app/src/test/.../ProviderRegistryTest.kt` | A registry change not mirrored on both sides **fails CI** |

**Exit gate:** schema validates the real file; `get_active_provider()` cannot return
`home_assistant`; registry parity test green; **no behaviour change** (the chat still uses
`api_keys.json` exactly as before).

---


## Track 1 - Desktop key-store unification (highest priority)

*This is the fix for CORRECTION 1. It is the difference between "the provider UI works" and
"the provider UI does nothing".*

| ID | Type | Task | Files / locations | Done when |
|---|---|---|---|---|
| T1.1 | [BUG] | **Stop writing plaintext keys.** `api_keys.json` currently stores `gemini_api_key`, `openrouter_api_key`, `groq_api_key` in the clear. Route all new writes through `core/cloud_config.py` (encrypted). Keep `api_keys.json` read-only for legacy migration. | `main.py:124,136`; `or_client.py:22-28`; `groq_client.py:22-28` | New keys never written to `api_keys.json`; legacy keys are migrated on first read and the legacy file is left intact (not deleted) |
| T1.2 | [BUG] | Make the desktop chat path read the **provider config**, not `api_keys.json`. Introduce `core/providers/keys.py::resolve_key(provider_id)` that prefers `cloud_providers.json` and falls back to `api_keys.json` for migration. | `main.py:136` `_get_api_key()`; `or_client.py:24`; `groq_client.py:24` | With a key saved via the Cloud Providers UI, the desktop chat uses it |
| T1.3 | [BUG] | Implement the **missing desktop providers.** `main.py:3775-3811` handles only Gemini / OpenRouter / Local. Anthropic, OpenAI, Ollama, LM Studio and Custom have no chat path. | `main.py:3775-3811`; new `core/providers/adapters.py` | Each of the 8 registry ids can answer a desktop chat |
| T1.4 | [BUG] | **Anthropic wire format is wrong.** The preset base URL is `https://api.anthropic.com/v1`, but Anthropic's Messages API is `POST /v1/messages` with `x-api-key` + `anthropic-version: 2023-06-01` - it is **not** `Authorization: Bearer` and **not** `/chat/completions`. OpenAI-compatible framing silently 404s. | `core/cloud_config.py:174`; `core/providers/registry.py` | Anthropic sends `x-api-key`, `anthropic-version`, and `POST /v1/messages` with body `{model, max_tokens, messages, system}`; verified against a live key |
| T1.5 | [BUG] | **Gemini endpoint is wrong for the OpenAI-compat preset.** `core/cloud_config.py:172` uses `.../v1beta/openai/` - that base URL is correct, but the resulting chat path must be `.../v1beta/openai/chat/completions` and models `.../v1beta/openai/models`, and auth must be `Authorization: Bearer <GEMINI_API_KEY>`. | `core/cloud_config.py:172`; `core/providers/registry.py` | Gemini answers via the OpenAI-compat endpoint, or the native `genai` adapter is used (it already exists at `main.py:312` and works) |
| T1.6 | [BUG] | Provider status line in the UI: "Not configured" / "Configured - <model>" / "Configured - no model set" | `ui/settings_pages.py` `_add_cloud_providers_section` | Status reflects the real saved state |
| T1.7 | [BUG] | Fix "Fetch models" to use the **resolved saved key** when the key field is blank. Today `FetchWorker` is constructed with `self._api_key.text()` (`:533`), which is empty after a save - so Fetch always 401s. | `ui/settings_pages.py:533` (the `_test_connection` path at `:566` already does this correctly - copy it) | Fetch works after Save without re-typing the key |
| T1.8 | [BUG] | `_load_provider_into_form` never sets the "Saved key (hidden)" placeholder, so a user cannot tell a provider is configured | `ui/settings_pages.py` `_load_provider_into_form` | Placeholder + status reflect the saved state |
| T1.9 | [BUG] | **The legacy clients snapshot the key at import time.** `or_client.py:349` (`client = OpenRouterClient()`) and the equivalent in `groq_client.py` read the key in `__init__` (`:85`) and freeze it into `self._headers`. A key saved after startup is never used until restart. | `or_client.py:84-91,349`; `groq_client.py:55-61` | Either the key is re-read per request, or the clients expose `reload()` and the settings UI calls it after a successful save |
| T1.10 | [BUG] | **`agent/llm.py` resolves keys from environment variables** (`agent/llm.py:192-198`), a **fourth** key source, and hard-codes the Groq URL + model (`llama-3.3-70b-versatile`), ignoring the provider config. | `agent/llm.py:186-200` | The agent backend chain resolves its cloud backend through the shared provider config |
| T1.11 | [NEW] | Inventory every module that resolves an API key, and assert in a test that there is exactly **one** resolution path | `core/providers/keys.py`; grep for `api_key` across `*.py` | A test fails if a new key-reading site appears outside `core/providers/keys.py` |

**Exit gate:** save a provider in the UI -> desktop chat is answered by that provider -> the key
never appears in plaintext on disk -> `api_keys.json` is not written by any new code path -> the
key takes effect **without restarting** the app.

---


## Track 2 - Desktop router & routing

| ID | Type | Task | Files / locations | Done when |
|---|---|---|---|---|
| T2.1 | [NEW] | Add the router: `ProviderRouter.resolve(mode)` (ordered candidate chain) and `ProviderRouter.chat(mode, messages)` (first success + attempt log). **Reconcile with the existing `core/llm_router.py` first - see T2.12.** | `core/llm_router.py` (evolve) or `core/providers/router.py` (replace) | Returns a `RouterResult` with `text`, `provider_id`, `model`, `attempts` |
| T2.2 | [NEW] | Chain construction: `routing[mode]` -> legacy `default_ai_provider` alias -> "Auto". "Local" = local only. Unconfigured providers are **skipped**, not fatal. Provider `fallback[]` appended. Local engine last. Dedup. | `core/providers/router.py` | Covered by the unit tests in Track 4 |
| T2.3 | [BUG] | **Wire the router into the desktop chat path.** `main.py:3771` reads `default_ai_provider`; `app_settings["routing"]` is written by the UI (`settings_pages.py:406`) and **never read**. | `main.py:3771` | The Routing card actually changes which provider answers |
| T2.4 | [BUG] | **Wire the router into the model/status path.** `main.py:2836` also reads `default_ai_provider`. | `main.py:2836` | Both paths use one resolver |
| T2.5 | [NEW] | Legacy alias guarantee: if `routing` is absent, use `default_ai_provider`; label mapping `"Gemini"/"Google Gemini"`->`gemini`, `"OpenRouter"`->`openrouter`, `"Groq"`->`groq`, `"OpenAI"`->`openai`, `"Anthropic"`->`anthropic`, `"Local"`->local | `core/providers/router.py` | An existing user sees **no behaviour change** on upgrade |
| T2.6 | [NEW] | Structured logging: `provider_route` / `provider_attempt` / `provider_route_final`. Never log keys or message bodies. | `core/providers/router.py`, logger `providers.router` | Matches the log lines in the spec 5.6 |
| T2.7 | [NEW] | Routing UI: status suffix per combo ("Groq (not configured)"), and a per-provider **fallback order** editor writing `fallback[]` | `ui/settings_pages.py:369-397` | The user can see and edit the real fallback chain |
| T2.8 | [BUG] | "Forget" should clear a Routing selection that points at the forgotten provider | `ui/settings_pages.py:677-690` | No dangling routing selection |
| T2.9 | [BUG] | **Route `agent/llm.py`'s backend chain through the router.** `agent/llm.py:155-201` builds its own `Backend([...])` from a selected local model, the bundled K2 runtime, and a hard-coded Groq cloud entry. It is used by `agent/loop.py:29,350` and `agent/integration.py:19`. | `agent/llm.py:155-201`; `agent/loop.py`; `agent/integration.py` | The agent uses the same resolved chain as chat, and its cloud backend honours the provider config |
| T2.10 | [BUG] | **Route `llm_client.py` through the router.** `llm_client.py:60-231` branches on `self._provider` (`Local`/`Groq`/`K2`) across `chat`, `chat_json`, `vision`, `vision_from_file` and `multi_turn`. | `llm_client.py:106-231` | `llm_client` delegates to the router instead of branching on a provider name |
| T2.11 | [NEW] | Per-turn routing hook: the router must accept a per-call provider override ("use Groq for this turn only") | `core/providers/router.py` | The agent can steer a single turn without changing global settings |
| T2.12 | [BUG] | **Reconcile the orphaned `core/llm_router.py`.** It already defines a `ProviderRouter` with a conflicting config schema, no consumers, a plaintext loader that bypasses the encryption, and an OpenAI-only fallback. Either evolve it in place or replace it - but there must be exactly **one** router and **one** config schema. | `core/llm_router.py:1-104` | No second `ProviderRouter` exists; `load_default()` cannot read the encrypted file in plaintext; `core/llm_adapter.py` either exists or the dead import is removed |

**Exit gate:** desktop chat honours the Routing card; `default_ai_provider` still honoured when
`routing` is absent; the local brain still answers when nothing is configured; **all six** LLM
paths go through the router (none of them deleted yet).

---


## Track 3 - Android provider fixes

| ID | Type | Task | Files / locations | Done when |
|---|---|---|---|---|
| T3.1 | [BUG] | **Android can only hold ONE provider.** `CloudKeyStore` stores a single blob under `KEY_BLOB` (`CloudKeyStore.kt:82,115`) and `load()` returns one config. But the desktop stores a **list**. The `fallback[]` and multi-provider fallback chain are therefore impossible on Android today. Migrate the blob to a JSON **array** of providers. | `core/CloudKeyStore.kt:80-160` | `loadAll(ctx): List<CloudProviderConfig>`; `load(ctx)` returns the primary; existing single-provider installs migrate on first read |
| T3.2 | [BUG] | **Gemini and Anthropic have no endpoint.** `cloudEndpoint()` (`LocalEngineManager.kt:1004-1018`) has branches for groq/openai/openrouter/ollama/lmstudio only; `gemini` and `anthropic` fall into the `else` branch, which returns `null` when `base_url` is blank -> `cloudChat` returns `null` silently. The user saves a Gemini key and **nothing ever happens**. | `core/LocalEngineManager.kt:1004-1018` | Gemini and Anthropic resolve to working endpoints |
| T3.3 | [BUG] | **Anthropic needs a different wire shape.** `cloudChat` always sends `Authorization: Bearer` (`:971`) and always reads `choices[0].message.content` (`:985-993`). Anthropic needs `x-api-key` + `anthropic-version: 2023-06-01`, `POST /v1/messages`, body `{model, max_tokens, messages, system}`, and the response is `content[0].text`. | new `core/ProviderEndpoint.kt`; `LocalEngineManager.kt:962-1001` | Anthropic answers on Android |
| T3.4 | [BUG] | **Gemini OpenAI-compat needs the right path.** `cloudEndpoint` must produce `.../v1beta/openai/chat/completions` and use `Authorization: Bearer`. | `core/ProviderEndpoint.kt` | Gemini answers on Android |
| T3.5 | [BUG] | **`params` are string-typed on Android.** `CloudProviderConfig.params: Map<String, String>` (`CloudKeyStore.kt:33`) and `fromJson` coerces every value with `optString` (`:66-68`). So `{"temperature": 0.7}` round-trips as `"0.7"`, and `cloudChat` sends `body.put(k, v)` with a **String** (`:979`) -> `"temperature":"0.7"`, which providers reject or ignore. The desktop stores them as real JSON numbers (`settings_pages.py:653`). | `core/CloudKeyStore.kt:33,66-68`; `LocalEngineManager.kt:979`; `ui/CloudProviderEditor.kt:285-294` `parseJsonObject` | `params` round-trip as numbers/booleans; `parseJsonObject` returns `Map<String, Any>` preserving types |
| T3.6 | [BUG] | **The onboarding UI leaks the key and corrupts the config.** `ProviderSelector.kt:50` pre-fills the **decrypted** key into the dialog; `:77` does `.copy(provider = name, apiKey = ...)` which keeps the previous provider's `base_url`/`model`/`headers` while changing the provider id. | `ui/ProviderSelector.kt` | See T3.7 |
| T3.7 | [REFACTOR] | **Remove the duplicate onboarding provider UI.** `ProviderSelector.kt` is rendered only by the onboarding route (`StellaConnectApp.kt:243`). Replace that route with `CloudProviderEditor` and delete `ProviderSelector.kt`. (The `google_drive`/`onedrive`/`dropbox` OAuth cards there are non-functional placeholders - `onClick = { }`.) | `ui/ProviderSelector.kt` (delete); `ui/StellaConnectApp.kt:241-247`; `ui/SettingsSections.kt` | One provider UI on Android. This closes the "keys never displayed plaintext" criterion. |
| T3.8 | [BUG] | **Fallback chain is parsed but never used.** `fallback: List<String>` is stored (`CloudKeyStore.kt:34`) and read (`:69-71`), but `cloudChat` only ever tries the one config. | `core/LocalEngineManager.kt:962-1001` | On failure, the next id in `fallback` is tried, then the local engine |
| T3.9 | [BUG] | **`ChatPromptReceiver` has no cloud fallback.** It calls only `LocalEngineManager.chat` (`ChatPromptReceiver.kt:62`) and bails at `:44-47` when no local model is present - so the broadcast path can never use a configured cloud provider, while the foreground path can. | `core/ChatPromptReceiver.kt:42-62` | Broadcast path uses the same fallback-aware chain as the foreground path |
| T3.10 | [NEW] | **One shared fallback-aware answer chain.** The foreground service (`StellaConnectForegroundService.kt:211-239`) already does local -> cloud -> state line. Extract it and use it from `ChatPromptReceiver` too. | new `core/AnswerChain.kt`; `StellaConnectForegroundService.kt:211-239`; `ChatPromptReceiver.kt` | Both entry points produce identical answers for the same input |
| T3.11 | [BUG] | Android "Test" button is OpenAI-only: `testConnection` (`CloudProviderEditor.kt:325-347`) always POSTs `/chat/completions` with `Authorization: Bearer`. It cannot test Gemini or Anthropic. | `ui/CloudProviderEditor.kt:324-347` | Test uses the same wire format as the real chat path |
| T3.12 | [BUG] | Android "Fetch" button is OpenAI-only: `fetchModels` (`CloudProviderEditor.kt:297-322`) always GETs `{base}/models` with `Authorization: Bearer`. Gemini needs `.../v1beta/openai/models`; Anthropic has no models endpoint - return a static model list instead. | `ui/CloudProviderEditor.kt:296-322` | Fetch returns the provider's real model list |
| T3.13 | [BUG] | Changing the provider dropdown does **not** clear the retained key, so a Gemini key can be saved against Groq. | `ui/CloudProviderEditor.kt:111-124` | Changing provider either clears the key or warns |
| T3.14 | [NEW] | Android provider **status** indicator + "configured" detection per provider | `ui/CloudProviderEditor.kt` | The user can see which providers are configured |
| T3.15 | [NEW] | Android routing / fallback **order** editor writing `fallback[]` | `ui/SettingsSections.kt` | The fallback chain is user-editable on Android too |
| T3.16 | [BUG] | Share one wire-format module between `cloudChat`, `testConnection` and `fetchModels` - today the same OpenAI-only assumptions are duplicated in three places. | `core/ProviderEndpoint.kt`; `LocalEngineManager.kt`; `ui/CloudProviderEditor.kt` | One wire-format implementation, three call sites |
| T3.17 | [BUG] | Confirm `LocalEngineManager.cloudChat` is reached from **all** chat surfaces, not just the foreground service (HUD/overlay paths included). | `LocalEngineManager.kt`; `StellaConnectForegroundService.kt`; `ChatPromptReceiver.kt`; any HUD/overlay path | Every chat surface can reach the cloud rung |

**Exit gate:** Gemini and Anthropic both answer on Android; `params` keep their JSON types; the
decrypted key is never rendered anywhere; the broadcast and foreground paths share one chain.

---



## Track 4 - Testing

| ID | Type | Task | Files / locations | Done when |
|---|---|---|---|---|
| T4.1 | [NEW] | Router unit tests: chain order, "Auto", "Local", legacy alias, dedup, skip-unconfigured, fallback[] append | `tests/test_provider_router.py` | >= 12 assertions covering the matrix in spec 12 |
| T4.2 | [NEW] | Key-resolution tests: provider-config preferred, legacy `api_keys.json` fallback, empty -> unconfigured | `tests/test_provider_keys.py` | Migration path proven both ways |
| T4.3 | [NEW] | `cloud_config` tests: encrypt/decrypt round-trip, masked vs raw, `home_assistant` excluded, schema validation of a written file | `tests/test_cloud_config.py` | All pass |
| T4.4 | [NEW] | Adapter tests against **recorded HTTP fixtures** (no network): Anthropic request headers/body, Gemini path, OpenAI-compat path, response parsing per provider | `tests/fixtures/providers/*.json` + `tests/test_provider_adapters.py` | Wire format asserted byte-for-byte |
| T4.5 | [NEW] | Android JVM tests: `params` type round-trip, single->array migration, Anthropic/Gemini endpoint resolution, response parsing | `app/src/test/.../CloudKeyStoreTest.kt`, `ProviderEndpointTest.kt` | All pass |
| T4.6 | [NEW] | Android test: the decrypted key is **never** present in any rendered UI state | `app/src/test/.../ProviderUiTest.kt` | Regression guard for T3.6/T3.7 |
| T4.7 | [NEW] | Registry parity test (see T0.7) run in **both** CI legs | `tests/test_provider_registry.py`, `ProviderRegistryTest.kt` | A one-sided registry edit fails |
| T4.8 | [BUG] | Fix the two pre-existing Android/temp-dir permission failures in the baseline | see baseline notes | Full suite green |
| T4.9 | [BUG] | The full `pytest` run exceeded the command timeout. Split the suite (or run with `-p no:cacheprovider` and a per-file timeout) so CI can complete | `tests/` | Full suite runs green in CI |

**Exit gate:** every task above has a test; the full suite is green.

---

## Track 5 - Migration & rollout

| ID | Type | Task | Files / locations | Done when |
|---|---|---|---|---|
| T5.1 | [NEW] | Desktop: on first read of `api_keys.json`, copy `gemini_api_key` / `openrouter_api_key` / `groq_api_key` into the encrypted provider store, **without deleting the legacy file** | `core/providers/keys.py` | Legacy users keep working; the encrypted store is populated |
| T5.2 | [NEW] | Android: migrate the single-provider blob to an array on first read; also fold in the legacy `cloud_api_key` prefs entry | `core/CloudKeyStore.kt` (`migrateLegacyApiKey` already exists at `:162`) | Existing installs keep their key and gain a list |
| T5.3 | [NEW] | Feature flag: `providers.router_enabled` (default **off** in stage 1) so the router can be rolled out gradually | `app_settings.json` | The old path remains the default until sign-off |
| T5.4 | [NEW] | Rollout stages, each independently revertable: **S1** foundation -> **S2** key unification -> **S3** desktop router -> **S4** Android fixes -> **S5** Android router -> **S6** cleanup gates | this document | Each stage has an entry/exit gate and a rollback |
| T5.5 | [NEW] | Migration verification matrix (desktop + Android, x legacy/new config) | `docs/phase4-5-migration-matrix.md` | Every cell has an expected result |

**Exit gate:** an upgrade from the current release changes nothing for the user; the new provider
UI is the only way keys are written.

---

## Track 6 - Cleanup gates (from spec 13)

Gates **A, B, E** are conditionally approved; **C, D, F** are not approved in this phase.

| Gate | Target | Precondition | Reversibility |
|---|---|---|---|
| A | `ui/provider_selector.py` (desktop duplicate) | **Already safe** - it is a 38-line stub with no importer anywhere | Restore the file from git |
| B | Legacy plaintext `api_keys.json` **writes** | T1.1 + T5.1 merged | Re-enable the writer; the file still exists |
| C | `core/local_brain.py` relocation | **DEFERRED** - protected path | n/a |
| D | Legacy LLM client deletion (`llm_client.py`, `or_client.py`, `groq_client.py`, `agent/llm.py`) | **DEFERRED** - load-bearing until T2.3 | n/a |
| E | `ProviderSelector.kt` (Android duplicate) | T3.7 merged | Restore the file + the onboarding route |
| F | `home_assistant` provider records | **DEFERRED** - see spec 13 F | n/a |

---


## Track 7 - Reconcile `todo.md` with reality

`todo.md` is the project's tracker; leaving it stale guarantees the next session repeats this
audit. Each item below is a specific correction, with the evidence.

| ID | Type | Task | Where | Done when |
|---|---|---|---|---|
| T7.1 | [BUG] | Correct `:129` - "test-connection removed per user". Test Connection **exists** on both surfaces (`settings_pages.py:279`, `CloudProviderEditor.kt:226`). Restate the decision as open (D5). | `todo.md:129` | The line no longer asserts a false fact |
| T7.2 | [BUG] | Correct `:129` - "Android `ProviderSelector.kt` integrated into `SettingsScreen.kt`". It is **not**; `SettingsScreen.kt:88` -> `CloudProvidersDetail` -> `CloudProviderEditor`. `ProviderSelector.kt` is onboarding-only. | `todo.md:129` | The line names the file that is actually used |
| T7.3 | [BUG] | Correct `:129` - "desktop parity scaffold `ui/provider_selector.py`". It is a dead 38-line stub with no importer. | `todo.md:129` | The line reflects that it is unused (and Gate A removes it) |
| T7.4 | [BUG] | Correct `:132` - "Actions: Test connection Â· Save Â· Forget" are **already implemented** on both surfaces. Move to a verification checkbox, not a to-do. | `todo.md:132` | The line is a `[x]` with evidence |
| T7.5 | [BUG] | Correct `:151` - "kills 5 LLM paths". It is **six**: add `agent/llm.py`'s env-var key source, and note `agent/router_policy.py` is a target-helper, not an LLM path. | `todo.md:151` | The count and the list are right |
| T7.6 | [BUG] | Correct `:143` "Keys never displayed plaintext after save" - it is **currently violated on Android** (`ProviderSelector.kt:50` prefills the decrypted key). Keep it as a failing to-do with a pointer to T3.6/T3.7. | `todo.md:143` | The line says "fails until T3.7" |
| T7.7 | [BUG] | Add the missing Phase 4 items this audit found: routing is **saved but never read** (`settings_pages.py:406` writes, nothing consumes); desktop provider config is **never read by chat**; Anthropic/Gemini have **no desktop chat path**; Android `params` are **string-typed**. | `todo.md` Phase 4 section | All four are tracked as to-dos |
| T7.8 | [NEW] | Add a `docs/phase4-5-tasks.md` link at the top of the Phase 4 and Phase 5 sections of `todo.md` | `todo.md` | The tracker points at the task list |
| T7.9 | [BUG] | Note the **seventh** LLM-ish artefact: `core/llm_router.py` already defines a `ProviderRouter` with a conflicting schema and no consumers. `todo.md:151` does not mention it. | `todo.md:151` | The line names the existing router and the decision (D11) |

**Exit gate:** `todo.md` no longer contains a statement contradicted by the code.

---

## Open decisions (must be resolved before Stage 1 starts)

| # | Decision | Recommendation | Impact if changed |
|---|---|---|---|
| D1 | Registry source of truth | Shared `config/providers.json`, consumed by Python **and** Kotlin | If it stays duplicated in two languages, the parity test becomes the only guard |
| D2 | Anthropic default wire format | **Native** `POST /v1/messages` + `x-api-key` + `anthropic-version: 2023-06-01` | An OpenAI-compat default would need Anthropic to expose one; it does not |
| D3 | Gemini default wire format | **OpenAI-compat** `.../v1beta/openai/chat/completions` + `Authorization: Bearer` (matches `core/cloud_config.py:172`) | The native `genai` SDK path already works on desktop (`main.py:312`) but adds a dependency to Android |
| D4 | Android "Test Connection" scope | Test the **real** chat path (same wire format as production), not a synthetic ping | A synthetic OpenAI ping would keep reporting "OK" for Gemini/Anthropic while the actual chat fails |
| D5 | Test Connection - keep or remove? | **Re-decide.** `todo.md:129` says "removed per user", but the buttons exist on both surfaces. Recommendation: **keep** it, but make it test the **real** wire format (T3.11) | Removing it leaves the user no way to tell a bad key from a bad model name until a chat fails |
| D6 | Multi-provider on Android | Yes - migrate to an array (T3.1) | If it stays single-provider, Android fallback chains are impossible |
| D7 | Anthropic model catalogue | Anthropic has **no** `/models` endpoint. Ship a static list in the registry (`config/providers.json`) | A hard-coded list needs manual updates when Anthropic adds models |
| D8 | Desktop `api_keys.json` | Migrate-and-leave (never delete) | Deleting breaks any external tool that reads it |
| D9 | Scope of "kills 5 LLM paths" | **Six** paths. Interpretation: route all six through the router; **delete** none until the router is proven | Deleting `or_client.py`/`groq_client.py` early breaks `main.py` and `llm_client.py` |
| D10 | Key resolution ownership | One module, `core/providers/keys.py`, owns every key read (T1.11) | Four separate key sources today (`api_keys.json`, env vars, provider store, import-time snapshot) is the root cause of CORRECTION 1 |
| D11 | Which router survives? | **Evolve `core/llm_router.py` in place** and delete the other idea. It already owns the name `ProviderRouter`, already has `ordered()`/`complete()`/fallback logic, and is already referenced by the spec | Two routers = two config schemas = the same class of bug this whole phase exists to fix. If it is replaced instead, `core/llm_router.py` must be deleted in the same commit. |
| D12 | Where does the router live? | `core/providers/router.py` (new package, registry + adapters + keys + router together) and `core/llm_router.py` becomes a thin re-export | A flat `core/llm_router.py` that imports from `core/providers/` keeps both import paths working during the transition |

---


## Verification matrix (summary)

| Scenario | Desktop | Android |
|---|---|---|
| Save a Groq key, chat | T1.2 + T1.3 | T3.1 + T3.2 |
| Save a Gemini key, chat | T1.5 | T3.4 |
| Save an Anthropic key, chat | T1.4 | T3.3 |
| Key never shown after save | T0.6 | T3.6 + T3.7 |
| `params` keep JSON types | already true | T3.5 |
| Routing card changes the answer | T2.3 | T3.15 |
| Fallback chain actually runs | T2.2 | T3.8 |
| Broadcast == foreground answer | n/a | T3.10 |
| Legacy config still works | T5.1 | T5.2 |
| Schema validates the real file | T0.4 | T0.4 |
| Saved key works without restart | T1.9 | n/a (reads on each call) |
| Only one key-resolution path | T1.11 | T3.1 |
| Only one router / one config schema | T2.12 | n/a |
| No plaintext key on disk | T1.1 + T5.1 | T3.1 (Keystore) |
| All six LLM paths use the router | T2.9 + T2.10 + T2.1 | n/a |

---

## Suggested execution order

```
S1  T0.1-T0.7   foundation, no behaviour change      <- start here
S2  T1.1-T1.11  desktop key unification              <- the real fix
S3  T2.1-T2.12  desktop router (+ all six LLM paths)
S4  T3.1-T3.17  Android fixes
S5  (router on Android, mirroring T2)
S6  cleanup gates A, B, E only
S7  T7.1-T7.9   reconcile todo.md
```

Sign-off checklist (spec 17) plus: **D1-D12 resolved**, **T4.8/T4.9 green**, **T4.4 adapter
fixtures** locked in.

---

## Quick-start: the smallest change with the biggest impact

If only one thing gets done this cycle, do **T1.2 + T1.9** together:

```
core/providers/keys.py    -> resolve_key(provider_id) reading cloud_providers.json first,
                             falling back to api_keys.json
or_client.py / groq_client.py -> re-read the key per request instead of at import time
```

That single change makes the **desktop Cloud Providers UI actually work** for the first time -
the encrypted provider store becomes the live source of truth, and a saved key takes effect
without a restart. Everything else in Track 2 is then an enhancement rather than a rescue.

