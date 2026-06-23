"""Maps worker ordinals to concrete adapters and describes the pool to the
planner ordinally — concrete model names are never put in the planner prompt
(worker-registry spec, §0.6)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from ..types import WorkerSpec

if TYPE_CHECKING:  # pragma: no cover
    from .adapter import WorkerAdapter


class _Calibration(Protocol):  # structural; real type lands in phase 7
    def for_worker(self, worker_id: int) -> dict[str, float]: ...


class WorkerRegistry:
    def __init__(self, adapters: list["WorkerAdapter"]) -> None:
        self._by_id: dict[int, "WorkerAdapter"] = {}
        for a in adapters:
            if a.spec.id in self._by_id:
                raise ValueError(f"Duplicate worker id {a.spec.id}")
            self._by_id[a.spec.id] = a

    def get(self, worker_id: int) -> "WorkerAdapter":
        if worker_id not in self._by_id:
            raise KeyError(f"No worker with id {worker_id}")
        return self._by_id[worker_id]

    def pool(self) -> list[WorkerSpec]:
        return [self._by_id[i].spec for i in sorted(self._by_id)]

    def describe_for_planner(self, calibration: _Calibration | None = None) -> str:
        lines: list[str] = []
        for spec in self.pool():
            caps: list[str] = []
            if calibration is not None:
                cal = calibration.for_worker(spec.id)
                caps = [f"{k} (win {v:.2f})" for k, v in sorted(cal.items(), key=lambda kv: -kv[1])]
            if not caps:
                caps = [f"{k} {v:.2f}" for k, v in sorted(spec.capabilities.items(), key=lambda kv: -kv[1])]
            cap_str = ", ".join(caps) if caps else "no priors yet"
            role = " [conductor-eligible]" if spec.conductor_eligible else ""
            lines.append(f"Model {spec.id} — {cap_str}{role}")
        return "\n".join(lines)
