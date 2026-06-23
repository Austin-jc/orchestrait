"""The dispatch loop — the only place workers and verifiers are called.
Escalation fires ONLY on a verifier failure: a `replan` step spawns a local
sub-plan bounded by `max_depth`; an unverified step runs exactly once. `react`
is reserved/deferred (D11)."""

from __future__ import annotations

from ..types import Plan, Primitive, Step, StepResult
from .budget import BudgetEnforcer, BudgetExceeded


def build_context(prompt: str, step: Step, results: list[StepResult]) -> list[dict]:
    """Pure: assemble the chat history a step sees from its `access` edges.

    `"all"` = every prior result, `[]` = blind, `[i, j]` = those indices.
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
    def __init__(self, registry, *, planner=None, verifiers=None, max_tokens: int = 1024, temperature: float = 0.2) -> None:
        self.registry = registry
        self.planner = planner
        self.verifiers = verifiers
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
        bus=None,
    ) -> list[StepResult]:
        results = sink if sink is not None else []
        for i, step in enumerate(plan.steps):
            enforcer.check()  # raises BudgetExceeded -> caller keeps partial `sink`
            if bus:
                await bus.emit(
                    "step_started",
                    index=i,
                    depth=depth,
                    worker_id=step.worker_id,
                    subtask=step.subtask,
                    primitive=step.primitive.value,
                    access=step.access,
                    verifier=step.verifier,
                )
            adapter = self.registry.get(step.worker_id)
            # Subscription governance (D4): block a call that would exceed the axis.
            if getattr(adapter.spec, "kind", "") == "claude_subscription" and enforcer.would_exceed_subscription(1):
                raise BudgetExceeded(
                    "max_subscription_prompts",
                    enforcer.budget.max_subscription_prompts,
                    enforcer.subscription_prompts + 1,
                )
            context = build_context(prompt, step, results)
            if bus:
                await bus.emit("worker_call", index=i, depth=depth, worker_id=step.worker_id, kind=getattr(adapter.spec, "kind", ""))
            output, usage = await adapter.call(context, **self._cfg(step))
            enforcer.add_usage(usage)
            sr = StepResult(index=i, worker_id=step.worker_id, output=output, usage=usage)

            # ── verify ──
            verifier = None
            verdict = None
            if step.verifier and self.verifiers is not None and step.verifier in self.verifiers:
                verifier = self.verifiers.get(step.verifier)
                verdict = await verifier.verify(step, output)
                sr.verdict, sr.score = verdict.kind, verdict.score
                if bus:
                    await bus.emit("verdict", index=i, depth=depth, kind=verdict.kind, score=verdict.score)

            # ── escalate (only on a real failure) ──
            if verdict is not None and verdict.failed:
                if step.primitive == Primitive.REPLAN and depth < enforcer.budget.max_depth and self.planner is not None:
                    if bus:
                        await bus.emit("escalation", index=i, depth=depth, primitive="replan")
                    subplan = await self.planner.replan(prompt, step, output, verdict, enforcer)
                    children: list[StepResult] = []
                    await self.execute(subplan, prompt, enforcer, depth + 1, sink=children, bus=bus)
                    sr.children = children
                    if children:
                        sr.output = children[-1].output
                        if verifier is not None:
                            v2 = await verifier.verify(step, sr.output)
                            sr.verdict, sr.score = v2.kind, v2.score
                            if bus:
                                await bus.emit("verdict", index=i, depth=depth, kind=v2.kind, score=v2.score, requalified=True)
                # NORMAL, react (deferred), or depth exhausted: accept the failed output.

            results.append(sr)
            if bus:
                await bus.emit("step_done", depth=depth, result=sr.model_dump())
                await bus.emit("budget_tick", totals=enforcer.totals())
        return results
