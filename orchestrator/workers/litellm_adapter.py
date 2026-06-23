"""Metered API / OpenAI-compatible adapter via LiteLLM. Cost is reported in
USD (worker-registry spec). LiteLLM is imported lazily so the package and its
tests do not require it installed."""

from __future__ import annotations

import time

from ..types import Usage, WorkerSpec


class LiteLLMAdapter:
    def __init__(
        self,
        spec: WorkerSpec,
        *,
        prices: dict[str, dict[str, float]] | None = None,
        api_base: str | None = None,
    ) -> None:
        self.spec = spec
        self.prices = prices or {}
        self.api_base = api_base

    async def call(
        self, messages: list[dict], *, max_tokens: int, temperature: float
    ) -> tuple[str, Usage]:
        import litellm  # lazy

        t0 = time.monotonic()
        resp = await litellm.acompletion(
            model=self.spec.name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            api_base=self.api_base,
        )
        wall = time.monotonic() - t0
        text = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None) or {}
        tin = int(getattr(usage, "prompt_tokens", 0) or (usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0))
        tout = int(getattr(usage, "completion_tokens", 0) or (usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0))
        return text, Usage(usd=self._cost(resp, tin, tout), wall_seconds=wall, tokens_in=tin, tokens_out=tout)

    def _cost(self, resp, tin: int, tout: int) -> float:
        try:
            import litellm

            c = litellm.completion_cost(completion_response=resp)
            if c:
                return float(c)
        except Exception:
            pass
        p = self.prices.get(self.spec.name)
        if p:
            return (tin / 1000) * p.get("input", 0.0) + (tout / 1000) * p.get("output", 0.0)
        return 0.0

    async def test_connection(self) -> tuple[bool, str]:
        try:
            await self.call([{"role": "user", "content": "ping"}], max_tokens=5, temperature=0.0)
            return True, "ok"
        except Exception as e:  # pragma: no cover - network dependent
            return False, str(e)
