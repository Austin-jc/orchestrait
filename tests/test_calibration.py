import time

from orchestrator.calibration import CalibrationEntry, CalibrationStore, CalibrationTable


def test_for_worker_filters_stale_entries():
    t = CalibrationTable(ttl_seconds=100)
    now = 1000.0
    t.put(CalibrationEntry(worker_id=0, task_type="math", win_rate=0.8, measured_at=now))
    t.put(CalibrationEntry(worker_id=0, task_type="code", win_rate=0.5, measured_at=now - 200))
    assert t.for_worker(0, now=now) == {"math": 0.8}  # stale 'code' excluded


def test_version_change_invalidates_entries():
    t = CalibrationTable()
    t.put(CalibrationEntry(worker_id=0, task_type="math", win_rate=0.8, worker_version="v1"))
    dropped = t.invalidate_for_version(0, "v2")
    assert len(dropped) == 1
    assert t.get(0, "math") is None


def test_store_roundtrip(tmp_path):
    s = CalibrationStore(path=tmp_path / "cal.json")
    s.put(CalibrationEntry(worker_id=1, task_type="mcq", win_rate=0.9, measured_at=time.time()))
    reloaded = CalibrationStore(path=tmp_path / "cal.json")
    assert reloaded.table().get(1, "mcq").win_rate == 0.9
