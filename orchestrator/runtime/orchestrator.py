"""Top-level entrypoint: plan -> execute -> synthesize -> Answer (+RunTrace).
A BudgetExceeded mid-execution is caught so the partial results still
synthesize and the trace records which axis was hit."""

from __future__ import annotations

from ..events import EventBus
from ..types import Answer, Budget, RunTrace, StepResult
from .budget import BudgetEnforcer, BudgetExceeded
from .executor import Executor
from .planner import Planner
from .synthesizer import DefaultSynthesizer, Synthesizer


class Orchestrator:
    def __init__(
        self,
        registry,
        planner: Planner,
        executor: Executor,
        synthesizer: Synthesizer | None = None,
        *,
        default_budget: Budget | None = None,
    ) -> None:
        self.registry = registry
        self.planner = planner
        self.executor = executor
        self.synthesizer = synthesizer or DefaultSynthesizer()
        self.default_budget = default_budget or Budget()

    async def run(self, prompt: str, budget: Budget | None = None, bus: EventBus | None = None) -> Answer:
        bus = bus or EventBus()
        enforcer = BudgetEnforcer(budget or self.default_budget)
        results: list[StepResult] = []
        budget_hit: str | None = None
        plan = None
        try:
            await bus.emit("run_started", prompt=prompt)
            plan = await self.planner.plan(prompt, enforcer)
            await bus.emit("plan_ready", plan=plan.model_dump())
            await self.executor.execute(plan, prompt, enforcer, sink=results, bus=bus)
        except BudgetExceeded as e:
            budget_hit = e.axis

        text = await self.synthesizer.synthesize(prompt, results, enforcer=enforcer)
        await bus.emit("synthesis", text=text)
        totals = enforcer.totals()
        await bus.emit("run_done", totals=totals, budget_hit=budget_hit, answer=text)
        await bus.close()
        trace = RunTrace(
            prompt=prompt,
            plan=plan,
            results=results,
            total_usd=totals["usd"],
            total_wall_seconds=totals["wall_seconds"],
            total_subscription_prompts=totals["subscription_prompts"],
            budget_hit=budget_hit,
            events=list(bus.log),
        )
        return Answer(text=text, trace=trace)
