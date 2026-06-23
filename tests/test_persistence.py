import time

from orchestrator.calibration import CalibrationEntry, CalibrationTable, SqliteCalibrationStore
from orchestrator.persistence import TraceStore
from orchestrator.types import Answer, RunTrace


def test_sqlite_calibration_roundtrip(tmp_path):
    s = SqliteCalibrationStore(path=tmp_path / "o.sqlite")
    s.put(CalibrationEntry(worker_id=2, task_type="math", win_rate=0.75, n=4, measured_at=time.time()))
    reloaded = SqliteCalibrationStore(path=tmp_path / "o.sqlite").table().get(2, "math")
    assert reloaded.win_rate == 0.75 and reloaded.n == 4


def test_sqlite_replace_and_for_worker(tmp_path):
    s = SqliteCalibrationStore(path=tmp_path / "o.sqlite")
    table = CalibrationTable()
    table.put(CalibrationEntry(worker_id=0, task_type="mcq", win_rate=1.0, measured_at=0.0))
    s.replace(table)
    assert s.for_worker(0, now=0.0) == {"mcq": 1.0}


def test_trace_store_roundtrip(tmp_path):
    ts = TraceStore(path=tmp_path / "o.sqlite")
    rid = ts.save(Answer(text="hi", trace=RunTrace(prompt="q")), created_at=123.0)
    got = ts.get(rid)
    assert got["text"] == "hi" and got["trace"]["prompt"] == "q"
    assert ts.list()[0]["id"] == rid
