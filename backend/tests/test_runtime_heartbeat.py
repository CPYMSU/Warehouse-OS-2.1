from __future__ import annotations

import threading
import time
from contextlib import contextmanager

import pytest

from app import runtime_heartbeat
from app.core.config import Settings


class FakeEngine:
    def __init__(self):
        self.calls = []
        self.disposed = False
        self.fail = False

    @contextmanager
    def begin(self):
        if self.fail:
            raise RuntimeError("synthetic secret must never be logged")
        yield self

    def execute(self, statement, parameters):
        self.calls.append((str(statement), parameters))

    def dispose(self):
        self.disposed = True


@pytest.fixture
def pulse(monkeypatch, tmp_path):
    engine = FakeEngine()
    captured = {}

    def factory(url, **kwargs):
        captured.update(kwargs)
        return engine

    monkeypatch.setattr(runtime_heartbeat, "create_engine", factory)
    worker = runtime_heartbeat.RuntimeHeartbeat(Settings(_env_file=None), "synthetic")
    worker.marker = tmp_path / "ready"
    return worker, engine, captured


def test_separate_connections_have_bounded_connect_statement_and_tcp_timeouts(pulse):
    _, _, options = pulse
    assert options["poolclass"] is runtime_heartbeat.NullPool
    assert options["connect_args"]["connect_timeout"] == 3
    assert "statement_timeout=3000" in options["connect_args"]["options"]
    assert "lock_timeout=1000" in options["connect_args"]["options"]
    assert options["connect_args"]["tcp_user_timeout"] == 5000


def test_liveness_does_not_forge_progress_or_clear_errors(pulse):
    worker, engine, _ = pulse
    worker._pulse()
    sql, params = engine.calls[-1]
    assert params["stalled"] is False
    for forbidden in ("last_poll_at", "last_claim_at", "last_success_at", "last_error",
                      "lease_expires_at", "digital_asset", "deployment"):
        assert forbidden not in sql
    assert "ELSE platform.runtime_workers.status END" in sql
    assert worker.marker.exists()


def test_watchdog_marks_stalled_without_changing_task_and_recovers_on_progress(pulse):
    worker, engine, _ = pulse
    worker._progress_at = time.monotonic() - worker.progress_timeout - 1
    worker._pulse()
    assert engine.calls[-1][1]["stalled"] is True
    assert not worker.marker.exists()
    worker.progress()
    worker._pulse()
    assert engine.calls[-1][1]["stalled"] is False
    assert worker.marker.exists()


def test_failed_database_does_not_refresh_ready_marker(pulse):
    worker, engine, _ = pulse
    engine.fail = True
    with pytest.raises(RuntimeError):
        worker._pulse()
    assert not worker.marker.exists()


def test_background_liveness_continues_while_work_thread_waits_and_stops_on_exit(pulse):
    worker, engine, _ = pulse
    worker.interval = 0.005
    with worker:
        deadline = time.monotonic() + 2
        while len(engine.calls) < 3 and time.monotonic() < deadline:
            threading.Event().wait(0.005)
        assert len(engine.calls) >= 3
    assert not worker._thread.is_alive()
    assert engine.disposed
    count = len(engine.calls)
    threading.Event().wait(0.02)
    assert len(engine.calls) == count


def test_database_failure_logging_is_redacted_and_recovers(pulse, caplog):
    worker, engine, _ = pulse
    worker.interval = 0.005
    engine.fail = True
    with worker:
        deadline = time.monotonic() + 2
        while not caplog.records and time.monotonic() < deadline:
            threading.Event().wait(0.005)
        assert "RuntimeError" in caplog.text
        assert "synthetic secret" not in caplog.text
        assert not worker.marker.exists()
        engine.fail = False
        while not engine.calls and time.monotonic() < deadline:
            threading.Event().wait(0.005)
        assert engine.calls


def test_dead_owner_and_stopping_worker_cannot_refresh_marker(pulse):
    worker, engine, _ = pulse
    worker._owner = threading.Thread(target=lambda: None)
    worker._run()
    assert not engine.calls
    assert engine.disposed
    worker._stop.set()
    worker._pulse()
    assert not worker.marker.exists()


@pytest.mark.parametrize("stale,expected", [(5, 5 / 3), (30, 5), (120, 5)])
def test_interval_remains_shorter_than_normal_expiry(monkeypatch, stale, expected):
    monkeypatch.setattr(runtime_heartbeat, "create_engine", lambda *a, **k: FakeEngine())
    worker = runtime_heartbeat.RuntimeHeartbeat(
        Settings(_env_file=None, runtime_controller_stale_seconds=stale), "synthetic"
    )
    assert worker.interval == expected


@pytest.mark.parametrize("seconds", [0, 59, 86401])
def test_watchdog_configuration_is_finite_and_validated(seconds):
    with pytest.raises(ValueError):
        runtime_heartbeat.RuntimeHeartbeat(
            Settings(_env_file=None), "synthetic", progress_timeout=seconds
        )
