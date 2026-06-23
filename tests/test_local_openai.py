from orchestrator.types import WorkerSpec
from orchestrator.workers.local_openai import LocalOpenAIAdapter


async def test_local_openai_parses_and_charges_wall_clock():
    spec = WorkerSpec(id=0, name="llama3", kind="local_openai")
    adapter = LocalOpenAIAdapter(spec)

    async def fake_post(payload, headers):
        assert payload["model"] == "llama3"
        assert payload["stream"] is False
        return {
            "choices": [{"message": {"content": "hi there"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        }

    adapter._post_chat = fake_post  # type: ignore[assignment]
    text, usage = await adapter.call([{"role": "user", "content": "hi"}], max_tokens=10, temperature=0.0)
    assert text == "hi there"
    assert usage.usd == 0.0  # local inference: cost is wall-clock, not USD
    assert usage.wall_seconds >= 0.0
    assert usage.tokens_in == 3 and usage.tokens_out == 2
