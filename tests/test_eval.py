import json

from orchestrator.measurement import evaluate
from orchestrator.measurement.bank import Task
from orchestrator.runtime import DefaultSynthesizer, Executor, FrontierLLMPlanner, Orchestrator
from orchestrator.types import WorkerSpec
from orchestrator.verify import default_registry
from orchestrator.workers import MockWorkerAdapter, WorkerRegistry

BANK = [
    Task(id="m", task_type="math", prompt="What is 2+2? Reply with the number.", verifier="math_equiv", expected="4"),
    Task(id="q", task_type="mcq", prompt="pick B: A) A B) B. Reply letter.", verifier="exact_match", expected="B"),
]


def _conductor(messages):
    system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
    if "planning conductor" in system:
        return json.dumps({"steps": [{"worker_id": 1, "subtask": "do", "access": "all", "primitive": "normal"}]})
    return "WRONG"  # single-shot conductor answers are wrong


def _math_only(messages):
    text = " ".join(m["content"] for m in messages)
    return "4" if "2+2" in text else "nope"


def _mcq_only(messages):
    text = " ".join(m["content"] for m in messages)
    return "B" if "pick" in text else "0"


async def test_evaluate_computes_orchestrator_and_single_shot_rates():
    a0 = MockWorkerAdapter(WorkerSpec(id=0, name="c", kind="mock"), responder=_conductor)
    a1 = MockWorkerAdapter(WorkerSpec(id=1, name="w1", kind="mock"), responder=_math_only)
    a2 = MockWorkerAdapter(WorkerSpec(id=2, name="w2", kind="mock"), responder=_mcq_only)
    reg = WorkerRegistry([a0, a1, a2])
    planner = FrontierLLMPlanner(a0, reg)
    orch = Orchestrator(reg, planner, Executor(reg, planner=planner, verifiers=default_registry()), DefaultSynthesizer())

    report = await evaluate(orch, reg, BANK, default_registry(), baseline_worker_id=1)

    # Orchestrator routes everything to w1 (math-only): math right, mcq wrong -> 0.5
    assert report.orchestrator == 0.5
    assert report.workers[0] == 0.0  # conductor single-shot is always wrong
    assert report.workers[1] == 0.5  # math-only
    assert report.workers[2] == 0.5  # mcq-only
    assert report.best_single == 0.5
    assert report.delta_vs_best == 0.0
    assert report.n == 2
    by = {t.task_type: t for t in report.by_type}
    assert by["math"].orchestrator == 1.0 and by["mcq"].orchestrator == 0.0
