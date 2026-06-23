"""SQLite run-trace history (D14). Timestamps are passed in by the caller
(stamped at call sites, not inside, to keep this side-effect light)."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from .types import Answer

_DDL = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY, prompt TEXT, created_at REAL, trace TEXT
)
"""


class TraceStore:
    def __init__(self, path: str | Path = "data/orchestrait.sqlite") -> None:
        self.path = str(path)
        with self._conn() as c:
            c.execute(_DDL)

    def _conn(self) -> sqlite3.Connection:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def save(self, answer: Answer, *, created_at: float) -> str:
        run_id = uuid.uuid4().hex
        with self._conn() as c:
            c.execute(
                "INSERT INTO runs (id, prompt, created_at, trace) VALUES (?,?,?,?)",
                (run_id, answer.trace.prompt, created_at, answer.model_dump_json()),
            )
        return run_id

    def get(self, run_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT trace FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, limit: int = 50) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, prompt, created_at FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"id": r[0], "prompt": r[1], "created_at": r[2]} for r in rows]
