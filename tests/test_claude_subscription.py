from orchestrator.types import WorkerSpec
from orchestrator.workers.claude_subscription import ClaudeSubscriptionAdapter


async def test_parses_result_and_charges_one_prompt():
    captured = {}

    async def runner(args, prompt, env):
        captured.update(args=args, prompt=prompt, env=env)
        return '{"result": "the answer"}'

    spec = WorkerSpec(id=0, name="claude", kind="claude_subscription")
    adapter = ClaudeSubscriptionAdapter(spec, oauth_token="tok", runner=runner)
    text, usage = await adapter.call(
        [{"role": "system", "content": "be terse"}, {"role": "user", "content": "q"}],
        max_tokens=10,
        temperature=0.0,
    )
    assert text == "the answer"
    assert usage.subscription_prompts == 1
    assert "--output-format" in captured["args"] and "json" in captured["args"]
    assert "--append-system-prompt" in captured["args"]
    assert captured["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "tok"
    assert "User: q" in captured["prompt"]
    assert "be terse" not in captured["prompt"]  # system goes via flag, not the prompt body


async def test_tolerates_plain_text_output():
    async def runner(args, prompt, env):
        return "just text"

    adapter = ClaudeSubscriptionAdapter(
        WorkerSpec(id=0, name="c", kind="claude_subscription"), runner=runner
    )
    text, _ = await adapter.call([{"role": "user", "content": "q"}], max_tokens=5, temperature=0.0)
    assert text == "just text"
