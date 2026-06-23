"""Verifiable task bank for measurement + eval. Code-task `expected` paths are
resolved relative to the bank file."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class Task(BaseModel):
    id: str
    task_type: str
    prompt: str
    verifier: str
    expected: str | None = None


def load_bank(path: str | Path = "tasks/bank.json") -> list[Task]:
    p = Path(path)
    if not p.exists():
        return []
    raw = json.loads(p.read_text())
    items = raw.get("tasks", raw) if isinstance(raw, dict) else raw
    base = p.parent
    tasks: list[Task] = []
    for item in items:
        task = Task(**item)
        if task.verifier == "code_exec" and task.expected and not Path(task.expected).is_absolute():
            task.expected = str((base / task.expected).resolve())
        tasks.append(task)
    return tasks
