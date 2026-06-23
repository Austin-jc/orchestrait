"""Reconstruct a RunTrace from an emitted event log — proving the live stream
and the persisted trace are the same data at different times
(run-observability spec)."""

from __future__ import annotations

from .types import Plan, RunTrace, StepResult


def trace_from_events(prompt: str, events: list[dict]) -> RunTrace:
    plan: Plan | None = None
    results: list[StepResult] = []
    totals: dict = {}
    budget_hit: str | None = None
    for ev in events:
        t = ev.get("type")
        if t == "plan_ready" and ev.get("plan") is not None:
            plan = Plan.model_validate(ev["plan"])
        elif t == "step_done":
            results.append(StepResult.model_validate(ev["result"]))
        elif t == "run_done":
            totals = ev.get("totals") or {}
            budget_hit = ev.get("budget_hit")
    return RunTrace(
        prompt=prompt,
        plan=plan,
        results=results,
        total_usd=totals.get("usd", 0.0),
        total_wall_seconds=totals.get("wall_seconds", 0.0),
        total_subscription_prompts=totals.get("subscription_prompts", 0),
        budget_hit=budget_hit,
        events=list(events),
    )
