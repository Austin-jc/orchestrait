"""The conductor. A pluggable `Planner` emits strict JSON validating against
`Plan`, with one validate-and-retry before failing loudly (conductor-planning
spec). v1 emits `normal`-only plans (escalation primitives land in phase 6;
`react` is deferred per D11)."""

from __future__ import annotations

import json
from typing import Protocol

from ..types import Plan
from .budget import BudgetEnforcer


class Planner(Protocol):
    async def plan(
        self, prompt: str, enforcer: BudgetEnforcer, calibration=None
    ) -> Plan: ...


# The opening line is also how the MockWorkerAdapter recognises a planning call.
PLANNER_SYSTEM = """You are the planning conductor for a multi-model orchestrator.

Decompose the user's task into a short plan and return ONLY JSON matching this schema:
{{
  "reasoning": str,
  "steps": [
    {{"worker_id": int, "subtask": str, "access": [int]|"all", "primitive": "normal"}}
  ],
  "budget": {{"max_spend_usd": float, "max_wall_seconds": float}}
}}

Workers (refer to them only by ordinal):
{workers}

Rules:
- Assess difficulty first. A single-step plan is fine for easy prompts. Reward frugality.
- `access` lists the indices of earlier steps whose output this step may read
  ("all" = every prior step, [] = none).
- In this version use ONLY the "normal" primitive.
- Return JSON only, no prose, no code fences.
"""


def parse_plan(text: str) -> Plan:
    """Extract and validate a Plan from model text (tolerates ```json fences)."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.endswith("```"):
            s = s[: -3]
        if s.lstrip().startswith("json"):
            s = s.lstrip()[4:]
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1:
        s = s[start : end + 1]
    return Plan.model_validate(json.loads(s))


class FrontierLLMPlanner:
    def __init__(self, conductor, registry, *, max_tokens: int = 2048, temperature: float = 0.2) -> None:
        self.conductor = conductor
        self.registry = registry
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def plan(self, prompt: str, enforcer: BudgetEnforcer, calibration=None) -> Plan:
        system = PLANNER_SYSTEM.format(workers=self.registry.describe_for_planner(calibration))
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        enforcer.check()
        text, usage = await self.conductor.call(
            messages, max_tokens=self.max_tokens, temperature=self.temperature
        )
        enforcer.add_usage(usage)
        try:
            return parse_plan(text)
        except Exception as e:
            # one retry with the validation error appended, then fail loudly
            messages.append({"role": "assistant", "content": text})
            messages.append(
                {
                    "role": "user",
                    "content": f"That was not valid: {e}. Return ONLY valid JSON matching the schema.",
                }
            )
            enforcer.check()
            text2, usage2 = await self.conductor.call(
                messages, max_tokens=self.max_tokens, temperature=self.temperature
            )
            enforcer.add_usage(usage2)
            return parse_plan(text2)
