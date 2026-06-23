## Context

The source research (`orchestrator-foundation.md`) specifies a headless, single-process multi-model orchestrator: a frontier-LLM planner emits a plan-as-DAG, an executor runs it over a worker pool behind LiteLLM, verifiers trigger local escalation, and an offline loop calibrates the planner. Its explicit non-goals were UI, streaming, and a closed/metered worker pool.

This change extends that foundation into a **local-first product** with three additions the research left out: users plug in their *own* backends (local models, API keys, **a Claude subscription**), they **watch** plans execute, and they **measure** the win on their own machine. The research's `Protocol`-based seams (`Planner`, `WorkerAdapter`, `Verifier`, `Synthesizer`) make most of this an extension rather than a rewrite — but three assumptions must bend: "everything is a LiteLLM target," "cost is USD," and "return the trace at the end."

The non-negotiable principles of the research (§0: two loops; pick-a-plan-not-a-mode; verifiers-as-trigger; hard budgets; perishable calibration; ordinal swappable workers) are inherited unchanged.

## Goals / Non-Goals

**Goals:**
- Run the full plan → execute → verify → escalate → synthesize loop locally, single-process, async.
- Let users register heterogeneous backends through one adapter interface, including a Claude Pro/Max subscription used as the conductor.
- Make the performance win **measurable and provable on the user's own pool**, anchored to Baseline A (orchestrating model X beats single-shot model X).
- Visualize both a single live run (animated DAG) and the aggregate proof (benchmark delta).

**Non-Goals:**
- Hosted multi-tenant SaaS on a shared subscription (ToS-disallowed); a future cloud tier uses API keys and charges fees.
- Beating a *frontier* model with a cheap *local* pool (Baseline B) — not claimed; the eval would expose it.
- A trained planner, LLM-judge verifiers, distributed execution, final-answer token streaming.

## Decisions

### D1 — Local-first, on-device; cloud is a separate API-fee tier
The Claude subscription path is the product's differentiator, and Anthropic explicitly disallows third-party subscription bridging ("does not allow third party developers to offer claude.ai login or rate limits for their products"). Using *your own* subscription on *your own* machine is supported automation; serving *other* users from one subscription is not. Therefore the product is a thing you run locally with your own auth. A hosted tier can exist later but must fall back to metered API keys and drop the subscription feature.
*Alternative rejected:* cloud-first SaaS — would forfeit the subscription feature or violate ToS.

### D2 — Multi-adapter SPI; LiteLLM is one adapter, not the gateway
The research's "everything is a LiteLLM target, no special path" cannot hold once a subscription (a CLI subprocess) and local servers are first-class. We define a `WorkerAdapter` SPI with concrete kinds:
- `litellm` — metered frontier/OpenAI-compatible APIs; cost in USD from token usage × price map.
- `claude_subscription` — drives `claude -p` headless (see D3).
- `local_openai` — Ollama/vLLM/LM Studio behind an OpenAI-compatible endpoint; cost ≈ wall-clock.

The planner still sees workers ordinally (`Model 0…k`) with capability metadata; the registry maps ordinal → adapter (§0.6 preserved).
*Alternative rejected:* force everything through a LiteLLM custom provider — a subprocess CLI with subscription OAuth and schema flags does not fit LiteLLM's request shape cleanly.

### D3 — Subscription via `claude -p` headless, NOT the Agent SDK
Verified against official docs: the **Agent SDK requires an API key** and cannot use subscription auth. **`claude -p` headless uses the active login**, with subscription OAuth as default and a long-lived token (`claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN`) for server use. The conductor adapter invokes:
```
claude -p --bare --output-format json --json-schema '<Plan schema>' --append-system-prompt '<planner prompt>'
```
`--bare` skips plugin/MCP/hook discovery (low overhead); `--json-schema` enforces strict `Plan` conformance. Per-invocation subprocess (~100–500ms startup) is acceptable for the *conductor* because it fires ~once per request.
*Alternative rejected:* Agent SDK (needs API key, defeats the subscription point); OpenAI-compatible proxy wrapper (ToS gray, reselling-shaped).

### D4 — Subscription is rate-limit-bounded; the budget governs its use, not a hard role lock
Subscription is metered in **prompts per rolling 5-hour window** (~225 Max 5× / ~900 Max 20×) plus a weekly cap — built for one interactive user. Orchestration multiplies calls (a plan with escalation = 10–30 worker calls), so the real hazard is *broad fan-out* onto the subscription, not subscription use as such. Policy: the subscription is the natural **conductor** (1 call/request) and **may also be assigned as a worker for select high-value steps when the task suits it** (e.g. a hard reasoning or synthesis step) — but never as a parallel fan-out target. The hard guard is the `max_subscription_prompts` budget axis (D5), which caps total subscription calls across *all* roles, so a runaway loop cannot silently drain the daily quota. The planner is instructed to prefer local/metered workers for breadth and spend subscription calls only where they earn it.
*Alternative rejected:* a hard conductor-only lock — it needlessly forfeits the subscription's quality on the few steps that benefit most, and the budget axis already provides the safety the lock was meant to give.

### D5 — Multi-axis budget generalizes USD
`Budget` gains typed axes: `max_spend_usd`, `max_wall_seconds`, `max_subscription_prompts` (plus existing `max_depth`, `max_react_steps`). Each adapter reports usage in its native unit; the enforcer caps each axis independently and stays the single non-bypassable gate (§0.4). For the planner's frugality reasoning, native units don't compare directly ($0.01 vs 3 GPU-s vs 1 prompt) — resolved in D10 (user-set axis weights).

### D6 — Baseline A is the performance anchor; verifiers are therefore core, not optional
The promise is "your model beats itself, measurably." That only has meaning where outputs are gradable. So verifiers move from optional polish to load-bearing: no verifier ⇒ no escalation ⇒ the loop degrades to the weaker decompose-and-merge (MoA) baseline (research §14). The product scopes its *win claim* to verifiable tasks. An "unverified mode" (decompose + synthesize, no escalation) may exist but is labeled weaker and makes no performance claim.

### D7 — RunTrace becomes a live append-only event stream
To animate execution, the executor emits typed events at every decision point — `plan_ready`, `step_started`, `worker_call`, `token` (optional), `verdict`, `escalation`, `budget_tick`, `step_done`, `synthesis`, `run_done` — over SSE/WebSocket. The final `RunTrace` (research §12) is just the event log replayed. This generalizes §12 without violating it; the executor remains the only place workers/verifiers are called.

### D8 — Dual visualizer
Two UI surfaces serve the two halves of "beat + visualize":
- **Live run**: React Flow DAG; nodes = steps, edges = `access` dependencies, badge = primitive; nodes animate pending → running → pass/fail → escalating; `replan` failures expand an inline sub-DAG; budget meters burn down.
- **Proof/benchmark**: reuses the measurement harness to run a held-out bank through each single worker vs the orchestrator and renders the delta ("78% vs 71% best single — on your pool") plus a calibration heatmap (model × task-type win-rate, with freshness/TTL).

### D9 — Tech stack
Backend: Python 3.11+, FastAPI, Pydantic v2, LiteLLM, tenacity, pytest/pytest-asyncio (per research §2). Frontend: Next.js/React + React Flow + SSE/WebSocket client. Persistence: in-memory + JSON to start, SQLite once measurement lands. Secrets: a local encrypted store (not plain env) since users paste API keys into a UI.

### D10 — Budget cost normalization: user-set axis weights, not a synthetic exchange rate
The planner compares costs across axes with no natural exchange rate ($ vs wall-clock vs subscription-prompts). Decision: the user sets per-axis **weights** (a tuning knob in the UI) and the planner minimizes the weighted sum; we do not fabricate a USD-equivalent for GPU-seconds or prompts. Default weights treat local wall-clock as cheap and subscription-prompts as scarce.
*Alternative rejected:* a single hardcoded "cost score" — it bakes in an exchange rate that is wrong for most users' hardware/plan mix.

### D11 — v1 ships `normal` + `replan`; `react` is deferred
`replan` (ADaPT-style failing-step recursion) carries the verifiable-task win; `react` targets steps interacting with an unpredictable external signal and is off the v1 critical path. Decision: implement `normal` and `replan` in v1; keep `react` reserved in the `Primitive` enum and plan schema but defer its executor to a later change, and instruct the planner not to emit `react` until then.

### D12 — `code_exec` sandbox: subprocess + rlimits in v1, behind a swappable boundary
Subprocess + CPU/mem/wall limits is the v1 isolation; the sandbox stays an explicit, swappable interface so a container/microVM backend can replace it later without touching callers. The *interface* is the load-bearing decision, not the v1 strength.

### D13 — Synthesizer policy: config, default "strongest available"
Passthrough for a single terminal step; for multi-step plans, a combining call whose worker is configurable, defaulting to the strongest available worker.

### D14 — Persistence: JSON through phase 5, SQLite at phase 7
In-memory + JSON files until the measurement loop lands; cut the calibration store and trace history over to SQLite at phase 7, when they begin needing queries.

## Risks / Trade-offs

- **Weak local workers can't beat a frontier model** → Anchor every claim to Baseline A (same-model). The eval surfaces B/C as per-task upside, never as a headline. Honest framing is the mitigation.
- **A weak conductor produces bad plans** (small local models struggle to emit valid structured plans) → Validate-and-retry once, then fail loudly; the UI warns when a low-capability model is assigned the conductor role and recommends the subscription or a strong API model.
- **Subscription rate-limit exhaustion** → `max_subscription_prompts` budget axis caps subscription calls across all roles and halts before overrun (D4); planner prefers non-subscription workers for fan-out; UI surfaces remaining 5-hour window budget.
- **`code_exec` runs model-produced code** → sandboxed subprocess + rlimits behind a swappable boundary (research §9); never execute outside the sandbox; treat as the primary security surface.
- **Subprocess overhead per `claude -p` call** → acceptable for once-per-request conductor; `--bare` minimizes it; do not use subscription for workers (D4).
- **BYO secrets at rest** → local encrypted store; never log keys; never send keys anywhere but the user's chosen provider.
- **Users skip verifiers and expect a win** → UX education: unverified runs are clearly labeled "no win measured"; the proof view requires verifiable tasks.

## Open Questions

All six initial open questions are resolved — see D4 (subscription as a selective worker), D10 (cost weights), D11 (`react` deferred), D12 (sandbox), D13 (synthesizer), D14 (persistence). Remaining downstream details, to settle during implementation rather than now:
- Default axis-weight values and how they surface in the tuning UI (D10).
- The criteria the planner uses to judge a step "high-value" enough to spend a subscription call on (D4).
