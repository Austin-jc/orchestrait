"""Offline measurement harness — runs each worker over the task bank, scores
with the matching verifier, and writes a CalibrationTable. Completely separate
from the runtime request path (§0.1)."""

from __future__ import annotations

import time

from ..calibration import CalibrationEntry, CalibrationTable
from ..types import Step
from .bank import Task


async def measure(
    registry,
    bank: list[Task],
    verifiers,
    *,
    sample: int | None = None,
    max_tokens: int = 512,
    now: float | None = None,
) -> CalibrationTable:
    table = CalibrationTable()
    now = time.time() if now is None else now

    by_type: dict[str, list[Task]] = {}
    for t in bank:
        by_type.setdefault(t.task_type, []).append(t)

    for task_type, tasks in by_type.items():
        chosen = tasks[:sample] if sample else tasks
        for spec in registry.pool():
            adapter = registry.get(spec.id)
            wins = cost = 0.0
            n = 0
            for task in chosen:
                output, usage = await adapter.call(
                    [{"role": "user", "content": task.prompt}], max_tokens=max_tokens, temperature=0.0
                )
                verifier = verifiers.get(task.verifier)
                verdict = await verifier.verify(
                    Step(worker_id=spec.id, subtask=task.prompt, verifier=task.verifier, expected=task.expected),
                    output,
                )
                wins += 1 if verdict.passed else 0
                cost += usage.usd
                n += 1
            if n:
                table.put(
                    CalibrationEntry(
                        worker_id=spec.id,
                        task_type=task_type,
                        win_rate=wins / n,
                        avg_cost=cost / n,
                        n=n,
                        measured_at=now,
                        worker_version=spec.name,
                    )
                )
    return table
