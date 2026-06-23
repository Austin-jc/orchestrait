"""The single, non-bypassable budget gate (budget-enforcement spec, §0.4).
Every model call charges usage here; `check()` halts the run when any axis is
exhausted."""

from __future__ import annotations

import time
from typing import Callable

from ..types import Budget, Usage


class BudgetExceeded(Exception):
    def __init__(self, axis: str, limit: float, used: float) -> None:
        self.axis = axis
        self.limit = limit
        self.used = used
        super().__init__(f"Budget exceeded on {axis}: used {used} > limit {limit}")


class BudgetEnforcer:
    def __init__(self, budget: Budget, *, clock: Callable[[], float] = time.monotonic) -> None:
        self.budget = budget
        self._clock = clock
        self._start = clock()
        self.spent_usd = 0.0
        self.subscription_prompts = 0
        self.react_steps = 0

    @property
    def elapsed(self) -> float:
        return self._clock() - self._start

    def check(self) -> None:
        """Raise BudgetExceeded if any axis is over its limit. Call before each
        model call."""
        if self.spent_usd > self.budget.max_spend_usd:
            raise BudgetExceeded("max_spend_usd", self.budget.max_spend_usd, round(self.spent_usd, 6))
        if self.elapsed > self.budget.max_wall_seconds:
            raise BudgetExceeded("max_wall_seconds", self.budget.max_wall_seconds, round(self.elapsed, 3))
        if self.subscription_prompts > self.budget.max_subscription_prompts:
            raise BudgetExceeded(
                "max_subscription_prompts", self.budget.max_subscription_prompts, self.subscription_prompts
            )

    def would_exceed_subscription(self, additional: int = 1) -> bool:
        return self.subscription_prompts + additional > self.budget.max_subscription_prompts

    def add_usage(self, usage: Usage) -> None:
        self.spent_usd += usage.usd
        self.subscription_prompts += usage.subscription_prompts

    def totals(self) -> dict:
        return {
            "usd": round(self.spent_usd, 6),
            "wall_seconds": round(self.elapsed, 3),
            "subscription_prompts": self.subscription_prompts,
        }
