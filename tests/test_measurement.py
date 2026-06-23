from orchestrator.measurement import load_bank, measure
from orchestrator.measurement.bank import Task
from orchestrator.types import WorkerSpec
from orchestrator.verify import default_registry
from orchestrator.workers import MockWorkerAdapter, WorkerRegistry


def _bank():
    return [
        Task(id="m1", task_type="math", prompt="2+2", verifier="math_equiv", expected="4"),
        Task(id="q1", task_type="mcq", prompt="pick B", verifier="exact_match", expected="B"),
    ]


async def test_measure_produces_per_type_winrates():
    def r0(messages):  # good at math, bad at mcq
        text = " ".join(m["content"] for m in messages)
        return "4" if "2+2" in text else "Z"

    def r1(messages):  # good at mcq, bad at math
        text = " ".join(m["content"] for m in messages)
        return "B" if "pick" in text else "0"

    reg = WorkerRegistry(
        [
            MockWorkerAdapter(WorkerSpec(id=0, name="w0", kind="mock"), responder=r0),
            MockWorkerAdapter(WorkerSpec(id=1, name="w1", kind="mock"), responder=r1),
        ]
    )
    table = await measure(reg, _bank(), default_registry())
    assert table.get(0, "math").win_rate == 1.0
    assert table.get(0, "mcq").win_rate == 0.0
    assert table.get(1, "mcq").win_rate == 1.0
    assert table.get(1, "math").win_rate == 0.0
    # the planner consumes it (grounded assignment)
    assert "math (win 1.00)" in reg.describe_for_planner(table)


def test_load_bank_resolves_code_spec_paths():
    bank = load_bank("tasks/bank.json")
    code = [t for t in bank if t.verifier == "code_exec"]
    assert code and code[0].expected.endswith("add_spec.py")
