## Why

Frontier-quality answers usually mean paying frontier per-token prices or accepting a single model's blind spots. Research (Sakana's *Conductor*, ReWOO/LLMCompiler/ADaPT) shows that **decomposing a task into a planned DAG, running it over a worker pool, and escalating only on verifier failure beats single-shot use of the same model** — the win comes from plan topology + verification, not just routing. No tool today lets a user wire up *their own* models (local, API, or a Claude subscription), run this orchestration locally, **watch the plan execute**, and **measure the win on their own machine**.

This change establishes that tool: a local-first, bring-your-own-everything orchestrator whose promise is *"orchestrating your model beats using it alone — and here is the proof."*

## What Changes

- **A local-first orchestration runtime** that plans a task into a DAG of subtasks, executes it over a worker pool, verifies step outputs, escalates failing steps via local sub-plans, and synthesizes one answer. Single-process, async, runs on the user's machine.
- **A pluggable adapter layer** so users plug in their own backends. **BREAKING from the source spec's "everything is a LiteLLM target":** LiteLLM becomes *one* adapter among several. v1 ships three adapter kinds: metered API (LiteLLM), **Claude subscription via `claude -p` headless** (`CLAUDE_CODE_OAUTH_TOKEN`, `--json-schema`, `--bare`), and local OpenAI-compatible endpoints (Ollama/vLLM).
- **A conductor (planner) that is itself pluggable** — any strong model, including the Claude subscription, emits a strict JSON `Plan`. Reserved for the low-call-count planning role so it survives subscription rate limits.
- **Verifier-triggered escalation** (`code_exec`, `math_equiv`, `exact_match`) — the only thing that turns an unmeasured plan into a *measurable* win. No verifier ⇒ no escalation ⇒ no win claim.
- **A multi-axis budget enforcer** — generalizes per-token USD into USD **or** wall-clock **or** subscription-prompts, enforced centrally so a runaway loop cannot exhaust a daily quota.
- **An offline measurement + eval harness** — measures which of the user's plugged-in models wins which task type (calibration), and proves the orchestrator ≥ best single worker (the headline claim, **anchored to Baseline A**: orchestrating model X vs single-shot model X).
- **A live event stream** — the run trace becomes an append-only event log over SSE/WebSocket so a UI can animate execution in real time.
- **A local visualizer UI** with two surfaces: a **live animated DAG** (witness plan → execute → verify → escalate) and a **benchmark/proof view** (believe the "beats a model" claim numerically), plus registry/secrets config and parameter tuning.

### Non-goals (v1)

- Hosted multi-tenant SaaS on a shared subscription (Anthropic disallows third-party subscription bridging; cloud tier, if any, uses API keys and charges fees).
- Fanning worker calls onto a subscription (rate-limit suicide — subscription is conductor-only).
- A trained planner (Conductor GRPO recipe) — deferred; the frontier/subscription planner captures most of the gain.
- LLM-judge verifiers and non-verifiable domains as a *win* claim — escalation has no signal there; an unverified "decompose + synthesize" mode may exist but is labeled weaker, with no performance claim.
- Distributed multi-node execution; token-by-token streaming of the *final* answer.

## Capabilities

### New Capabilities
- `orchestration-runtime`: the executor control flow — plan → execute → verify → escalate (normal/replan/react primitives) → synthesize; context assembly from access edges; depth enforcement.
- `worker-registry`: the pluggable adapter SPI; ordinal worker exposure to the planner; capability metadata; the three v1 adapter kinds and connection testing.
- `conductor-planning`: the planner protocol; strict JSON `Plan` emission with validate-and-retry; calibration injection; subscription-conductor support.
- `verification`: the verifier registry and v1 verifiers; the sandboxed code-execution security boundary; verdicts as the escalation trigger.
- `budget-enforcement`: the multi-axis `Budget`, central non-bypassable enforcement, and `BudgetExceeded` halting.
- `calibration-and-eval`: the offline measurement harness, the calibration store with TTL/freshness, and the eval/proof mode (orchestrator vs best single worker, Baseline A).
- `run-observability`: the `RunTrace` model and the live append-only event stream (SSE/WebSocket) emitted at every executor decision point.
- `visualizer-ui`: the local UI — live DAG, benchmark/proof view, worker registry + secrets config, and parameter tuning.

### Modified Capabilities
<!-- None — greenfield project, no existing specs. -->

## Impact

- **New project**, greenfield. Python 3.11+ async backend (FastAPI, Pydantic v2, LiteLLM, tenacity) + a local web UI (Next.js/React, React Flow for the DAG, SSE/WebSocket for live events).
- **New external dependency surface:** the `claude` CLI (for the subscription adapter) and local model servers (Ollama/vLLM) are optional, user-supplied backends.
- **Security-sensitive surface:** `code_exec` runs model-produced code — sandboxed (subprocess + rlimits in v1) behind a swappable boundary; and a local secrets store for BYO API keys.
- **Persistence:** calibration store + traces (in-memory/JSON to start, SQLite once measurement lands).
