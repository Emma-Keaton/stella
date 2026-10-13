# Stella — AGI Roadmap

Where Stella is, what is actually missing, and the order we build it in.

This document exists so the ambition is written down honestly and we can be
held to it. It is a roadmap, not a claim.

---

## 0. Honest starting position (read this first)

**What Stella is today:** a local-first assistant with an agentic loop, a tool
registry, a planner, an executor, an error-recovery path, and a verified 0.9B
runtime that runs offline on-device.

**What Stella is not:** an AGI. Not close, and no plan below makes it one on a
schedule. Anyone who tells you otherwise is selling something.

**Where we genuinely win today:** locality, privacy, cost, and autonomy. Stella
runs with the network off, keeps user data on the device, and can act without a
subscription. Frontier cloud agents cannot do that. That axis is real and worth
defending.

**Where we genuinely lose today:** raw reasoning. The bundled K2 model is 0.9B
class. It will lose to frontier models on hard multi-step reasoning, long
context, and anything requiring deep world knowledge. Benchmarks are explicit
that long-context baselines stay "highly competitive" against far more
elaborate memory systems.

So the strategy is **not** "out-reason the frontier on a phone." It is:

> Become the best agent that runs on the user's own hardware and their own
> context, and become progressively stronger by routing to frontier models when
> the task warrants it.

That is a real, achievable, and honest goal.

---

## Phase 0 — Foundation (current)

- [x] Agentic loop with bounded turns, repeat-detection, honest failure reporting
- [x] Tool registry with permission gating and workspace confinement
- [x] Local K2 runtime (0.9B) verified loading and serving on-device
- [x] Android + desktop + CI pipelines, K2-bundled and public variants

## Phase 1 — Measurement first

**Principle: an agent that is not measured is not improving, it is drifting.**

Build a local eval harness before any memory work. Otherwise every subsequent
claim — "this made it smarter" — is unfalsifiable.

- [ ] Task suite: file ops, search, arithmetic, multi-step planning, failure recovery
- [ ] Runner that works fully offline against K2
- [ ] Metrics: task success, tool-call accuracy, turns-to-success, tokens, latency
- [ ] Regression gate: CI fails if score drops below baseline
- [ ] Record every run to `evals/runs/<timestamp>.json` so we can diff over time

Reference points from current research: STATE-Bench measures whether an agent
*finishes a task*; LoCoMo/LongMemEval measure whether it *recalls*. We care
about the first. Retrieval scores are a proxy, not an outcome.

## Phase 2 — Procedural memory (highest evidence-weighted win)

The single largest measured gap. In the EvoMemBench comparison, **procedural
long-term memory was the top-performing family** (+14.5pp at 16K context),
beating both retrieval and general memory.

It stores **reusable execution patterns** — how a task was actually solved —
not facts.

- [ ] Execution-trace store: (goal-shape, tool sequence, outcome, duration)
- [ ] Retrieval by task similarity, not keyword overlap
- [ ] Success/failure labelling per trace
- [ ] Inject top-N traces into the system prompt, budgeted
- [ ] Measure against Phase 1 baseline before and after

Why this first: tool-use episodes benefit most from reusable execution
guidance — action routines, failure-aware strategies, parameter-filling
procedures. That is precisely what a personal assistant accumulates over time.

## Phase 3 — Self-improvement loop (outcome → reflection → instruction)

The ACE / "Dreaming" pattern: record what happened, reflect, rewrite the
agent's own playbook. Anthropic reported ~6x task-completion gains from a
scheduled between-session review.

- [ ] Outcome recorder: every task ends with success / partial / failure + why
- [ ] Reflection job (scheduled, not hot-path): cluster failures, extract patterns
- [ ] Playbook store: versioned instruction fragments the agent edits itself
- [ ] Every change version-controlled and revertible
- [ ] Guardrail: the loop may only edit its playbook, never its safety rules

Stella already has `skill_forge.py`. This closes the loop it currently leaves
open.

## Phase 4 — Memory hygiene

Research is blunt: memory **hurts** at large context if it injects noise, and
the *write* step is barely measured anywhere. Failure modes we must handle:

- [ ] Write policy: not everything is worth keeping
- [ ] Eviction and decay of stale facts
- [ ] Contradiction resolution (newer wins, but record the supersession)
- [ ] Consolidation: merge duplicates
- [ ] Injection budget: inject only what the task needs, never the whole store

## Phase 5 — Frontier routing

This is how Stella gets genuinely stronger than a 0.9B model without
pretending to be one.

- [ ] Task triage: classify local vs frontier at request time
- [ ] Cost/latency/privacy policy — local by default, frontier on explicit opt-in
- [ ] Provider abstraction already exists in `agent/llm.py` (`Backend`)
- [ ] Frontier handles: deep reasoning, long synthesis, unfamiliar code
- [ ] Local handles: everything touching personal data, always

## Phase 6 — Continual learning

- [ ] Fine-tuning pipeline for the local model on Stella's own successful traces
- [ ] Preference signals from the user (accept/reject/correct)
- [ ] Held-out eval to prove a fine-tune actually helped
- [ ] Per-user adapters, so the model specialises to one person

Only meaningful once Phases 1–3 produce trustworthy traces.

---

## Non-negotiables

These hold regardless of capability level. They are the product.

1. **Local-first.** Personal data never leaves the device without explicit consent.
2. **Honest failure.** Report what failed. Never fabricate a result.
3. **User control.** Permissions are granted, never taken.
4. **Reversibility.** Every self-modification is versioned and revertible.
5. **Measured claims.** No improvement is claimed without a before/after number.

## What "better than existing agents" would require

Stated plainly so we can be held to it. Against a *local, private* agent:
plausible within Phases 1–4. Against frontier cloud agents on raw capability:
not achievable and not the goal. The defensible claim is:

> Stella performs the user's actual daily work, on their own hardware, with
> their own context, without a subscription — and gets measurably better at
> that specific set of tasks over time.

That is a strong product. It is also achievable.