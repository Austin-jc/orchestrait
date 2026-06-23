from orchestrator.types import Budget, Plan, Primitive, Step, Usage, Verdict


def test_plan_parses_from_json():
    data = {
        "reasoning": "r",
        "steps": [{"worker_id": 1, "subtask": "do", "access": [], "primitive": "normal"}],
    }
    plan = Plan.model_validate(data)
    assert plan.steps[0].worker_id == 1
    assert plan.steps[0].primitive == Primitive.NORMAL
    assert isinstance(plan.budget, Budget)


def test_step_defaults():
    s = Step(worker_id=0, subtask="x")
    assert s.access == []
    assert s.primitive == Primitive.NORMAL
    assert s.verifier is None


def test_step_access_all():
    assert Step(worker_id=0, subtask="x", access="all").access == "all"


def test_verdict_failed_passed():
    assert Verdict(kind="fail").failed
    assert Verdict(kind="pass").passed
    assert not Verdict(kind="pass").failed


def test_usage_add():
    u = Usage(usd=0.1, subscription_prompts=1) + Usage(usd=0.2, subscription_prompts=2)
    assert round(u.usd, 3) == 0.3
    assert u.subscription_prompts == 3
