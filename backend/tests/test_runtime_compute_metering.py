from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from app import runtime_controller_base as base
from app.core.config import Settings


def test_runtime_controller_records_interval_compute_usage_without_breaking_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = UUID("00000000-0000-0000-0000-000000000101")
    workspace_id = UUID("00000000-0000-0000-0000-000000000102")
    deployment_id = UUID("00000000-0000-0000-0000-000000000103")
    container_name = "warehouse-runtime-metered"
    controller = base.RuntimeController(Settings())
    controller._last_compute_usage_reconcile = -1000
    controller._compute_usage_samples[
        f"{deployment_id}:{container_name}"
    ] = (
        datetime.now(UTC) - timedelta(seconds=60),
        {
            "cpu_seconds_total": 10.0,
            "memory_bytes": 1 * 1024 * 1024,
            "network_bytes_total": 100.0,
            "gpu_seconds_total": 0.0,
        },
    )
    monkeypatch.setattr(
        controller,
        "_compute_usage_candidates",
        lambda: [
            {
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "deployment_id": deployment_id,
                "compute_node": "warehouse",
                "container_names": [container_name],
            }
        ],
    )

    class _Engine:
        def __init__(self, _socket: Path) -> None:
            pass

        def resource_usage(self, _name: str) -> dict[str, float]:
            return {
                "cpu_seconds_total": 12.0,
                "memory_bytes": 2 * 1024 * 1024,
                "network_bytes_total": 200.0,
                "gpu_seconds_total": 0.0,
            }

        def close(self) -> None:
            pass

    records: list[tuple[UUID, UUID, dict[str, object]]] = []
    monkeypatch.setattr(base, "DockerEngine", _Engine)
    monkeypatch.setattr(
        base,
        "record_compute_usage",
        lambda tenant, workspace, payload: records.append((tenant, workspace, payload))
        or {"ok": True},
    )

    assert controller.reconcile_compute_usage() == 1
    assert len(records) == 1
    tenant, workspace, payload = records[0]
    assert tenant == tenant_id
    assert workspace == workspace_id
    assert payload["deployment_id"] == str(deployment_id)
    assert payload["compute_node"] == "warehouse"
    assert payload["cpu_seconds"] == pytest.approx(2.0)
    assert payload["network_bytes"] == 100
    assert payload["memory_mb_seconds"] == pytest.approx(120.0, abs=2.0)
    assert payload["metering_source"] == "runtime"
    assert payload["notify_ai"] is False
