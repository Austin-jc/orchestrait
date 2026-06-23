## ADDED Requirements

### Requirement: Complete run trace
Every run SHALL return a serializable `RunTrace` containing the plan, each `StepResult` (nested for sub-plans), per-step worker, cost, and verdict, total spend, total wall-time, and whether any budget axis was hit.

#### Scenario: Trace captures a nested escalation
- **WHEN** a `replan` step spawns a sub-plan
- **THEN** the trace records the parent step result with its children sub-plan results nested beneath it

### Requirement: Live event stream
The executor SHALL emit typed events at every decision point — at least `plan_ready`, `step_started`, `worker_call`, `verdict`, `escalation`, `budget_tick`, `step_done`, `synthesis`, and `run_done` — over a streaming transport (SSE/WebSocket) so a client can render execution in real time.

#### Scenario: Client receives ordered events during a run
- **WHEN** a client subscribes to a run's event stream
- **THEN** it receives `plan_ready` before any `step_started`, and `run_done` last
- **AND** each step emits `step_started` before its `verdict` and `step_done`

#### Scenario: Escalation is observable live
- **WHEN** a verified step fails and escalates
- **THEN** an `escalation` event is emitted before the sub-plan's `step_started` events

### Requirement: Trace equals the replayed event log
The final `RunTrace` SHALL be reconstructable from the emitted event log, so the live stream and the persisted trace are the same data at different times.

#### Scenario: Replaying events reproduces the trace
- **WHEN** the event log for a completed run is replayed
- **THEN** the resulting structure equals the `RunTrace` returned at run completion
