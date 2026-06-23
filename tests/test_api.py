import json

import pytest

from orchestrator.config import Config
from orchestrator.factory import build_orchestrator
from orchestrator.types import WorkerSpec

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from orchestrator.api.server import create_app  # noqa: E402


def _client():
    cfg = Config(
        workers=[WorkerSpec(id=0, name="a", kind="mock"), WorkerSpec(id=1, name="b", kind="mock")],
        conductor_worker_id=0,
    )
    return TestClient(create_app(build_orchestrator(cfg)))


def test_openai_compatible_chat_completions():
    c = _client()
    r = c.post(
        "/v1/chat/completions",
        json={"model": "x", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert body["choices"][0]["message"]["content"].startswith("[b]")
    assert "x_orchestrator_trace" not in body


def test_chat_completions_debug_includes_trace():
    c = _client()
    r = c.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hi"}], "x_orchestrator_debug": True},
    )
    assert "x_orchestrator_trace" in r.json()


def test_run_endpoint_returns_trace():
    r = _client().post("/run", json={"prompt": "hi"})
    assert r.status_code == 200
    assert r.json()["trace"]["plan"]["steps"][0]["worker_id"] == 1


def test_run_stream_emits_sse_events():
    with _client().stream("POST", "/run/stream", json={"prompt": "hi"}) as r:
        assert r.status_code == 200
        types = []
        for line in r.iter_lines():
            if line and line.startswith("data: "):
                types.append(json.loads(line[len("data: "):])["type"])
    assert types[0] == "run_started"
    assert types[-1] == "run_done"
    assert "step_done" in types


def test_workers_endpoint():
    r = _client().get("/workers")
    assert r.status_code == 200
    assert len(r.json()["workers"]) == 2
