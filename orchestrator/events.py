"""In-process event bus for one run. The orchestrator publishes typed events
at each decision point; the API streams them (SSE/WebSocket). The full log is
retained so the RunTrace is reconstructable from it (run-observability spec)."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

# Event types emitted during a run (run-observability spec).
EVENT_TYPES = {
    "run_started",
    "plan_ready",
    "step_started",
    "worker_call",
    "verdict",        # phase 6
    "escalation",     # phase 6
    "budget_tick",
    "step_done",
    "synthesis",
    "run_done",
}


class EventBus:
    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self.log: list[dict] = []
        self._seq = 0
        self._closed = False

    async def emit(self, type: str, **data) -> None:
        self._seq += 1
        event = {"type": type, "seq": self._seq, **data}
        self.log.append(event)
        await self._queue.put(event)

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self._queue.put(None)  # sentinel ends stream()

    async def stream(self) -> AsyncIterator[dict]:
        while True:
            event = await self._queue.get()
            if event is None:
                break
            yield event
