"""Wire a `Config` into a runnable `Orchestrator`. Adapter kinds: `mock`,
`litellm`, `local_openai`, `claude_subscription`. Secrets are resolved from the
environment first (no file side effects), then the local encrypted store."""

from __future__ import annotations

import json
import os

from .config import Config
from .runtime import DefaultSynthesizer, Executor, FrontierLLMPlanner, Orchestrator
from .types import WorkerSpec
from .verify import default_registry
from .workers import (
    ClaudeSubscriptionAdapter,
    LiteLLMAdapter,
    LocalOpenAIAdapter,
    MockWorkerAdapter,
    WorkerRegistry,
)


def _make_secret_resolver():
    store = {"obj": None}

    def resolve(ref: str | None) -> str | None:
        if not ref:
            return None
        env = os.environ.get(ref)
        if env:
            return env
        if store["obj"] is None:
            from .secrets import SecretsStore

            store["obj"] = SecretsStore()
        return store["obj"].get(ref)

    return resolve


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


def build_adapter(spec: WorkerSpec, *, config: Config, workers: list[WorkerSpec], resolve_secret):
    if spec.kind == "mock":
        return MockWorkerAdapter(spec, responder=_mock_responder(spec, workers))
    if spec.kind == "litellm":
        return LiteLLMAdapter(spec, prices=config.prices, api_base=spec.api_base)
    if spec.kind == "local_openai":
        return LocalOpenAIAdapter(
            spec,
            api_base=spec.api_base or "http://localhost:11434/v1",
            api_key=resolve_secret(spec.secret_ref),
        )
    if spec.kind == "claude_subscription":
        token = resolve_secret(spec.secret_ref) or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
        return ClaudeSubscriptionAdapter(spec, oauth_token=token)
    raise ValueError(f"Unknown adapter kind '{spec.kind}'.")


def build_orchestrator(config: Config) -> Orchestrator:
    workers = config.workers
    if not workers:
        raise ValueError("No workers configured. Add a `workers:` list to config.yaml.")
    resolve_secret = _make_secret_resolver()
    adapters = [
        build_adapter(s, config=config, workers=workers, resolve_secret=resolve_secret) for s in workers
    ]
    registry = WorkerRegistry(adapters)
    conductor = registry.get(config.conductor_worker_id)
    d = config.defaults
    planner = FrontierLLMPlanner(conductor, registry, temperature=d.temperature, max_tokens=d.max_tokens)
    executor = Executor(
        registry,
        planner=planner,
        verifiers=default_registry(),
        max_tokens=d.max_tokens,
        temperature=d.temperature,
    )
    synthesizer = DefaultSynthesizer(adapter=conductor, max_tokens=d.max_tokens, temperature=d.temperature)
    return Orchestrator(registry, planner, executor, synthesizer, default_budget=d.budget)
