## ADDED Requirements

### Requirement: Verifier registry and verdicts
The system SHALL provide a verifier registry mapping a name to a `Verifier`, where a verifier returns a `Verdict(kind="pass"|"fail", score, detail)` and `failed` is `kind == "fail"`. Verdicts SHALL be the only escalation trigger in the runtime.

#### Scenario: Step resolves its verifier by name
- **WHEN** a step declares `verifier: "code_exec"`
- **THEN** the runtime resolves it from the registry and applies it to the step output, recording the verdict on the step result

### Requirement: v1 verifiers
The system SHALL ship `exact_match` (normalized string / MCQ-letter equality), `math_equiv` (symbolic via sympy where possible, else numeric tolerance), and `code_exec` (run produced code against a spec/test file). Verifiers SHALL be fast and deterministic and SHALL run inline on the execution path.

#### Scenario: exact_match grades an MCQ answer
- **WHEN** a step output normalizes to the same MCQ letter as `expected`
- **THEN** the verdict is `pass`

#### Scenario: code_exec passes only when all tests pass
- **WHEN** produced code is run against its spec and any test fails
- **THEN** the verdict is `fail` with detail identifying the failure

### Requirement: Sandboxed code execution boundary
`code_exec` SHALL run model-produced code inside a sandbox with CPU, memory, and wall-time limits, and SHALL never execute untrusted code outside that boundary. The sandbox SHALL be an explicit, swappable interface (subprocess + rlimits in v1).

#### Scenario: Resource-exhausting code is contained
- **WHEN** produced code exceeds the configured CPU or memory limit
- **THEN** execution is terminated by the sandbox and the verdict is `fail`, without affecting the host process

### Requirement: No LLM judges in v1
The verifier set SHALL NOT include LLM-judge verifiers in v1, since they reintroduce the guessing the design exists to remove.

#### Scenario: Verification stays deterministic
- **WHEN** the same output is verified twice with the same verifier and inputs
- **THEN** the verdict is identical
