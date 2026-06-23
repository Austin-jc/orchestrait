"""Calibration table: per-(worker, task_type) win-rate + cost, with TTL
freshness and worker-version invalidation (calibration-and-eval spec). It is a
cache with an expiry — never hardcoded constants (§0.5)."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field

WEEK = 7 * 24 * 3600.0


class CalibrationEntry(BaseModel):
    worker_id: int
    task_type: str
    win_rate: float
    avg_cost: float = 0.0
    n: int = 0
    measured_at: float = 0.0
    worker_version: str = ""


class CalibrationTable(BaseModel):
    entries: dict[str, CalibrationEntry] = Field(default_factory=dict)
    ttl_seconds: float = WEEK

    @staticmethod
    def key(worker_id: int, task_type: str) -> str:
        return f"{worker_id}:{task_type}"

    def put(self, entry: CalibrationEntry) -> None:
        self.entries[self.key(entry.worker_id, entry.task_type)] = entry

    def get(self, worker_id: int, task_type: str) -> CalibrationEntry | None:
        return self.entries.get(self.key(worker_id, task_type))

    def is_stale(self, entry: CalibrationEntry, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return (now - entry.measured_at) > self.ttl_seconds

    def for_worker(self, worker_id: int, now: float | None = None) -> dict[str, float]:
        """{task_type: win_rate} for fresh entries — consumed by the planner."""
        out: dict[str, float] = {}
        for e in self.entries.values():
            if e.worker_id == worker_id and not self.is_stale(e, now):
                out[e.task_type] = e.win_rate
        return out

    def invalidate_for_version(self, worker_id: int, version: str) -> list[str]:
        """Drop a worker's entries whose recorded version differs (re-measure)."""
        dropped = [
            k
            for k, e in self.entries.items()
            if e.worker_id == worker_id and e.worker_version != version
        ]
        for k in dropped:
            del self.entries[k]
        return dropped
