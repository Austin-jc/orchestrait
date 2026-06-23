from orchestrator.types import Step
from orchestrator.verify import ExactMatch, MathEquiv


async def test_exact_match_strict_for_freeform():
    v = ExactMatch()
    assert (await v.verify(Step(worker_id=0, subtask="x", expected="Paris"), "paris")).kind == "pass"
    assert (await v.verify(Step(worker_id=0, subtask="x", expected="Paris"), "London")).kind == "fail"


async def test_exact_match_mcq_letter_in_verbose_output():
    v = ExactMatch()
    verdict = await v.verify(Step(worker_id=0, subtask="x", expected="B"), "I think the answer is B.")
    assert verdict.kind == "pass"


async def test_math_equiv_numeric_with_verbose_and_tolerance():
    v = MathEquiv()
    assert (await v.verify(Step(worker_id=0, subtask="x", expected="42"), "the result is = 42")).kind == "pass"
    assert (await v.verify(Step(worker_id=0, subtask="x", expected="42"), "= 41")).kind == "fail"
    assert (await v.verify(Step(worker_id=0, subtask="x", expected="3.141592"), "pi ~ 3.14159265")).kind == "pass"
