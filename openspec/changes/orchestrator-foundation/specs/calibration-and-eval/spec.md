## ADDED Requirements

### Requirement: Offline measurement harness
The system SHALL provide an offline harness that, for each (worker, task-type), runs the worker over a sample of verifiable tasks, scores outputs with the matching verifier, and records win-rate and average cost. The harness SHALL run completely separately from the runtime request path.

#### Scenario: Harness produces a calibration table
- **WHEN** the harness runs over a task bank with at least one task type and a worker pool
- **THEN** it writes a calibration entry per (worker_id, task_type) with `{win_rate, avg_cost, n, measured_at}`

### Requirement: Calibration store with freshness
The calibration store SHALL be a cache with an expiry, never hardcoded constants. Entries SHALL be marked stale past a configurable TTL, and re-measurement SHALL be triggerable when a worker's version string changes.

#### Scenario: Stale entry is flagged
- **WHEN** a calibration entry's `measured_at` is older than the configured TTL
- **THEN** the store reports it as stale

#### Scenario: Worker version change invalidates calibration
- **WHEN** a registered worker's version string changes
- **THEN** its calibration entries are marked for re-measurement

### Requirement: Eval/proof mode anchored to Baseline A
The system SHALL reuse the harness to evaluate the orchestrator against each single worker on a held-out bank and report the delta, anchored to Baseline A (orchestrating a model versus single-shot use of the same model).

#### Scenario: Proof report shows orchestrator vs best single worker
- **WHEN** the eval runs on a held-out verifiable bank
- **THEN** it reports the orchestrator's score and each single worker's score so the delta is visible (e.g. orchestrator ≥ best single worker)

#### Scenario: Same-model baseline is computed
- **WHEN** the eval anchors to Baseline A for a given model
- **THEN** it compares orchestrating that model against single-shot use of the same model on identical tasks
