"""Explicit disposable-database checks; never use the ordinary application DSN."""
from __future__ import annotations

import os
import re
import threading
import time

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.runtime_heartbeat import RuntimeHeartbeat

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def db():
    url = os.environ.get("WAREHOUSE_HEARTBEAT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("requires dedicated heartbeat_test database")
    parsed = make_url(url)
    assert parsed.host == "127.0.0.1"
    assert re.fullmatch(r"heartbeat_test(?:_r[0-9]+)?", parsed.database or "")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA platform"))
        conn.execute(text("""
            CREATE TABLE platform.runtime_workers (
              worker_id text PRIMARY KEY, provider_key text NOT NULL, release_id text,
              status text NOT NULL DEFAULT 'online'
                CHECK (status IN ('online','degraded','draining')),
              started_at timestamptz NOT NULL DEFAULT now(),
              last_seen_at timestamptz NOT NULL DEFAULT now(), last_poll_at timestamptz,
              last_claim_at timestamptz, last_success_at timestamptz, last_error text,
              metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
              updated_at timestamptz NOT NULL DEFAULT now()
            )
        """))
    yield url, engine
    engine.dispose()


def test_real_long_task_preserves_work_timestamps_and_remains_online(db, tmp_path):
    url, engine = db
    worker = RuntimeHeartbeat(Settings(_env_file=None, database_url=url), "long-task")
    worker.marker = tmp_path / "ready"
    with worker:
        # A real >30s blocked work phase, with real background database updates.
        deadline = time.monotonic() + 36
        samples = []
        while time.monotonic() < deadline:
            threading.Event().wait(1)
            with engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT last_seen_at > now() - interval '30 seconds' AS fresh,
                           last_poll_at,last_claim_at,last_success_at,last_error
                    FROM platform.runtime_workers WHERE worker_id='long-task'
                """)).one()
                samples.append(row.fresh)
                assert tuple(row)[1:] == (None, None, None, None)
        assert len(samples) >= 30 and all(samples)
        assert worker.marker.exists()
    assert not worker._thread.is_alive()


@pytest.mark.parametrize("status", ["degraded", "draining"])
def test_real_upsert_preserves_errors_progress_and_existing_status(db, tmp_path, status):
    url, engine = db
    worker = RuntimeHeartbeat(Settings(_env_file=None, database_url=url), status)
    worker.marker = tmp_path / "ready"
    worker._pulse()
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE platform.runtime_workers SET status=:status,last_error='keep-error',
                last_poll_at='2020-01-01 00:00:00+00',
                last_claim_at='2020-01-01 00:00:00+00',
                last_success_at='2020-01-01 00:00:00+00',
                metadata=jsonb_build_object('keep',true)
            WHERE worker_id=:status
        """), {"status": status})
    worker._pulse()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT status,last_error,extract(year from last_poll_at),
                extract(year from last_claim_at),extract(year from last_success_at),metadata
            FROM platform.runtime_workers WHERE worker_id=:status
        """), {"status": status}).one()
        assert tuple(row)[:5] == (status, "keep-error", 2020, 2020, 2020)
        assert row.metadata["keep"] is True
    worker.engine.dispose()


def test_real_lock_contention_is_bounded_and_next_pulse_recovers(db, tmp_path):
    url, engine = db
    worker = RuntimeHeartbeat(Settings(_env_file=None, database_url=url), "locked")
    worker.marker = tmp_path / "ready"
    worker._pulse()
    before = worker.marker.stat().st_mtime_ns
    with engine.begin() as blocker:
        blocker.execute(text("SELECT 1 FROM platform.runtime_workers "
                             "WHERE worker_id='locked' FOR UPDATE"))
        started = time.monotonic()
        with pytest.raises(Exception):
            worker._pulse()
        assert time.monotonic() - started < 5
        assert worker.marker.stat().st_mtime_ns == before
    worker._pulse()
    assert worker.marker.stat().st_mtime_ns > before
    worker.engine.dispose()
