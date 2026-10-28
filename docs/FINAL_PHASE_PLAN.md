# Stella — Final Phase Pre-Launch Plan (slimmed)

This is the consolidated, de-duplicated plan for the final phase before app launch.
It merges: AGI_ROADMAP.md, phase4-5-provider-spec.md, phase4-5-tasks.md,
STELLA_SETUP.md, errors.md, settings.md, build.md, model-management.md,
release-notes.md, IOS_BUILD.md, and the todo.md Phase K tracker.

Status convention: `[x]` done · `[~]` in progress · `[ ]` pending · `[!]` blocked.

---

## 0. Honest starting position

Stella is a local-first assistant: agentic loop, tool registry, planner, executor,
error-recovery path, verified 0.9B local runtime. Not AGI. Wins on locality,
privacy, cost, autonomy. Loses on raw reasoning vs frontier cloud models.
Strategy: best on-device agent + route to frontier models when warranted.

---

## 1. What remains to build (final phase)

### 1.1 Provider integration (Phase 4/5) — in progress, highest priority

From phase4-5-provider-spec.md and phase4-5-tasks.md:

- [~] `core/providers/registry.py` — provider table (id, label, base_url, auth_style, wire_format, models_url, key_required) — 8 entries: groq, gemini, openai, anthropic, openrouter, ollama, lmstudio, custom
- [~] `core/providers/keys.py` — single key-resolution path (`resolve_key(provider_id)`), prefers encrypted `cloud_providers.json`, falls back to legacy `api_keys.json`
- [~] `core/providers/router.py` — `ProviderRouter.resolve(mode)` + `chat(mode, messages)`, ordered candidate chain, fallback, structured logging
- [~] Wire desktop chat path (`main.py:3771`) through router; keep legacy clients as wire implementations
- [~] Wire Android Gemini + Anthropic endpoints (`core/ProviderEndpoint.kt`)
- [~] Android `params` typed as JSON values (not strings)
- [~] Android `ChatPromptReceiver` shares `answerChain()` with foreground service
- [~] `config/cloud_providers.schema.json` — reconcile to runtime array format
- [~] `home_assistant` excluded from AI provider accessors
- [~] Tests: `tests/test_provider_router.py`, `tests/test_provider_keys.py`, `tests/test_cloud_config.py`, adapter fixtures
- [!] Cleanup gates A/B/E (dead scripts, legacy writes, dead UI scaffold) — approved but NOT yet committed
- [!] Gates C/D/F (legacy LLM clients, home_assistant relocation, ui.py split) — DEFERRED

### 1.2 Eval harness (AGI Roadmap Phase 1) — not started

- [ ] Task suite: file ops, search, arithmetic, multi-step planning, failure recovery
- [ ] Offline runner against K2
- [ ] Metrics: task success, tool-call accuracy, turns-to-success, tokens, latency
- [ ] Regression gate: CI fails if score drops below baseline
- [ ] Record runs to `evals/runs/<timestamp>.json`

### 1.3 Procedural memory (AGI Roadmap Phase 2) — not started

- [ ] Execution-trace store: (goal-shape, tool sequence, outcome, duration)
- [ ] Retrieval by task similarity
- [ ] Success/failure labelling per trace
- [ ] Inject top-N traces into system prompt, budgeted

### 1.4 Self-improvement loop (AGI Roadmap Phase 3) — partially done

`skill_forge.py` exists but the loop is open:
- [ ] Outcome recorder: every task ends success/partial/failure + why
- [ ] Reflection job (scheduled, between-session): cluster failures, extract patterns
- [ ] Playbook store: versioned instruction fragments the agent edits itself
- [ ] Version-controlled, revertible changes
- [ ] Guardrail: may only edit playbook, never safety rules

### 1.5 Memory hygiene (AGI Roadmap Phase 4) — not started

- [ ] Write policy: not everything worth keeping
- [ ] Eviction and decay of stale facts
- [ ] Contradiction resolution
- [ ] Consolidation: merge duplicates
- [ ] Injection budget

### 1.6 Frontier routing (AGI Roadmap Phase 5) — not started

- [ ] Task triage: local vs frontier at request time
- [ ] Cost/latency/privacy policy — local by default, frontier on opt-in

### 1.7 Continual learning (AGI Roadmap Phase 6) — not started

- [ ] Fine-tuning pipeline on successful traces
- [ ] Preference signals: accept/reject/correct (this is what the update skill feeds)
- [ ] Per-user adapters

### 1.8 Skill lifecycle management (new, this phase) — being built now

- [x] `features/skill_catalog/` — list/find/install/register/run skills (done)
- [ ] `features/skill_add/` — create new skill files from a spec (building now)
- [ ] `features/skill_build/` — validate/compile/run test_cases for a skill (building now)
- [ ] `features/skill_update/` — context-aware skill file updates from interaction (building now)

---

## 2. Skills still needing to be built

| Skill | Purpose | Status |
|-------|---------|--------|
| `skill_update` | Context-aware updates to existing skill files from user interaction (preferences, fixes, version bumps) | **Building now** |
| `skill_add` | Create new skill files (manifest/skill/test_cases/__init__) from a spec | **Building now** |
| `skill_build` | Validate/compile/run test_cases for a skill package; report results | **Building now** |

These three form a complete skill lifecycle: add → build → update.

### 2.1 Why these three

Per the AGI roadmap Phase 3/6 and errors.md "Fix it yourself": the agent should
reflect on interaction outcomes, record accept/reject/correct preference signals,
and rewrite its own skill playbooks (versioned, revertible). `skill_update` is
the write path; `skill_add` is the create path; `skill_build` is the verify path.
`skill_catalog` (already built) is the discover/run path.

---

## 3. Omitted features from the documents (not yet implemented)

From AGI_ROADMAP.md:
- [ ] Eval harness (`evals/runs/`) — Phase 1
- [ ] Procedural memory trace store — Phase 2
- [ ] Self-improvement reflection job + playbook store — Phase 3
- [ ] Memory hygiene (write policy, eviction, contradiction, consolidation) — Phase 4
- [ ] Frontier routing triage — Phase 5
- [ ] Continual learning / fine-tuning pipeline / per-user adapters — Phase 6

From phase4-5-provider-spec.md:
- [ ] Provider router unit tests (`tests/test_provider_router.py`)
- [ ] Key-resolution tests (`tests/test_provider_keys.py`)
- [ ] Cloud config encrypt/decrypt tests (`tests/test_cloud_config.py`)
- [ ] Adapter tests against recorded HTTP fixtures (`tests/fixtures/providers/`)
- [ ] Android JVM tests for params type round-trip, endpoint resolution
- [ ] Contract test mirroring `ThemeContractTest.kt` pattern

From STELLA_SETUP.md:
- [ ] Feedback → Issues → Updates loop end-to-end (structured reports, scrubbing, GitHub issue creation, changelog)

From errors.md:
- [ ] "Fix it yourself" — agent analyzes error and updates its own code (partially: `agent/error_handler.py` referenced but skill_update makes it concrete)

---

## 4. Non-negotiables (carried from AGI_ROADMAP)

1. Local-first — personal data never leaves device without explicit consent
2. Honest failure — report what failed, never fabricate
3. User control — permissions granted, never taken
4. Reversibility — every self-modification versioned and revertible
5. Measured claims — no improvement claimed without before/after number

---

## 5. Cleanup gates (from phase4-5-tasks.md section 9)

| Gate | Target | Approved? | Status |
|------|--------|-----------|--------|
| A | `scripts/watch_*.ps1` (dead dev scripts) | Yes | Not yet committed |
| B | Legacy plaintext `api_keys.json` writes | Yes | Not yet committed |
| E | `ui/provider_selector.py` (dead desktop scaffold) | Yes | Not yet committed |
| C | Legacy LLM client relocation | No — deferred | Deferred |
| D | `home_assistant` relocation | No — deferred | Deferred |
| F | `ui.py` module split | No — separate project | Deferred |

Dead working-tree deletions (already applied, uncommitted):
- `scripts/watch_all.ps1`, `watch_exe_public.ps1`, `watch_k2_apk.ps1`, `watch_k2exe.ps1`
- `stella-connect-android/.../core/K2Manager.kt`
- `core/k2_runtime.py` (shim re-exporting `core.engine_runtime`) — KEEP SHIM

---

## 6. Documentation to update / delete

### Update:
- `docs/settings.md` — describe shipped provider UI (not intended)
- `todo.md` — Phase 4 checkboxes reflect what was actually shipped; add link to `docs/phase4-5-tasks.md`
- `PHASE_K_EXTENSION.md` — mark A/B/D/N/O/P as implemented (already done)

### Delete (obsolete):
- `docs/IOS_BUILD.md` — iOS is "future plan, not a build"; the build.md/release-notes already cover mobile. Keep only if iOS work resumes.
- `docs/release-notes.md` — Android-specific; merge relevant build info into build.md, then retire.

### Keep:
- `docs/build.md`, `docs/errors.md`, `docs/model-management.md`, `docs/STELLA_SETUP.md`, `docs/AGI_ROADMAP.md`, `docs/phase4-5-provider-spec.md`, `docs/phase4-5-tasks.md`

---

## 7. Execution order (staged)

```
S1  Provider foundation (registry, keys, schema, home_assistant exclusion)
S2  Desktop key unification + router (all six LLM paths)
S3  Desktop UI completion (status line, fetch fix, error mapping)
S4  Android provider parity (endpoints, params types, answer chain)
S5  Skill lifecycle: skill_add, skill_build, skill_update (this phase)
S6  Eval harness + procedural memory (AGI roadmap Phases 1-2)
S7  Cleanup gates A, B, E + docs reconciliation
```

---

## 8. Sign-off checklist

- [ ] V1-V28 provider verification matrix green
- [ ] `pytest` matches baseline; `gradlew assembleDebug` succeeds; desktop launches
- [ ] `todo.md` no longer contains statements contradicted by code
- [ ] `docs/settings.md` describes shipped provider UI
- [ ] Skill lifecycle (add/build/update) compiles and smoke-tests green
- [ ] Cleanup gates A/B/E committed as separate, clearly-labelled commit
