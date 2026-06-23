# Orchestrator Framework — Implementation Foundation

> **For:** Claude Code, as the foundation for a fresh implementation.
> **What this is:** an opinionated spec for a multi-model agent orchestrator. The runtime answers requests by writing and executing a plan over a pool of worker models; an offline loop measures which model wins which task and calibrates the planner.
> **Design lineage:** Sakana's *Conductor* (arXiv:2512.04388) for the plan-as-a-DAG idea, ReWOO / LLMCompiler / ADaPT for the up-front-plan-with-local-adaptation pattern. We are **not** training a model in the initial phases — the planner is a frontier LLM emitting a structured plan.

---

## 0. Read this first — non-negotiable principles

These are load-bearing. Do not refactor them away for convenience; they are the reason the design works.

1. **Two separate loops.** The **runtime loop** serves requests. The **measurement loop** runs offline and produces a calibration table. They share data structures but never run in the same call path. Keep them in separate packages.
2. **Pick a plan, not a mode.** There is no up-front "use ReAct vs plan-execute" classifier. The planner emits one plan; the *shape* of that plan (its step flags) determines how adaptive each step is. Adaptivity escalates **on a verifier failure during execution**, never on a prediction made beforehand.
3. **Verifiers are the trigger.** Escalation (replan / react) only fires when a step can be told it failed. A step with no verifier cannot escalate — it runs once. The framework is only as good as its graders.
4. **Hard budgets, always.** Every run carries a budget (max recursion depth, max react steps, max spend, max wall-clock). Unbounded adaptivity = infinite loops + runaway cost. Enforce centrally; a step cannot opt out.
5. **Calibration is perishable.** The calibration table is a cache with an expiry, not a constant. Never hardcode "model X is best at Y." Read it from the store; re-measure when a worker version changes.
6. **Workers are swappable and ordinal to the planner.** The planner sees models as `Model 0, Model 1, …` with capability metadata, not brand names, to avoid prior bias. The registry maps ordinals → concrete adapters.

If a requested change violates one of these, stop and flag it rather than implementing it.

---

## 1. Scope

### In scope (v1)
- A runtime that accepts a prompt, plans, executes over a worker pool, verifies, and synthesizes one answer.
- A plan representation supporting three step primitives: `normal`, `replan`, `react`.
- A worker registry abstracting frontier APIs and self-hosted open models behind one interface (via LiteLLM).
- A verifier registry (code execution, math equivalence, MCQ/exact-match to start).
- A budget enforcer.
- An offline measurement harness + calibration store.
- Full run tracing.

### Out of scope (v1 — explicit non-goals)
- Training/fine-tuning a planner model (that is a later, optional phase — see §13).
- A UI. Expose an API; building a frontend is separate.
- Streaming token-by-token output (return complete answers first; add streaming later).
- Distributed multi-node execution. Single-process async is the target.
- Non-verifiable domains. If the task has no automatic grader, the adaptive machinery has no signal — document this limit, don't paper over it with an LLM judge in v1.

---

## 2. Tech choices

- **Language:** Python 3.11+, fully type-annotated. `async`/`await` throughout — execution is I/O-bound on model calls.
- **Models gateway:** [LiteLLM](https://docs.litellm.ai) as the unified client for frontier providers. One `acompletion` call shape for everything.
- **Open-weight workers:** assume served behind an OpenAI-compatible endpoint (vLLM or a hosted provider). They are just another LiteLLM target — no special path.
- **Data models:** Pydantic v2 for schemas and validation (plans arrive as model-generated JSON; validate hard).
- **Config:** Pydantic `BaseSettings` + a `config.yaml`. No secrets in code; API keys via env.
- **API:** FastAPI, exposing an OpenAI-compatible `/v1/chat/completions` so existing tools point at it unchanged.
- **Sandbox (verifier):** subprocess with resource limits for code execution; design the interface so it can be swapped for a container/microVM later.
- **Tracing:** structured JSON logs + an in-memory `RunTrace` returned with every response (and persistable).
- **Testing:** `pytest` + `pytest-asyncio`. Mock workers for unit tests; a recorded-fixtures mode for integration.

Dependencies (initial): `litellm`, `pydantic>=2`, `pydantic-settings`, `fastapi`, `uvicorn`, `pyyaml`, `tenacity` (retries), `pytest`, `pytest-asyncio`.

---

## 3. System overview

```
                          ┌──────────────────── RUNTIME (online) ────────────────────┐
  prompt ──▶ Orchestrator ─▶ Planner ─▶ Plan ─▶ Executor ─▶ Verify ─▶ Synthesizer ─▶ answer
                 │                                  │  ▲           │
                 │                                  │  └─ escalate (replan/react) on fail
                 │                                  ▼
                 │                            Worker Registry ──▶ [frontier APIs | open models]
                 │                                  ▲
                 └──────── reads ── Calibration Store ◀──── writes ──┐
                                                                     │
                          ┌────────────── MEASUREMENT (offline) ─────┴──────┐
                          │  Harness: run each worker on verifiable tasks,  │
                          │  score per-model/per-subtask → Calibration table │
                          └──────────────────────────────────────────────────┘
```

The **Planner** reads the calibration table so its `assign` decisions are measured, not guessed. The **Executor** is the only component that calls workers and verifiers. The **Budget enforcer** wraps execution and can halt any run.

---

## 4. Project structure

```
orchestrator/
├── pyproject.toml
├── config.yaml
├── orchestrator/
│   ├── __init__.py
│   ├── types.py              # Pydantic models: Plan, Step, StepResult, Budget, RunTrace, WorkerSpec…
│   ├── config.py             # Settings, worker pool config, loading
│   ├── runtime/
│   │   ├── orchestrator.py    # top-level entrypoint: run(prompt) -> Answer
│   │   ├── planner.py         # Planner protocol + FrontierLLMPlanner (Phase 1)
│   │   ├── executor.py        # the dispatch loop; primitive handling; escalation
│   │   ├── synthesizer.py     # combine step results -> final answer
│   │   └── budget.py          # BudgetEnforcer, BudgetExceeded
│   ├── workers/
│   │   ├── registry.py        # WorkerRegistry: ordinal -> adapter, capability metadata
│   │   └── adapter.py         # WorkerAdapter (LiteLLM-backed); call(messages, cfg) -> text + usage
│   ├── verify/
│   │   ├── registry.py        # VerifierRegistry: name -> Verifier
│   │   ├── base.py            # Verifier protocol -> VerdictPass/Fail(score, detail)
│   │   ├── code_exec.py       # sandboxed execution verifier
│   │   ├── math_equiv.py      # symbolic / numeric equivalence
│   │   └── exact_match.py     # MCQ / exact answer
│   ├── calibration/
│   │   ├── store.py           # CalibrationStore: get/put per-(model, task_type) stats
│   │   └── table.py           # CalibrationTable model + freshness/expiry
│   ├── measurement/
│   │   └── harness.py         # offline: run workers over task bank, write calibration
│   ├── trace.py               # RunTrace assembly + serialization
│   └── api/
│       └── server.py          # FastAPI, OpenAI-compatible endpoint
├── tasks/                     # verifiable task banks for measurement + eval
└── tests/
```

---

## 5. Data model (`types.py`)

Implement these as Pydantic models. Field names matter — the planner is prompted to emit JSON matching `Plan`.

```python
from enum import Enum
from pydantic import BaseModel, Field

class Primitive(str, Enum):
    NORMAL = "normal"   # run once
    REPLAN = "replan"   # on verifier fail, spawn a local sub-plan for this step
    REACT  = "react"    # bounded observe→decide→act loop, this step only

class Step(BaseModel):
    worker_id: int                      # ordinal into the worker pool
    subtask: str                        # the tailored instruction
    access: list[int] | str             # upstream step indices visible here, or "all", or []
    primitive: Primitive = Primitive.NORMAL
    verifier: str | None = None         # name in VerifierRegistry; None => unverified, no escalation
    expected: str | None = None         # ground-truth handle for the verifier, if applicable

class Budget(BaseModel):
    max_depth: int = 2                  # recursion / replan depth
    max_react_steps: int = 4
    max_spend_usd: float = 0.50
    max_wall_seconds: float = 120.0

class Plan(BaseModel):
    reasoning: str = ""                 # planner CoT (kept for trace, not executed)
    steps: list[Step]
    budget: Budget = Field(default_factory=Budget)

class StepResult(BaseModel):
    index: int
    worker_id: int
    output: str
    verdict: str | None = None          # "pass" | "fail" | None
    score: float | None = None
    usage_usd: float = 0.0
    children: list["StepResult"] = []   # sub-plan results from replan/react

class Answer(BaseModel):
    text: str
    trace: "RunTrace"

class WorkerSpec(BaseModel):
    id: int                             # ordinal exposed to planner
    name: str                           # concrete model string (litellm), hidden from planner prompt
    served: str = "api"                 # "api" | "local"
    capabilities: dict[str, float] = {} # optional priors; calibration overrides at runtime
```

---

## 6. Component contracts

Define these as `Protocol`s so phases can swap implementations.

```python
class Planner(Protocol):
    async def plan(self, prompt: str, pool: list[WorkerSpec],
                   calibration: CalibrationTable) -> Plan: ...

class WorkerAdapter(Protocol):
    async def call(self, messages: list[dict], *, max_tokens: int,
                   temperature: float) -> tuple[str, float]:  # (text, usd_cost)
        ...

class Verifier(Protocol):
    async def verify(self, step: Step, output: str) -> Verdict:  # pass/fail + score + detail
        ...

class Synthesizer(Protocol):
    async def synthesize(self, prompt: str, results: list[StepResult]) -> str: ...
```

**Phase-1 implementations:**
- `FrontierLLMPlanner` — calls a strong model with the plan prompt (see §8), parses + validates JSON into a `Plan`. Reads `calibration` and injects per-task win-rates into the prompt so `assign` is grounded.
- `WorkerAdapter` — thin LiteLLM wrapper; computes `usd_cost` from token usage + a price map in config.
- `Synthesizer` — for a single terminal step, pass through; for multiple, a small LLM call that combines (configurable which worker).

---

## 7. Runtime loop (`executor.py`) — core algorithm

This is the heart of the framework. Implement exactly this control flow.

```
execute(plan, prompt, budget, depth=0) -> list[StepResult]:
    enforce depth <= budget.max_depth
    results = []
    for i, step in enumerate(plan.steps):
        budget.check()                      # raises BudgetExceeded on spend/time/limits

        context = build_context(prompt, step.access, results)   # access_list = the edges
        output, cost = worker_registry[step.worker_id].call(context, cfg_for(step))
        budget.add_spend(cost)

        verdict = None
        if step.verifier:
            verdict = verifier_registry[step.verifier].verify(step, output)

        sr = StepResult(index=i, worker_id=step.worker_id, output=output,
                        verdict=verdict.kind if verdict else None,
                        score=verdict.score if verdict else None, usage_usd=cost)

        # ── escalation: only on a real failure signal ──
        if verdict and verdict.failed:
            if step.primitive == REPLAN and depth < budget.max_depth:
                subplan = planner.replan(prompt, step, output, verdict, pool, calibration)
                sr.children = execute(subplan, prompt, budget, depth+1)
                sr.output = terminal_output(sr.children) or sr.output

            elif step.primitive == REACT:
                sr = react_loop(step, prompt, results, budget)   # bounded by max_react_steps

            # NORMAL (or depth exhausted): accept the failed output, move on
        results.append(sr)
    return results
```

`react_loop`: repeatedly let the **planner model itself** observe the last output and emit either a single next action (worker + subtask) or a "done", capped at `budget.max_react_steps`, each iteration charged to the budget. This is ReAct scoped to one step — not the whole task.

**Key invariants for the implementer:**
- The executor is the *only* place workers and verifiers are called.
- `build_context` is pure: it assembles prior subtask+response messages named in `step.access` (`"all"` = every prior, `[]` = blind, `[i,j]` = those indices) into a chat history. No side effects.
- Escalation never happens without `verdict.failed`. An unverified step (`verifier=None`) runs exactly once regardless of primitive.
- Every model call goes through the budget. No exceptions.

After `execute` returns, the orchestrator calls `synthesizer.synthesize(prompt, results)` to produce the final `Answer`.

---

## 8. Plan schema + planner prompt (`planner.py`)

The planner emits **JSON only** matching `Plan`. Validate with Pydantic; on parse failure, retry once with the validation error appended, then fail loudly.

Prompt requirements (system prompt for `FrontierLLMPlanner`):
- Describe the job: produce up to N steps, each with `worker_id`, `subtask`, `access`, `primitive`, and optionally `verifier`/`expected`.
- Present workers **ordinally** (`Model 0 … Model k`) with capability lines drawn from the calibration table, e.g. `Model 2 — strong: code-gen (win 0.71), weak: MCQ`.
- State the primitive guidance plainly: use `normal` by default; `replan` for a step whose correctness is checkable and likely to need a second attempt; `react` only for steps interacting with an unpredictable external signal. **Most steps should be `normal`.** Reward frugality — do not add steps that don't earn their cost.
- Require it to assess difficulty first and allow a single-step plan for easy prompts.

Example emitted plan:

```json
{
  "reasoning": "Plan then implement then check.",
  "steps": [
    {"worker_id": 2, "subtask": "Devise an efficient algorithm for X.", "access": [], "primitive": "normal"},
    {"worker_id": 0, "subtask": "Implement the algorithm in Python.", "access": "all", "primitive": "replan", "verifier": "code_exec", "expected": "tests/x_spec.py"},
    {"worker_id": 1, "subtask": "Review the implementation for edge cases.", "access": "all", "primitive": "normal"}
  ],
  "budget": {"max_depth": 2, "max_react_steps": 4, "max_spend_usd": 0.40}
}
```

---

## 9. Verifiers (`verify/`)

A `Verifier` returns `Verdict(kind="pass"|"fail", score: float, detail: str)`. `failed` is `kind == "fail"`.

v1 verifiers:
- `code_exec` — run the produced code against a spec/test file in a sandboxed subprocess with CPU/mem/time limits; pass iff all tests pass. **Treat this as the security-sensitive surface** — never run untrusted code outside the sandbox; make the sandbox boundary an explicit, swappable interface.
- `math_equiv` — normalize and compare against `expected` (symbolic via sympy where possible, else numeric tolerance).
- `exact_match` — normalized string / MCQ-letter equality.

Verifiers must be **fast and deterministic**; they run inline on the hot path. No LLM judges in v1 (they reintroduce the guessing this design exists to remove).

---

## 10. Measurement loop (`measurement/harness.py`) — OFFLINE

Completely separate from runtime. Given a bank of verifiable tasks (`tasks/`), for each `(worker, task_type)`:

```
for task_type in bank:
    for worker in pool:
        for task in sample(bank[task_type], n):
            output = worker.call(task.prompt)
            verdict = verifier_for(task).verify(task, output)
            record(worker.id, task_type, verdict.passed, cost)
calibration.put(win_rate, avg_cost, sample_n, measured_at)
```

Output: a `CalibrationTable` keyed by `(worker_id, task_type)` → `{win_rate, avg_cost_usd, n, measured_at}`. The runtime planner reads this. Schedule re-runs when any worker's version string changes; mark stale entries past a configurable TTL.

This harness is also your eval harness — reuse it to score the whole orchestrator against held-out tasks.

---

## 11. API surface (`api/server.py`)

Expose OpenAI-compatible `POST /v1/chat/completions`. Map the incoming `messages` to a prompt, run the orchestrator, return the synthesized answer in OpenAI response shape. Include the `RunTrace` under a non-standard field (e.g. `x_orchestrator_trace`) when a debug flag is set. This lets existing OpenAI-client tooling target the orchestrator with only a base-URL change.

---

## 12. Observability (`trace.py`)

Every run returns a `RunTrace`: the plan, each `StepResult` (nested for sub-plans), per-step worker + cost + verdict, total spend, total wall-time, and whether budgets were hit. Make it serializable to JSON and cheap to log. This is how you'll debug "why did it pick that model / why did it loop."

---

## 13. Build milestones

Implement in this order. Each milestone is independently runnable and testable.

**M1 — Single-pass skeleton.** `types`, `WorkerAdapter` (one real provider + a mock), `WorkerRegistry`, `FrontierLLMPlanner` emitting `normal`-only plans, `Executor` with no escalation, passthrough `Synthesizer`, `BudgetEnforcer` (spend + wall-time). CLI entry: `run(prompt) -> answer`.
*Acceptance:* a multi-step plan executes over real workers with correct `access` wiring; budget halts a runaway; full trace returned.

**M2 — Verifiers + measurement.** `exact_match`, `math_equiv`, `code_exec` (sandboxed). `CalibrationStore` + `measurement/harness`. Planner reads calibration into its prompt.
*Acceptance:* harness produces a calibration table over a small task bank; planner's `assign` reflects it; verifiers return correct verdicts on fixtures.

**M3 — Escalation primitives.** `replan` (recursive sub-plan via `planner.replan`) and `react` (`react_loop`), both budget-bounded; depth enforcement.
*Acceptance:* a deliberately-failing verified step triggers exactly one replan within depth; a `react` step loops ≤ `max_react_steps`; an unverified step never escalates.

**M4 — API + eval.** OpenAI-compatible endpoint; reuse the harness to benchmark the orchestrator vs. each single worker on held-out tasks; emit a comparison report.
*Acceptance:* an OpenAI client hits the endpoint unchanged; eval shows orchestrator ≥ best single worker on the bank (the whole point).

**M5 (optional, deferred) — Trained planner.** Only if low-latency/cheap planning or sub-task-level preferences justify it. Reproduce the Conductor recipe: Qwen2.5-7B base, GRPO, the executor above *as the RL environment*, verifier verdicts *as the reward*. Note the real cost is the worker-API bill during rollouts and serving open workers, not the 2×H100. Swap `FrontierLLMPlanner` → `TrainedPlanner` behind the same `Planner` protocol; nothing else changes.

---

## 14. Design rationale (why these choices — keep, don't undo)

- **Frontier-model planner first, training deferred.** Ablations on the Conductor showed an untrained frontier model dropped into the same scaffold captured most of the gain (~71.6 of 75.6 avg); training mainly buys *calibration*, which we get from the measurement loop instead. Training is a latency/cost optimization, not a capability prerequisite.
- **The value isn't routing.** Fixing all workers to one model still beat that model alone — decomposition + tailored prompting + verification topology carry independent weight. Hence the planner emits *subtasks and access edges*, not just model picks; and verify/synthesize is mandatory, not optional (a flat fan-out without verification is the weaker MoA baseline).
- **Reveal, don't predict.** An up-front mode classifier commits to a strategy before any evidence exists — the same blind-prior failure the Conductor's RL exists to correct. Escalating on verifier failure replaces the guess with a measured signal at runtime.
- **Up-front plan + local adaptation.** This is where frontier deep-research systems converged (ReWOO/LLMCompiler for the up-front DAG; ADaPT for failing-step-only recursion). The three primitives are exactly that: a flat plan is plan-execute, a `replan` step is ADaPT, a `react` step is scoped ReAct.
- **Measurement loop as the durable asset.** Models update and any frozen "best model" knowledge rots; a harness that re-measures is renewable. That's why calibration is a store with a TTL, not constants.

---

## 15. Open decisions (flag to the user; don't silently pick)

- **Worker pool composition** — which frontier APIs + which open models, and whether open models are self-hosted (vLLM) or via a hosted OpenAI-compatible provider. Affects infra cost more than anything else.
- **Sandbox strength for `code_exec`** — subprocess+rlimits (simple, weaker isolation) vs container/microVM (stronger, heavier). Start simple behind a clean interface.
- **Task bank** — which verifiable datasets seed the measurement loop and eval (mirror the Conductor's: math, MCQ, code; pick versions you can grade).
- **Synthesizer policy** — passthrough for single-step, but for multi-step: dedicated synthesizer worker, or reuse the strongest available? Make it config.
- **Persistence** — calibration store and traces: in-memory + JSON files to start, or SQLite? SQLite recommended once M2 lands.

---

*This document is the contract. If implementation pressure pushes against §0, surface it rather than quietly relaxing it.*
