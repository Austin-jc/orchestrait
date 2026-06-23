"""The dispatch loop — the only place workers (and, from phase 6, verifiers)
are called. v1 here is single-pass: normal dispatch, no escalation. `replan`
and verifier-triggered escalation land in phase 6."""

from __future__ import annotations

from ..types import Plan, Step, StepResult
from .budget import BudgetEnforcer


def build_context(prompt: str, step: Step, results: list[StepResult]) -> list[dict]:
    """Pure: assemble the chat history a step sees from its `access` edges.

    `"all"` = every prior result, `[]` = blind, `[i, j]` = those indices. No
    side effects.
    """
    messages: list[dict] = [{"role": "user", "content": prompt}]
    if step.access == "all":
        chosen = list(results)
    elif isinstance(step.access, list):
        wanted = set(step.access)
        chosen = [r for r in results if r.index in wanted]
    else:
        chosen = []
    for r in chosen:
        messages.append({"role": "assistant", "content": f"[step {r.index} output]\n{r.output}"})
    messages.append({"role": "user", "content": step.subtask})
    return messages


class Executor:
    def __init__(self, registry, *, max_tokens: int = 1024, temperature: float = 0.2) -> None:
        self.registry = registry
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _cfg(self, step: Step) -> dict:
        return {"max_tokens": self.max_tokens, "temperature": self.temperature}

    async def execute(
        self,
        plan: Plan,
        prompt: str,
        enforcer: BudgetEnforcer,
        depth: int = 0,
        sink: list[StepResult] | None = None,
    ) -> list[StepResult]:
        results = sink if sink is not None else []
        for i, step in enumerate(plan.steps):
            enforcer.check()  # raises BudgetExceeded -> caller keeps partial `sink`
            context = build_context(prompt, step, results)
            adapter = self.registry.get(step.worker_id)
            output, usage = await adapter.call(context, **self._cfg(step))
            enforcer.add_usage(usage)
            results.append(
                StepResult(index=i, worker_id=step.worker_id, output=output, usage=usage)
            )
        return results
