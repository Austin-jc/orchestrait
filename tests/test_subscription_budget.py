import pytest

from orchestrator.runtime import BudgetEnforcer, BudgetExceeded, Executor
from orchestrator.types import Budget, Plan, Step, WorkerSpec
from orchestrator.workers import MockWorkerAdapter, WorkerRegistry


def _sub_worker():
    # MockWorkerAdapter reports 1 subscription_prompt per call when kind matches.
    return MockWorkerAdapter(WorkerSpec(id=0, name="sub", kind="claude_subscription"), fixed="x")


async def test_subscription_call_blocked_when_it_would_exceed_axis():
    reg = WorkerRegistry([_sub_worker()])
    plan = Plan(
        steps=[Step(worker_id=0, subtask="a", access=[]), Step(worker_id=0, subtask="b", access=[])]
    )
    sink: list = []
    with pytest.raises(BudgetExceeded) as ei:
        await Executor(reg).execute(
            plan, "P", BudgetEnforcer(Budget(max_subscription_prompts=1)), sink=sink
        )
    assert ei.value.axis == "max_subscription_prompts"
    assert len(sink) == 1  # first allowed, second blocked before issuing


async def test_subscription_allowed_within_budget():
    reg = WorkerRegistry([_sub_worker()])
    plan = Plan(steps=[Step(worker_id=0, subtask="a", access=[])])
    res = await Executor(reg).execute(plan, "P", BudgetEnforcer(Budget(max_subscription_prompts=1)))
    assert len(res) == 1
    assert res[0].usage.subscription_prompts == 1
