"""Persist the calibration table to JSON (SQLite cutover at phase 7/8 per D14).
Reads on construction; writes on put/save. No side effects if the file is
absent."""

from __future__ import annotations

from pathlib import Path

from .table import CalibrationEntry, CalibrationTable


class CalibrationStore:
    def __init__(self, path: str | Path = "data/calibration.json") -> None:
        self.path = Path(path)
        self._table = self._load()

    def _load(self) -> CalibrationTable:
        if self.path.exists():
            return CalibrationTable.model_validate_json(self.path.read_text())
        return CalibrationTable()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self._table.model_dump_json(indent=2))

    def table(self) -> CalibrationTable:
        return self._table

    def replace(self, table: CalibrationTable) -> None:
        self._table = table
        self.save()

    def put(self, entry: CalibrationEntry) -> None:
        self._table.put(entry)
        self.save()

    def for_worker(self, worker_id: int, now: float | None = None) -> dict[str, float]:
        return self._table.for_worker(worker_id, now)
