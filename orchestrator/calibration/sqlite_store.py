"""SQLite-backed calibration store (D14 cutover). Same interface as the JSON
`CalibrationStore`, so it drops into the planner/factory unchanged."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .table import CalibrationEntry, CalibrationTable

_DDL = """
CREATE TABLE IF NOT EXISTS calibration (
    worker_id INTEGER, task_type TEXT, win_rate REAL, avg_cost REAL,
    n INTEGER, measured_at REAL, worker_version TEXT,
    PRIMARY KEY (worker_id, task_type)
)
"""
_COLS = "worker_id, task_type, win_rate, avg_cost, n, measured_at, worker_version"


class SqliteCalibrationStore:
    def __init__(self, path: str | Path = "data/orchestrait.sqlite") -> None:
        self.path = str(path)
        with self._conn() as c:
            c.execute(_DDL)

    def _conn(self) -> sqlite3.Connection:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def _row(self, e: CalibrationEntry) -> tuple:
        return (e.worker_id, e.task_type, e.win_rate, e.avg_cost, e.n, e.measured_at, e.worker_version)

    def put(self, entry: CalibrationEntry) -> None:
        with self._conn() as c:
            c.execute(f"INSERT OR REPLACE INTO calibration ({_COLS}) VALUES (?,?,?,?,?,?,?)", self._row(entry))

    def replace(self, table: CalibrationTable) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM calibration")
            c.executemany(
                f"INSERT OR REPLACE INTO calibration ({_COLS}) VALUES (?,?,?,?,?,?,?)",
                [self._row(e) for e in table.entries.values()],
            )

    def table(self) -> CalibrationTable:
        table = CalibrationTable()
        with self._conn() as c:
            for r in c.execute(f"SELECT {_COLS} FROM calibration"):
                table.put(
                    CalibrationEntry(
                        worker_id=r[0], task_type=r[1], win_rate=r[2], avg_cost=r[3],
                        n=r[4], measured_at=r[5], worker_version=r[6],
                    )
                )
        return table

    def for_worker(self, worker_id: int, now: float | None = None) -> dict[str, float]:
        return self.table().for_worker(worker_id, now)
