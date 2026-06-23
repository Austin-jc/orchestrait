"""Wire a `Config` into a runnable `Orchestrator`. For M1 only `mock` and
`litellm` adapters are available; phase 3 adds `local_openai` and
`claude_subscription`."""

from __future__ import annotations

import json

from .config import Config
from .runtime import DefaultSynthesizer, Executor, FrontierLLMPlanner, Orchestrator
from .types import WorkerSpec
from .workers import LiteLLMAdapter, MockWorkerAdapter, WorkerRegistry


def _mock_responder(spec: WorkerSpec, workers: list[WorkerSpec]):
    """Returns a valid single-step plan for planning calls, else a canned
    worker reply — enough for a no-network smoke test of the full loop."""
    target = next((w.id for w in workers if w.id != spec.id), spec.id)
    plan_json = json.dumps(
        {
            "reasoning": "Single step suffices for the mock demo.",
            "steps": [
                {"worker_id": target, "subtask": "Answer the user's prompt.", "access": [], "primitive": "normal"}
            ],
            "budget": {},
        }
    )

    def responder(messages: list[dict]) -> str:
        system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
        if "planning conductor" in system:
            return plan_json
        last = messages[-1]["content"] if messages else ""
        return f"[{spec.name}] {last}"

    return responder


def build_adapter(spec: WorkerSpec, *, config: Config, workers: list[WorkerSpec]):
    if spec.kind == "mock":
        return MockWorkerAdapter(spec, responder=_mock_responder(spec, workers))
    if spec.kind == "litellm":
        return LiteLLMAdapter(spec, prices=config.prices)
    raise ValueError(
        f"Adapter kind '{spec.kind}' is not available yet "
        f"(phase 3 adds local_openai and claude_subscription)."
    )


def build_orchestrator(config: Config) -> Orchestrator:
    workers = config.workers
    if not workers:
        raise ValueError("No workers configured. Add a `workers:` list to config.yaml.")
    adapters = [build_adapter(s, config=config, workers=workers) for s in workers]
    registry = WorkerRegistry(adapters)
    conductor = registry.get(config.conductor_worker_id)
    d = config.defaults
    planner = FrontierLLMPlanner(conductor, registry, temperature=d.temperature, max_tokens=d.max_tokens)
    executor = Executor(registry, max_tokens=d.max_tokens, temperature=d.temperature)
    synthesizer = DefaultSynthesizer(adapter=conductor, max_tokens=d.max_tokens, temperature=d.temperature)
    return Orchestrator(registry, planner, executor, synthesizer, default_budget=d.budget)
