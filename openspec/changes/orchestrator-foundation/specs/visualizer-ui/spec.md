## ADDED Requirements

### Requirement: Live run visualizer
The UI SHALL render the plan as a directed graph (nodes = steps, edges = `access` dependencies, node badge = primitive) and animate execution by consuming the live event stream: nodes transition pending → running → pass/fail → escalating, and a failing `replan` node expands an inline sub-graph.

#### Scenario: DAG animates as a run progresses
- **WHEN** a user submits a prompt and a run begins
- **THEN** the plan graph appears on `plan_ready` and each node updates its visual state as `step_started`, `verdict`, and `step_done` events arrive

#### Scenario: Escalation expands inline
- **WHEN** an `escalation` event arrives for a node
- **THEN** the node visibly enters an escalating state and its sub-plan renders as a nested sub-graph

### Requirement: Budget meters
The UI SHALL display live budget consumption per active axis (USD, wall-clock, subscription-prompts) during a run, updating on `budget_tick` events.

#### Scenario: Subscription budget visible during a run
- **WHEN** a run uses a subscription conductor
- **THEN** the UI shows remaining `max_subscription_prompts` budget decreasing as conductor calls are made

### Requirement: Benchmark/proof view
The UI SHALL provide a benchmark view that runs the eval harness and renders the orchestrator-vs-single-worker delta (Baseline A), plus a calibration heatmap of (model × task-type) win-rates with freshness indicators.

#### Scenario: Proof view shows the win
- **WHEN** a user runs the benchmark on a verifiable bank
- **THEN** the UI displays the orchestrator score against each single worker's score so the delta is legible

#### Scenario: Heatmap flags stale calibration
- **WHEN** a calibration entry is past its TTL
- **THEN** the heatmap cell is marked stale

### Requirement: Worker registry and secrets configuration
The UI SHALL let a user add, edit, test, and remove workers — choosing the adapter kind, endpoint, model, and parameters — and SHALL store BYO API keys in a local encrypted secrets store, never in plaintext logs.

#### Scenario: Add and test a worker from the UI
- **WHEN** a user adds a worker, enters its configuration and credentials, and clicks test
- **THEN** the UI reports connection success or a human-readable failure, and persists the secret to the encrypted store on success

### Requirement: Parameter tuning
The UI SHALL expose tunable run parameters — budget axes, temperatures, the planner prompt/primitive guidance, and verifier selection — savable as named presets.

#### Scenario: Save and reuse a preset
- **WHEN** a user adjusts budget and temperature values and saves them as a named preset
- **THEN** the preset can be selected to configure a subsequent run
