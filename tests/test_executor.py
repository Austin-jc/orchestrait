import pytest

from orchestrator.runtime import BudgetEnforcer, BudgetExceeded, Executor, build_context
from orchestrator.types import Budget, Plan, Step, StepResult, Usage, WorkerSpec
from orchestrator.workers import MockWorkerAdapter, WorkerRegistry


def _echo(messages):
    return "ECHO::" + " | ".join(m["content"] for m in messages)


def test_build_context_blind_vs_access():
    results = [StepResult(index=0, worker_id=0, output="OUT0", usage=Usage())]
    blind = build_context("P", Step(worker_id=1, subtask="s", access=[]), results)
    assert not any("OUT0" in m["content"] for m in blind)
    seen = build_context("P", Step(worker_id=1, subtask="s", access=[0]), results)
    assert any("OUT0" in m["content"] for m in seen)


async def test_access_wiring():
    a0 = MockWorkerAdapter(WorkerSpec(id=0, name="w0"), fixed="OUT0")
    a1 = MockWorkerAdapter(WorkerSpec(id=1, name="w1"), responder=_echo)
    a2 = MockWorkerAdapter(WorkerSpec(id=2, name="w2"), responder=_echo)
    reg = WorkerRegistry([a0, a1, a2])
    plan = Plan(
        steps=[
            Step(worker_id=0, subtask="produce", access=[]),
            Step(worker_id=1, subtask="use step0", access=[0]),
            Step(worker_id=2, subtask="blind", access=[]),
        ]
    )
    results = await Executor(reg).execute(plan, "PROMPT", BudgetEnforcer(Budget()))
    assert results[0].output == "OUT0"
    assert "OUT0" in results[1].output           # step 1 saw step 0
    assert "OUT0" not in results[2].output       # step 2 was blind
    assert "PROMPT" in results[1].output and "PROMPT" in results[2].output


async def test_access_all():
    a0 = MockWorkerAdapter(WorkerSpec(id=0, name="w0"), fixed="OUT0")
    a1 = MockWorkerAdapter(WorkerSpec(id=1, name="w1"), responder=_echo)
    reg = WorkerRegistry([a0, a1])
    plan = Plan(
        steps=[
            Step(worker_id=0, subtask="p", access=[]),
            Step(worker_id=1, subtask="all", access="all"),
        ]
    )
    results = await Executor(reg).execute(plan, "P", BudgetEnforcer(Budget()))
    assert "OUT0" in results[1].output


async def test_budget_halts_runaway():
    a0 = MockWorkerAdapter(WorkerSpec(id=0, name="w0"), fixed="x", usd=1.0)
    reg = WorkerRegistry([a0])
    plan = Plan(
        steps=[
            Step(worker_id=0, subtask="s1", access=[]),
            Step(worker_id=0, subtask="s2", access=[]),
        ]
    )
    sink: list = []
    with pytest.raises(BudgetExceeded):
        await Executor(reg).execute(plan, "P", BudgetEnforcer(Budget(max_spend_usd=0.5)), sink=sink)
    assert len(sink) == 1  # first step ran, second halted before dispatch
