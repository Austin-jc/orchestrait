## ADDED Requirements

### Requirement: Strict JSON plan emission with validate-and-retry
The conductor SHALL emit JSON conforming to the `Plan` schema. The system SHALL validate it with Pydantic; on parse/validation failure it SHALL retry once with the validation error appended, then fail loudly.

#### Scenario: Valid plan is accepted
- **WHEN** the conductor returns JSON matching the `Plan` schema
- **THEN** it is parsed into a `Plan` and execution proceeds

#### Scenario: Invalid plan triggers one retry then loud failure
- **WHEN** the conductor returns malformed or schema-violating JSON twice in a row
- **THEN** the run fails with an explicit planning error rather than executing a partial plan

### Requirement: Calibration-grounded assignment
The conductor SHALL read the calibration table and inject per-(model, task-type) win-rates into its prompt so that worker assignment is grounded in measurement rather than guessed.

#### Scenario: Calibration shapes the planner prompt
- **WHEN** a calibration table has entries for the registered workers
- **THEN** the planner prompt includes capability lines reflecting those win-rates (e.g. `Model 2 — strong: code-gen (win 0.71)`)

### Requirement: Pluggable conductor including subscription
The conductor SHALL be implemented behind a `Planner` interface so any strong backend can fill the role, including a Claude subscription driven via `claude -p` headless with strict schema output.

#### Scenario: Subscription conductor emits a schema-valid plan
- **WHEN** the conductor is a `claude_subscription` worker invoked with `--output-format json --json-schema`
- **THEN** the returned plan validates against the `Plan` schema without a retry

#### Scenario: Weak conductor is flagged
- **WHEN** a low-capability model is assigned the conductor role
- **THEN** the system surfaces a warning recommending a stronger conductor (subscription or strong API model)

### Requirement: Frugal planning
The conductor SHALL default steps to `normal`, reserve `replan` for checkable steps likely to need a second attempt, and SHALL be permitted to emit a single-step plan for easy prompts. In v1 the conductor SHALL NOT emit the `react` primitive (deferred — see the escalation-primitives requirement).

#### Scenario: Easy prompt yields a minimal plan
- **WHEN** the conductor assesses a prompt as easy
- **THEN** it may emit a single-step plan rather than adding steps that do not earn their cost

#### Scenario: No react in v1 plans
- **WHEN** the conductor emits a v1 plan
- **THEN** it uses only `normal` and `replan` primitives
