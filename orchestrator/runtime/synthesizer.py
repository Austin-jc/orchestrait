"""Combine step results into one answer. Passthrough for a single terminal
step; a configurable combining call for multiple (D13: default 'strongest
available', falls back to the terminal output when no synthesizer is set)."""

from __future__ import annotations

from typing import Protocol

from ..types import StepResult
from .budget import BudgetEnforcer


class Synthesizer(Protocol):
    async def synthesize(
        self, prompt: str, results: list[StepResult], enforcer: BudgetEnforcer | None = None
    ) -> str: ...


class DefaultSynthesizer:
    def __init__(self, adapter=None, *, max_tokens: int = 1024, temperature: float = 0.2) -> None:
        self.adapter = adapter
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def synthesize(
        self, prompt: str, results: list[StepResult], enforcer: BudgetEnforcer | None = None
    ) -> str:
        if not results:
            return ""
        if len(results) == 1:
            return results[0].output
        if self.adapter is None:
            return results[-1].output
        joined = "\n\n".join(f"[step {r.index}]\n{r.output}" for r in results)
        messages = [
            {"role": "system", "content": "Combine the step outputs into one final answer to the task."},
            {"role": "user", "content": f"Task: {prompt}\n\nStep outputs:\n{joined}"},
        ]
        if enforcer is not None:
            enforcer.check()
        text, usage = await self.adapter.call(
            messages, max_tokens=self.max_tokens, temperature=self.temperature
        )
        if enforcer is not None:
            enforcer.add_usage(usage)
        return text
