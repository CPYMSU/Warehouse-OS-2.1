from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services.object_storage import LocalContentAddressedObjectStore
from app.services.workspace_retention import (
    RetentionPolicy,
    _containers_retired,
    _deployment_container_names,
    _public_plan,
    _release_path,
    _tree_bytes,
)


def test_retention_policy_has_bounded_rollback_and_source_floors() -> None:
    assert RetentionPolicy.from_payload({}).public() == {
        "keep_recent_deployments": 2,
        "keep_recent_sources": 5,
        "min_age_hours": 24,
        "include_sources": True,
        "include_expired_uploads": True,
    }
    assert RetentionPolicy.from_payload({"min_age_hours": 0}).min_age_hours == 0
    with pytest.raises(HTTPException) as deployment_floor:
        RetentionPolicy.from_payload({"keep_recent_deployments": 1})
    assert deployment_floor.value.status_code == 422
    with pytest.raises(HTTPException) as source_floor:
        RetentionPolicy.from_payload({"keep_recent_sources": 1})
    assert source_floor.value.status_code == 422


def test_release_path_and_tree_measurement_stay_inside_workspace(tmp_path: Path) -> None:
    settings = Settings(hosted_runtime_data_root=tmp_path / "runtime")
    tenant_id = uuid4()
    workspace_id = uuid4()
    deployment_id = uuid4()
    target = _release_path(
        settings,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        deployment_id=deployment_id,
    )
    target.mkdir(parents=True)
    (target / "source.bin").write_bytes(b"source")
    nested = target / "nested"
    nested.mkdir()
    (nested / "runtime.bin").write_bytes(b"runtime")
    assert _tree_bytes(target) == len(b"source") + len(b"runtime")
    assert target.name == str(deployment_id)
    assert str(workspace_id) in target.parts


def test_content_addressed_retirement_requires_exact_tenant_digest_key(
    tmp_path: Path,
) -> None:
    store = LocalContentAddressedObjectStore(tmp_path / "objects")
    tenant_id = uuid4()
    digest = "a" * 64
    object_key = store.object_key_for_sha256(tenant_id, digest)
    target = store.path_for(object_key)
    target.parent.mkdir(parents=True)
    target.write_bytes(b"immutable")
    with pytest.raises(RuntimeError, match="does not match"):
        store.retire_content_addressed_object(
            tenant_id=tenant_id,
            object_key=object_key,
            sha256="b" * 64,
        )
    assert target.is_file()
    assert (
        store.retire_content_addressed_object(
            tenant_id=tenant_id,
            object_key=object_key,
            sha256=digest,
        )
        == len(b"immutable")
    )
    assert not target.exists()
    assert (
        store.retire_content_addressed_object(
            tenant_id=tenant_id,
            object_key=object_key,
            sha256=digest,
        )
        == 0
    )


def test_public_plan_never_exposes_host_paths_or_container_names() -> None:
    plan = {
        "deployment_candidates": [
            {
                "id": str(uuid4()),
                "estimated_runtime_bytes": 12,
                "_path": "/private/runtime/path",
                "_container_names": ["warehouse-runtime-private"],
            }
        ],
        "source_candidates": [
            {
                "artifact_id": str(uuid4()),
                "logical_bytes": 34,
                "_object_key": "tenants/private/object",
                "_sha256": "a" * 64,
            }
        ],
        "expired_uploads": [
            {"upload_id": str(uuid4()), "received_bytes": 56, "_provider": "private"}
        ],
    }
    public = _public_plan(plan)
    rendered = str(public)
    assert "/private/runtime/path" not in rendered
    assert "warehouse-runtime-private" not in rendered
    assert "tenants/private/object" not in rendered
    assert "_provider" not in rendered


def test_runtime_container_filter_is_bound_to_candidate_deployment() -> None:
    deployment_id = uuid4()
    expected_prefix = f"warehouse-runtime-{str(deployment_id).replace('-', '')[:16]}"
    other_id = uuid4()
    other_name = f"warehouse-runtime-{str(other_id).replace('-', '')[:20]}"
    own_name = f"{expected_prefix}-web-0"

    assert _deployment_container_names(
        deployment_id,
        [own_name, other_name, "unmanaged-container", None],
    ) == [own_name]


def test_runtime_directory_waits_for_controller_container_acknowledgement() -> None:
    assert _containers_retired({"retention": {"state": "retry_required"}}) is False
    assert (
        _containers_retired(
            {
                "retention": {
                    "state": "retry_required",
                    "containers_retired_at": "2026-08-28T12:00:00+00:00",
                }
            }
        )
        is True
    )
