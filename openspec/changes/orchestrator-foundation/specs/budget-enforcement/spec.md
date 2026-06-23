## ADDED Requirements

### Requirement: Multi-axis budget
Every run SHALL carry a `Budget` with independent axes: `max_depth`, `max_react_steps`, `max_spend_usd`, `max_wall_seconds`, and `max_subscription_prompts`. Each worker adapter SHALL report usage in its native unit, charged to the matching axis.

#### Scenario: Local worker charges wall-clock, not USD
- **WHEN** a `local_openai` worker completes a call
- **THEN** the call's duration is charged to `max_wall_seconds` and `max_spend_usd` is unaffected

#### Scenario: Subscription conductor charges the prompt axis
- **WHEN** a `claude_subscription` conductor call completes
- **THEN** one unit is charged to `max_subscription_prompts`

### Requirement: Central non-bypassable enforcement
The budget enforcer SHALL be the single gate through which every model call passes, SHALL check limits before each call, and SHALL raise `BudgetExceeded` to halt the run when any axis is exhausted. No step SHALL opt out.

#### Scenario: Runaway loop is halted
- **WHEN** repeated escalation pushes any budget axis past its limit
- **THEN** the next budget check raises `BudgetExceeded` and the run stops with the partial trace intact

#### Scenario: Subscription quota is protected
- **WHEN** conductor calls would exceed `max_subscription_prompts`
- **THEN** the run halts before issuing the call, preventing silent exhaustion of the daily subscription quota
