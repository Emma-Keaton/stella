# Phase 4 / Phase 5 - Cloud Provider Integration & Cleanup Specification

Status: **DRAFT - for review before implementation**
Scope: Stella desktop (Python/PyQt6) + Stella Connect Android (Kotlin/Compose)
Source of truth: `todo.md` PHASE 4 / PHASE 5, `plan.md`, `docs/settings.md`, `docs/screens.md`

This spec turns the Phase 4/5 checklist into an ordered, **reversible** implementation plan:
every provider change lands and is verified *before* any legacy code, script, or file is deleted.
Deletion is never implied by an adjacent change - it is an explicit, separately-gated step.

---

## 0. Verified baseline (as of commit `2797f3e`, working tree dirty)

Everything below was confirmed by reading the tree, not inferred.

### 0.1 What already exists (do not rebuild)

| Area | Status | Evidence |
|---|---|---|
| Provider config schema (runtime) | Exists | `core/cloud_config.py` - `{provider, api_key, base_url, model, headers{}, params{}, fallback[]}` |
| Desktop encrypted store | Exists | `core/cloud_config.py` - Fernet, PBKDF2, `%LOCALAPPDATA%/StellaAI/config/cloud_providers.json` |
| Desktop 6-section settings IA | Exists **and wired** | `ui/settings_pages.py` -> `SettingsWidget` -> `ui/main_window.py:1765` added to `_center_stack` |
| Desktop Cloud Providers card | Exists | `ui/settings_pages.py:182-295` (`AIModelsPage._add_cloud_providers_section`) |
| Desktop provider actions | Exists | Save `:626`, Test `:550`, Fetch models `:474`, Forget `:677` |
| Desktop Routing card | Exists, **written but never read** | `ui/settings_pages.py:369-408` writes `app_settings["routing"]`; no reader anywhere |
| Android encrypted store | Exists | `CloudKeyStore.kt` - AES-256-GCM, Android Keystore, `stella_cloud_config` prefs |
| Android provider UI | Exists (cards + key dialog) | `ProviderSelector.kt`; rendered by `SettingsSections.kt:101` |
| Android `onGoToApi` | Exists | `SettingsScreen.kt:92` -> `SettingsSection.CLOUD_PROVIDERS` |
| Android cloud chat | Exists | `LocalEngineManager.cloudChat` (`LocalEngineManager.kt:962`) |
| Android cloud wiring | Exists | `StellaConnectForegroundService.kt:233` calls `cloudChat` |

### 0.2 The four real gaps (this is what the phase actually delivers)

**GAP-1 - Desktop provider config is write-only.**
`core/cloud_config.py` is read by exactly one production caller: `ui/settings_pages.py`.
`get_active_provider()` (`core/cloud_config.py:163`) - the function whose docstring says *"Get the
first configured provider (for Phase 5 router)"* - **has no production caller**. No chat path on
desktop ever consults the Cloud Providers card. Saving a provider changes nothing.

**GAP-2 - Desktop chat reads a different, older setting.**
`main.py:3771` reads `app_settings["default_ai_provider"]` and dispatches to `genai` (Gemini) /
`or_client` (OpenRouter) / `local_brain`. The new `routing` block written by the Routing card is
never read. Two parallel routing models, one live, one decorative.

**GAP-3 - The runtime format and the published schema disagree.**
`config/cloud_providers.schema.json` describes `{name, auth_type, endpoint, models[], key_env, status}`
wrapped in `{"providers": [...]}`. The runtime format is `{provider, api_key, base_url, model, headers{}, params{}, fallback[]}`,
unwrapped. `additionalProperties: false` in the schema would **reject every config the app actually writes**.
`todo.md` Phase 1.6 acceptance says *"Phase 5 router reads it unchanged"* - as written, that is impossible.

**GAP-4 - `home_assistant` is stored in the AI-provider store.**
`ui/settings_pages.py:915` saves a `home_assistant` config through the same `save_provider()`.
Since `get_active_provider()` returns `providers[0]`, a user who connected Home Assistant before
configuring an AI provider would get Home Assistant as their "active provider". Any router built on
`get_active_provider()` inherits this bug.

### 0.3 Provider coverage gap (affects both surfaces)

The OpenAI-compatible `chat/completions` shape covers `groq`, `openai`, `openrouter`, `ollama`,
`lmstudio`, `custom`. It does **not** cover:

- **`gemini`** - native `generativelanguage.googleapis.com` shape. The Gemini *OpenAI-compat* base
  URL exists in `core/cloud_config.py:PRESETS` (`.../v1beta/openai/`), and Android's
  `cloudEndpoint()` has **no `gemini` branch**, so it falls to the `else` branch and returns `null`
  (no base_url) -> cloud chat silently fails for Gemini on Android.
- **`anthropic`** - native `api.anthropic.com/v1/messages`, `x-api-key` header, `anthropic-version`
  header, different body shape.

Android `cloudEndpoint()` (`LocalEngineManager.kt:1004`) handles `groq`, `openai`, `openrouter`,
`ollama`, `lmstudio` and falls through to `custom`. **`gemini` and `anthropic` are broken.**
Desktop `PRESETS` lists `anthropic` as `https://api.anthropic.com/v1` - an OpenAI-shaped URL that
Anthropic's native API does not serve.

**This is the highest-risk item in the phase**: selecting Gemini or Anthropic and saving it
produces a config that looks correct and never answers.

### 0.4 Legacy LLM paths - the Phase 5 "kills 5 LLM paths" target

| Path | Live production callers | Destructive to remove? |
|---|---|---|
| `llm_client.py` | `main.py:92,353,384`, `discord_bot.py:36`, `skill_forge.py:341` | No - 4 callers |
| `or_client.py` | `llm_client.py:8`, `memory_manager.py:182,208`, `groq_client.py:235` | No - deep in memory |
| `groq_client.py` | `llm_client.py:9` + model list at `ui.py:11510`, `ui/settings.py:922` | No - UI reads `GROQ_MODELS` |
| `agent/llm.py` | `agent/loop.py:29,350`, `agent/integration.py:19`, `agent/__init__.py:33-37` | No - agent loop depends on it |
| `core/local_brain.py` | `main.py:30` + 12 sites, `ui.py:79,11404,11430,11454` | No - local inference + model mgmt |

**All five are load-bearing.** None can be deleted without first migrating every caller.
`core/local_brain.py` additionally provides the *local* inference path that `todo.md` Phase 5
explicitly says to **Keep** ("Keep: local model stack (K2/llama.cpp/Ollama)"). The Phase 5 note
*"kills 5 LLM paths"* refers to **consolidating them behind one router**, not deleting the files.
The spec resolves this: the router *absorbs* them; the modules become thin adapters; deletion is a
later, optional cleanup.

### 0.5 Current verification baseline

- `python -m compileall main.py ui core agent llm_client.py or_client.py groq_client.py` -> **exit 0**.
- `pytest tests/test_models_and_errors.py` -> **15 passed**.
- `pytest tests/test_stella_connect.py` -> 2 errors, `PermissionError` on the pytest temp dir -
  matches the documented pre-existing baseline ("148 passed, 9 environmental temp-dir errors").
- Full `pytest tests` exceeds the 30 s shell timeout in this environment; it must be run in
  background/batch during implementation, and compared against `.pytest_baseline.out`.

---

## 1. Scope and non-goals

### 1.1 In scope

1. Make the desktop Cloud Providers config **actually drive chat** (close GAP-1, GAP-2).
2. Make Android Gemini and Anthropic work; align provider coverage across both surfaces.
3. Reconcile `config/cloud_providers.schema.json` with the runtime format (close GAP-3).
4. Separate `home_assistant` from the AI-provider store (close GAP-4).
5. Make the Routing card real: per-mode (chat/agent/voice) provider selection with fallback.
6. Implement the Phase 4.2 field set on **both** surfaces: API key (masked, never echoed),
   model (editable + Fetch models via `/v1/models`), base URL (preset-prefilled), extra headers JSON,
   optional params.
7. Persist API keys encrypted at rest on both surfaces, and **never display them in plaintext
   after save** (explicit Phase 4 acceptance criterion).
8. Surface provider errors at model-load time (the deferred follow-up in `todo.md`).
9. Add unit/integration tests and a verification matrix.
10. Execute the gated cleanup workstreams in section 9.

### 1.2 Explicit non-goals

- **Not** building the `stella-core` daemon, the tools registry merge, the device/automation/
  memory/workspace/audit subsystems, or the `ui.py`/`main.py` module split. Those are Phase 5
  *beyond* provider integration and are out of scope here.
- **Not** deleting `llm_client.py`, `or_client.py`, `groq_client.py`, `agent/llm.py`,
  `core/local_brain.py` in this phase.
- **Not** changing the theme/token system, the workspace data model, or the screen redesign.
- **Not** adding OAuth cloud providers (`google_drive`, `onedrive`, `dropbox`) - the "Connect"
  buttons in `ProviderSelector.kt` remain non-functional and are labelled as such.
- **Not** touching `core/engine_runtime.py` / the `k2_runtime` rename or the deleted watch scripts
  except through the explicit gates in section 9.

---

## 2. Target architecture

```
                      +------------------------------------------------+
                      |            ProviderRouter (new)                 |
                      |  core/providers/router.py                      |
                      |  - resolve(mode) -> ProviderConfig chain        |
                      |  - per-turn attempt + fallback                  |
                      |  - ONE chat call site, per-wire-shape adapters  |
                      +----------------+-----------------------+---------+
                                       |                       |
                       +---------------v-------------+  +------v-------------------+
                       | DESKTOP (Python)           |  | ANDROID (Kotlin)         |
                       | core/cloud_config.py       |  | CloudKeyStore.kt         |
                       |  (Fernet, user-data dir)   |  |  (AES-GCM, Keystore)     |
                       | core/providers/adapter.py  |  | core/ProviderRouter.kt   |
                       | UI: ui/settings_pages.py   |  | core/ProviderEndpoint.kt  |
                       | Chat: main.py              |  | UI: ui/ProviderForm.kt   |
                       +-----------------------------+  +--------------------------+
```

**One shape, two adapters.** Both surfaces consume the *same* provider config document and the
*same* routing semantics. The wire format stays OpenAI-compatible where the provider supports it,
with explicit native adapters for Gemini and Anthropic.

### 2.1 Canonical provider document (runtime, both surfaces)

```
{provider, api_key, base_url, model, headers{}, params{}, fallback[]}
```

Unchanged from Phase 1.6. **Both surfaces already agree on this** - `CloudKeyStore.kt:27-45` and
`core/cloud_config.py` use identical field names. This spec preserves it.

### 2.2 Canonical routing document (new)

```
app_settings["routing"] = {
  "chat":  "Auto" | "Groq" | "Gemini" | "OpenAI" | "Anthropic" | "OpenRouter" | "Local",
  "agent": <same>,
  "voice": <same>,
}
```

The Routing card (`ui/settings_pages.py:380`) already writes exactly this shape and these labels.
**The spec keeps the labels as-is** to avoid a migration, and maps them to provider ids in one
place (section 2.4). "Auto" = first configured provider in the store, excluding non-AI providers.

### 2.3 Provider registry (single source of truth, both surfaces)

A table of provider descriptors drives UI population, endpoint derivation, auth style and model
listing. It replaces the four hardcoded lists that currently disagree:

- `core/cloud_config.py:PRESETS` (desktop base URLs)
- `ui/settings_pages.py:185` `PROVIDER_MAP` (desktop labels -> ids)
- `ui/provider_selector.py:7` `AI_PROVIDERS` (desktop scaffold, unused by the live card)
- `ProviderSelector.kt:19` `aiProviders` (Android ids)

**Desktop** - `core/providers/registry.py`:

```python
@dataclass(frozen=True)
class ProviderSpec:
    id: str
    label: str
    base_url: str          # default base URL ("" for custom)
    auth_style: str        # bearer | x-api-key | none
    wire_format: str       # openai | gemini | anthropic
    models_url: str | None # override for /v1/models; None = base_url + /models
    key_required: bool
```

**Android** - `core/ProviderRegistry.kt`: the same 8 entries, same ids, same labels.

The two tables are held in sync by a contract test (section 10), the same way `themes.json` and
`STELLA_TOKENS` are already kept in sync by `ThemeContractTest.kt`.

### 2.4 Routing label -> provider id

The Routing card writes labels ("Groq", "Google Gemini", "Local"). The router needs ids.
A single mapping resolves it; "Local" maps to the local engine, not to a cloud provider.

| Routing label | provider id / target |
|---|---|
| Auto | first configured AI provider, else local engine |
| Groq | `groq` |
| Gemini | `gemini` |
| OpenAI | `openai` |
| Anthropic | `anthropic` |
| OpenRouter | `openrouter` |
| Local | local engine (`core/local_brain.py` desktop, `LocalEngineManager` Android) |

"Local" is **not** a provider id, so it is excluded from the provider registry and from the
store. Selecting it never writes a provider config.

---

## 3. Data model & migration

### 3.1 Provider id, display label, auth style

| provider id | Label (desktop combo) | Display (Android) | Auth style | Wire shape |
|---|---|---|---|---|
| `groq` | Groq | Groq | `bearer` | OpenAI-compat |
| `gemini` | Google Gemini | Gemini | `bearer` | OpenAI-compat (default) |
| `openai` | OpenAI | OpenAI | `bearer` | OpenAI-compat |
| `anthropic` | Anthropic | Anthropic | `x-api-key` | OpenAI-compat (default) |
| `openrouter` | OpenRouter | OpenRouter | `bearer` | OpenAI-compat |
| `ollama` | Ollama (Local) | Ollama | `none` | OpenAI-compat |
| `lmstudio` | LM Studio (Local) | LM Studio | `none` | OpenAI-compat |
| `custom` | Custom (OpenAI-compatible) | Custom | `bearer`/`none` | OpenAI-compat |

Android currently lists raw ids (`groq`, `gemini`, ...) in `ProviderSelector.kt:19`; the desktop uses
display labels in `PROVIDER_MAP`. The spec normalises **both to provider ids** for storage and
display labels for UI (section 6.1).

### 3.2 `auth_style` and `wire_format` - new optional fields

Two new optional fields are added to the provider document:

```
auth_style:  "bearer" | "x-api-key" | "none"     (default "bearer")
wire_format: "openai" | "gemini" | "anthropic"    (default "openai")
```

Both are **optional and defaulted**, so existing configs keep working unchanged. `wire_format` is
derived automatically from `provider` when absent (`gemini` -> `gemini`, `anthropic` -> `anthropic`,
else `openai`). `custom` always stays `openai` unless the user explicitly overrides.

Backward compatibility: a config written by the current build (`{provider:"anthropic", ...}`) will
be read as `wire_format="anthropic"` and start working correctly with no user action.

### 3.3 Migration rules (additive, idempotent, non-destructive)

| From | To | Trigger | Action |
|---|---|---|---|
| Desktop: no provider file | - | first read | No-op; empty store |
| Desktop: config lacking `fallback` | adds `"fallback": []` | read | Fill default in memory |
| Desktop: config lacking `auth_style`/`wire_format` | adds derived values | read | Fill default in memory; **not** rewritten to disk until next Save (no disk churn on upgrade) |
| Desktop: `home_assistant` entry | stays in file, excluded from AI accessors | Phase 4 | Section 3.4 |
| Android: legacy `stella_cloud` prefs (`cloud_api_key`) | `stella_cloud_config` blob | `CloudKeyStore.load` | **Already implemented** (`migrateLegacyApiKey`) - verify only |
| Android: legacy `apiKey` set via `setApiKey()` | provider `custom` | existing | **Already implemented** - verify only |

### 3.4 `home_assistant` separation (GAP-4)

`home_assistant` is not an AI provider and must not appear in provider selection, the router's
candidate set, or `get_active_provider()`.

**Change:** `core/cloud_config.py` gains a predicate and a dedicated accessor.

```python
AI_PROVIDERS = frozenset({
    "groq", "gemini", "openai", "anthropic",
    "openrouter", "ollama", "lmstudio", "custom",
})

def is_ai_provider(provider_id: str) -> bool:
    return provider_id in AI_PROVIDERS

def load_ai_providers() -> list[dict]:      # ordered, excludes home_assistant
    return [p for p in load_providers_raw() if is_ai_provider(p.get("provider", ""))]

def get_active_provider() -> dict | None:   # now excludes home_assistant
    ai = load_ai_providers()
    return ai[0] if ai else None
```

**Migration:** `home_assistant` stays in the same file initially (no file format change, so no
data loss risk), but it is excluded from every AI-facing accessor. A later, optional cleanup
(Gate C3) may move it to `smart_home.json`; that is explicitly deferred.

**Effect:** the router can never select Home Assistant as an LLM.

---

## 4. Provider configuration & API-key handling

### 4.1 Desktop - storage

- Location: `%LOCALAPPDATA%/StellaAI/config/cloud_providers.json` (unchanged).
- Encryption: Fernet + PBKDF2-HMAC-SHA256, 100k iterations, per-machine salt in `.cloud_salt` (unchanged).
- Permissions: `0600` on POSIX; Windows inherits the user profile ACL (unchanged).
- Format: a JSON **array** of provider documents (unchanged - see 4.4 for the schema fix).

### 4.2 Desktop - API key lifecycle

| Action | Behaviour |
|---|---|
| Save with a key | Key written encrypted at rest. Form field cleared, placeholder becomes "Saved key (hidden)". |
| Save without a key | Previous key is **preserved** (`ui/settings_pages.py:640` already does this). |
| Load form | The key field is **never** populated with the real key; placeholder shows "Saved key (hidden)". |
| Forget | Provider document removed from the store (`delete_provider`). |
| Read for use | Only the router reads the decrypted key, via `load_provider()` / `load_ai_providers()`. |
| UI reveal button | The existing eye toggle (`ui/settings_pages.py:469`) reveals only what is typed in the field. It must **not** decrypt and display a stored key. |

**New requirement:** `load_providers()` currently masks `api_key` to `"********"` in the returned
dicts (`core/cloud_config.py:100`). `load_provider()` returns the **real** key. That asymmetry is
a footgun. The spec keeps it but makes the contract explicit in docstrings:
`load_providers()` = masked, safe for UI; `load_provider()` / `load_providers_raw()` = plaintext,
internal use only.

### 4.3 Android - storage & key lifecycle

- Storage: `SharedPreferences("stella_cloud_config")` key `config_blob`, value
  `Base64(iv || ciphertext)` (AES-256-GCM, Keystore-held key, alias `stella_cloud_cfg_key`).
  **Unchanged.**
- Key lifecycle mirrors desktop: never echoed back into the form after save. The
  "Update key" dialog in `ProviderSelector.kt:62` currently pre-fills `keyInput = cfg?.apiKey ?: ""`
  - this **puts the decrypted key on screen**. That violates the "keys never displayed plaintext
  after save" acceptance criterion and must be changed to start empty with a
  "Saved key (hidden)" hint, exactly like desktop.

### 4.4 Schema reconciliation (GAP-3)

`config/cloud_providers.schema.json` is rewritten to describe the **actual runtime document**:
a JSON **array** of provider documents.

Required per item: `provider`. Optional: `api_key`, `base_url`, `model`, `headers` (object of
string->string), `params` (object), `fallback` (array of string), `auth_style`
(`bearer`|`x-api-key`|`none`), `wire_format` (`openai`|`gemini`|`anthropic`).

Notes:
- The schema is a **descriptive contract for the runtime array**, so it can be validated against
  the real file with `jsonschema`. The previous `{"providers": [...]}` wrapper never matched
  anything the app wrote.
- `additionalProperties: true` at the item level (was `false`) so future optional fields do not
  break validation. Inside `headers`, values stay restricted to strings.
- `provider` enum includes `home_assistant` because that document genuinely lives in the same file.

### 4.5 Model discovery ("Fetch models")

- Endpoint: `base_url` + `/models` (OpenAI-compatible). For `gemini` the OpenAI-compat base
  `https://generativelanguage.googleapis.com/v1beta/openai/` is used, so `/models` works there too.
- Desktop already implements this in a `QThread` (`ui/settings_pages.py:474`). **Bug to fix:**
  the resolved `api_key`/`headers`/`base_url` computed at `:480-499` are **not** passed to the
  worker - line `:533` constructs `FetchWorker(base_url, self._api_key.text(), self._headers.text())`
  using the *raw* fields. The saved-key fallback therefore silently does not apply, and a user who
  saved a key and cleared the field gets an unauthenticated request. The worker must receive the
  resolved values.
- Android has **no** Fetch models. Add it to the provider form, using the same `/models` contract,
  with the key read from `CloudKeyStore` and never rendered.
- Failure handling: a non-200 must produce a readable error ("HTTP 401 - check your API key")
  rather than an empty combo box.

### 4.6 Test connection

- Phase 4.2 lists "Test connection" as a desktop action, but the Phase 1.6 note and the
  `todo.md` follow-up say *"test-connection removed per user (errors surface during model load)"*.
- **Resolution:** keep the desktop **Test connection** button (it is already implemented and
  Phase 4.2 explicitly lists it), but make the *primary* error surface the model-load path
  (section 4.7). Both paths share one error-formatting helper so the message is identical.
- Android: no test button. Errors surface at chat time, in the chat thread.

### 4.7 Error surfacing at model load

This closes the `todo.md` follow-up *"Model-load error surfacing: surface wrong key / credits /
quota / model availability during model loading"*.

A single mapping from HTTP status / exception to a human message, used by desktop Test
connection, desktop chat, and Android chat:

| Condition | Message |
|---|---|
| 401 / 403 | "Your API key was rejected. Check the key for <provider>." |
| 402 / 429 quota | "<provider> reports no credit / rate limit reached. Check your plan." |
| 404 | "That model is not available on <provider>. Check the model name." |
| 400 | "The provider rejected the request (check model name and params)." |
| timeout / connection error | "Could not reach <provider>. Check your connection." |
| 5xx | "<provider> is having trouble. Try again shortly." |

**Never** print the API key in an error, and never the full response body if it may echo the key.

---

## 5. Chat routing & fallback semantics

### 5.1 The router (new, desktop)

New module `core/providers/router.py`:

```python
class ProviderRouter:
    def __init__(self, config_store, settings): ...
    def resolve(self, mode: str) -> list[ProviderConfig]:
        """Ordered candidate chain for the given mode (chat|agent|voice)."""
    def chat(self, mode: str, messages: list[dict], **kw) -> RouterResult:
        """Try candidates in order; return the first success with provenance."""
```

`RouterResult` carries: `text`, `provider_id`, `model`, `attempts` (list of failures), so the UI
can say *which* provider answered and *why* the earlier ones were skipped.

### 5.2 Candidate chain construction

For mode `m`:

1. Read `app_settings["routing"][m]`. If absent, fall back to `app_settings["default_ai_provider"]`
   (legacy alias, section 5.3), else "Auto".
2. If the value is a concrete provider label -> that provider is **first** in the chain.
   - If that provider has no saved config -> it is **skipped** (with a recorded reason), and the
     chain continues. The chat must not fail because a routing label points at an unconfigured
     provider; it falls back.
3. If the value is "Local" -> the chain is `[local_engine]` only. No cloud fallback, because the
   user explicitly chose local.
4. If the value is "Auto" -> chain = all configured AI providers, in store order.
5. Append the configured provider's own `fallback` list (provider ids) after the primary, for
   explicit per-provider fallback ordering.
6. Append the local engine **last**, for "Auto" and for concrete cloud selections - local is the
   safety net when every cloud candidate fails.

De-duplicate the chain while preserving order.

### 5.3 Desktop chat wiring (closes GAP-1 and GAP-2)

The desktop currently has provider logic in three places. The spec introduces the router and
routes all three through it, **without** deleting the legacy modules in this phase:

| Call site | Today | After |
|---|---|---|
| `main.py:3771` chat path | `app_settings["default_ai_provider"]` -> `genai` / `or_client` / `local_brain` | `router.chat("chat", messages)`; the router internally calls the same legacy adapters |
| `main.py:2836` model-list/status | `app_settings["default_ai_provider"]` | `router.resolve("chat")` for the provider list; `default_ai_provider` still honoured as a **legacy alias** |
| `llm_client.py:71` `reload_settings` | `app_settings["default_ai_provider"]` | unchanged in this phase (see Gate C2) |

**Legacy alias rule:** if `app_settings["routing"]["chat"]` is absent, the router uses
`app_settings["default_ai_provider"]` if present, else "Auto". This guarantees that **every
existing user keeps their current behaviour** after upgrade - no silent provider switch. The
Routing card then becomes an override, not a replacement.

Mapping of the legacy value: `"Gemini"`/`"Google Gemini"` -> `gemini`, `"OpenRouter"` -> `openrouter`,
`"Groq"` -> `groq`, `"OpenAI"` -> `openai`, `"Anthropic"` -> `anthropic`, `"Local"` -> local engine.

**The legacy clients remain the wire implementations.** `genai` (Gemini native) and `or_client`
(OpenRouter) already work and are proven. The router calls them through a small adapter table:

```python
ADAPTERS = {
    "gemini":     GeminiAdapter(),      # google.genai, native
    "anthropic":  AnthropicAdapter(),   # x-api-key, /v1/messages
    "openai":     OpenAICompatAdapter(),
    "groq":       OpenAICompatAdapter(),
    "openrouter": OpenAICompatAdapter(),
    "custom":     OpenAICompatAdapter(),
    "ollama":     OpenAICompatAdapter(),
    "lmstudio":   OpenAICompatAdapter(),
}
```

This is the "one router, N adapters" shape Phase 5 asks for, without a risky rewrite of the
working clients.

### 5.4 Android chat wiring

Android already has the LOCAL -> DESKTOP -> CLOUD chain in
`StellaConnectForegroundService.answerLocally` (`:211-239`) and `LocalEngineManager.cloudChat`.

Gaps to close:

1. **`gemini` / `anthropic` endpoints** - add to `cloudEndpoint()` / introduce `ProviderEndpoint.kt`
   with a per-provider endpoint function and per-wire-shape request builder.
2. **`ChatPromptReceiver`** (`core/ChatPromptReceiver.kt`) calls **only** `LocalEngineManager.chat`.
   If no local model is present it logs "No model present" and returns - **no cloud fallback**.
   The chain is inconsistent between the foreground service and the broadcast receiver.
   Fix: route both through one shared `answerChain()`.
3. **`params` are typed `Map<String, String>`** on Android (`CloudKeyStore.kt:33`) but the desktop
   stores `params` as a JSON object with **numeric** values (`{"temperature": 0.7, "max_tokens": 2048}`
   - `ui/settings_pages.py:667` writes them from a JSON text field). On Android, `body.put(k, v)`
   with `v` as a String sends `"temperature": "0.7"` - a string where a number is required.
   **Fix:** `params` must be typed as a JSON value, not a string map, on both surfaces. Android:
   `params: Map<String, Any>`; the JSON parse must preserve numbers/booleans.
4. **Fallback chain is not implemented on Android** - `cfg.fallback` is parsed and stored but never
   used. Implement it: on failure, try the next id in `fallback`, then the local engine.
5. **No routing by mode on Android** - `LocalEngineManager._mode` is a single `StateFlow<String]`
   with "LOCAL"/"CLOUD". The spec keeps that string but adds a separate
   `ProviderRouter.resolve(mode)` for chat/agent/voice parity with desktop.

### 5.5 Fallback semantics (identical on both surfaces)

- A candidate is **skipped** when: no config, no API key (and the provider requires one), or the
  provider is explicitly unroutable ("Local").
- A candidate **fails** on: HTTP error, timeout, empty completion, or malformed response.
- Failures move to the next candidate. The final failure is reported with the full attempt list.
- A failed cloud attempt **never** silently produces an empty answer. The user always gets either
  a real answer or an explicit error.
- Local engine is the last resort for "Auto" and concrete-cloud selections; for an explicit
  "Local" selection there is no cloud fallback.

### 5.6 Observability

Every router decision is logged in a single structured line so a user can answer "why did it use
Groq instead of OpenRouter?":

```
provider_route mode=chat requested=Auto chain=groq,openai,local
provider_attempt mode=chat provider=groq model=llama-3.3-70b result=ok latency_ms=812
provider_attempt mode=chat provider=openai model=gpt-4o result=fail reason=http_429
provider_route_final mode=chat provider=groq attempts=2
```

- Desktop: `logging.getLogger("providers.router")`.
- Android: `Log.i("ProviderRouter", ...)` - no API keys, no message bodies, no auth headers.

---

## 6. UI / settings changes

### 6.1 Desktop - Cloud Providers card (`ui/settings_pages.py`)

The card already has provider combo, API key + reveal, model combo + Fetch, base URL, headers
JSON, params JSON, Test/Save/Forget. Changes:

1. Provider combo is populated **from the registry** (`core/providers/registry.py`), not the
   hardcoded `PROVIDER_MAP` literal. Labels stay identical, so no user-visible change.
2. Base URL is **prefilled from the registry** and shown/hidden per provider (visible for
   `custom`, `ollama`, `lmstudio`; visible-but-editable for others).
3. A **provider status line** shows the configured state: "Not configured" / "Configured -
   <model>" / "Configured - no model set".
4. **Save** now also writes `auth_style` and `wire_format` derived from the registry.
5. **Fetch models** uses the resolved key/base_url (bug fix, 4.5).
6. **Test connection** shows the mapped error message (4.7).
7. **Forget** clears the Routing override if it pointed at the forgotten provider, so the user is
   not left with a dangling selection. (Otherwise the router silently falls back - correct, but
   confusing; the UI should say so.)
8. A **"default for chat"** affordance is *not* added - the Routing card owns that. The Routing
   card is moved directly under Cloud Providers in the same section so the relationship is obvious.

### 6.2 Desktop - Routing card (`ui/settings_pages.py:369`)

1. The combo labels stay as they are today (`Auto`, `Groq`, `Gemini`, `OpenAI`, `Anthropic`,
   `OpenRouter`, `Local`) to avoid a migration.
2. Each combo gets a **status suffix** showing whether the selected provider is configured, e.g.
   "Groq (not configured)". Implemented by appending to the item text - the stored value remains
   the bare label.
3. A **fallback order** editor is added: an ordered list of provider ids used when the primary
   fails. It writes into the selected provider's `fallback` array in the provider document, so
   the fallback is per-provider (as the Phase 1.6 schema already models).
4. Reading `routing` is now meaningful (the router consumes it).

### 6.3 Android - Cloud Providers section (`SettingsSections.kt:86`)

Currently: `ProviderSelector` renders one card per provider, each with "Add key"/"Update key".

Changes:
1. Replace the per-provider card list with a **single provider form** matching the desktop:
   provider dropdown, API key (masked), model (+ Fetch models), base URL, headers, params.
   Rationale: the current card-per-provider design cannot express model/base_url at all, so a
   Gemini user cannot pick a model - which is exactly how the "saves but never answers" bug
   hides. **Parity with desktop is the requirement.**
2. The "Update key" dialog must **not** pre-fill the decrypted key (4.3).
3. `ProviderSelector.kt` keeps its function name and signature for compatibility, but delegates to
   the new form. The `google_drive`/`onedrive`/`dropbox` cards are removed from the AI-provider
   area (they are OAuth backup providers, not LLM providers) and their Connect buttons are
   disabled with a "coming soon" label.
4. The Android form shows the same **status line** as desktop.

### 6.4 Android - Settings screen (`SettingsScreen.kt`)

- `onGoToApi` already jumps to `SettingsSection.CLOUD_PROVIDERS` (`:92`). **Verified working** -
  the Phase 4 checkbox *"Wire `ModelDownloadHub.onGoToApi` -> jump to Cloud Providers section"*
  can be closed with no code change beyond confirming the anchor scrolls the section into view.
- No other screen changes are required for this phase.

### 6.5 Both surfaces - "model" is required for cloud providers

A provider saved without a `model` cannot answer a chat. The spec makes this explicit:

- Save is allowed (a key may be stored before the user picks a model), but the provider status
  line shows **"Configured - no model set"**, and the router **skips** a provider with no model
  when the mode requires chat (it is still usable for a manual "Fetch models" step).
- Rationale: silently sending a request with `model = <provider id>` (as Android's `cloudChat`
  does at `LocalEngineManager.kt:976`) produces a confusing 404 from the provider. Skipping with
  a clear reason is better.

---

## 7. Compatibility & migration guarantees

### 7.1 Guarantees

| # | Guarantee |
|---|---|
| G1 | A user with **no** provider config keeps their current chat behaviour exactly (legacy `default_ai_provider` path, then local brain). |
| G2 | A user with an existing provider config (from the current build) keeps their key, model, base URL, headers and params. The only change is that it now actually works. |
| G3 | No file format change. The provider file stays a JSON array; the schema file is corrected to match reality. |
| G4 | No destructive migration. Nothing is deleted, rewritten, or re-encrypted at upgrade time. |
| G5 | Both surfaces read and write the same document shape, so a config authored on one is valid on the other. |
| G6 | `home_assistant` keeps working (Smart Home card) and is excluded from the AI provider set. |
| G7 | The legacy `default_ai_provider` setting keeps working as a fallback when `routing` is absent. |
| G8 | Provider errors surface to the user instead of silently returning an empty answer. |

### 7.2 Migration sequence (idempotent, safe to run repeatedly)

1. Read providers via `load_ai_providers()` (excludes `home_assistant`).
2. For each, fill in-memory defaults for `fallback`, `auth_style`, `wire_format` if absent.
3. Do **not** write to disk during this step.
4. Write only when the user next presses Save.

### 7.3 Cross-surface interop

A config written on desktop and copied to Android (or vice versa) is valid, with one caveat:
`params` must preserve numeric types (5.4, item 3). Desktop already stores them as JSON values;
Android must be fixed to match.

---

## 8. Implementation sequence (staged, reversible)

Each stage is independently shippable and independently revertable. **No stage deletes anything.**

### Stage 1 - Foundation (additive, no behaviour change)
- 1.1 Add `core/providers/registry.py` (provider table).
- 1.2 Add `auth_style` / `wire_format` defaults to `core/cloud_config.py`; add `AI_PROVIDERS`,
      `is_ai_provider()`, `load_ai_providers()`; make `get_active_provider()` AI-only (GAP-4).
- 1.3 Rewrite `config/cloud_providers.schema.json` to match the runtime array (GAP-3).
- 1.4 Android: add `core/ProviderRegistry.kt` mirroring the Python registry.

*Exit criteria:* schema validates the real file; `get_active_provider()` never returns
`home_assistant`; no existing behaviour changes.

### Stage 2 - Desktop router (additive)
- 2.1 Add `core/providers/router.py` + adapters (`OpenAICompatAdapter`, `GeminiAdapter`,
      `AnthropicAdapter`).
- 2.2 Unit tests for chain construction, legacy alias, fallback order, `home_assistant` exclusion.
- 2.3 Wire `main.py:3771` chat path to `router.chat("chat", ...)`, keeping the legacy clients as
      the wire implementations.
- 2.4 Add the `providers.router` logger.

*Exit criteria:* desktop chat honours a saved provider; `default_ai_provider` still honoured
when `routing` is absent; local brain still answers when no provider is configured.

### Stage 3 - Desktop UI completion
- 3.1 Registry-driven provider combo + base URL prefills.
- 3.2 Fix the Fetch-models worker to use the resolved key/base_url.
- 3.3 Status line, error mapping (4.7), fallback-order editor, Routing status suffixes.
- 3.4 Save writes `auth_style`/`wire_format`.

*Exit criteria:* Save -> chat -> response round-trip works for every provider in the registry.

### Stage 4 - Android provider parity
- 4.1 `ProviderEndpoint.kt`: per-provider endpoints incl. `gemini` and `anthropic`; native
      request shapes (auth header + body).
- 4.2 `params` typed as JSON values, not strings (5.4 item 3).
- 4.3 Replace the Android card-per-provider UI with the desktop-parity form; stop pre-filling
      the decrypted key.
- 4.4 Android `ProviderRouter` with `fallback` support and per-mode resolution.
- 4.5 Unify `ChatPromptReceiver` and the foreground service onto one `answerChain()`.

*Exit criteria:* every registry provider answers a real chat on Android, or fails with a clear
message; the key is never shown in plaintext after save.

### Stage 5 - Observability, error surfacing, tests
- 5.1 Structured router logging on both surfaces.
- 5.2 Unified error mapping used by Test connection, desktop chat and Android chat.
- 5.3 Test suites (section 10).
- 5.4 Documentation updates: `docs/settings.md`, `todo.md` checkbox flips.

*Exit criteria:* the full verification matrix (section 11) passes.

### Stage 6 - Cleanup (gated, see section 9)
- **Only after** every gate in section 9 is green.

---

## 9. Cleanup gates (the ambiguous "delete" targets, separated)

The instruction to "delete" was ambiguous. It refers to **three unrelated things**. They are
separated here into independent workstreams, each with its own gate. **A gate opening in one
workstream never authorizes a deletion in another.**

### 9.0 Current working-tree deletions (already done, uncommitted)

`git status` currently shows these as deleted in the working tree:

| File | Referenced by | Verdict |
|---|---|---|
| `scripts/watch_all.ps1` | nothing (grep across `*.py`, `*.ps1`, `*.md`, `installer/Stella.spec`, `scripts/stella_build.py` returns no hits) | **Safe** - dead dev helper |
| `scripts/watch_exe_public.ps1` | nothing | **Safe** - dead dev helper |
| `scripts/watch_k2_apk.ps1` | nothing | **Safe** - dead dev helper |
| `scripts/watch_k2exe.ps1` | nothing | **Safe** - dead dev helper |
| `core/k2_runtime.py` (renamed -> `core/engine_runtime.py`) | `core/k2_runtime.py` still exists on disk as an untracked 762-byte **shim** re-exporting `core.engine_runtime` | **Keep the shim** - it is the compatibility path for `from core import k2_runtime` |
| `stella-connect-android/.../core/K2Manager.kt` | no `.kt` file references `K2Manager` | **Safe** - superseded by `LocalEngineManager` |

**Action:** these deletions are *already applied* and are unrelated to provider work. The spec
does not revert them, but it requires them to be **committed as a separate, clearly-labelled
commit** before provider work begins, so the provider diff is reviewable on its own.

The `core/k2_runtime.py` shim is **untracked** (`?? core/k2_runtime.py`). It must be `git add`ed
so it is not lost - it is the backward-compat path for `from core import k2_runtime`. Note that
`installer/Stella.spec:17` still mentions `core/k2_runtime.py` in a comment; that comment should
be updated to `core/engine_runtime.py`.

### Gate A - Dead dev scripts (SAFE, low risk)

**Scope:** `scripts/watch_all.ps1`, `scripts/watch_exe_public.ps1`, `scripts/watch_k2_apk.ps1`,
`scripts/watch_k2exe.ps1`.

**Pre-conditions (all must hold):**
- A1. Grep across the repo returns **zero** references to `watch_all`, `watch_exe_public`,
      `watch_k2_apk`, `watch_k2exe`. **Verified.**
- A2. `installer/Stella.spec` does not bundle them. **Verified.**
- A3. `scripts/stella_build.py` does not invoke them. **Verified.**
- A4. No documentation references them as required steps.

**Verification after deletion:** `python -m compileall scripts` passes; `installer/Stella.spec`
builds; a manual `build.ps1` produces a working exe.

**Reversal:** `git checkout -- scripts/`.

**Status: the gate is ALREADY satisfied** by the working tree. Commit as-is, separately.

### Gate B - Superseded Android `K2Manager.kt` (SAFE, low risk)

**Scope:** `stella-connect-android/app/src/main/java/com/stella/connect/core/K2Manager.kt`.

**Pre-conditions:**
- B1. Zero `.kt` references to `K2Manager`. **Verified.**
- B2. `AndroidManifest.xml` does not declare a component defined only in `K2Manager.kt`.
- B3. `gradlew assembleDebug` succeeds with the file removed.

**Verification after deletion:** `gradlew assembleDebug` green; the app boots; local-model
start/stop still works via `LocalEngineManager`; the HUD and foreground service still start the
engine.

**Reversal:** `git checkout -- <path>`.

### Gate C - Legacy LLM paths (DEFERRED, high risk - NOT in this phase)

**Scope (each is a separate sub-gate; none are approved by this spec):**
- C1. `llm_client.py`
- C2. `or_client.py`
- C3. `groq_client.py`
- C4. `agent/llm.py`
- C5. `core/local_brain.py`

**Current live callers (from section 0.4) - all must be migrated first:**

| Module | Callers that must be migrated before deletion |
|---|---|
| `llm_client.py` | `main.py:92,353,384`; `discord_bot.py:36`; `skill_forge.py:341` |
| `or_client.py` | `llm_client.py:8`; `memory_manager.py:182,208`; `groq_client.py:235` |
| `groq_client.py` | `llm_client.py:9`; `ui.py:11510` (`GROQ_MODELS`); `ui/settings.py:922` (`GROQ_MODELS`) |
| `agent/llm.py` | `agent/loop.py:29,350`; `agent/integration.py:19`; `agent/__init__.py:33-37` |
| `core/local_brain.py` | `main.py:30` + 12 call sites; `ui.py:79,11404,11430,11454` |

**Explicit blockers:**
- `core/local_brain.py` provides the **local** inference path that Phase 5 says to **Keep**.
  Deleting it removes on-device/loopback inference. **Not approved.**
- `groq_client.py`'s `GROQ_MODELS` list is read by two UI modules. Deleting the module without
  moving the model list breaks the desktop model dropdown.
- `agent/llm.py` is re-exported through `agent/__init__.py:33-37` as public API.

**Sub-gate C5 approval conditions (all required):**
1. Every caller in the table above has been migrated to the router or to an explicit local-engine
   module.
2. A grep for the module name returns **zero** hits in `*.py`, `ui/*.py`, `core/*.py`, `agent/*.py`,
   `installer/*.spec`.
3. The full `pytest` suite is green **and** the local-engine smoke test passes
   (load a local model, chat with it, unload it).
4. A desktop manual smoke: offline mode still answers; the model manager UI still lists models.
5. The replacement has been live for at least one full manual smoke cycle with a real local model.

**Reversal:** `git checkout -- <path>` (or revert the commit).

**Status: NOT APPROVED in this phase.** These modules become thin adapters behind the router
(sections 5.3, 5.4); deleting them is a separate Phase 5 decision.

### Gate D - `home_assistant` relocation (DEFERRED, optional)

**Scope:** move the `home_assistant` document from `cloud_providers.json` to
`smart_home.json` (or a dedicated store).

**Pre-conditions:**
- D1. The Smart Home card reads from the new store.
- D2. The old entry is copied, not moved, until the new path is verified - then removed.
- D3. A user with an existing `home_assistant` config keeps a working Smart Home connection.

**Status: NOT REQUIRED.** Section 3.4 already solves the *bug* (Home Assistant can never be
selected as an LLM) by excluding it at the accessor level. Relocating the file is cosmetic and
adds migration risk for no functional gain. **Recommended: skip.**

### Gate E - Dead UI scaffold `ui/provider_selector.py` (SAFE once superseded)

**Scope:** `ui/provider_selector.py` (`ProviderSelectorWidget`).

**Status:** it is a desktop parity scaffold that is **never imported** by the live settings UI
(only `ui/settings_pages.py` is used, and `ui/__init__.py:8` imports `settings_pages`, not
`provider_selector`). Grep confirms no importer.

**Pre-conditions:**
- E1. The desktop Cloud Providers card is complete (Stage 3 done) and the Android form matches
      (Stage 4 done), so the scaffold is genuinely redundant.
- E2. `ui/__init__.py` does not re-export it in a way other code relies on. **Verified: not
      imported.**

**Verification after deletion:** `python -c "from ui import StellaUI"` succeeds; the desktop
settings still open the AI & Models section.

**Status: approved for deletion only after Stage 4 completes.** Do not delete it before, or the
desktop loses its Android-parity reference implementation.

### Gate F - Legacy `ui.py` module (SEPARATE PROJECT - out of scope)

`ui.py` (15k+ lines, tracked) coexists with the `ui/` package. Python resolves `import ui` to the
**package** (`ui/__init__.py`), so the tracked `ui.py` is **dead code** - confirmed by
`importlib.util.find_spec('ui')` resolving to `E:\Projects\stella\ui\__init__.py`.

**This is a large, risky deletion and is explicitly NOT part of this phase.** It is listed here
only so it is not confused with the provider work. Recommendation: treat as its own Phase 5
workstream (matching `todo.md`: *"Desktop client: split `ui.py` (16.9k) / `main.py` (5.6k) into
modules"*).

---

## 10. Test plan

### 10.1 Desktop unit tests (new file `tests/test_providers_router.py`)

| Test | Asserts |
|---|---|
| `test_registry_matches_schema` | every registry id is in the schema `provider` enum; every id has a base_url (except `custom`) |
| `test_get_active_provider_excludes_home_assistant` | GAP-4 regression: a store containing only `home_assistant` returns `None` |
| `test_load_ai_providers_excludes_home_assistant` | ordering preserved, HA filtered out |
| `test_defaults_applied_for_legacy_config` | a config without `fallback`/`auth_style`/`wire_format` gets defaults in memory; file on disk is unchanged |
| `test_legacy_alias_used_when_no_routing` | G7: `default_ai_provider="OpenRouter"` with no `routing` -> chain starts with `openrouter` |
| `test_routing_overrides_legacy_alias` | `routing["chat"]="Groq"` -> chain starts with `groq` even if `default_ai_provider="OpenRouter"` |
| `test_local_selection_has_no_cloud_fallback` | "Local" -> chain is exactly `[local]` |
| `test_unconfigured_provider_is_skipped` | chain skips a provider with no saved config and continues |
| `test_fallback_order_appended` | provider's `fallback` list is appended after the primary |
| `test_chain_deduplicated` | no duplicate provider ids in the chain |
| `test_local_is_last_resort` | for "Auto", `local` is the final candidate |
| `test_router_falls_back_on_failure` | first candidate raises -> second candidate answers; `attempts` records the failure |
| `test_router_all_fail_returns_error` | every candidate fails -> explicit error, never an empty string |
| `test_error_mapping` | 401/402/429/404/400/5xx/timeout map to the documented messages |
| `test_error_message_never_contains_key` | the API key does not appear in any error string |
| `test_config_encrypted_at_rest` | the file on disk does not contain the plaintext key |
| `test_schema_validates_real_file` | `jsonschema.validate` passes on a written store |

### 10.2 Desktop integration tests

| Test | Asserts |
|---|---|
| `test_save_provider_then_router_resolves_it` | Save via `core.cloud_config.save_provider` -> `router.resolve("chat")` includes it |
| `test_forget_provider_removes_from_chain` | Forget -> the provider is gone from the chain |
| `test_home_assistant_saved_still_readable` | G6 regression: the Smart Home card can still load its token |

### 10.3 Android unit tests (new file `app/src/test/.../core/ProviderConfigTest.kt`)

| Test | Asserts |
|---|---|
| `test_config_roundtrip` | `CloudProviderConfig.toJson()` -> `fromJson()` preserves all fields |
| `test_params_preserve_numeric_types` | 5.4 item 3: `temperature` round-trips as a number, not a string |
| `test_legacy_config_defaults` | a config without `fallback` parses with an empty fallback |
| `test_endpoint_for_each_provider` | every registry id resolves to a non-null endpoint; `gemini` and `anthropic` included |
| `test_custom_endpoint_requires_base_url` | `custom` with no base_url -> null endpoint (no crash) |
| `test_known_providers_match_python_registry` | contract test: the Kotlin id list == the Python registry ids |

### 10.4 Android contract test

Mirror the existing `ThemeContractTest.kt` pattern: read `core/providers/registry.py` (or a
generated JSON) and assert the Kotlin registry matches, id for id, label for label. This is the
mechanism that prevents the Android/desktop provider drift that caused GAP-3.

**Preferred implementation:** add `config/providers.json` as the single generated source of
truth, imported by the Python registry and parsed by the Kotlin registry. A test asserts both
match the file.

---

## 11. Verification matrix

All rows must be **green** before any Gate A-E deletion is committed.

### 11.1 Behaviour preservation

| # | Check | Method | Pass condition |
|---|---|---|---|
| V1 | Existing local/Desktop behaviour intact | desktop manual smoke: offline mode, local model load, chat, unload | local brain answers exactly as before |
| V2 | Legacy `default_ai_provider` honoured | unit test + manual: set `default_ai_provider=OpenRouter`, no `routing` | chat uses OpenRouter |
| V3 | Existing provider configs survive upgrade | manual: configure a provider on the current build, upgrade, chat | same provider answers |
| V4 | Smart Home unaffected | manual: configure Home Assistant, open Settings > Connections | shows "Connected" |
| V5 | `pytest` green | `pytest tests` (background) vs `.pytest_baseline.out` | no new failures |
| V6 | Python compiles | `python -m compileall main.py ui core agent` | exit 0 |
| V7 | Android builds | `gradlew assembleDebug` | BUILD SUCCESSFUL |
| V8 | Desktop launches | `python main.py` | window opens, settings open |

### 11.2 New provider configuration works

| # | Check | Method | Pass condition |
|---|---|---|---|
| V9 | Desktop save -> reload persists | UI: save provider, restart app, reopen Settings | provider still configured, key not shown |
| V10 | Desktop schema validates the real file | `jsonschema.validate` on the written store | no error |
| V11 | Android save -> reload persists | UI: save provider, force-stop, reopen Settings | provider still configured, key not shown |
| V12 | Keys never shown in plaintext after save | manual, both surfaces | field is empty / masked placeholder |
| V13 | Android "Update key" does not pre-fill the key | manual | dialog opens empty |
| V14 | Fetch models works with a saved key | manual, both surfaces | model list populates (bug fix 4.5) |
| V15 | Provider status line accurate | manual | matches configured state |

### 11.3 Chat reaches the selected cloud provider

| # | Check | Method | Pass condition |
|---|---|---|---|
| V16 | Desktop: selected provider answers | configure Groq, chat | response; router log shows `provider=groq result=ok` |
| V17 | Desktop: Gemini answers | configure Gemini with a model, chat | response (GAP-3 / 0.3 closed) |
| V18 | Desktop: Anthropic answers | configure Anthropic with a model, chat | response |
| V19 | Desktop: Custom provider answers | point at an OpenAI-compatible endpoint, chat | response reaches that exact endpoint |
| V20 | Desktop: Ollama / LM Studio answer | local server running, chat | response |
| V21 | Android: Groq / OpenAI / OpenRouter answer | chat on device | response |
| V22 | Android: Gemini answers | chat on device | response (the 0.3 bug closed) |
| V23 | Android: Anthropic answers | chat on device | response |
| V24 | Android: Custom provider answers | chat on device | response |
| V25 | Android: `ChatPromptReceiver` reaches cloud | `adb shell am broadcast -a com.stella.connect.CHAT_PROMPT --es prompt "hi"` with no local model | response (5.4 item 2 closed) |
| V26 | Routing override honoured | set chat routing to a different provider | that provider answers (log confirms) |
| V27 | Fallback works | primary provider given a bad key | secondary provider answers; log shows the failure |
| V28 | All providers fail | bad keys everywhere | explicit error, **not** an empty reply |

### 11.4 Legacy paths have no remaining callers (only needed for Gate C)

| # | Check | Method | Pass condition |
|---|---|---|---|
| V29 | `llm_client` callers migrated | grep | zero callers (currently 4) |
| V30 | `or_client` callers migrated | grep | zero callers (currently 4+) |
| V31 | `groq_client` callers migrated | grep | zero callers (currently 3+) |
| V32 | `agent/llm` callers migrated | grep | zero callers (currently 4) |
| V33 | `local_brain` callers migrated | grep | zero callers (currently 16) |
| V34 | Local engine smoke | load a local model, chat, unload | works after migration |

**V29-V34 are red today and are expected to stay red in this phase.** They are the exit criteria
for Gate C, which is deferred.

---

## 12. Logging, validation & failure behaviour summary

| Concern | Rule |
|---|---|
| Key exposure | Never log, print, or display a decrypted API key. `load_providers()` masks; only internal accessors return plaintext. |
| Key storage | Encrypted at rest on both surfaces (Fernet / AES-256-GCM). |
| Error bodies | Truncate provider error bodies to 200 chars and strip anything that could echo the key. |
| Router logging | Structured, one line per decision; provider id + model + result + reason; never message content. |
| Missing config | A provider with no saved config is *skipped*, not an error. |
| Missing model | A provider with no model is *skipped* for chat, with reason `no_model`. |
| Invalid JSON in headers/params | Save is rejected with the parse error; the previous config is left untouched. (Desktop already does this at `ui/settings_pages.py:654`.) |
| Bad base URL | Save is rejected; the provider is not written. |
| Wrong key | HTTP 401/403 -> mapped message; the chat falls back to the next candidate. |
| No candidates at all | The chat returns the local engine if available, else an explicit "no provider configured" message. |
| Android missing config | `cloudChat` returns `null` (existing behaviour) -> the chain falls through. |
| Encryption unavailable | Desktop falls back to plaintext with `0600` (`core/cloud_config.py` `_HAS_CRYPTO` path) - unchanged, but it must be logged once at WARNING. |

---

## 13. Risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | Gemini/Anthropic endpoints are wrong -> "saves but never answers" persists | High (the current bug) | V17, V18, V22, V23 are mandatory gates |
| R2 | The legacy alias is dropped, silently switching existing users' provider | High | G1/G7; the alias is mandatory; V2 |
| R3 | Android `params` string-typing breaks temperature/max_tokens | Medium | 5.4 item 3; V21-V24 |
| R4 | The router is added but a caller is missed, leaving dead config | Medium | V16-V28 sweep across all surfaces |
| R5 | Deleting the legacy clients before migrating callers | Critical | Gate C sub-gates; V29-V34 |
| R6 | `home_assistant` selected as an LLM | Medium | GAP-4 fix + unit test + V4 |
| R7 | Schema change breaks a validator somewhere | Low | The schema is only descriptive; V10 |
| R8 | The Fetch-models worker bug is masked because the user re-types the key | Low | Fix + V14 |
| R9 | `ui.py` deletion removes still-used code | Critical | Gate F is a separate project; **not** in this phase |

---

## 14. Open decisions for review

1. **Provider registry source of truth** - a generated `config/providers.json` (recommended, keeps
   Python and Kotlin provably in sync) vs. two hand-maintained tables plus a contract test.
   *Recommendation: `config/providers.json`.*
2. **`wire_format` for Gemini** - the OpenAI-compatibility endpoint
   (`.../v1beta/openai/`) is simpler and uniform, but the native endpoint is more capable and
   already proven on desktop via `genai`. *Recommendation: default to OpenAI-compat for uniformity,
   but keep the native Gemini adapter available (it is already needed for `main.py`'s live path).*
3. **Anthropic default** - Anthropic's OpenAI-compat endpoint exists but is not universally
   available. *Recommendation: default `anthropic` to the native `/v1/messages` shape, and treat
   `wire_format` as an explicit override.*
4. **Whether "Test connection" survives** - Phase 4.2 lists it; the Phase 1.6 note removes it.
   *Recommendation: keep it on desktop (already built), drop it on Android, and make model-load
   errors the primary surface on both.*
5. **Gate D (`home_assistant` relocation)** - recommended to skip; the accessor-level fix is
   sufficient.
6. **Gate F (legacy `ui.py`)** - confirmed dead by import resolution, but a separate project.

---

## 15. Definition of done

- [ ] Stage 1-5 complete; Stage 6 not started.
- [ ] V1-V28 green; V29-V34 explicitly deferred with this spec as the reason.
- [ ] `config/cloud_providers.schema.json` validates the real provider file.
- [ ] `get_active_provider()` cannot return `home_assistant`.
- [ ] Gemini and Anthropic verified working on **both** surfaces.
- [ ] No API key is ever displayed in plaintext after save on either surface.
- [ ] The Android `params` numeric-type bug is fixed.
- [ ] `ChatPromptReceiver` and the foreground service share one answer chain.
- [ ] Router logs show provider selection, attempts and failures.
- [ ] `pytest` matches the baseline; `gradlew assembleDebug` succeeds; the desktop launches.
- [ ] `todo.md` Phase 4 checkboxes are updated to reflect what was actually shipped.
- [ ] `docs/settings.md` describes the shipped provider UI, not the intended one.

---

## 16. Coverage matrix vs `todo.md` (review gate)

This table is the cross-check the spec must pass before implementation starts.
"Status" reflects the **verified** state of the tree today, not an assumption.

### 16.1 Phase 4

| `todo.md` item | Verified status today | Spec section |
|---|---|---|
| 4. IA 1. AI & Models - Cloud Providers | Desktop card exists (wired); Android exists but is card-per-provider | 6.1, 6.3 |
| 4. IA 1. AI & Models - On-device Model | Desktop card exists (`_add_local_model_section`); Android has Download hub | out of scope (not provider work) |
| 4. IA 1. AI & Models - Routing | Card exists but **write-only** | 5.2, 6.2 |
| 4. IA 2-6 (Connections, Memory & Data, Permissions, Appearance, System) | All six pages exist and are wired (`ui/settings_pages.py`); the checkboxes are **stale** | out of scope |
| 4.2 Fields: API key masked/never echoed | Desktop OK; **Android leaks the key into the "Update key" dialog** | 4.2, 4.3 |
| 4.2 Fields: model editable + Fetch models | Desktop exists (with the resolved-key bug); **Android missing** | 4.5, 6.3 |
| 4.2 Fields: base URL preset-prefilled | Desktop OK; Android missing | 6.1, 6.3 |
| 4.2 Fields: extra headers JSON | Desktop OK; Android stores but never sends correctly | 6.1, 6.3 |
| 4.2 Fields: optional params | Desktop OK; **Android sends them as strings** | 5.4 item 3 |
| 4.2 Custom = all fields editable, agent routes to exact endpoint | Desktop base_url is editable; **no router consumes it** | 5.3, 5.4 |
| 4.2 Actions: Test / Save / Forget | Desktop all three exist | 4.6, 6.1 |
| 4.2 Android LOCAL->DESKTOP->CLOUD consumes provider+key | Foreground service does; **`ChatPromptReceiver` does not** | 5.4 items 2, 4 |
| 4.2 Wire `ModelDownloadHub.onGoToApi` | **Already wired** (`SettingsScreen.kt:92`) | 6.4 - verify only |
| 4.2 Android Settings section index + detail screens | Exists (`SettingsSections.kt`) | 6.3, 6.4 |
| 4.2 Desktop replace `SettingsHubPage` with sidebar + 6 pages | **Already done** (`ui/settings_pages.py` -> `ui/main_window.py:1765`) | out of scope - done |
| 4 Verification: Every IA row exists on both surfaces | Desktop yes; Android sections exist | 6.3 |
| 4 Verification: Custom provider round-trip | **Fails today** (no router) | 5.3, 5.4, V19/V24 |
| 4 Verification: Keys never displayed plaintext after save | **Fails on Android** | 4.3, V12/V13 |
| 4 Verification: Android build + desktop launch green | Baseline captured | 0.5, V7/V8 |

### 16.2 Phase 5

| `todo.md` item | Verified status today | Spec section |
|---|---|---|
| 5 `providers/` ProviderRouter, consumes Phase 1.6 config | Does not exist. `get_active_provider()` has **no caller** | 5.1-5.3 |
| 5 ProviderRouter "kills 5 LLM paths" | All 5 are **load-bearing**; 16 live callers | 0.4, Gate C (deferred) |
| 5 `tools/` one registry | Not provider work | out of scope |
| 5 `agent/` one loop | Not provider work | out of scope |
| 5 `device/`, `automation/`, `memory/`, `workspace/`, `audit/` | Not provider work | out of scope |
| 5 Desktop client split `ui.py` / `main.py` | Legacy `ui.py` is dead (package wins import) | Gate F (separate project) |
| 5 Keep: local model stack | `core/local_brain.py` is the local stack | Gate C5 (explicitly kept) |
| 5 Verification: pytest green, new unit tests for router | Router tests specified | 10.1-10.3 |
| 5 Verification: Android node executes desktop command | Not provider work | out of scope |

### 16.3 The three items this spec changes the plan for

1. **"Kills 5 LLM paths"** is reinterpreted as *consolidate behind one router*, not *delete the
   files*. Deleting them is deferred to Gate C with explicit pre-conditions. `core/local_brain.py`
   is protected outright.
2. **"Phase 5 router reads it unchanged"** is impossible as written, because
   `config/cloud_providers.schema.json` describes a different document than the runtime one.
   The schema is corrected to describe the runtime array; the runtime format is unchanged.
3. **"Delete"** is split into Gates A-F. Only A, B and E are ever approved, each with its own
   verified pre-conditions. C, D and F are explicitly not approved in this phase.

---

## 17. Review checklist (sign-off before implementation)

- [ ] Gap analysis (section 0) confirmed against the tree by a second reader.
- [ ] The interpretation of "kills 5 LLM paths" as consolidation-not-deletion is accepted.
- [ ] The schema rewrite in 4.4 is accepted as the fix for the Phase 1.6 acceptance wording.
- [ ] The `home_assistant` accessor-level fix (3.4) is accepted in place of file relocation (Gate D).
- [ ] The legacy `default_ai_provider` alias (5.3) is accepted as the upgrade-safety mechanism.
- [ ] Open decisions in section 14 are answered.
- [ ] The gate structure (section 9) is accepted, including which gates are *not* approved.
- [ ] The provider registry source of truth (section 14, decision 1) is chosen.
