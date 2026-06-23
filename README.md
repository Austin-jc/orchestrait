# Orchestrait

A **local-first multi-model orchestrator**. Bring your own models — local
(Ollama/vLLM), metered APIs, or a Claude Pro/Max **subscription** — and let a
conductor plan a task into a DAG, run it over your worker pool, verify each
step, escalate failures, and synthesize one answer.

> The promise: **orchestrating your model beats using it alone — and here's the
> proof.** (Baseline A: the same model, orchestrated, vs single-shot.)

This is the reference implementation of `orchestrator-foundation` (see
`openspec/changes/orchestrator-foundation/`). Lineage: Sakana's *Conductor*
(plan-as-a-DAG), ReWOO / LLMCompiler / ADaPT (up-front plan + local adaptation).

## How it works

```
prompt ─▶ Conductor ─▶ Plan(DAG) ─▶ Executor ─▶ Verify ─▶ Synthesize ─▶ answer
              │ (your strong model      │  ▲              │
              │  or Claude sub)         │  └─ escalate (replan) on verifier fail
              ▼                         ▼
        Calibration store        Worker pool  (local · API · subscription)
        (which model wins             ▲
         which task type)             └── Budget enforcer ($ · wall · sub-prompts)
```

- **Conductor (planner)** emits a strict JSON `Plan`; reads calibration so model
  assignment is *measured*, not guessed.
- **Executor** is the only thing that calls workers/verifiers; escalation fires
  *only* on a verifier failure (`replan` spawns a depth-bounded sub-plan).
- **Budget** is multi-axis (USD, wall-clock, subscription-prompts) and
  non-bypassable; subscription calls are reserved for the conductor + a few
  high-value steps, never broad fan-out.
- **Measurement loop** (offline) scores each of *your* models per task type and
  proves the orchestrator ≥ best single worker on a held-out bank.

## Quick start

### Backend (Python 3.11+)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,api]"          # add ",litellm" for metered API workers
pytest -q                            # 57 tests
python -m orchestrator "Compute 17 * 23, then check it."   # CLI (mock workers)
orchestrait-serve                    # API at http://127.0.0.1:8000
```

### UI (Next.js)

```bash
cd ui
npm install
npm run dev                          # http://localhost:3000  (expects the API on :8000)
```

Four tabs: **Run** (live animated DAG + budget meters), **Workers** (registry +
encrypted secrets), **Tuning** (budget/preset params), **Proof** (orchestrator-
vs-single eval + calibration heatmap).

## Configure your backends

Edit `config.yaml` (workers can also be managed from the UI's Workers tab).
Secrets never live in the file — only a `secret_ref` name; values come from env
vars or the encrypted store.

```yaml
workers:
  - { id: 0, kind: mock, name: mock-strong, conductor_eligible: true }
  - { id: 2, kind: local_openai, name: "llama3.1:8b", api_base: http://localhost:11434/v1 }
  - { id: 3, kind: litellm, name: gpt-4o-mini, secret_ref: OPENAI_API_KEY }
  - { id: 4, kind: claude_subscription, name: claude-subscription, conductor_eligible: true, secret_ref: CLAUDE_CODE_OAUTH_TOKEN }
```

- **Local (Ollama/vLLM/LM Studio):** point `api_base` at the OpenAI-compatible
  endpoint. Cost is wall-clock (free).
- **Metered API (LiteLLM):** set `secret_ref` to the env var / stored secret
  holding the key. Cost is USD.
- **Claude subscription:** run `claude setup-token` to get a long-lived token,
  store it as `CLAUDE_CODE_OAUTH_TOKEN`. Driven via `claude -p` headless. Best
  as the **conductor** — it's rate-limited (prompts per 5h), so the budget caps
  it and the planner avoids fanning workers onto it.

The "money" config: **subscription conductor + local workers** = frontier-grade
planning at near-zero marginal cost.

## OpenAI-compatible endpoint

`POST /v1/chat/completions` runs the orchestrator — point any OpenAI client at
`http://127.0.0.1:8000/v1` with a base-URL change. Add `"x_orchestrator_debug":
true` to get the full `RunTrace`.

## Proof (Baseline A)

`POST /eval` (or the Proof tab) runs the held-out bank through each single
worker and the orchestrator and reports the delta. The win is measurable only on
**verifiable** task types (math, MCQ, code); open-ended prompts run but make no
win claim. See `tasks/bank.json` for the bank and `orchestrator/verify/` for the
graders.

## Layout

```
orchestrator/     runtime (planner, executor, budget, synthesizer), workers,
                  verify (+ sandbox), calibration, measurement, api, events
ui/               Next.js + React Flow visualizer
tasks/            verifiable task bank
tests/            57 pytest tests
openspec/         the spec-driven change that defines this build
```

## Security

Local-first by design. Model-produced code runs only in a sandbox; secrets are
encrypted at rest. See [SECURITY.md](SECURITY.md). Do not run a multi-tenant
hosted service on a personal subscription — a hosted tier must use metered API
keys.
