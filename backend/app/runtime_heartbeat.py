"""Bounded process liveness, separate from controller work and task leases."""

from __future__ import annotations

import logging
import os
import socket
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.core.config import Settings

logger = logging.getLogger(__name__)


class RuntimeHeartbeat:
    """One daemon and dedicated, bounded connections; never claim or complete work."""

    def __init__(
        self, settings: Settings, worker_id: str, *, progress_timeout: int = 10800
    ) -> None:
        # One phase can include a supported 2h job plus image preparation.
        # This watchdog is distinct from the unchanged 30s liveness threshold.
        if not 60 <= progress_timeout <= 86400:
            raise ValueError("progress timeout must be 60..86400 seconds")
        self.worker_id = worker_id
        self.interval = min(5.0, max(0.25, settings.runtime_controller_stale_seconds / 3))
        self.progress_timeout = progress_timeout
        self.marker = Path("/tmp/runtime-controller-ready")
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._progress_at = time.monotonic()
        self._owner = threading.current_thread()
        # No shared Session or pool with the work loop. Do not log connection errors:
        # driver exceptions can contain DSNs. A lost connection remains observable
        # through normal heartbeat expiry, not an unbounded local retry loop.
        self.engine = create_engine(
            settings.database_url,
            poolclass=NullPool,
            connect_args={
                "connect_timeout": 3,
                "options": "-c statement_timeout=3000 -c lock_timeout=1000",
                "keepalives": 1,
                "keepalives_idle": 5,
                "keepalives_interval": 1,
                "keepalives_count": 2,
                "tcp_user_timeout": 5000,
            },
        )
        self._thread = threading.Thread(
            target=self._run, name="runtime-liveness", daemon=True
        )

    def progress(self) -> None:
        """Only called by the work thread after a real phase returns."""
        with self._lock:
            self._progress_at = time.monotonic()

    def _pulse(self) -> None:
        with self._lock:
            stalled = time.monotonic() - self._progress_at >= self.progress_timeout
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO platform.runtime_workers(
                      worker_id, provider_key, release_id, status, last_seen_at, metadata
                    ) VALUES (
                      :worker, 'warehouse_runtime_v1', :release,
                      CASE WHEN :stalled THEN 'degraded' ELSE 'online' END, now(),
                      jsonb_build_object('hostname', CAST(:hostname AS text),
                        'progress_watchdog_stalled', CAST(:stalled AS boolean))
                    )
                    ON CONFLICT (worker_id) DO UPDATE SET
                      last_seen_at=now(), updated_at=now(),
                      status=CASE WHEN :stalled THEN 'degraded'
                        ELSE platform.runtime_workers.status END,
                      metadata=platform.runtime_workers.metadata ||
                        jsonb_build_object('progress_watchdog_stalled',
                          CAST(:stalled AS boolean))
                    """
                ),
                {"worker": self.worker_id, "release": os.getenv("WAREHOUSE_RELEASE_ID"),
                 "hostname": socket.gethostname(), "stalled": stalled},
            )
        if not stalled and not self._stop.is_set() and self._owner.is_alive():
            self.marker.write_text(
                f"{self.worker_id} {datetime.now(UTC).isoformat()}", encoding="utf-8"
            )

    def _run(self) -> None:
        try:
            while not self._stop.is_set() and self._owner.is_alive():
                try:
                    self._pulse()
                except Exception as exc:
                    logger.warning("Runtime liveness update failed (%s)", type(exc).__name__)
                if self._stop.wait(self.interval):
                    break
        finally:
            self.engine.dispose()

    def __enter__(self) -> RuntimeHeartbeat:
        self._thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        self._stop.set()
        self._thread.join(timeout=10)
