## ADDED Requirements

### Requirement: Pluggable adapter SPI
The system SHALL define a `WorkerAdapter` interface and provide at least three concrete adapter kinds in v1: `litellm` (metered API/OpenAI-compatible), `claude_subscription` (the `claude -p` headless CLI), and `local_openai` (Ollama/vLLM/LM Studio behind an OpenAI-compatible endpoint). Each adapter SHALL accept chat messages and return output text plus a usage report in the adapter's native cost unit.

#### Scenario: A local OpenAI-compatible endpoint is registered and callable
- **WHEN** a user registers a `local_openai` worker with a base URL and model name
- **THEN** the executor can dispatch a step to it through the common adapter interface
- **AND** the returned usage report expresses cost as wall-clock time

#### Scenario: A metered API worker reports USD cost
- **WHEN** a `litellm` worker completes a call
- **THEN** its usage report expresses cost in USD derived from token usage and the configured price map

### Requirement: Ordinal worker exposure with capability metadata
The registry SHALL expose workers to the planner ordinally (`Model 0 … Model k`) with capability metadata, never by brand name, and SHALL map each ordinal to its concrete adapter internally.

#### Scenario: Planner sees ordinals, not brands
- **WHEN** the planner prompt is assembled
- **THEN** workers appear as `Model 0`, `Model 1`, … with capability lines
- **AND** the concrete provider/model string is not present in the planner prompt

### Requirement: Connection testing
The registry SHALL let a user test a worker's connectivity and basic completion before it is used in a run, returning a clear success or failure with the reason.

#### Scenario: Test a misconfigured worker
- **WHEN** a user tests a worker whose endpoint is unreachable or whose credentials are invalid
- **THEN** the test returns a failure with a human-readable reason
- **AND** the worker is not marked ready

### Requirement: Subscription adapter is conductor-eligible only
A `claude_subscription` worker SHALL be flagged conductor-eligible and SHALL NOT be selectable as a fan-out worker target, to protect the subscription rate-limit budget.

#### Scenario: Subscription worker cannot be a fan-out worker
- **WHEN** a plan attempts to assign a fan-out execution step to a `claude_subscription` worker
- **THEN** the assignment is rejected and surfaced as a configuration error
