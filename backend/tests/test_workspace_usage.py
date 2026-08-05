from __future__ import annotations

from uuid import uuid4

from app.core.config import Settings
from app.services.workspace_usage import measure_workspace_runtime_storage


def test_runtime_and_data_occupancy_are_separated_without_following_symlinks(
    tmp_path,
) -> None:
    tenant_id = uuid4()
    workspace_id = uuid4()
    settings = Settings(hosted_runtime_data_root=tmp_path / "runtime")
    workspace = (
        settings.hosted_runtime_data_root
        / "tenants"
        / str(tenant_id)
        / "workspaces"
        / str(workspace_id)
    )
    release = workspace / "releases" / "release-1"
    runtime_cache = workspace / "data" / ".runtime" / "python"
    customer_data = workspace / "data" / "uploads"
    release.mkdir(parents=True)
    runtime_cache.mkdir(parents=True)
    customer_data.mkdir(parents=True)
    (release / "source.tar").write_bytes(b"src")
    (release / "venv.bin").write_bytes(b"venv!")
    (runtime_cache / "dependencies.bin").write_bytes(b"runtime")
    (customer_data / "customer.bin").write_bytes(b"customer-data")
    outside = tmp_path / "outside-secret"
    outside.write_bytes(b"must-not-be-counted")
    (workspace / "data" / "unsafe-link").symlink_to(outside)

    measured = measure_workspace_runtime_storage(
        settings,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
    )

    assert measured["runtime_release_bytes"] == len(b"srcvenv!runtime")
    assert measured["data_volume_bytes"] == len(b"customer-data")
    assert measured["measurement_status"] == "complete"
    assert measured["scan_error_count"] == 0
    assert measured["symlinks_followed"] is False
