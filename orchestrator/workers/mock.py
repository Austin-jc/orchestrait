"""Deterministic adapter for unit tests and offline demos (task 1.4)."""

from __future__ import annotations

from typing import Callable

from ..types import Usage, WorkerSpec


class MockWorkerAdapter:
    """A worker that returns canned/derived output with no network.

    - `responder(messages) -> str` gives full control (used to assert what
      context a step saw).
    - `fixed` returns a constant string.
    - otherwise it echoes the last user message.

    Every call is recorded in `self.calls` for assertions.
    """

    def __init__(
        self,
        spec: WorkerSpec,
        responder: Callable[[list[dict]], str] | None = None,
        *,
        fixed: str | None = None,
        usd: float = 0.0,
        wall: float = 0.001,
    ) -> None:
        self.spec = spec
        self._responder = responder
        self._fixed = fixed
        self._usd = usd
        self._wall = wall
        self.calls: list[list[dict]] = []

    async def call(
        self, messages: list[dict], *, max_tokens: int, temperature: float
    ) -> tuple[str, Usage]:
        self.calls.append(messages)
        if self._responder is not None:
            text = self._responder(messages)
        elif self._fixed is not None:
            text = self._fixed
        else:
            text = messages[-1]["content"] if messages else ""
        usage = Usage(
            usd=self._usd,
            wall_seconds=self._wall,
            subscription_prompts=1 if self.spec.kind == "claude_subscription" else 0,
        )
        return text, usage

    async def test_connection(self) -> tuple[bool, str]:
        return True, "mock ok"
