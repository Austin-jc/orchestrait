import pytest

from orchestrator.runtime import BudgetEnforcer, BudgetExceeded
from orchestrator.types import Budget, Usage


def test_spend_axis_raises():
    e = BudgetEnforcer(Budget(max_spend_usd=0.5))
    e.check()  # fine at zero
    e.add_usage(Usage(usd=1.0))
    with pytest.raises(BudgetExceeded) as ei:
        e.check()
    assert ei.value.axis == "max_spend_usd"


def test_wall_axis_with_fake_clock():
    t = {"v": 0.0}
    e = BudgetEnforcer(Budget(max_wall_seconds=10.0), clock=lambda: t["v"])
    e.check()
    t["v"] = 11.0
    with pytest.raises(BudgetExceeded) as ei:
        e.check()
    assert ei.value.axis == "max_wall_seconds"


def test_subscription_axis_raises():
    e = BudgetEnforcer(Budget(max_subscription_prompts=1))
    e.add_usage(Usage(subscription_prompts=2))
    with pytest.raises(BudgetExceeded) as ei:
        e.check()
    assert ei.value.axis == "max_subscription_prompts"


def test_totals():
    e = BudgetEnforcer(Budget(), clock=lambda: 0.0)
    e.add_usage(Usage(usd=0.25, subscription_prompts=3))
    assert e.totals()["usd"] == 0.25
    assert e.totals()["subscription_prompts"] == 3
