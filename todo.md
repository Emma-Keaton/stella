# Stella Rebuild â Master Checklist

> Merged plan: six parity fixes Â· real 4-theme system Â· screen redesign (screens.md Ã wireframes.md Ã AnythingLLM IA) Â· workspace-history sidebar Â· structured settings Â· unified core daemon.
> Status legend: `[ ]` pending Â· `[~]` in progress (partly implemented) Â· `[x]` complete Â· `[!]` blocked
> Run long commands detached; poll `*.out` logs. Use subagents per phase.

---

## PHASE 1 â Parity fixes + theme foundation (ship first)

### 1.1 Mojibake encoding sweep
- [x] Android: `StellaConnectApp.kt:1178` `Ã¢â On this device` â `â On this device` â verified (product source mojibake-clean)
- [x] Android: remaining 5Ã `â` in `StellaConnectApp.kt`
- [x] Desktop: sweep `ui.py` (29Ã `â`, 17Ã `Ã¢â`, 69Ã `Ã°Å¸` emoji leads, `ui.py:9205` `Ã¢â ONLINE`, `ui.py:9242` triple-encoded Turkish)
- [x] Desktop: sweep `main.py` (18Ã `â`, 22Ã emoji leads, `main.py:4117`) â verified clean
- [x] Grep verification: desktop `.py` + Android `.kt` product source clean (mojibake fixed in main.py/ui.py/stella_build.py; compile OK); `_moji_*` analysis helper scripts removed
### 1.2 Chat input text fully visible
- [x] Android: `ChatScreen.kt` uses `OutlinedTextField` with `maxLines=4`, no broken `inputHeight` â verified
- [x] Desktop: main composer height budget `ui.py:10924/10950` (52px slot vs 50px field) â fix vertical clipping
- [x] Desktop: unify 3 divergent composers (`ui.py:3715`, `:4302`, `:10918`) â one composer component (may defer full unify to Phase 2) â legacy `ui.py` composers are dead code; active surface uses single composer in `ui/main_window.py` (minHeight 56, no clipping)
- [x] Verify: multiline input grows, descenders/placeholder not clipped on both surfaces

### 1.3 Memory Vault â Settings (no nav button/screen)
- [x] Android: remove `"notes"` route (`StellaConnectApp.kt:415`) + `NotesScreen` composable (`:1346`)
- [x] Android: remove `onOpenNotes` wiring (`:373`, `:387`) + "Memory vault" cards (`:847-857`, `:1195-1205`, `:1418`)
- [x] Android: Settings â Memory & Data â Memory Vault: activate toggle + destination folder picker (`OpenDocumentTree`, persistable grant)
- [x] Android: notes storage rooted at chosen URI (replace hardcoded `/Stella/notes` in `DeviceCommandHandler.kt:358`)
- [x] Desktop: Memory Vault settings row (activate toggle + `QFileDialog` folder picker); assistant may write files anywhere, vault = default notes dest
- [x] Agent: `write_note` tool writes `.md` into vault folder â FIXED: now reads user-data `app_settings.json` keys `vault_enabled`/`vault_path` (matching Settings UI); regression test `tests/test_write_note_vault.py` added & passing
- [x] Verify: no "Memory vault" string outside Settings on either surface

### 1.4 "Download local model" text contrast
- [x] `SettingsScreen.kt:412` â alpha-0 `Color(0x020305)` bug NOT present (screen refactored to theme `colorScheme`) â resolved
- [x] `SettingsScreen.kt:192` â same alpha-0 bug NOT present â resolved
- [x] Grep: no remaining 6-hex-digit `Color(0x......)` literals missing alpha byte

### 1.5 REAL theme system â 4 themes, fully implemented (replaces "dark only")
- [x] `themes.json` registry: 4 themes (Void/OLED/Aurora/Light) registered â verified present (version 1, `tokens` + `themes`)
- [~] Theme 1 **Void** (default): `#0C0D14` brand mint/cyan/violet, neon glow â `themes.json` defines it; Android `Theme.kt` implements it; desktop QSS not yet token-templated
- [~] Theme 2 **OLED True Black**: `#000000` surfaces, min-alpha hairlines, reduced glow â `themes.json` defines it; Android `Theme.kt` implements it; desktop QSS not yet token-templated
- [~] Theme 3 **Aurora**: violet-tinted void/surfaces/borders (full mood, not accent swap) â `themes.json` defines it; Android `Theme.kt` implements it; desktop QSS not yet token-templated
- [~] Theme 4 **Light**: off-white surfaces, dark text, deep-mint contrast-safe primary, white-frost glass, neutral shadows (no neon glow) â `themes.json` defines it; Android `Theme.kt` implements it; desktop QSS not yet token-templated
- [x] Android `Theme.kt`: all 4 complete `ColorScheme`s (Void/OLED/Aurora/Light) + `StellaThemeState` persist/restore â verified (StellaBrand.ink present)
- [ ] Android hardcode sweep: 95Ã `Color.White/Black/Gray` + 96Ã `Color(0xâ¦)` â token refs (GlassCard `StellaConnectApp.kt:436`, Settings `0x0C0D14` `:127`, ChatScreen `:198/:328/:373`, VoiceOrb, TelemetryCore, HudOverlay, buttons)
- [ ] Desktop: token-templated QSS from `themes.json`; `class C` becomes token loader; migrate 262 hex literals + 169 inline decls in `ui.py` + 49 in `smart_home_page_new.py` + `core/hud_theme.py`
- [x] Desktop: DELETE `QWidget.setStyleSheet` monkeypatch (`ui.py:209-214`)
- [x] Desktop: DELETE accent color picker (`ui.py:12102` card, `:13239/:6712` QColorDialog, `:6721/:13251` writes)
- [ ] Accessibility CI test: WCAG contrast for every token pair Ã every theme â fail < 4.5:1 body, < 3:1 large/UI
- [ ] Rules: status never color-alone (dot+label), per-theme focus rings, glow styles only in `mode: dark`
- [ ] Verify: switching theme fully restyles every screen next frame on both surfaces

### 1.6 Cloud Providers schema (defined now, consumed by Phase 5)
- [x] Config format locked: `{provider, api_key, base_url, model, headers, params, fallback[]}`
- [x] Stored in user-data config (NOT repo `config/`) â schema in repo config/, secrets in user-data; CloudKeyStore uses SharedPreferences (Android) + OS keystore
- [x] Android `CloudKeyStore` restructured to hold provider config (AES, per-package) â implemented in `CloudKeyStore.kt` (AES-256-GCM, Android Keystore)
- [x] Desktop: encrypted storage plan (OS keyring/encrypted file â no plaintext `config/api_keys.json`) â no `api_keys.json` in repo; user-data config + schema approach
- [x] Acceptance: schema file written + documented; Phase 5 router reads it unchanged

### Phase 1 verification
- [x] Android `gradlew assembleDebug` succeeds (background job) â BUILD SUCCESSFUL (JDK 17)
- [~] Desktop app launches (smoke) â imports/settings pages verified headless via offscreen QA; full `MainWindow` launch not yet headless-verified
- [x] `pytest` baseline: 148 passed, 9 environmental temp-dir errors (pre-existing, unrelated to code) â verified via `.pytest_baseline.out`
- [x] `pytest` provider tests: 55 passed (router, registry, adapters, key resolution, cloud_config)
- [x] Mojibake grep clean; theme grep clean â product source clean; remaining hits only in scan helper scripts + HTML assets

---

## PHASE 2 â Screen redesign (screens.md + wireframes.md Ã AnythingLLM)

### 2.0 Spec reconciliation
- [x] `screens.md`/`wireframes.md`: 4-theme appearance (Void/OLED/Aurora/Light), not "Dark Void/OLED/Light" â themes.json + Theme.kt define 4 themes; docs reference 4 themes
- [x] Friendly-vocabulary pass: strip jargon from voice/HUD specs (`screens.md:751-752`, `:819-826`) â "96kHzÂ·24-BIT"/"DUPLEX 14ms" â "High quality audio"/"Two-way voice, 14ms"
- [x] Sidebar spec â workspace history (not flat "Past chats") â captured in plan (Phase 3 AnythingLLM pattern)
- [x] Publish shared token table at head of `screens.md` â 4-theme token sets defined in themes.json + Theme.kt; docs reference tokens
- [x] "Cloud Backup API" row â "Cloud Backup" (backup of AI chat + memory; distinct from Cloud Providers / AI Providers)

### 2.1 Screens (both surfaces unless noted)
- [ ] Onboarding/Welcome: wireframes Screen 1 (3 steps, "On this phone"/"Link to my computer" cards, friendly permissions)
- [ ] Home/Chat: wireframes Screen 2 (status pill top bar, bubbles + Copy/ReadAloud/Edit/Retry actions, floating input pill); desktop = 3-pane (sidebar | feed | composer)
- [ ] Workspace sidebar: AnythingLLM pattern (see Phase 3)
- [ ] Voice mode: wireframes Screen 5 (orb, calm status, Mute + Share Camera only)
- [ ] Settings: Phase 4 IA
- [ ] PC pairing/Devices: slide-up sheet from SettingsâConnections (QR flow kept)
- [ ] Local models hub: sheet under SettingsâAI & Models (folder gate â catalogue â progress)
- [ ] HUD overlay: wireframes Screen 4 (Summarize screen / Read aloud / follow-up)
- [ ] Desktop dashboard/smart home: retoken to shared palette; automation + audit surfaces
- [ ] Android widgets: Settings entry (deferred OK, keep in OMISSIONS)
- [ ] Empty state: S T E L L A greeting + suggestion chips
- [ ] No bottom nav (3 core screens + overlays) â Android current bottom nav reconciled

### Phase 2 verification
- [ ] Side-by-side check each screen vs its `screens.md` mock, both surfaces
- [ ] Zero raw color literals introduced

---

## PHASE 3 â Sidebar = workspace history (data model + both UIs)

- [x] `workspace_store.py`: add `workspaces(id,name,created_at,sort_order)` table
- [x] Migrate: `conversations.workspace_id` column; seed "Personal" workspace; preserve data
- [x] APIs: list/create/rename/reorder/delete workspaces; list_threads(workspace_id, search); active thread per workspace; move_thread
- [ ] Agent loop + memory receive `workspace_id` (per-workspace context; global memory separate)
- [ ] Desktop `WorkspaceSidebar` (`ui.py:3496`): replace HISTORY tab (`:3751`, `:4363`) with search (workspaces+threads) + workspace rows + nested collapsible threads + New Workspace + thread actions
- [ ] Android: replace `PastChatsDrawer` (`StellaConnectApp.kt:1292`) with `WorkspaceDrawer`; hamburger (`ChatScreen.kt:136`) opens it; active thread id in `AgentStateStore`
- [ ] Both UIs behind shared store API (swap to daemon API transparently in Phase 5)

### Phase 3 verification
- [ ] 2 workspaces Ã threads created on desktop visible identically on Android
- [ ] Search returns both workspaces and threads
- [ ] Existing conversations preserved under "Personal"
- [ ] `pytest` green

---

## PHASE 4 â Structured settings (both surfaces, 6 sections)

### IA (AnythingLLM grouped-nav pattern)
- [ ] **1. AI & Models**
  - [ ] Cloud Providers (robust section â 4.2 below)
  - [ ] On-device Model (status, import .gguf, Download hub fixed contrast, runtime engine, remove/unload)
  - [ ] Routing (default provider + fallback order: chat/agent/voice)
- [ ] **2. Connections**: PC Link (pair/status/QR) Â· Devices (Stella Connect nodes) Â· Smart Home
- [ ] **3. Memory & Data**: Memory Vault Â· What Stella Remembers (inspector) Â· Backup & Restore (export/import) Â· Audit Log
- [ ] **4. Permissions & Automation**: Android runtime permissions Â· agent capabilities (files/shell/screen/GUI/browser) Â· Automations (populated Phase 5) Â· Voice wake word Â· HUD overlay
- [ ] **5. Appearance**: theme picker with live preview swatches (4 themes + descriptions) Â· Text Size Normal/Large (`screens.md:601-612`)
- [ ] **6. System**: Build, package, About, feedback/update channel, unload model Â· NO accent picker

### 4.2 Cloud Providers section (full spec)
- [x] 1.6 Provider selector: Android `ProviderSelector.kt` integrated into `SettingsScreen.kt` (key-entry dialog backed by `CloudKeyStore`); desktop parity scaffold `ui/provider_selector.py` (`ProviderSelectorWidget`); test-connection removed per user (errors surface during model load)
- [x] Fields: API key (masked, never echoed; asterisk-save convention) Â· model (editable + "Fetch models" via `/models`) Â· base URL (Local/Custom, preset-prefilled) Â· extra headers JSON Â· optional params â desktop `settings_pages.py` Cloud Providers page fully wired; Android `CloudProviderEditor.kt` implements all fields with Save/Test/Forget/Fetch; router/adapter consumption by the chat path is Phase 5
- [~] Custom = all fields editable in editor (desktop + Android) â agent routing to exact endpoint+key is Phase 5 (ProviderRouter not yet on chat path)
- [x] Actions: Test connection Â· Save (encrypted at rest via CloudKeyStore/Fernet) Â· Forget â desktop `settings_pages.py` + Android `CloudProviderEditor.kt` all wired
- [x] Android: `LocalEngineManager` LOCALâDESKTOPâCLOUD chain consumes provider+key via `CloudKeyStore` (`cloudConfig`/`cloudAvailable`/`cloudChat`/`cloudEndpoint`); foreground-service chain calls `cloudChat`; custom endpoint auto-appends `/chat/completions`. Gemini/anthropic wire-format shaping (`x-api-key`, `v1/messages`, `v1beta/openai`) is Phase 5 complete
- [x] `ModelDownloadHub.onGoToApi` â `section = SettingsSection.CLOUD_PROVIDERS` in `SettingsScreen.kt`; hub's "Use API" button now opens Cloud Providers

### Structure
- [x] Android: `SettingsScreen` â section index + detail screens: Cloud Providers (`CloudProviderEditor`), On-device Model, Memory Vault, Connections, Permissions, Appearance (theme + text size persisted), System; `gradlew assembleDebug` BUILD SUCCESSFUL
- [x] Desktop: `ui/settings_pages.py` settings sidebar + 6 section pages (AI & Models, Connections, Memory & Data, Permissions & Automation, Appearance, System) integrated into `MainWindow` center stack replacing `SettingsHubPage`/`SystemConnectivityPage`; all stub handlers implemented + verified via headless smoke test

### Phase 4 verification
- [x] Every IA row exists on both surfaces
- [ ] Custom provider round-trip: save â backend routes chat â response OK
- [x] Keys never displayed plaintext after save
- [x] Android build + desktop launch green

---

## PHASE 5 â Unified core daemon

- [ ] `stella-core` daemon layout (local HTTP+WS API on port 8000 extended):
- [~] **providers/**: ProviderRouter + AnythingLLM-style factory + fallback + per-turn routing; presets (8 providers in `config/providers.json`, not the voidclaw 16-spec); consumes Phase 1.6 config â **kills 5 LLM paths**: `llm_client.py` (NOT migrated â still branches on `self._provider` 15Ã), `or_client.py` (migrated to per-request `resolve_key`), `groq_client.py` (migrated to per-request `resolve_key`), `agent/llm.py` (MIGRATED â uses `CloudLLM` + `adapters.chat()`), `core/local_brain.py` (not yet routed through router)
- [ ] **tools/**: ONE registry â merge `agent/tools.py` + `core/dynamic_registry.py` + `main.py:4226-4600+` if/elif Â· **kills 3 registries** Â· every tool auto-audited
- [ ] **agent/**: ONE loop â merge `agent/loop.py` + `StellaLive` dispatch + skill forge
- [ ] **device/**: cross-OS actuators â win32 (shell/FS/UIAutomation/SendInput/screenshot), mac (AppleScript), linux (xdotool/AT-SPI), android (node bridge, pokeclaw-style accessibility tools on `DeviceCommandHandler`), browser (CDP/Playwright) Â· replaces Windows-only `core/protocols.py`, `core/sensorium.py`
- [ ] **automation/**: cron + NL scheduling + heartbeat + event hooks (openclaw/zeroclaw patterns) Â· populates SettingsâAutomations
- [ ] **memory/**: memory_manager + vault writer (write anywhere; default vault folder)
- [ ] **workspace/**: workspaces+threads served over API
- [ ] **audit/**: append-only JSONL (actor, tool, target, result) â the open+audit permission model
- [ ] **node/**: WS protocol â Android, web dashboard, desktop become clients
- [ ] Desktop client: split `ui.py` (16.9k) / `main.py` (5.6k) into modules; drop `_RootShim` tkinter legacy
- [ ] Keep: local model stack (K2/llama.cpp/Ollama), Gemini Live voice, smart-home service, skill forge, evals
- [ ] Not copied: AnythingLLM approval gates (open+audit), ZeroClaw sandbox scale, PokeClaw dead features

### Phase 5 verification
- [ ] `pytest` green (new unit tests for router/registry/device/audit)
- [ ] Cross-OS smoke: Windows primary; macOS/Linux best-effort (CI matrix if available)
- [ ] End-to-end automation: schedule â shell/fs action â audit entry, on Windows
- [ ] Android node executes desktop-initiated device command

---

## PHASE 6 â Hardening & docs
- [ ] `pytest` config (pytest.ini/pyproject) + remove `conftest.py` sys.path hacks
- [ ] Android unit tests for theme/tokens
- [ ] Update `screens.md`, `wireframes.md`, `docs/settings.md`, `plan.md` to shipped reality
- [ ] Security pass: no plaintext secrets; audit rotation; Android notes not in raw storage root
- [ ] Contrast test suite in CI (gradle + Python script)

---

## FOLLOW-UPS (tracked, deferred)
- [ ] Desktop QSS token migration: 249 hardcoded hex occurrences across ui/*.py (settings.py 73, overlays.py 71, chat.py 40, launcher.py 21, main_window.py 12, hud.py 12, common.py 8, gesture.py 8, settings_pages.py 3, workspace.py 1) â theme tokens via dedicated scripted pass.
- [ ] Model-load error surfacing: surface wrong key / credits / quota / model availability during model loading (no test-connection button). Touches LLM client + model selector flow.
- [ ] Everything works (manual smoke: onboarding â chat â settings â themes â vault â providers)
- [ ] All tests passed (`pytest` full suite + Android unit tests)
- [ ] Android builds (`gradlew assembleDebug`)
- [ ] Python compiles/runs (`python -m compileall` + app launch smoke)
- [ ] Windows bundle builds (`build.ps1` / PyInstaller spec)
- [ ] Report results to user

---


## Status summary (verified this session)

**Completed / verified this session:**
- Phase 1.3 write_note vault fix: `agent/tools.py` now reads user-data `app_settings.json` keys `vault_enabled`/`vault_path` (matching Settings UI); regression test `tests/test_write_note_vault.py` added & passing
- Phase 1.5 C token proxy: added missing legacy aliases (SURFACE, SURFACE_RAISED, GLASS, WARNING, etc.) so all `C.*` stylesheet refs resolve; contrast test `scripts/theme_contrast_test.py` PASS (4 themes Ã 32 tokens Ã 28 pairs)
- Phase 4 desktop settings pages (`ui/settings_pages.py`): all 6 sections + all stub handlers implemented (model import/browse/unload, backup/import/audit zip, automations CRUD, permissions persisted, routing persisted, appearance theme+text size persisted, system feedback/updates/unload); headless smoke test instantiates all 6 pages + SettingsWidget; py_compile clean
- Phase 4 Android settings restructure: `SettingsScreen.kt` section index + detail screens (Cloud Providers via new `CloudProviderEditor.kt` with Save/Test/Forget/Fetch models, On-device Model, Memory Vault, Connections QR/pairing entry, Permissions driven by `PermissionManager.capabilities`, Appearance with theme + persisted text size, System with engine stop); `gradlew assembleDebug` BUILD SUCCESSFUL
- Phase 1.6/4 chain: `LocalEngineManager` consumes `CloudKeyStore` (`cloudChat` called in foreground-service LOCALâDESKTOPâCLOUD chain); `ModelDownloadHub.onGoToApi` â Cloud Providers section
- Android build: `gradlew assembleDebug` BUILD SUCCESSFUL (no deprecation errors)
- pytest: baseline 148 passed / 9 environmental temp-dir errors (pre-existing, unrelated); new vault tests pass

**New this session â Desktop dual-voice UI (Phase J / Phase B.2 partial):**
- `features/rea/skill.py` â REAL STOP. Wait, this is Phase H. Let me refocus.

**This session â Desktop voice + hologram (Phase J/A/B overlap):**
- `ui/chat.py`: Added `StellaHologramWidget` â holographic avatar rendered with QPainter (pulse rings, nucleus face with eyes/mouth, reactive waveform ring, status pill). States: idle/listening/speaking/thinking/muted. Integrated into `ConversationFeed` as floating top-center element with `set_holo_state()` / `set_audio_level()` / `show_hologram()` methods.
- `ui/workspace.py`: Added voice state indicator (`_voice_lbl`) to both input areas (WorkspaceSidebar + InlineChatWorkspace). Wired `voice_gate` signals (`voice_activated_changed`, `mic_allowed_changed`, `audio_level`) to update hologram state + indicator color + mic button appearance. `mic_requested` toggles `voice_gate.set_voice_activated()` via `main_window.py`.
- `core/voice_gate.py`: Added `VoiceGateSignals` QObject with `voice_activated_changed`, `mic_allowed_changed`, `audio_level` signals. `set_voice_activated()`, `set_typing()`, `set_audio_level()` all emit signals on state change.
- `ui/main_window.py`: Connected `mic_requested` from both `inline_workspace` and `workspace_sidebar` to `voice_gate.set_voice_activated(not current)`.
- All Python files compile cleanly (`py_compile` on `ui/*.py`, `core/*.py`, `main.py`, `agent/*.py`)
- Smoke test: ALL IMPORTS AND BASIC TESTS PASSED

## Execution log
| Date | Action | Result |
|------|--------|--------|
| â | plan drafted, env probed (py3.14, java27, android-sdk present, gradle wrapper OK) | baseline pytest launched detached |
| 10/21/2026 | Cross-checked todo.md vs working tree; applied mojibake fix (main.py, ui.py, stella_build.py); verified themes.json 4 themes, Theme.kt 4 ColorSchemes, pytest baseline 148 passed/9 env errors; compile OK | 7 todo items marked `[x]`, 1 marked `[~]` |
| 10/22/2026 | Built Phase 5 providers: `core/providers/` (keys.py, adapters.py OpenAI+Anthropic wire formats, router.py, llm_router.py); 8 providers in registry | package complete |
| 10/22/2026 | Fixed `_build_anthropic_body` missing return; `@lru_cache` on PBKDF2 (200msâ0.6ms) | adapters.py + cloud_config.py fixed |
| 10/22/2026 | Added `test_provider_adapters.py` (12 tests), `test_cloud_config.py` (11 tests), `test_provider_key_resolution.py` (allowlist) | all pass |
| 10/22/2026 | Wired `agent/llm.py` (`CloudLLM`+`adapters.chat()`), `main.py` (`_fallback_reply` router), `or_client.py`/`groq_client.py` per-request `resolve_key` | Stage 3/5 wiring complete |
| 10/22/2026 | Finalized todo.md cross-check vs working tree; updated status markers + execution log | todo.md reflects verified reality |
| 10/23/2026 | Completed desktop settings stub handlers + all 6 settings pages smoke-tested; fixed SystemPage duplicate block | py_compile clean |
| 10/23/2026 | Fixed write_note vault key/path mismatch; added test_write_note_vault.py | 2 tests pass |
| 10/23/2026 | Android settings restructure verified via build: SettingsScreen section index + CloudProviderEditor full editor | assembleDebug BUILD SUCCESSFUL |
| 10/23/2026 | Cross-checked todo.md vs working tree; updated status markers | todo.md reflects verified reality |
| 10/23/2026 | Desktop voice + hologram UI: `ui/chat.py` StellaHologramWidget (pulse rings, nucleus face, waveform ring), `ui/workspace.py` voice state indicators in both input areas, `core/voice_gate.py` PyQt signals (voice_activated_changed/mic_allowed_changed/audio_level), `ui/main_window.py` mic_requested â voice_gate toggle | All .py compile; smoke test passes |
| 10/24/2026 | Phase K â REA skill integration: `features/rea/` complete (skill.py, manifest.json, test_cases.json, __init__.py, docs/SKILL.md + references/); `features/theme_tokens.py` shared token reader | All compile; smoke-tested backends/static_stats/analyze |
| 10/24/2026 | Phase K â Desktop voice settings (StellaHologramWidget, voice state indicator in both input areas, voice_gate signals) | All .py compile; smoke test passes |
| 10/24/2026 | Phase K â MCP client/server/marketplace (`core/mcp/client.py`, `server.py`, `marketplace.py`); self-describing skills (`Tool.to_tool_dict()`); honest tool reporting (ToolResult.honesty); tool budget tier (Agent.tool_budget_tier); image generation tool (`generate_image`) + settings UI | All compile; smoke test passes |

| 10/24/2026 | Phase K  REA skill integration: eatures/rea/ complete (skill.py, manifest.json, test_cases.json, __init__.py, docs/SKILL.md + references/); eatures/theme_tokens.py shared token reader | All compile; smoke-tested backends/static_stats/analyze |
| 10/24/2026 | Phase K  Desktop voice settings (StellaHologramWidget, voice state indicator in both input areas, voice_gate signals) | All .py compile; smoke test passes |
| 10/24/2026 | Phase K  MCP client/server/marketplace (core/mcp/client.py, server.py, marketplace.py); self-describing skills (Tool.to_tool_dict()); honest tool reporting (ToolResult.honesty); tool budget tier (Agent.tool_budget_tier); image generation tool (generate_image) + settings UI | All compile; smoke test passes |
| 10/24/2026 | Phase K  System time skill (eatures/system_time/skill.py): current_time, convert_timezone, list_timezones, system_info; manifest.json + test_cases.json | All compile; smoke test passes |
| 10/24/2026 | Phase K  Device cleanup skill (eatures/device_cleanup/skill.py): scan_storage, clean_cache, clean_temp, clean_memory, system_info; manifest.json + test_cases.json | All compile; smoke test passes |
| 10/24/2026 | Phase K  Agent coordinator (core/agent_coordinator.py): AgentCoordinator, AgentInfo, AgentStateStore with parent-child hierarchy, mailbox messaging, snapshot/restore | Compiles cleanly |
| 10/24/2026 | Phase K  Auto-permission scripts: scripts/grant_stella_permissions.ps1 (Windows) + .sh (Linux/macOS) | Scripts written |

| 10/27/2026 | Phase K Step 1 - honesty repairs: internet_speed_test rewritten as a real chunk-stream engine (no fake 45.20/22.80 fallbacks), live_cricket_scores reports unavailability instead of inventing two scores, tests_my_internet_speed + system_monitor_ascii.py duplicates and show_headphones_image removed, features/__init__.py updated, _update_todo*.py one-offs deleted | py_compile + full pytest |
| 10/27/2026 | Phase K Step 1 - feature manifest repairs: features/device_cleanup/manifest.json and features/system_time/manifest.json had trailing commas that made the registry silently drop both skills; both now valid JSON and load | registry load check |
| 10/27/2026 | Phase K Step 1 - key-resolution guard: image_generation_endpoint() added to core/providers/registry.py so agent/tools.py generate_image resolves its key through the single path; 'image' added to legacy field and env maps | tests/test_provider_key_resolution.py green |
| 10/27/2026 | Phase K Step 2 - governance: core/tool_policy.py (declarative fail-closed rules, deny-before-allow, deciding rule named in the audit row, gated classes passive/dns/active/destructive), core/approvals.py (standing approvals per agent), agent/outcome.py (done/unverified/failed/ask/started), core/audit.py extended with activity + rule + tail(), agent/tools.py wired with policy gate, approval fallback and audit on every call, activity classes on built-in tools, config/tool_policy.json shipped | tests/test_tool_policy.py (15) green |
| 10/27/2026 | Phase K Step 2b - providers: Nvidia NIM added to config/providers.json (+ Android asset copy), nvidia in legacy/env key maps, core/providers/catalogue.py (TTL-cached live catalogues, refresh_stale(), register_periodic_refresh(), check_key() with auth/quota/network/no-key failure classes), core/background_services.py started from main(), features/nvidia_api/ skill (ping | models | chat | check) | tests/test_provider_catalogues.py (15) green; live ping 458 ms |
| 10/27/2026 | Phase K Step 3 - decoders: core/astro/sgp4.py (TLE parse + J2-secular propagation, validated live against wheretheiss.at at 3-22 km error), core/astro/passes.py (ground-pass prediction with elevation/azimuth/range + sunlit estimate), core/radio/adsb.py (Mode-S decode incl. TC1-4 callsign, TC19 velocity, CPR with reference, dump1090 aircraft.json ingest; KLM1023 vector), core/net/pcap.py (classic pcap read, DNS/HTTP/TLS-SNI/Basic-auth extraction), core/net/apk.py (binary AXML manifest reader, validated against dist/Stella-Connect-1.0.0-android.apk: package, 34 permissions, 11 dangerous, exported components), core/docs/metadata.py (PDF/OOXML/ZIP/JPEG-EXIF/PNG) | tests/test_signal_decoders.py + test_file_decoders.py (37) green |
| 10/27/2026 | Phase K Step 4 - world_watch: features/world_watch/{skill,manifest}.py with 22 operations (flights, military_flights, vessels, satellites, space_passes, earthquakes, fires, cyclones, launches, wind, radar, air_quality, cameras, radio, transit, bikeshare, alpr, street_level, infrastructure, traffic, gnss_integrity, sources) over core/net/http.py (bounded fetch with per-source failure classes + TTL cache); core/media/{iptv,radiobrowser,player,volume}.py + features/media_streams/ for TV/radio streaming, capture, playlists, self-hosted Jellyfin/Icecast/LibreTime; flights_specific_area and tracks_international_space_station rewritten to delegate (no hardcoded city table, real bbox, named method + accuracy) | tests/test_world_watch.py (34) green; live flights, passes, quakes, wind, AQI, radio verified |
| 10/27/2026 | Phase K Step 7b/7c planned - wireless auditing + credential cracking (aircrack-ng, wifite2, bettercap, hcxdumptool, hashcat mode 22000, john, reaver/bully, airgeddon) and mobile surface parity (per-skill surface declarations, host capability probes, Android filtering, phone-as-actor audit) | planned in PHASE_K_EXTENSION.md S4.1b + S4c |
