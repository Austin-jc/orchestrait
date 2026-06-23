"""Eval / proof mode (calibration-and-eval spec). Scores the orchestrator
against each single worker on a held-out bank and reports the delta, anchored to
Baseline A (orchestrating a model vs single-shot use of the same model)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..types import Step
from .bank import Task


class TypeEval(BaseModel):
    task_type: str
    n: int
    orchestrator: float
    workers: dict[int, float]


class EvalReport(BaseModel):
    n: int
    orchestrator: float
    workers: dict[int, float]                 # worker_id -> single-shot win-rate
    best_single_id: int | None = None
    best_single: float = 0.0
    delta_vs_best: float = 0.0
    baseline_worker_id: int | None = None     # the "same model" anchor (Baseline A)
    delta_vs_baseline: float = 0.0
    by_type: list[TypeEval] = Field(default_factory=list)


async def _passes(verifiers, task: Task, output: str) -> bool:
    verifier = verifiers.get(task.verifier)
    verdict = await verifier.verify(
        Step(worker_id=-1, subtask=task.prompt, verifier=task.verifier, expected=task.expected), output
    )
    return verdict.passed


async def evaluate(orchestrator, registry, bank: list[Task], verifiers, *, baseline_worker_id: int | None = None, budget=None) -> EvalReport:
    worker_ids = [s.id for s in registry.pool()]
    orch_wins = 0
    worker_wins = {wid: 0 for wid in worker_ids}
    acc: dict[str, dict] = {}
    n = len(bank)

    for task in bank:
        t = acc.setdefault(task.task_type, {"orch": 0, "workers": {w: 0 for w in worker_ids}, "n": 0})
        t["n"] += 1

        answer = await orchestrator.run(task.prompt, budget=budget)
        if await _passes(verifiers, task, answer.text):
            orch_wins += 1
            t["orch"] += 1

        for wid in worker_ids:
            output, _ = await registry.get(wid).call(
                [{"role": "user", "content": task.prompt}], max_tokens=512, temperature=0.0
            )
            if await _passes(verifiers, task, output):
                worker_wins[wid] += 1
                t["workers"][wid] += 1

    workers_rate = {wid: (w / n if n else 0.0) for wid, w in worker_wins.items()}
    best_id = max(workers_rate, key=workers_rate.get) if workers_rate else None
    best = workers_rate.get(best_id, 0.0) if best_id is not None else 0.0
    orch_rate = orch_wins / n if n else 0.0
    by_type = [
        TypeEval(
            task_type=tt,
            n=d["n"],
            orchestrator=d["orch"] / d["n"],
            workers={k: v / d["n"] for k, v in d["workers"].items()},
        )
        for tt, d in acc.items()
    ]
    baseline_rate = workers_rate.get(baseline_worker_id, 0.0) if baseline_worker_id is not None else 0.0
    return EvalReport(
        n=n,
        orchestrator=orch_rate,
        workers=workers_rate,
        best_single_id=best_id,
        best_single=best,
        delta_vs_best=orch_rate - best,
        baseline_worker_id=baseline_worker_id,
        delta_vs_baseline=(orch_rate - baseline_rate) if baseline_worker_id is not None else 0.0,
        by_type=by_type,
    )
