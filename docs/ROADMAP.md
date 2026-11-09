# Roadmap — AGI Roadmap, Phases 1–5 (Complete)

Stella is a local-first assistant with an agentic loop, a tool registry, a planner, an executor, an error-recovery path, and skills that run on desktop and Android.

**Stella is not** an AGI, and no plan below makes it one on a schedule.

**Where Stella genuinely wins:** locality, privacy, cost, and autonomy. Stella runs with the network off, keeps user data on the device, and can act without a subscription.

**Where Stella genuinely loses:** raw reasoning compared to frontier cloud models. Stella routes to user-chosen providers (Gemini, OpenAI-compatible, Anthropic, OpenRouter, Groq, Ollama, LM Studio, custom) when the task warrants it.

**Strategy:** Become the best agent that runs on the user's own hardware and their own context, and become progressively stronger by routing to user-selected models when the task warrants it.

## Non-negotiables

These hold regardless of capability level:

1. **Local-first.** Personal data never leaves the device without explicit consent.
2. **Honest failure.** Report what failed. Never fabricate a result.
3. **User control.** Permissions are granted, never taken.
4. **Reversibility.** Every self-modification is versioned and revertible.
5. **Measured claims.** No improvement is claimed without a before/after number.

## Completed Phases 1–5

### Phase 1 — Measurement first ✅

Principle: an agent that is not measured is not improving, it is drifting. Build a local eval harness before any memory work.

- [x] Task suite: file ops, search, arithmetic, multi-step planning, failure recovery (`evals/tasks.py`, 13 tasks)
- [x] Runner that works fully offline against the local model (`evals/runner.py`)
- [x] Metrics: task success, tool-call accuracy, turns-to-success, tokens, latency
- [x] Regression gate: CI-ready baseline comparison (`evals/baseline.json`, 53.8% baseline)
- [x] Record every run to `evals/runs/<timestamp>.json`

Reference points: STATE-Bench measures whether an agent *finishes a task*; LoCoMo/LongMemEval measure whether it *recalls*. We care about the first.

Baseline: 7/13 passed (53.8%) — tools 100%, files 40%, planning 0%, robustness 67%.

### Phase 2 — Procedural memory ✅

Stores **reusable execution patterns** — how a task was actually solved — not facts.

- [x] Execution-trace store: (goal-shape, tool sequence, outcome, duration) — `src/backend/agent/procedural.py`
- [x] Retrieval by task similarity, not keyword overlap — shape-based + term overlap scoring
- [x] Success/failure labelling per trace — `record()` tags success/failure
- [x] Inject top-N traces into the system prompt, budgeted — `recall()` with budget_chars limit
- [x] Measure against Phase 1 baseline before and after — hook into `AgentExecutor.execute()`

### Phase 3 — Self-improvement loop ✅

The ACE / "Dreaming" pattern: record what happened, reflect, rewrite the agent's own playbook.

- [x] Outcome recorder: every task ends with success / partial / failure + why — `AgentExecutor` records via `proc_record()`
- [x] Reflection job (scheduled, not hot-path): cluster failures, extract patterns — `src/backend/agent/reflection.py`
- [x] Playbook store: versioned instruction fragments — `version_history()`, `revert()` in procedural.py
- [x] Every change version-controlled and revertible — append-only JSONL, superseded never deleted
- [x] Guardrail: reflection only reads/reports, never edits safety rules — documented in module docstring

### Phase 4 — Memory hygiene ✅

Memory hurts at large context if it injects noise; the *write* step is barely measured anywhere.

- [x] Write policy: not everything is worth keeping — `should_store()` (min 2 tool steps, non-empty goal, definite outcome)
- [x] Eviction and decay of stale facts — `decay_score()`, `decay_candidates()`, `_enforce_cap()` in procedural.py
- [x] Contradiction resolution (newer wins, but record the supersession) — `resolve_contradictions()`
- [x] Consolidation: merge duplicates — `consolidate_duplicates()` sums uses, merges notes
- [x] Injection budget: inject only what the task needs — `injection_budget()`, `recall()` budget_chars cap

### Phase 5 — Frontier routing ✅

How Stella gets stronger without pretending to be a frontier model.

- [x] Task triage: classify local vs frontier at request time — `src/backend/agent/frontier_router.py`
- [x] Cost/latency/privacy policy — local by default, frontier on explicit opt-in — `FORCE_LOCAL_KEYWORDS` always win
- [x] Provider abstraction already exists — `src/backend/core/providers/` (OpenAI-compatible, Anthropic, Gemini, local)
- [x] Frontier handles: deep reasoning, long synthesis, unfamiliar code — STRONG_FRONTIER_KEYWORDS
- [x] Local handles: everything touching personal data, always — FORCE_LOCAL_KEYWORDS

## Future Phase

### Phase 6 — Continual learning

Only meaningful once Phases 1–5 produce trustworthy traces.

- [ ] Fine-tuning pipeline on Stella's own successful traces
- [ ] Preference signals from the user (accept/reject/correct)
- [ ] Held-out eval to prove a fine-tune actually helped
- [ ] Per-user adapters, so the model specialises to one person

## What "better than existing agents" would require

Against a *local, private* agent: plausible within Phases 1–5. Against frontier cloud agents on raw capability: not achievable and not the goal.

The defensible claim:

> Stella performs the user's actual daily work, on their own hardware, with their own context, without a subscription — and gets measurably better at that specific set of tasks over time.

## Build & Release

Stella ships as:
- **Desktop:** Electron + SolidJS app connecting to a Python backend via WebSocket IPC (`ws://127.0.0.1:8765`)
- **Android:** Kotlin/Compose companion app connecting via StellaProtocol WebSocket
- **Backend:** Python with auto-discovered actions, plugins, and skills, frontier routing, procedural memory, reflection, and memory hygiene

No K2 model is bundled. Users download models themselves via the download hub in Settings if they want local inference. No private/public app distinction — single build per platform.
