import pytest

from orchestrator.runtime import BudgetEnforcer, FrontierLLMPlanner
from orchestrator.types import Budget, WorkerSpec
from orchestrator.workers import MockWorkerAdapter, WorkerRegistry

VALID = '{"reasoning":"ok","steps":[{"worker_id":1,"subtask":"do","access":[],"primitive":"normal"}]}'


def _registry():
    a0 = MockWorkerAdapter(WorkerSpec(id=0, name="c", kind="mock"))
    a1 = MockWorkerAdapter(WorkerSpec(id=1, name="w", kind="mock"))
    return WorkerRegistry([a0, a1])


async def test_parses_valid_plan():
    conductor = MockWorkerAdapter(WorkerSpec(id=0, name="c", kind="mock"), fixed=VALID)
    planner = FrontierLLMPlanner(conductor, _registry())
    plan = await planner.plan("q", BudgetEnforcer(Budget()))
    assert plan.steps[0].worker_id == 1


async def test_parses_plan_with_code_fence():
    fenced = "```json\n" + VALID + "\n```"
    conductor = MockWorkerAdapter(WorkerSpec(id=0, name="c", kind="mock"), fixed=fenced)
    planner = FrontierLLMPlanner(conductor, _registry())
    plan = await planner.plan("q", BudgetEnforcer(Budget()))
    assert plan.steps[0].subtask == "do"


async def test_validate_and_retry_once():
    seq = ["this is not json", VALID]
    conductor = MockWorkerAdapter(
        WorkerSpec(id=0, name="c", kind="mock"), responder=lambda m: seq.pop(0)
    )
    planner = FrontierLLMPlanner(conductor, _registry())
    plan = await planner.plan("q", BudgetEnforcer(Budget()))
    assert plan.steps[0].subtask == "do"
    assert seq == []  # used the original call and exactly one retry


async def test_fails_loudly_after_retry():
    conductor = MockWorkerAdapter(WorkerSpec(id=0, name="c", kind="mock"), fixed="garbage, no json")
    planner = FrontierLLMPlanner(conductor, _registry())
    with pytest.raises(Exception):
        await planner.plan("q", BudgetEnforcer(Budget()))
