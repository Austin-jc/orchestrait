## 1. Project scaffolding

- [x] 1.1 Create Python package layout (`orchestrator/` with `runtime/`, `workers/`, `verify/`, `calibration/`, `measurement/`, `api/`) and `pyproject.toml` with deps (litellm, pydantic>=2, pydantic-settings, fastapi, uvicorn, pyyaml, tenacity, pytest, pytest-asyncio)
- [x] 1.2 Implement `types.py` Pydantic models: `Primitive`, `Step`, `Budget` (multi-axis), `Plan`, `StepResult`, `Answer`, `WorkerSpec`, `Verdict`, `RunTrace`
- [x] 1.3 Implement `config.py` (Pydantic `BaseSettings` + `config.yaml`; secrets via env, never in code)
- [x] 1.4 Set up pytest + pytest-asyncio and a `MockWorkerAdapter` for deterministic unit tests

## 2. Core runtime skeleton (single-pass, no escalation)

- [x] 2.1 Define the `WorkerAdapter` SPI and implement the `litellm` adapter (returns text + USD usage from token×price map)
- [x] 2.2 Implement `WorkerRegistry` with ordinal exposure (`Model 0…k`) and capability metadata; concrete model strings hidden from planner prompts
- [x] 2.3 Implement `BudgetEnforcer` as the single non-bypassable gate with `max_spend_usd` + `max_wall_seconds`, raising `BudgetExceeded`
- [x] 2.4 Implement `FrontierLLMPlanner` emitting `normal`-only plans with strict JSON parse + validate-and-retry-once
- [x] 2.5 Implement `Executor` with pure `build_context` (access edges: `"all"` / `[]` / `[i,j]`), normal-only dispatch, no escalation
- [x] 2.6 Implement passthrough `Synthesizer` (single terminal step) and a multi-result combiner
- [x] 2.7 Wire `orchestrator.run(prompt) -> Answer` and a CLI entrypoint; test that a multi-step plan executes with correct access wiring and the budget halts a runaway

## 3. Plug-in backends (BYO models, keys, subscription)

- [ ] 3.1 Implement the `local_openai` adapter (Ollama/vLLM/LM Studio base URL + model; usage charged as wall-clock)
- [ ] 3.2 Implement the `claude_subscription` adapter driving `claude -p --bare --output-format json --json-schema <Plan> --append-system-prompt`, using `CLAUDE_CODE_OAUTH_TOKEN`
- [ ] 3.3 Add the `max_subscription_prompts` budget axis and per-adapter native-unit usage reporting
- [ ] 3.4 Enforce subscription budget governance: charge every `claude_subscription` call (any role) to `max_subscription_prompts`, allow conductor + select worker steps, block calls that would exceed the axis, and guide the planner to prefer non-subscription workers for fan-out
- [ ] 3.5 Implement worker connection testing (success / human-readable failure) used before a worker is marked ready
- [ ] 3.6 Implement a local encrypted secrets store for BYO API keys (no plaintext logs)

## 4. Observability and live event stream

- [ ] 4.1 Define typed run events (`plan_ready`, `step_started`, `worker_call`, `verdict`, `escalation`, `budget_tick`, `step_done`, `synthesis`, `run_done`) and emit them from the executor at each decision point
- [ ] 4.2 Assemble the serializable `RunTrace` (nested step results, totals, budget-hit flags) and prove it equals the replayed event log
- [ ] 4.3 Implement the FastAPI server: OpenAI-compatible `POST /v1/chat/completions`, a run endpoint, and an SSE/WebSocket stream of run events

## 5. Visualizer UI — live run + configuration

- [ ] 5.1 Scaffold the local Next.js/React app and an SSE/WebSocket client for the run event stream
- [ ] 5.2 Render the plan as a React Flow DAG (nodes = steps, edges = `access`, badge = primitive) on `plan_ready`
- [ ] 5.3 Animate node states (pending → running → pass/fail) from live events; show live budget meters per active axis
- [ ] 5.4 Build the worker registry + secrets config UI (add/edit/test/remove workers, choose adapter kind, store keys encrypted)
- [ ] 5.5 Build parameter tuning (budget axes, temperatures, planner prompt/primitive guidance, verifier selection) with named presets

## 6. Verifiers and escalation (the win mechanism)

- [ ] 6.1 Implement the verifier registry and `Verdict`; resolve `step.verifier` by name on the execution path
- [ ] 6.2 Implement `exact_match` and `math_equiv` (sympy/numeric) verifiers with fixture tests
- [ ] 6.3 Implement `code_exec` behind a swappable sandbox boundary (subprocess + CPU/mem/time rlimits); verify containment of resource-exhausting code
- [ ] 6.4 Implement the `replan` primitive (recursive sub-plan via `planner.replan`) with `max_depth` enforcement; escalate only on `verdict.failed`
- [ ] 6.5 (Deferred, post-v1) `react` primitive (`react_loop`) — out of v1 scope per D11; keep it reserved in the schema and instruct the planner not to emit `react`
- [ ] 6.6 Surface `escalation` events so the UI expands a failing `replan` node into an inline nested sub-graph
- [ ] 6.7 Test that an unverified step never escalates and a verified failing step triggers exactly one replan within depth

## 7. Measurement, calibration, and proof

- [ ] 7.1 Build a small verifiable task bank (math, MCQ, code) under `tasks/` with graders
- [ ] 7.2 Implement the offline measurement harness (per worker × task-type win-rate + avg cost), fully separate from the runtime path
- [ ] 7.3 Implement the calibration store with TTL/freshness and worker-version-change invalidation
- [ ] 7.4 Wire the planner to read calibration win-rates into its prompt (grounded assignment)
- [ ] 7.5 Implement the eval/proof mode: orchestrator vs each single worker, anchored to Baseline A (same-model single-shot)
- [ ] 7.6 Build the benchmark/proof UI view (orchestrator-vs-single delta) and the calibration heatmap with stale-entry flags

## 8. End-to-end validation and hardening

- [ ] 8.1 End-to-end test demonstrating Baseline A on at least one verifiable task type (orchestrator ≥ best single worker)
- [ ] 8.2 Security pass on the `code_exec` sandbox boundary and the secrets store (no key leakage, no out-of-sandbox execution)
- [ ] 8.3 Persistence cutover to SQLite for calibration + traces once measurement lands
- [ ] 8.4 Write README/usage docs: local setup, registering backends (incl. `claude setup-token`), and reading the proof view
