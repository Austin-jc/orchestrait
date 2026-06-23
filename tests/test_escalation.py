import json

from orchestrator.runtime import BudgetEnforcer, Executor, FrontierLLMPlanner
from orchestrator.types import Budget, WorkerSpec
from orchestrator.verify import default_registry
from orchestrator.workers import MockWorkerAdapter, WorkerRegistry

MAIN_PLAN = json.dumps(
    {
        "steps": [
            {
                "worker_id": 1,
                "subtask": "do",
                "access": [],
                "primitive": "replan",
                "verifier": "exact_match",
                "expected": "RIGHT",
            }
        ]
    }
)
SUB_PLAN = json.dumps({"steps": [{"worker_id": 2, "subtask": "redo", "access": [], "primitive": "normal"}]})


def _conductor_responder(messages):
    system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
    if "fixing a failed step" in system:
        return SUB_PLAN
    if "planning conductor" in system:
        return MAIN_PLAN
    return "x"


def _setup(worker2_output="RIGHT"):
    a0 = MockWorkerAdapter(WorkerSpec(id=0, name="c", kind="mock"), responder=_conductor_responder)
    a1 = MockWorkerAdapter(WorkerSpec(id=1, name="w1", kind="mock"), fixed="WRONG")
    a2 = MockWorkerAdapter(WorkerSpec(id=2, name="w2", kind="mock"), fixed=worker2_output)
    reg = WorkerRegistry([a0, a1, a2])
    planner = FrontierLLMPlanner(a0, reg)
    ex = Executor(reg, planner=planner, verifiers=default_registry())
    return planner, ex


async def test_verified_failure_triggers_exactly_one_replan_and_passes():
    planner, ex = _setup(worker2_output="RIGHT")
    plan = await planner.plan("q", BudgetEnforcer(Budget()))
    results = await ex.execute(plan, "q", BudgetEnforcer(Budget(max_depth=2)))
    sr = results[0]
    assert sr.verdict == "pass"        # replan fixed it
    assert len(sr.children) == 1       # exactly one sub-plan spawned
    assert sr.output == "RIGHT"


async def test_depth_zero_blocks_replan():
    planner, ex = _setup()
    plan = await planner.plan("q", BudgetEnforcer(Budget()))
    results = await ex.execute(plan, "q", BudgetEnforcer(Budget(max_depth=0)))
    assert results[0].children == []   # depth 0 is not < max_depth 0 -> no escalation
    assert results[0].verdict == "fail"


async def test_unverified_step_never_escalates():
    plan_no_verifier = json.dumps(
        {"steps": [{"worker_id": 1, "subtask": "do", "access": [], "primitive": "replan"}]}
    )

    def conductor(messages):
        system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
        return plan_no_verifier if "planning conductor" in system else "x"

    a0 = MockWorkerAdapter(WorkerSpec(id=0, name="c", kind="mock"), responder=conductor)
    a1 = MockWorkerAdapter(WorkerSpec(id=1, name="w1", kind="mock"), fixed="WRONG")
    reg = WorkerRegistry([a0, a1])
    planner = FrontierLLMPlanner(a0, reg)
    ex = Executor(reg, planner=planner, verifiers=default_registry())
    plan = await planner.plan("q", BudgetEnforcer(Budget()))
    results = await ex.execute(plan, "q", BudgetEnforcer(Budget()))
    assert results[0].children == []   # no verifier -> no escalation, runs once
    assert results[0].verdict is None
