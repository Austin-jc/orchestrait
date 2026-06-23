## ADDED Requirements

### Requirement: Plan execution over a worker pool
The runtime SHALL accept a prompt, obtain a `Plan` from the conductor, and execute its steps in order over the worker pool, producing one synthesized answer. The executor SHALL be the only component that calls workers and verifiers.

#### Scenario: Multi-step plan executes with correct dispatch
- **WHEN** a valid multi-step `Plan` is executed against a registered worker pool
- **THEN** each step is dispatched to the worker named by its `worker_id` ordinal, in plan order
- **AND** the run returns a single `Answer` plus a complete `RunTrace`

#### Scenario: Workers are only ever called by the executor
- **WHEN** any component other than the executor attempts to invoke a worker or verifier
- **THEN** that path does not exist in the architecture (workers/verifiers are reachable only through the executor)

### Requirement: Access-based context assembly
The executor SHALL build each step's context purely from the upstream results named in `step.access`, where `"all"` means every prior step, `[]` means no prior context, and `[i, j]` means those step indices. Context assembly SHALL have no side effects.

#### Scenario: Access list selects upstream context
- **WHEN** a step declares `access: [0, 2]`
- **THEN** only the subtask+response of steps 0 and 2 are assembled into that step's chat history
- **AND** steps not listed are excluded

#### Scenario: Blind step receives no prior context
- **WHEN** a step declares `access: []`
- **THEN** the step is run with only the global prompt and its own subtask, no prior step outputs

### Requirement: Verifier-triggered escalation only
A step SHALL escalate only when its verifier returns a failure. A step with no verifier SHALL run exactly once regardless of its primitive. Escalation SHALL NOT fire on any prediction made before execution.

#### Scenario: Unverified step never escalates
- **WHEN** a step has `verifier: null` and `primitive: replan`
- **THEN** the step runs exactly once and does not spawn a sub-plan

#### Scenario: Verified failing step escalates
- **WHEN** a `replan` step's verifier returns a failing verdict and depth is below the budget limit
- **THEN** exactly one local sub-plan is spawned for that step

### Requirement: Escalation primitives with depth bound
The runtime SHALL support `normal` (run once) and `replan` (on verifier fail, execute a local sub-plan bounded by `max_depth`) in v1, and recursion depth SHALL never exceed `budget.max_depth`. The `react` primitive (a bounded observe→decide→act loop) is reserved in the `Primitive` enum and plan schema but deferred beyond v1; until it is implemented the planner SHALL NOT emit `react`.

#### Scenario: Replan respects depth limit
- **WHEN** a `replan` step fails its verifier but the current depth already equals `max_depth`
- **THEN** no further sub-plan is spawned and the failing output is accepted

#### Scenario: React is not emitted in v1
- **WHEN** the conductor produces a v1 plan
- **THEN** no step uses the `react` primitive

### Requirement: Answer synthesis
After execution, the runtime SHALL synthesize the step results into a single answer: passthrough for a single terminal step, and a combining step for multiple results.

#### Scenario: Single-step passthrough
- **WHEN** a plan has one terminal step
- **THEN** that step's output is returned as the answer without an extra synthesis call
