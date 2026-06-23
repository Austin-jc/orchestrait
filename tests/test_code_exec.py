from orchestrator.types import Step
from orchestrator.verify import CodeExec
from orchestrator.verify.sandbox import Limits

SPEC = "import solution\nassert solution.add(2, 3) == 5\nassert solution.add(-1, 1) == 0\nprint('ok')\n"


async def test_code_exec_passes_correct_solution(tmp_path):
    spec = tmp_path / "spec_test.py"
    spec.write_text(SPEC)
    v = CodeExec(limits=Limits(wall_seconds=15))
    out = "```python\ndef add(a, b):\n    return a + b\n```"
    verdict = await v.verify(Step(worker_id=0, subtask="add", expected=str(spec)), out)
    assert verdict.kind == "pass"


async def test_code_exec_fails_wrong_solution(tmp_path):
    spec = tmp_path / "spec_test.py"
    spec.write_text(SPEC)
    v = CodeExec(limits=Limits(wall_seconds=15))
    verdict = await v.verify(
        Step(worker_id=0, subtask="add", expected=str(spec)), "def add(a, b):\n    return a - b\n"
    )
    assert verdict.kind == "fail"


async def test_sandbox_contains_runaway_code(tmp_path):
    # An infinite loop at import time must be contained by the wall-clock kill,
    # not hang the host process.
    spec = tmp_path / "spec_test.py"
    spec.write_text("import solution\n")
    v = CodeExec(limits=Limits(wall_seconds=2, cpu_seconds=2))
    verdict = await v.verify(
        Step(worker_id=0, subtask="x", expected=str(spec)), "while True:\n    pass\n"
    )
    assert verdict.kind == "fail"
