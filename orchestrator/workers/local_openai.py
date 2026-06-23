"""Local OpenAI-compatible adapter (Ollama / vLLM / LM Studio). Cost is
reported as wall-clock — local inference has no per-token USD price
(worker-registry spec, D5)."""

from __future__ import annotations

import time

import httpx

from ..types import Usage, WorkerSpec


class LocalOpenAIAdapter:
    def __init__(
        self,
        spec: WorkerSpec,
        *,
        api_base: str = "http://localhost:11434/v1",
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.spec = spec
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def _post_chat(self, payload: dict, headers: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.api_base}/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            return r.json()

    async def call(
        self, messages: list[dict], *, max_tokens: int, temperature: float
    ) -> tuple[str, Usage]:
        payload = {
            "model": self.spec.name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        t0 = time.monotonic()
        data = await self._post_chat(payload, headers)
        wall = time.monotonic() - t0
        text = (data["choices"][0]["message"]["content"]) or ""
        usage = data.get("usage") or {}
        return text, Usage(
            wall_seconds=wall,
            tokens_in=int(usage.get("prompt_tokens", 0) or 0),
            tokens_out=int(usage.get("completion_tokens", 0) or 0),
        )

    async def test_connection(self) -> tuple[bool, str]:
        try:
            await self.call([{"role": "user", "content": "ping"}], max_tokens=5, temperature=0.0)
            return True, "ok"
        except Exception as e:  # pragma: no cover - network dependent
            return False, str(e)
