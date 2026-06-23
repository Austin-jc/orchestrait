"""FastAPI surface (api spec / task 4.3):
- POST /v1/chat/completions  — OpenAI-compatible; point existing clients here.
- POST /run                  — run and return the Answer (+trace).
- POST /run/stream           — Server-Sent Events of the live run.
- GET  /health, GET /workers — basics for the UI.

FastAPI/uvicorn are optional deps (`pip install -e '.[api]'`); they're imported
inside `create_app` so the rest of the package doesn't require them.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid

from pydantic import BaseModel, Field

from ..calibration import SqliteCalibrationStore
from ..config import load_config
from ..events import EventBus
from ..factory import build_orchestrator
from ..measurement import evaluate, load_bank, measure
from ..persistence import TraceStore
from ..verify import default_registry


class ChatRequest(BaseModel):
    model: str | None = "orchestrait"
    messages: list[dict] = Field(default_factory=list)
    x_orchestrator_debug: bool = False


class RunRequest(BaseModel):
    prompt: str


def _prompt_from_messages(messages: list[dict]) -> str:
    users = [m.get("content", "") for m in messages if m.get("role") == "user"]
    if users:
        return users[-1]
    return "\n\n".join(m.get("content", "") for m in messages)


def create_app(orchestrator=None):
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse, StreamingResponse

    from fastapi import HTTPException

    app = FastAPI(title="Orchestrait", version="0.1.0")
    store = SqliteCalibrationStore()
    traces = TraceStore()
    orch = orchestrator or build_orchestrator(load_config(), calibration=store)
    verifiers = default_registry()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/workers")
    async def workers():
        return {"workers": [s.model_dump() for s in orch.registry.pool()]}

    @app.get("/calibration")
    async def calibration():
        return store.table().model_dump()

    @app.post("/measure")
    async def run_measure():
        table = await measure(orch.registry, load_bank(), verifiers)
        store.replace(table)
        return table.model_dump()

    @app.post("/eval")
    async def run_eval():
        baseline = orch.planner.conductor.spec.id
        report = await evaluate(
            orch, orch.registry, load_bank(), verifiers, baseline_worker_id=baseline
        )
        return report.model_dump()

    @app.post("/v1/chat/completions")
    async def chat_completions(body: ChatRequest):
        answer = await orch.run(_prompt_from_messages(body.messages))
        tin = sum(r.usage.tokens_in for r in answer.trace.results)
        tout = sum(r.usage.tokens_out for r in answer.trace.results)
        resp = {
            "id": f"orchestrait-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "model": body.model or "orchestrait",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": answer.text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": tin, "completion_tokens": tout, "total_tokens": tin + tout},
        }
        if body.x_orchestrator_debug:
            resp["x_orchestrator_trace"] = answer.trace.model_dump()
        return JSONResponse(resp)

    @app.post("/run")
    async def run(body: RunRequest):
        answer = await orch.run(body.prompt)
        run_id = traces.save(answer, created_at=time.time())
        payload = answer.model_dump()
        payload["run_id"] = run_id
        return JSONResponse(payload)

    @app.get("/runs")
    async def runs():
        return {"runs": traces.list()}

    @app.get("/runs/{run_id}")
    async def get_run(run_id: str):
        trace = traces.get(run_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="run not found")
        return trace

    @app.post("/run/stream")
    async def run_stream(body: RunRequest):
        bus = EventBus()

        async def gen():
            task = asyncio.create_task(orch.run(body.prompt, bus=bus))
            try:
                async for event in bus.stream():
                    yield f"data: {json.dumps(event)}\n\n"
            finally:
                await task

        return StreamingResponse(gen(), media_type="text/event-stream")

    return app


def main() -> None:  # pragma: no cover - server entrypoint
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8000)


if __name__ == "__main__":  # pragma: no cover
    main()
