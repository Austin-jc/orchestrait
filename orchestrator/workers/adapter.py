"""The pluggable worker adapter SPI (worker-registry spec). LiteLLM is one
adapter among several — local OpenAI-compatible and the Claude subscription
CLI land in phase 3."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..types import Usage, WorkerSpec


@runtime_checkable
class WorkerAdapter(Protocol):
    spec: WorkerSpec

    async def call(
        self, messages: list[dict], *, max_tokens: int, temperature: float
    ) -> tuple[str, Usage]:
        """Run one completion. Returns (text, native-unit usage)."""
        ...

    async def test_connection(self) -> tuple[bool, str]:
        """(ok, human-readable reason). Used before a worker is marked ready."""
        ...
