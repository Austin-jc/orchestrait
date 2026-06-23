import json

from orchestrator.config import Config
from orchestrator.factory import build_orchestrator
from orchestrator.runtime import (
    BudgetEnforcer,
    DefaultSynthesizer,
    Executor,
    FrontierLLMPlanner,
    Orchestrator,
)
from orchestrator.types import Budget, WorkerSpec
from orchestrator.workers import MockWorkerAdapter, WorkerRegistry

PLAN = json.dumps(
    {"steps": [{"worker_id": 1, "subtask": "answer", "access": [], "primitive": "normal"}]}
)


async def test_end_to_end_single_step_passthrough():
    def conductor(messages):
        system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
        return PLAN if "planning conductor" in system else "ignored"

    a0 = MockWorkerAdapter(WorkerSpec(id=0, name="c", kind="mock"), responder=conductor)
    a1 = MockWorkerAdapter(WorkerSpec(id=1, name="w", kind="mock"), fixed="WORKER_ANSWER")
    reg = WorkerRegistry([a0, a1])
    orch = Orchestrator(
        reg, FrontierLLMPlanner(a0, reg), Executor(reg), DefaultSynthesizer(), default_budget=Budget()
    )
    ans = await orch.run("question")
    assert ans.text == "WORKER_ANSWER"  # single terminal step -> passthrough
    assert ans.trace.plan is not None
    assert ans.trace.results[0].output == "WORKER_ANSWER"
    assert ans.trace.budget_hit is None


async def test_factory_smoke():
    cfg = Config(
        workers=[
            WorkerSpec(id=0, name="a", kind="mock"),
            WorkerSpec(id=1, name="b", kind="mock"),
        ],
        conductor_worker_id=0,
    )
    ans = await build_orchestrator(cfg).run("hello")
    assert ans.text.startswith("[b]")  # worker 1 echoes the subtask
    assert ans.trace.budget_hit is None
    assert ans.trace.plan.steps[0].worker_id == 1


async def test_run_records_budget_hit():
    # conductor plans 2 steps on a pricey worker; budget halts mid-execution.
    plan = json.dumps(
        {
            "steps": [
                {"worker_id": 1, "subtask": "s1", "access": [], "primitive": "normal"},
                {"worker_id": 1, "subtask": "s2", "access": [], "primitive": "normal"},
            ]
        }
    )

    def conductor(messages):
        system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
        return plan if "planning conductor" in system else "x"

    a0 = MockWorkerAdapter(WorkerSpec(id=0, name="c", kind="mock"), responder=conductor)
    a1 = MockWorkerAdapter(WorkerSpec(id=1, name="w", kind="mock"), fixed="x", usd=1.0)
    reg = WorkerRegistry([a0, a1])
    orch = Orchestrator(
        reg, FrontierLLMPlanner(a0, reg), Executor(reg), DefaultSynthesizer()
    )
    ans = await orch.run("q", budget=Budget(max_spend_usd=0.5))
    assert ans.trace.budget_hit == "max_spend_usd"
    assert len(ans.trace.results) == 1  # only the first step completed
