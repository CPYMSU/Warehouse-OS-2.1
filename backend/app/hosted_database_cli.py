"""Deployment-manager entry point for verified HDD database migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from uuid import UUID

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import system_session, tenant_session
from app.services import hosted_database
from app.services.digital_asset_hosting import (
    WORKSPACE_ALL_SCOPES,
    WorkspaceCredential,
    migrate_tenant_databases_to_hdd,
)
from app.services.hosting_fabric import apply_fabric_resource
from app.services.object_storage import object_store_read_candidates
from app.services.source_packages import inspect_source_archive
from app.services.workspace_deployments import configure_workspace_runtime

ASSET_NO_RE = re.compile(r"^DMA-[A-Z0-9-]{8,80}$")
SOURCE_PATH_RE = re.compile(r"^[A-Za-z0-9_.@/+ -]{1,240}$")
SOURCE_READ_SUFFIXES = frozenset({".ini", ".json", ".md", ".py", ".sql", ".toml", ".txt"})
WORKSPACE_JOB_SPECS = {
    "alembic-upgrade": {
        "command": "MK7_ENV=production alembic upgrade head",
        "database_url_env": "MK7_MIGRATION_DATABASE_URL",
        "timeout_seconds": 1200,
    },
    "catalog-import": {
        "command": "MK7_ENV=production mk7 catalog-import",
        "database_url_env": "MK7_MIGRATION_DATABASE_URL",
        "timeout_seconds": 1200,
    },
}


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (UUID, Path)):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _target(asset_no: str) -> tuple[UUID, dict[str, object]]:
    normalized = asset_no.strip().upper()
    if not ASSET_NO_RE.fullmatch(normalized):
        raise ValueError("Invalid digital asset number")
    with system_session() as session:
        tenant_ids = [
            UUID(str(value))
            for value in session.execute(text("SELECT id FROM iam.tenants")).scalars()
        ]
    for tenant_id in tenant_ids:
        with tenant_session(tenant_id) as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT a.id AS asset_id,a.asset_no,a.name AS asset_name,
                               w.id AS workspace_id,w.workspace_key,w.active_deployment_id
                        FROM digital_asset.assets AS a
                        JOIN digital_asset.workspaces AS w ON w.asset_id=a.id
                        WHERE a.asset_no=:asset_no AND w.status='active'
                        ORDER BY w.updated_at DESC LIMIT 1
                        """
                    ),
                    {"asset_no": normalized},
                )
                .mappings()
                .one_or_none()
            )
            if row is not None:
                return tenant_id, dict(row)
    raise ValueError("Digital asset workspace not found")


def _operator_credential(tenant_id: UUID, workspace_id: object) -> WorkspaceCredential:
    with tenant_session(tenant_id) as session:
        credential_id = session.execute(
            text(
                """
                SELECT id FROM digital_asset.api_credentials
                WHERE workspace_id=:workspace_id AND key_kind='primary'
                  AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at>now())
                ORDER BY issued_at DESC LIMIT 1
                """
            ),
            {"workspace_id": workspace_id},
        ).scalar_one_or_none()
    if credential_id is None:
        raise ValueError("Workspace has no active primary operator credential")
    return WorkspaceCredential(
        tenant_id=tenant_id,
        workspace_id=UUID(str(workspace_id)),
        credential_id=UUID(str(credential_id)),
        scopes=frozenset(WORKSPACE_ALL_SCOPES),
        label="Deployment manager database operator",
        key_kind="internal_operator",
        parent_credential_id=None,
    )


def _source_artifact(
    tenant_id: UUID, target: dict[str, object]
) -> tuple[dict[str, object], Path]:
    with tenant_session(tenant_id) as session:
        artifact = (
            session.execute(
                text(
                    """
                    SELECT ar.id,ar.version_id,ar.storage_provider,ar.object_key,
                           ar.sha256,ar.size_bytes,ar.verification,v.version_no
                    FROM digital_asset.artifacts AS ar
                    LEFT JOIN digital_asset.asset_versions AS v ON v.id=ar.version_id
                    WHERE ar.asset_id=:asset_id AND ar.storage_role='code'
                      AND ar.state='verified'
                    ORDER BY ar.created_at DESC LIMIT 1
                    """
                ),
                {"asset_id": target["asset_id"]},
            )
            .mappings()
            .one_or_none()
        )
    if artifact is None:
        raise ValueError("Workspace has no verified source artifact")
    settings = get_settings()
    for store in object_store_read_candidates(settings, str(artifact["storage_provider"])):
        path = store.path_for(str(artifact["object_key"]))
        if path.is_file():
            return dict(artifact), path
    raise ValueError("Verified source object is unavailable")


def _source_files(path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    inspect_source_archive(path, max_uncompressed_bytes=2 * 1024 * 1024 * 1024)
    selected: list[dict[str, object]] = []
    documents: dict[str, object] = {}

    def observe(name: str, size: int, content: bytes | None) -> None:
        normalized = name.replace("\\", "/").strip("/")
        basename = PurePosixPath(normalized).name.lower()
        interesting = (
            basename in {"warehouse.hosting.json", "alembic.ini"}
            or "manifest" in basename
            or "migration" in normalized.lower()
            or "/alembic/versions/" in f"/{normalized.lower()}"
            or "catalog" in basename
        )
        if not interesting:
            return
        selected.append(
            {
                "path": normalized,
                "size_bytes": int(size),
                "sha256": hashlib.sha256(content).hexdigest() if content is not None else None,
            }
        )
        if content is not None and basename.endswith(".json") and len(content) <= 1024 * 1024:
            try:
                documents[normalized] = json.loads(content)
            except (UnicodeDecodeError, json.JSONDecodeError):
                documents[normalized] = {"invalid_json": True}

    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue
                content = archive.read(item) if item.file_size <= 2 * 1024 * 1024 else None
                observe(item.filename, item.file_size, content)
    else:
        with tarfile.open(path, mode="r:*") as archive:
            for item in archive:
                if not item.isfile():
                    continue
                stream = archive.extractfile(item) if item.size <= 2 * 1024 * 1024 else None
                content = stream.read() if stream is not None else None
                observe(item.name, item.size, content)
    return sorted(selected, key=lambda item: str(item["path"])), documents


def _read_source_member_bytes(
    path: Path,
    member_path: str,
    *,
    allowed_suffixes: frozenset[str],
    max_bytes: int,
) -> tuple[str, bytes]:
    normalized = member_path.replace("\\", "/").strip("/")
    if (
        not SOURCE_PATH_RE.fullmatch(normalized)
        or ".." in PurePosixPath(normalized).parts
        or PurePosixPath(normalized).suffix.lower() not in allowed_suffixes
    ):
        raise ValueError("Source path or file type is not allowed")
    content: bytes | None = None
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            candidates = [name for name in archive.namelist() if name.strip("/") == normalized]
            if len(candidates) == 1:
                info = archive.getinfo(candidates[0])
                if info.file_size > max_bytes:
                    raise ValueError("Source member exceeds the permitted size")
                content = archive.read(info)
    else:
        with tarfile.open(path, mode="r:*") as archive:
            candidates = [
                item
                for item in archive
                if item.isfile() and item.name.strip("/") == normalized
            ]
            if len(candidates) == 1:
                if candidates[0].size > max_bytes:
                    raise ValueError("Source member exceeds the permitted size")
                stream = archive.extractfile(candidates[0])
                content = stream.read() if stream is not None else None
    if content is None:
        raise ValueError("Source member was not found")
    return normalized, content


def _read_source_member(path: Path, member_path: str) -> str:
    _normalized, content = _read_source_member_bytes(
        path,
        member_path,
        allowed_suffixes=frozenset({".sql"}),
        max_bytes=2 * 1024 * 1024,
    )
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Migration SQL must be UTF-8") from exc


def inspect_workspace(asset_no: str) -> dict[str, object]:
    tenant_id, target = _target(asset_no)
    artifact, source_path = _source_artifact(tenant_id, target)
    files, documents = _source_files(source_path)
    with tenant_session(tenant_id) as session:
        database = session.execute(
            text(
                "SELECT id,logical_name,provider_key,status,database_ref,role_ref,"
                "actual_size_bytes,size_measured_at,capabilities,config "
                "FROM digital_asset.database_bindings WHERE workspace_id=:workspace_id "
                "ORDER BY is_default DESC,created_at LIMIT 1"
            ),
            {"workspace_id": target["workspace_id"]},
        ).mappings().one_or_none()
        migrations = list(
            session.execute(
                text(
                    "SELECT version,checksum,status,error,applied_at "
                    "FROM digital_asset.database_migration_history "
                    "WHERE workspace_id=:workspace_id ORDER BY applied_at"
                ),
                {"workspace_id": target["workspace_id"]},
            ).mappings()
        )
        backups = list(
            session.execute(
                text(
                    "SELECT id,label,sha256,size_bytes,status,metadata,created_at,completed_at "
                    "FROM digital_asset.database_backups WHERE workspace_id=:workspace_id "
                    "ORDER BY created_at DESC LIMIT 10"
                ),
                {"workspace_id": target["workspace_id"]},
            ).mappings()
        )
        resources = list(
            session.execute(
                text(
                    "SELECT resource_kind,resource_key,status,desired_state,"
                    "observed_state,last_error "
                    "FROM digital_asset.hosting_resources WHERE workspace_id=:workspace_id "
                    "ORDER BY resource_kind,resource_key"
                ),
                {"workspace_id": target["workspace_id"]},
            ).mappings()
        )
        deployments = list(
            session.execute(
                text(
                    "SELECT d.id,d.revision,d.source_version_id,d.runtime_profile_key,"
                    "d.status,d.health,d.public_url,d.requested_config,d.result,"
                    "d.created_at,d.completed_at,(w.active_deployment_id=d.id) AS active "
                    "FROM digital_asset.deployments AS d "
                    "JOIN digital_asset.workspaces AS w ON w.id=d.workspace_id "
                    "WHERE d.workspace_id=:workspace_id "
                    "ORDER BY d.created_at DESC LIMIT 20"
                ),
                {"workspace_id": target["workspace_id"]},
            ).mappings()
        )
    return _json_safe(
        {
            "ok": True,
            "tenant_id": tenant_id,
            "target": target,
            "database": dict(database) if database is not None else None,
            "migrations": [dict(item) for item in migrations],
            "backups": [dict(item) for item in backups],
            "fabric_resources": [dict(item) for item in resources],
            "deployments": [dict(item) for item in deployments],
            "source": artifact,
            "source_release_files": files,
            "source_json_documents": documents,
        }
    )


def reconcile_workspace_capabilities(asset_no: str) -> dict[str, object]:
    tenant_id, target = _target(asset_no)
    with tenant_session(tenant_id) as session:
        binding = (
            session.execute(
                text(
                    "SELECT b.*,c.secret_ciphertext,c.credential_kind "
                    "FROM digital_asset.database_bindings AS b "
                    "LEFT JOIN digital_asset.database_credentials AS c "
                    "ON c.database_binding_id=b.id "
                    "WHERE b.workspace_id=:workspace_id AND b.status='ready' "
                    "ORDER BY b.is_default DESC,b.created_at LIMIT 1"
                ),
                {"workspace_id": target["workspace_id"]},
            )
            .mappings()
            .one()
        )
        evidence = hosted_database.reconcile_capabilities(session, dict(binding))
    return _json_safe({"ok": True, "target": target, "capabilities": evidence})


def backup_workspace(asset_no: str) -> dict[str, object]:
    tenant_id, target = _target(asset_no)
    credential = _operator_credential(tenant_id, target["workspace_id"])
    stamp = get_settings().environment + "-" + hashlib.sha256(asset_no.encode()).hexdigest()[:12]
    return apply_fabric_resource(
        credential,
        {
            "kind": "backup",
            "resource_key": "database",
            "spec": {
                "action": "create",
                "mode": "logical",
                "destination": "local",
                "label": f"operator-pre-release-{stamp}",
                "retention_days": 30,
            },
        },
        get_settings(),
        idempotency_key=None,
    )


def migrate_workspace_from_source(
    asset_no: str, member_path: str, version: str
) -> dict[str, object]:
    tenant_id, target = _target(asset_no)
    _artifact, source_path = _source_artifact(tenant_id, target)
    migration_sql = _read_source_member(source_path, member_path)
    credential = _operator_credential(tenant_id, target["workspace_id"])
    return apply_fabric_resource(
        credential,
        {
            "kind": "database_migration",
            "resource_key": version,
            "spec": {"version": version, "sql": migration_sql},
        },
        get_settings(),
        idempotency_key=None,
    )


def read_workspace_source_member(asset_no: str, member_path: str) -> dict[str, object]:
    tenant_id, target = _target(asset_no)
    artifact, source_path = _source_artifact(tenant_id, target)
    normalized, content = _read_source_member_bytes(
        source_path,
        member_path,
        allowed_suffixes=SOURCE_READ_SUFFIXES,
        max_bytes=512 * 1024,
    )
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Source member must be UTF-8 text") from exc
    return {
        "ok": True,
        "asset_no": target["asset_no"],
        "source_version_id": str(artifact["version_id"]),
        "path": normalized,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "content": text_content,
    }


def deploy_workspace_latest(asset_no: str) -> dict[str, object]:
    tenant_id, target = _target(asset_no)
    credential = _operator_credential(tenant_id, target["workspace_id"])
    artifact, _source_path = _source_artifact(tenant_id, target)
    return configure_workspace_runtime(
        credential,
        {
            "runtime_type": "auto",
            "deploy": True,
            "idempotency_key": f"operator-source-{artifact['version_id']}",
        },
        get_settings(),
    )


def stage_python_workspace(asset_no: str, source_version_id: str) -> dict[str, object]:
    """Create a Python 3.12 test release without changing production traffic."""

    tenant_id, target = _target(asset_no)
    try:
        source_id = UUID(source_version_id)
    except ValueError as exc:
        raise ValueError("Invalid source version id") from exc
    with tenant_session(tenant_id) as session:
        exists = session.execute(
            text(
                "SELECT 1 FROM digital_asset.asset_versions AS v "
                "JOIN digital_asset.artifacts AS ar ON ar.version_id=v.id "
                "WHERE v.id=:source_id AND v.asset_id=:asset_id "
                "AND ar.storage_role='code' AND ar.state='verified'"
            ),
            {"source_id": source_id, "asset_id": target["asset_id"]},
        ).scalar_one_or_none()
    if exists is None:
        raise ValueError("Verified source version does not belong to the target asset")
    credential = _operator_credential(tenant_id, target["workspace_id"])
    return configure_workspace_runtime(
        credential,
        {
            "runtime_type": "api",
            "runtime": "python3.12",
            "runtime_profile": "python3.12.v1",
            "source_version_id": str(source_id),
            "component": "api",
            "entrypoint": "app.py",
            "start_command": "uvicorn app:app --host 0.0.0.0 --port $PORT",
            "health_path": "/health",
            "activate": False,
            "deploy": True,
            "idempotency_key": f"operator-stage-python-{source_id}-runtime-v2",
        },
        get_settings(),
    )


def run_workspace_job(
    asset_no: str, source_version_id: str, job_kind: str
) -> dict[str, object]:
    """Run one audited source job without exposing a generic server command surface."""

    tenant_id, target = _target(asset_no)
    try:
        source_id = UUID(source_version_id)
    except ValueError as exc:
        raise ValueError("Invalid source version id") from exc
    spec = WORKSPACE_JOB_SPECS.get(job_kind)
    if spec is None:
        raise ValueError("Unsupported workspace job")
    with tenant_session(tenant_id) as session:
        exists = session.execute(
            text(
                "SELECT 1 FROM digital_asset.asset_versions AS v "
                "JOIN digital_asset.artifacts AS ar ON ar.version_id=v.id "
                "WHERE v.id=:source_id AND v.asset_id=:asset_id "
                "AND ar.storage_role='code' AND ar.state='verified'"
            ),
            {"source_id": source_id, "asset_id": target["asset_id"]},
        ).scalar_one_or_none()
    if exists is None:
        raise ValueError("Verified source version does not belong to the target asset")
    credential = _operator_credential(tenant_id, target["workspace_id"])
    return configure_workspace_runtime(
        credential,
        {
            "runtime_type": "job",
            "runtime": "python3.12",
            "runtime_profile": "python3.12.v1",
            "source_version_id": str(source_id),
            "component": f"job-{job_kind}",
            "entrypoint": "src/mk7_platform/cli.py",
            "start_command": spec["command"],
            "database_url_env": spec["database_url_env"],
            "timeout_seconds": spec["timeout_seconds"],
            "execution_mode": "job",
            "activate": False,
            "deploy": True,
            "idempotency_key": f"operator-job-{source_id}-{job_kind}-v1",
        },
        get_settings(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "migrate-tenant",
            "workspace-inspect",
            "workspace-capabilities",
            "workspace-backup",
            "workspace-migrate-source",
            "workspace-deploy",
            "workspace-stage-python",
            "workspace-job",
            "workspace-source-read",
        ),
    )
    parser.add_argument("target")
    parser.add_argument("source_path", nargs="?")
    parser.add_argument("version", nargs="?")
    args = parser.parse_args()
    if args.command == "migrate-tenant":
        result = migrate_tenant_databases_to_hdd(UUID(args.target))
    elif args.command == "workspace-inspect":
        result = inspect_workspace(args.target)
    elif args.command == "workspace-capabilities":
        result = reconcile_workspace_capabilities(args.target)
    elif args.command == "workspace-backup":
        result = backup_workspace(args.target)
    elif args.command == "workspace-deploy":
        result = deploy_workspace_latest(args.target)
    elif args.command == "workspace-stage-python":
        if not args.source_path:
            parser.error("workspace-stage-python requires source_version_id")
        result = stage_python_workspace(args.target, args.source_path)
    elif args.command == "workspace-job":
        if not args.source_path or not args.version:
            parser.error("workspace-job requires source_version_id and job_kind")
        result = run_workspace_job(args.target, args.source_path, args.version)
    elif args.command == "workspace-source-read":
        if not args.source_path:
            parser.error("workspace-source-read requires source_path")
        result = read_workspace_source_member(args.target, args.source_path)
    else:
        if not args.source_path or not args.version:
            parser.error("workspace-migrate-source requires source_path and version")
        result = migrate_workspace_from_source(args.target, args.source_path, args.version)
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
