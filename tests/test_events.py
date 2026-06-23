import json

from orchestrator.events import EventBus
from orchestrator.runtime import DefaultSynthesizer, Executor, FrontierLLMPlanner, Orchestrator
from orchestrator.trace import trace_from_events
from orchestrator.types import Budget, WorkerSpec
from orchestrator.workers import MockWorkerAdapter, WorkerRegistry

PLAN = json.dumps(
    {
        "steps": [
            {"worker_id": 1, "subtask": "a", "access": [], "primitive": "normal"},
            {"worker_id": 1, "subtask": "b", "access": [0], "primitive": "normal"},
        ]
    }
)


def _orch():
    def conductor(messages):
        system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
        return PLAN if "planning conductor" in system else "ignored"

    a0 = MockWorkerAdapter(WorkerSpec(id=0, name="c", kind="mock"), responder=conductor)
    a1 = MockWorkerAdapter(WorkerSpec(id=1, name="w", kind="mock"), fixed="OUT")
    reg = WorkerRegistry([a0, a1])
    return Orchestrator(reg, FrontierLLMPlanner(a0, reg), Executor(reg), DefaultSynthesizer(), default_budget=Budget())


async def test_events_emitted_in_order():
    bus = EventBus()
    await _orch().run("q", bus=bus)
    types = [e["type"] for e in bus.log]
    assert types[0] == "run_started"
    assert "plan_ready" in types
    assert types.index("plan_ready") < types.index("step_started")
    assert types[-1] == "run_done"
    # every step emits step_started before its step_done
    assert types.index("step_started") < types.index("step_done")


async def test_trace_equals_replayed_event_log():
    answer = await _orch().run("q")
    rebuilt = trace_from_events("q", answer.trace.events)
    assert rebuilt.model_dump() == answer.trace.model_dump()
