"""Core data model for the orchestrator.

Field names are load-bearing: the planner is prompted to emit JSON that
validates against `Plan`. See specs/orchestration-runtime and the research
foundation (§5) for the contract.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Primitive(str, Enum):
    """Per-step adaptivity. `react` is reserved in v1 (D11) — the planner is
    instructed not to emit it until its executor lands."""

    NORMAL = "normal"  # run once
    REPLAN = "replan"  # on verifier fail, spawn a local sub-plan (phase 6)
    REACT = "react"    # reserved, deferred post-v1


class Usage(BaseModel):
    """A worker call's cost reported in the adapter's native units. Each axis
    is charged independently by the budget enforcer (D5)."""

    usd: float = 0.0
    wall_seconds: float = 0.0
    subscription_prompts: int = 0
    tokens_in: int = 0
    tokens_out: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            usd=self.usd + other.usd,
            wall_seconds=self.wall_seconds + other.wall_seconds,
            subscription_prompts=self.subscription_prompts + other.subscription_prompts,
            tokens_in=self.tokens_in + other.tokens_in,
            tokens_out=self.tokens_out + other.tokens_out,
        )


class Verdict(BaseModel):
    """A verifier's decision. `failed` is the only escalation trigger."""

    kind: Literal["pass", "fail"]
    score: float = 0.0
    detail: str = ""

    @property
    def failed(self) -> bool:
        return self.kind == "fail"

    @property
    def passed(self) -> bool:
        return self.kind == "pass"


class Step(BaseModel):
    worker_id: int
    subtask: str
    access: list[int] | Literal["all"] = Field(default_factory=list)
    primitive: Primitive = Primitive.NORMAL
    verifier: str | None = None
    expected: str | None = None


class Budget(BaseModel):
    """Multi-axis budget (D5). Every model call passes through the enforcer;
    no step can opt out."""

    max_depth: int = 2
    max_react_steps: int = 4
    max_spend_usd: float = 0.50
    max_wall_seconds: float = 120.0
    max_subscription_prompts: int = 50


class Plan(BaseModel):
    reasoning: str = ""  # planner CoT, kept for the trace, not executed
    steps: list[Step]
    budget: Budget = Field(default_factory=Budget)


class StepResult(BaseModel):
    index: int
    worker_id: int
    output: str
    verdict: str | None = None  # "pass" | "fail" | None
    score: float | None = None
    usage: Usage = Field(default_factory=Usage)
    children: list["StepResult"] = Field(default_factory=list)  # replan/react sub-results


class WorkerSpec(BaseModel):
    id: int                       # ordinal exposed to the planner
    name: str                     # concrete model string — hidden from planner prompts
    kind: str = "litellm"         # adapter kind: litellm | local_openai | claude_subscription | mock
    served: str = "api"           # "api" | "local"
    conductor_eligible: bool = True
    capabilities: dict[str, float] = Field(default_factory=dict)


class RunTrace(BaseModel):
    """Serializable record of a run. In phase 4 this becomes reconstructable
    from the live event log (run-observability spec)."""

    prompt: str
    plan: Plan | None = None
    results: list[StepResult] = Field(default_factory=list)
    total_usd: float = 0.0
    total_wall_seconds: float = 0.0
    total_subscription_prompts: int = 0
    budget_hit: str | None = None  # name of the exhausted axis, if any
    events: list[dict] = Field(default_factory=list)


class Answer(BaseModel):
    text: str
    trace: RunTrace


StepResult.model_rebuild()
