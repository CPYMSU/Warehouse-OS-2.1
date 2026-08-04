from __future__ import annotations

import io
import json
import tarfile

import pytest
from fastapi import HTTPException

from app.services.deployment_acceptance import _json_pointer, _lifecycle_evidence
from app.services.hosting_compatibility import (
    HOSTING_SCHEMA,
    LEGACY_HOSTING_SCHEMA,
    declared_lifecycle_job,
    manifest_runtime_defaults,
    validate_hosting_manifest,
)
from app.services.source_packages import inspect_source_archive
from app.services.workspace_deployments import _acceptance_ready_for_activation


def _manifest() -> dict[str, object]:
    return {
        "schema": HOSTING_SCHEMA,
        "runtime": {
            "type": "api",
            "runtime": "python3.12",
            "entrypoint": "src/app.py",
            "build_command": "python -m pip install .",
            "start_command": "uvicorn app:app --host 0.0.0.0 --port $PORT",
            "health_path": "/healthz",
        },
        "data": {
            "persistent_path": "/workspace/data",
            "database_policy": "platform_managed",
            "runtime_database_url_env": "DATABASE_URL",
            "migration_database_url_env": "APP_MIGRATION_DATABASE_URL",
        },
        "lifecycle": {
            "jobs": [
                {
                    "name": "migrate",
                    "command": "alembic upgrade head",
                    "database_access": "migration",
                    "required_before_activation": True,
                }
            ]
        },
        "acceptance": {
            "required_before_activation": True,
            "http": [
                {
                    "name": "modules",
                    "path": "/api/v1/modules",
                    "operator": "length_equals",
                    "expected": 8,
                }
            ],
            "database": {
                "context": {
                    "app.tenant_id": "00000000-0000-4000-8000-000000000001"
                },
                "counts": [
                    {
                        "name": "resources",
                        "schema": "catalog",
                        "relation": "learning_resources",
                        "expected": 2,
                    }
                ],
            },
        },
        "deployment": {
            "strategy": "staged",
            "retain_previous": True,
            "require_acceptance_before_activation": True,
        },
    }


def test_v23_manifest_normalizes_runtime_jobs_and_acceptance() -> None:
    manifest = validate_hosting_manifest(
        _manifest(),
        source_paths={"src/app.py", "warehouse.hosting.json"},
    )

    assert manifest["schema"] == HOSTING_SCHEMA
    assert len(str(manifest["contract_digest"])) == 64
    assert manifest["deployment"] == {
        "strategy": "staged",
        "activate_when_healthy": False,
        "retain_previous": True,
        "require_acceptance_before_activation": True,
    }
    defaults = manifest_runtime_defaults(manifest)
    assert defaults["runtime_type"] == "api"
    assert defaults["entrypoint"] == "src/app.py"
    assert defaults["database_url_env"] == "DATABASE_URL"
    assert defaults["activate"] is False
    job = declared_lifecycle_job(manifest, "migrate")
    assert job is not None
    assert job["database_access"] == "migration"
    assert job["database_url_env"] == "APP_MIGRATION_DATABASE_URL"


def test_v22_manifest_remains_valid_but_cannot_claim_v23_lifecycle() -> None:
    legacy = {
        "schema": LEGACY_HOSTING_SCHEMA,
        "runtime": {"type": "static", "health_path": "/"},
        "data": {"persistent_path": "/workspace/data", "database_policy": "none"},
    }
    normalized = validate_hosting_manifest(legacy)
    assert normalized["schema"] == LEGACY_HOSTING_SCHEMA
    assert normalized["lifecycle"] == {"jobs": []}

    legacy["lifecycle"] = {"jobs": []}
    with pytest.raises(HTTPException) as raised:
        validate_hosting_manifest(legacy)
    assert raised.value.detail["reason"] == "hosting_manifest_invalid"


def test_manifest_rejects_source_entrypoint_that_is_not_in_archive() -> None:
    with pytest.raises(HTTPException) as raised:
        validate_hosting_manifest(
            _manifest(),
            source_paths={"warehouse.hosting.json", "src/other.py"},
        )
    assert raised.value.detail["field"] == "runtime.entrypoint"


def test_source_archive_promotes_manifest_to_verified_signals(tmp_path) -> None:
    archive_path = tmp_path / "source.tar.gz"
    members = {
        "warehouse.hosting.json": json.dumps(_manifest()).encode(),
        "src/app.py": b"app = object()\n",
    }
    with tarfile.open(archive_path, "w:gz") as archive:
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))

    archive = inspect_source_archive(archive_path, max_uncompressed_bytes=1024 * 1024)

    assert archive.signals["hosting_contract"]["declared"] is True
    assert archive.signals["hosting_contract"]["schema"] == HOSTING_SCHEMA
    manifest = archive.signals["hosting_manifest"]
    assert manifest["acceptance"]["database"]["connection"] == "runtime"


def test_acceptance_helpers_bind_json_and_required_job_to_contract_digest() -> None:
    contract = validate_hosting_manifest(
        _manifest(),
        source_paths={"src/app.py", "warehouse.hosting.json"},
    )
    assert _json_pointer({"data": {"items": [1, 2]}}, "/data/items") == [1, 2]
    evidence, failures = _lifecycle_evidence(
        [
            {
                "id": "job-1",
                "status": "ready",
                "health": "healthy",
                "requested_config": {
                    "lifecycle_job": {
                        "name": "migrate",
                        "contract_digest": contract["contract_digest"],
                    }
                },
            }
        ],
        contract,
    )
    assert failures == []
    assert evidence == [{"name": "migrate", "accepted": True, "deployment_id": "job-1"}]


def test_activation_rejects_stale_or_cross_source_acceptance_evidence() -> None:
    deployment = {
        "source_version_id": "source-v2",
        "requested_config": {
            "compatibility_contract": {
                "contract_digest": "contract-v2",
                "deployment": {"require_acceptance_before_activation": True},
            }
        },
        "result": {
            "acceptance": {
                "accepted": True,
                "source_version_id": "source-v1",
                "contract_digest": "contract-v2",
            }
        },
    }
    assert _acceptance_ready_for_activation(deployment) is False

    deployment["result"]["acceptance"]["source_version_id"] = "source-v2"
    deployment["result"]["acceptance"]["contract_digest"] = "contract-v1"
    assert _acceptance_ready_for_activation(deployment) is False

    deployment["result"]["acceptance"]["contract_digest"] = "contract-v2"
    assert _acceptance_ready_for_activation(deployment) is True
