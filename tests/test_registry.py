from orchestrator.types import WorkerSpec
from orchestrator.workers import MockWorkerAdapter, WorkerRegistry


def test_describe_for_planner_hides_names_shows_cost():
    reg = WorkerRegistry(
        [
            MockWorkerAdapter(WorkerSpec(id=0, name="secret-model-name", kind="claude_subscription")),
            MockWorkerAdapter(WorkerSpec(id=1, name="other-secret", kind="local_openai")),
        ]
    )
    desc = reg.describe_for_planner()
    assert "Model 0" in desc and "Model 1" in desc
    assert "secret-model-name" not in desc  # concrete name hidden from planner
    assert "cost:" in desc
    assert "subscription (scarce" in desc  # subscription is flagged scarce
    assert "free/local" in desc


async def test_registry_test_delegates_to_adapter():
    reg = WorkerRegistry([MockWorkerAdapter(WorkerSpec(id=0, name="c", kind="mock"))])
    ok, reason = await reg.test(0)
    assert ok and "mock" in reason
