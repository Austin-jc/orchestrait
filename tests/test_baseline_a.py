"""End-to-end demonstration of Baseline A (task 8.1): orchestrating a model
beats single-shot use of that same model on a verifiable task type. Model 1
fails math alone (0.0); orchestrated with verify+replan it reaches 1.0."""

import json

from orchestrator.measurement import evaluate
from orchestrator.measurement.bank import Task
from orchestrator.runtime import DefaultSynthesizer, Executor, FrontierLLMPlanner, Orchestrator
from orchestrator.types import WorkerSpec
from orchestrator.verify import default_registry
from orchestrator.workers import MockWorkerAdapter, WorkerRegistry

BANK = [
    Task(id="m1", task_type="math", prompt="Compute 2+2. Reply with the number.", verifier="math_equiv", expected="4"),
    Task(id="m2", task_type="math", prompt="Compute 3+3. Reply with the number.", verifier="math_equiv", expected="6"),
]


def _conductor(messages):
    system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
    user = messages[-1]["content"]
    if "fixing a failed step" in system:
        return json.dumps({"steps": [{"worker_id": 2, "subtask": "redo", "access": "all", "primitive": "normal"}]})
    if "planning conductor" in system:
        expected = "4" if "2+2" in user else "6"
        return json.dumps(
            {
                "steps": [
                    {"worker_id": 1, "subtask": "solve " + user, "access": [], "primitive": "replan",
                     "verifier": "math_equiv", "expected": expected}
                ]
            }
        )
    return "WRONG"


def _fixer(messages):
    text = " ".join(m["content"] for m in messages)
    if "2+2" in text:
        return "4"
    if "3+3" in text:
        return "6"
    return "0"


async def test_baseline_a_orchestrator_beats_single_shot_of_same_model():
    a0 = MockWorkerAdapter(WorkerSpec(id=0, name="conductor", kind="mock"), responder=_conductor)
    a1 = MockWorkerAdapter(WorkerSpec(id=1, name="model-x", kind="mock"), fixed="WRONG")  # fails math alone
    a2 = MockWorkerAdapter(WorkerSpec(id=2, name="fixer", kind="mock"), responder=_fixer)
    reg = WorkerRegistry([a0, a1, a2])
    planner = FrontierLLMPlanner(a0, reg)
    orch = Orchestrator(
        reg, planner, Executor(reg, planner=planner, verifiers=default_registry()), DefaultSynthesizer()
    )

    report = await evaluate(orch, reg, BANK, default_registry(), baseline_worker_id=1)

    assert report.workers[1] == 0.0          # model 1 single-shot fails every math task
    assert report.orchestrator == 1.0        # orchestrating model 1 (+verify/replan) gets them all
    assert report.orchestrator >= report.best_single   # the headline claim holds
    assert report.delta_vs_baseline == 1.0   # Baseline A: orchestration beats same-model single-shot
