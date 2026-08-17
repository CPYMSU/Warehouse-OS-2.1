"""Durable, resumable source-package ingestion for every workspace.

The request plane only accepts bounded parts and queues completed uploads.  A
Runtime Controller worker performs full digest verification, safe archive
inspection and immutable source registration outside Cloudflare's request
deadline.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import system_session, tenant_session
from app.services.digital_asset_hosting import (
    WorkspaceCredential,
    _audit,
    _workspace_billable_usage,
    _workspace_row,
)
from app.services.object_storage import object_store_for_provider
from app.services.source_packages import inspect_source_archive
from app.services.workspace_autonomy import (
    SOURCE_UPLOAD_HEADROOM_BYTES,
    allocation_target_bytes,
    ensure_capacity,
)
from app.services.workspace_deployments import (
    register_workspace_source,
    workspace_source_upload_target,
)

SOURCE_UPLOAD_CHUNK_BYTES = 4 * 1024 * 1024
SOURCE_UPLOAD_TTL_HOURS = 24
SOURCE_UPLOAD_MAX_ATTEMPTS = 3
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def _request_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _clean_sha256(value: object) -> str:
    digest = str(value or "").strip().lower()
    if not _SHA256_RE.fullmatch(digest):
        raise HTTPException(status_code=422, detail="sha256 must be 64 lowercase hex characters")
    return digest


def _clean_filename(value: object) -> str:
    filename = Path(str(value or "").strip()).name
    if not filename or len(filename) > 240 or filename in {".", ".."}:
        raise HTTPException(status_code=422, detail="filename must be 1 to 240 characters")
    return filename


def _job_public(row: dict[str, object], *, idempotent_replay: bool = False) -> dict[str, object]:
    upload_id = str(row["id"])
    part_count = int(row["part_count"])
    received_parts = row.get("received_part_numbers") or []
    result = row.get("result") if isinstance(row.get("result"), dict) else {}
    error = row.get("error") if isinstance(row.get("error"), dict) else {}
    payload: dict[str, object] = {
        "ok": str(row["status"]) not in {"failed", "expired", "cancelled"},
        "upload_id": upload_id,
        "status": str(row["status"]),
        "idempotent_replay": idempotent_replay,
        "filename": str(row["filename"]),
        "version_no": row.get("version_no"),
        "component": row.get("component_name"),
        "size_bytes": int(row["expected_size_bytes"]),
        "sha256": str(row["expected_sha256"]),
        "chunk_size_bytes": int(row["chunk_size_bytes"]),
        "part_count": part_count,
        "received_bytes": int(row.get("received_bytes") or 0),
        "received_parts": [int(value) for value in received_parts],
        "progress": round(
            min(1.0, int(row.get("received_bytes") or 0) / int(row["expected_size_bytes"])),
            6,
        ),
        "attempt_count": int(row.get("attempt_count") or 0),
        "expires_at": (
            row["expires_at"].isoformat()
            if isinstance(row.get("expires_at"), datetime)
            else row.get("expires_at")
        ),
        "endpoints": {
            "part": f"/api/workspaces/v1/source-uploads/{upload_id}/parts/{{part_no}}",
            "complete": f"/api/workspaces/v1/source-uploads/{upload_id}/complete",
            "status": f"/api/workspaces/v1/source-uploads/{upload_id}",
        },
    }
    if result:
        payload["result"] = result
        if isinstance(result.get("source"), dict):
            payload["source"] = result["source"]
    if error:
        payload["error"] = error
    if row.get("source_version_id"):
        payload["source_version_id"] = str(row["source_version_id"])
    return payload


def _job_row(session: object, upload_id: UUID, *, lock: bool = False) -> dict[str, object]:
    suffix = " FOR UPDATE" if lock else ""
    row = (
        session.execute(
            text(
                "SELECT * FROM digital_asset.source_upload_jobs "
                "WHERE id=:upload_id" + suffix
            ),
            {"upload_id": upload_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Source upload not found")
    result = dict(row)
    result["received_part_numbers"] = list(
        session.execute(
            text(
                "SELECT part_no FROM digital_asset.source_upload_parts "
                "WHERE upload_id=:upload_id ORDER BY part_no"
            ),
            {"upload_id": upload_id},
        ).scalars()
    )
    return result


def create_source_upload(
    credential: WorkspaceCredential,
    payload: dict[str, object],
    *,
    idempotency_key: str | None,
    settings: Settings,
) -> dict[str, object]:
    """Create or recover one upload reservation without receiving its body."""

    credential.require("deploy:write")
    filename = _clean_filename(payload.get("filename"))
    digest = _clean_sha256(payload.get("sha256") or payload.get("expected_sha256"))
    try:
        size_bytes = int(payload.get("size_bytes") or payload.get("expected_size_bytes") or 0)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="size_bytes must be an integer") from exc
    if size_bytes <= 0:
        raise HTTPException(status_code=422, detail="size_bytes must be positive")
    if size_bytes > settings.source_max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "reason": "source_upload_exceeds_host_limit",
                "requested_bytes": size_bytes,
                "max_bytes": settings.source_max_upload_bytes,
                "next_action": "reduce the archive or request a governed host-limit increase",
            },
        )
    version_no = str(payload.get("version_no") or "").strip() or None
    if version_no and len(version_no) > 80:
        raise HTTPException(status_code=422, detail="version_no is too long")
    component = str(payload.get("component") or payload.get("component_name") or "").strip()
    component = component or None
    if component and len(component) > 63:
        raise HTTPException(status_code=422, detail="component is too long")
    content_type = str(payload.get("content_type") or "application/octet-stream").strip()[:160]
    key = str(idempotency_key or f"source:{digest}").strip()
    if not 8 <= len(key) <= 240:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be 8 to 240 characters")
    canonical = {
        "filename": filename,
        "content_type": content_type,
        "version_no": version_no,
        "component": component,
        "size_bytes": size_bytes,
        "sha256": digest,
    }
    request_digest = _request_digest(canonical)

    if credential.key_kind == "primary":
        ensure_capacity(
            credential,
            required_free_bytes=size_bytes + SOURCE_UPLOAD_HEADROOM_BYTES,
            reason="automatic_primary_resumable_source_upload",
        )
    target = workspace_source_upload_target(credential, settings)
    now = datetime.now(UTC)
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=True)
        replay = (
            session.execute(
                text(
                    "SELECT * FROM digital_asset.source_upload_jobs "
                    "WHERE workspace_id=:workspace_id AND idempotency_key=:key"
                ),
                {"workspace_id": credential.workspace_id, "key": key},
            )
            .mappings()
            .one_or_none()
        )
        if replay is not None:
            if str(replay["request_digest"]) != request_digest:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "reason": "source_upload_idempotency_conflict",
                        "upload_id": str(replay["id"]),
                    },
                )
            if str(replay["status"]) in {"expired", "cancelled"}:
                session.execute(
                    text(
                        "UPDATE digital_asset.source_upload_jobs SET status='created',"
                        "updated_at=now(),"
                        "received_bytes=0,received_parts=0,attempt_count=0,"
                        "result='{}'::jsonb,error='{}'::jsonb,"
                        "storage_provider=:provider,expires_at=:expires_at,completed_at=NULL "
                        "WHERE id=:id"
                    ),
                    {
                        "id": replay["id"],
                        "provider": target["storage_provider"],
                        "expires_at": now + timedelta(hours=SOURCE_UPLOAD_TTL_HOURS),
                    },
                )
            return _job_public(
                _job_row(session, UUID(str(replay["id"]))),
                idempotent_replay=True,
            )

        if version_no:
            active_version_upload = session.execute(
                text(
                    "SELECT id,status FROM digital_asset.source_upload_jobs "
                    "WHERE workspace_id=:workspace_id AND version_no=:version_no "
                    "AND status IN ('created','uploading','queued','verifying')"
                ),
                {"workspace_id": credential.workspace_id, "version_no": version_no},
            ).mappings().one_or_none()
            if active_version_upload is not None:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "reason": "source_version_upload_already_active",
                        "upload_id": str(active_version_upload["id"]),
                        "status": str(active_version_upload["status"]),
                    },
                )
            conflict = session.execute(
                text(
                    "SELECT v.id,v.artifact_sha256 FROM digital_asset.asset_versions AS v "
                    "WHERE v.asset_id=:asset_id AND v.version_no=:version_no"
                ),
                {"asset_id": workspace["asset_id"], "version_no": version_no},
            ).mappings().one_or_none()
            if conflict is not None and str(conflict["artifact_sha256"]) != digest:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "reason": "source_version_number_conflict",
                        "version_no": version_no,
                        "existing_sha256": str(conflict["artifact_sha256"]),
                        "requested_sha256": digest,
                        "next_action": "use a new immutable version number",
                    },
                )

        existing = session.execute(
            text(
                """
                SELECT v.id AS source_version_id,v.legacy_id,v.version_no,
                       v.artifact_sha256,ar.size_bytes
                FROM digital_asset.asset_versions AS v
                JOIN digital_asset.artifacts AS ar
                  ON ar.version_id=v.id AND ar.storage_role='code' AND ar.state='verified'
                WHERE v.asset_id=:asset_id AND ar.sha256=:sha256
                ORDER BY v.created_at DESC LIMIT 1
                """
            ),
            {"asset_id": workspace["asset_id"], "sha256": digest},
        ).mappings().one_or_none()
        upload_id = uuid4()
        part_count = math.ceil(size_bytes / SOURCE_UPLOAD_CHUNK_BYTES)
        if existing is not None:
            if int(existing["size_bytes"]) != size_bytes:
                raise HTTPException(
                    status_code=422,
                    detail="Source size does not match its SHA-256",
                )
            source = {
                "id": int(existing["legacy_id"]),
                "uuid": str(existing["source_version_id"]),
                "version_no": str(existing["version_no"]),
                "artifact_sha256": digest,
                "artifact_hash": digest,
            }
            row = session.execute(
                text(
                    """
                    INSERT INTO digital_asset.source_upload_jobs(
                      id,tenant_id,workspace_id,credential_id,idempotency_key,request_digest,
                      filename,content_type,version_no,component_name,expected_size_bytes,
                      expected_sha256,chunk_size_bytes,part_count,received_bytes,
                      received_parts,status,storage_provider,source_version_id,result,
                      expires_at,completed_at
                    ) VALUES (
                      :id,:tenant_id,:workspace_id,:credential_id,:key,:request_digest,
                      :filename,:content_type,:version_no,:component,:size_bytes,
                      :sha256,:chunk_size,:part_count,:size_bytes,:part_count,'verified',
                      :provider,:source_version_id,CAST(:result AS jsonb),:expires_at,now()
                    ) RETURNING *
                    """
                ),
                {
                    "id": upload_id,
                    "tenant_id": credential.tenant_id,
                    "workspace_id": credential.workspace_id,
                    "credential_id": credential.credential_id,
                    "key": key,
                    "request_digest": request_digest,
                    **canonical,
                    "chunk_size": SOURCE_UPLOAD_CHUNK_BYTES,
                    "part_count": part_count,
                    "provider": target["storage_provider"],
                    "source_version_id": existing["source_version_id"],
                    "result": json.dumps(
                        {"ok": True, "idempotent_replay": True, "source": source}
                    ),
                    "expires_at": now + timedelta(hours=SOURCE_UPLOAD_TTL_HOURS),
                },
            ).mappings().one()
            return _job_public(dict(row), idempotent_replay=True)

        usage = _workspace_billable_usage(
            session,
            tenant_id=credential.tenant_id,
            workspace_id=credential.workspace_id,
            asset_id=workspace["asset_id"],
        )
        reserved = int(
            session.execute(
                text(
                    "SELECT COALESCE(sum(expected_size_bytes),0) "
                    "FROM digital_asset.source_upload_jobs "
                    "WHERE workspace_id=:workspace_id "
                    "AND status IN ('created','uploading','queued','verifying')"
                ),
                {"workspace_id": credential.workspace_id},
            ).scalar_one()
        )
        available = int(workspace["storage_quota_bytes"]) - int(usage["total_bytes"]) - reserved
        if size_bytes > available and credential.key_kind == "primary":
            previous_quota = int(workspace["storage_quota_bytes"])
            required_total = (
                int(usage["total_bytes"])
                + reserved
                + size_bytes
                + SOURCE_UPLOAD_HEADROOM_BYTES
            )
            expanded_quota = allocation_target_bytes(
                required_total,
                current_bytes=previous_quota,
            )
            session.execute(
                text(
                    "UPDATE digital_asset.workspaces SET storage_quota_bytes=:quota,"
                    "revision=revision+1 WHERE id=:workspace_id"
                ),
                {"quota": expanded_quota, "workspace_id": credential.workspace_id},
            )
            _audit(
                session,
                None,
                "digital_asset.workspace_quota_auto_expanded",
                {
                    "workspace_id": str(credential.workspace_id),
                    "reason": "concurrent_source_upload_reservations",
                    "before_bytes": previous_quota,
                    "after_bytes": expanded_quota,
                    "reserved_bytes": reserved,
                },
                tenant_id=credential.tenant_id,
            )
            available = expanded_quota - int(usage["total_bytes"]) - reserved
        if size_bytes > available:
            raise HTTPException(
                status_code=507,
                detail={
                    "reason": "workspace_upload_reservation_exceeds_quota",
                    "required_bytes": size_bytes,
                    "available_bytes": max(available, 0),
                },
            )
        row = session.execute(
            text(
                """
                INSERT INTO digital_asset.source_upload_jobs(
                  id,tenant_id,workspace_id,credential_id,idempotency_key,request_digest,
                  filename,content_type,version_no,component_name,expected_size_bytes,
                  expected_sha256,chunk_size_bytes,part_count,storage_provider,expires_at
                ) VALUES (
                  :id,:tenant_id,:workspace_id,:credential_id,:key,:request_digest,
                  :filename,:content_type,:version_no,:component,:size_bytes,
                  :sha256,:chunk_size,:part_count,:provider,:expires_at
                ) RETURNING *
                """
            ),
            {
                "id": upload_id,
                "tenant_id": credential.tenant_id,
                "workspace_id": credential.workspace_id,
                "credential_id": credential.credential_id,
                "key": key,
                "request_digest": request_digest,
                **canonical,
                "chunk_size": SOURCE_UPLOAD_CHUNK_BYTES,
                "part_count": part_count,
                "provider": target["storage_provider"],
                "expires_at": now + timedelta(hours=SOURCE_UPLOAD_TTL_HOURS),
            },
        ).mappings().one()
        _audit(
            session,
            None,
            "digital_asset.source_upload_created",
            {
                "workspace_id": str(credential.workspace_id),
                "upload_id": str(upload_id),
                "sha256": digest,
                "size_bytes": size_bytes,
                "part_count": part_count,
            },
            tenant_id=credential.tenant_id,
        )
    return _job_public(dict(row))


def put_source_upload_part(
    credential: WorkspaceCredential,
    upload_id: UUID,
    part_no: int,
    content: bytes,
    *,
    expected_sha256: str | None,
    settings: Settings,
) -> dict[str, object]:
    credential.require("deploy:write")
    digest = hashlib.sha256(content).hexdigest()
    if expected_sha256 and _clean_sha256(expected_sha256) != digest:
        raise HTTPException(
            status_code=422,
            detail={"reason": "source_upload_part_sha256_mismatch", "actual": digest},
        )
    with tenant_session(credential.tenant_id) as session:
        row = _job_row(session, upload_id, lock=True)
        if UUID(str(row["workspace_id"])) != credential.workspace_id:
            raise HTTPException(status_code=404, detail="Source upload not found")
        if str(row["status"]) not in {"created", "uploading"}:
            raise HTTPException(
                status_code=409,
                detail={"reason": "source_upload_not_accepting_parts", "status": row["status"]},
            )
        part_count = int(row["part_count"])
        chunk_size = int(row["chunk_size_bytes"])
        if part_no < 0 or part_no >= part_count:
            raise HTTPException(status_code=422, detail="Upload part number is out of range")
        expected_size = (
            chunk_size
            if part_no < part_count - 1
            else int(row["expected_size_bytes"]) - chunk_size * (part_count - 1)
        )
        if len(content) != expected_size:
            raise HTTPException(
                status_code=422,
                detail={
                    "reason": "source_upload_part_size_mismatch",
                    "expected_bytes": expected_size,
                    "actual_bytes": len(content),
                },
            )
        existing = session.execute(
            text(
                "SELECT size_bytes,sha256 FROM digital_asset.source_upload_parts "
                "WHERE upload_id=:upload_id AND part_no=:part_no"
            ),
            {"upload_id": upload_id, "part_no": part_no},
        ).mappings().one_or_none()
        if existing is not None and (
            int(existing["size_bytes"]) != len(content) or str(existing["sha256"]) != digest
        ):
            raise HTTPException(
                status_code=409,
                detail={"reason": "source_upload_part_conflict", "part_no": part_no},
            )
        store = object_store_for_provider(settings, str(row["storage_provider"]))
        path = store.source_upload_part_path(
            tenant_id=credential.tenant_id,
            upload_id=upload_id,
            part_no=part_no,
        )
        replay = existing is not None and path.is_file() and path.stat().st_size == len(content)
        if not replay:
            store.put_source_upload_part(
                tenant_id=credential.tenant_id,
                upload_id=upload_id,
                part_no=part_no,
                content=content,
            )
        if existing is None:
            session.execute(
                text(
                    "INSERT INTO digital_asset.source_upload_parts("
                    "upload_id,tenant_id,part_no,size_bytes,sha256"
                    ") VALUES (:upload_id,:tenant_id,:part_no,:size_bytes,:sha256)"
                ),
                {
                    "upload_id": upload_id,
                    "tenant_id": credential.tenant_id,
                    "part_no": part_no,
                    "size_bytes": len(content),
                    "sha256": digest,
                },
            )
            session.execute(
                text(
                    "UPDATE digital_asset.source_upload_jobs SET status='uploading',"
                    "updated_at=now(),"
                    "received_bytes=received_bytes+:size_bytes,received_parts=received_parts+1,"
                    "expires_at=now()+interval '24 hours' WHERE id=:upload_id"
                ),
                {"upload_id": upload_id, "size_bytes": len(content)},
            )
        updated = _job_row(session, upload_id)
    response = _job_public(updated, idempotent_replay=replay)
    response["part"] = {"part_no": part_no, "size_bytes": len(content), "sha256": digest}
    return response


def complete_source_upload(
    credential: WorkspaceCredential,
    upload_id: UUID,
    *,
    settings: Settings,
) -> dict[str, object]:
    credential.require("deploy:write")
    with tenant_session(credential.tenant_id) as session:
        row = _job_row(session, upload_id, lock=True)
        if UUID(str(row["workspace_id"])) != credential.workspace_id:
            raise HTTPException(status_code=404, detail="Source upload not found")
        current = str(row["status"])
        if current in {"queued", "verifying", "verified"}:
            return _job_public(row, idempotent_replay=True)
        if current not in {"created", "uploading"}:
            raise HTTPException(
                status_code=409,
                detail={"reason": "source_upload_cannot_complete", "status": current},
            )
        parts = session.execute(
            text(
                "SELECT part_no,size_bytes FROM digital_asset.source_upload_parts "
                "WHERE upload_id=:upload_id ORDER BY part_no"
            ),
            {"upload_id": upload_id},
        ).mappings().all()
        expected_numbers = list(range(int(row["part_count"])))
        observed_numbers = [int(part["part_no"]) for part in parts]
        observed_bytes = sum(int(part["size_bytes"]) for part in parts)
        if (
            observed_numbers != expected_numbers
            or observed_bytes != int(row["expected_size_bytes"])
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "source_upload_incomplete",
                    "received_parts": observed_numbers,
                    "expected_part_count": int(row["part_count"]),
                    "received_bytes": observed_bytes,
                    "expected_bytes": int(row["expected_size_bytes"]),
                },
            )
        store = object_store_for_provider(settings, str(row["storage_provider"]))
        missing = [
            part_no
            for part_no in expected_numbers
            if not store.source_upload_part_path(
                tenant_id=credential.tenant_id, upload_id=upload_id, part_no=part_no
            ).is_file()
        ]
        if missing:
            raise HTTPException(
                status_code=409,
                detail={"reason": "source_upload_parts_missing_from_storage", "parts": missing},
            )
        session.execute(
            text(
                "UPDATE digital_asset.source_upload_jobs SET status='queued',"
                "updated_at=now(),error='{}'::jsonb,"
                "lease_owner=NULL,lease_expires_at=NULL,expires_at=now()+interval '24 hours' "
                "WHERE id=:upload_id"
            ),
            {"upload_id": upload_id},
        )
        _audit(
            session,
            None,
            "digital_asset.source_upload_queued",
            {"workspace_id": str(credential.workspace_id), "upload_id": str(upload_id)},
            tenant_id=credential.tenant_id,
        )
        updated = _job_row(session, upload_id)
    return _job_public(updated)


def source_upload_status(
    credential: WorkspaceCredential,
    upload_id: UUID,
) -> dict[str, object]:
    if not {"deploy:read", "deploy:write"}.intersection(credential.scopes):
        credential.require("deploy:read")
    with tenant_session(credential.tenant_id) as session:
        row = _job_row(session, upload_id)
    if UUID(str(row["workspace_id"])) != credential.workspace_id:
        raise HTTPException(status_code=404, detail="Source upload not found")
    return _job_public(row)


class _PartSequenceStream:
    """Minimal BinaryIO reader over immutable part files."""

    def __init__(self, paths: list[Path]) -> None:
        self.paths = paths
        self.index = 0
        self.current: BinaryIO | None = None

    def read(self, size: int = -1) -> bytes:
        if size == 0:
            return b""
        output = bytearray()
        target = size if size >= 0 else None
        while target is None or len(output) < target:
            if self.current is None:
                if self.index >= len(self.paths):
                    break
                self.current = self.paths[self.index].open("rb")
                self.index += 1
            chunk = self.current.read(-1 if target is None else target - len(output))
            if chunk:
                output.extend(chunk)
            else:
                self.current.close()
                self.current = None
        return bytes(output)

    def close(self) -> None:
        if self.current is not None:
            self.current.close()
            self.current = None


def claim_source_upload(worker_id: str, settings: Settings) -> tuple[UUID, UUID] | None:
    lease = datetime.now(UTC) + timedelta(
        seconds=max(300, settings.runtime_controller_lease_seconds)
    )
    with system_session() as session:
        tenants = [
            UUID(str(value))
            for value in session.execute(
                text("SELECT id FROM iam.tenants WHERE status='active' ORDER BY id")
            ).scalars()
        ]
    for tenant_id in tenants:
        with tenant_session(tenant_id) as session:
            upload_id = session.execute(
                text(
                    """
                    SELECT id FROM digital_asset.source_upload_jobs
                    WHERE status='queued'
                       OR (status='verifying' AND lease_expires_at < now())
                    ORDER BY created_at
                    FOR UPDATE SKIP LOCKED LIMIT 1
                    """
                )
            ).scalar_one_or_none()
            if upload_id is None:
                continue
            session.execute(
                text(
                    "UPDATE digital_asset.source_upload_jobs SET status='verifying',"
                    "updated_at=now(),"
                    "lease_owner=:worker,lease_expires_at=:lease,"
                    "attempt_count=attempt_count+1 WHERE id=:upload_id"
                ),
                {"worker": worker_id, "lease": lease, "upload_id": upload_id},
            )
            return tenant_id, UUID(str(upload_id))
    return None


def _claimed_upload_snapshot(tenant_id: UUID, upload_id: UUID) -> dict[str, object]:
    with tenant_session(tenant_id) as session:
        row = session.execute(
            text(
                """
                SELECT j.*,c.scopes,c.label,c.key_kind,c.parent_credential_id
                FROM digital_asset.source_upload_jobs AS j
                JOIN digital_asset.api_credentials AS c ON c.id=j.credential_id
                WHERE j.id=:upload_id AND j.status='verifying'
                """
            ),
            {"upload_id": upload_id},
        ).mappings().one_or_none()
    if row is None:
        raise RuntimeError("Claimed source upload is unavailable")
    return dict(row)


def process_claimed_source_upload(
    tenant_id: UUID,
    upload_id: UUID,
    settings: Settings,
) -> dict[str, object]:
    snapshot = _claimed_upload_snapshot(tenant_id, upload_id)
    credential = WorkspaceCredential(
        tenant_id=tenant_id,
        workspace_id=UUID(str(snapshot["workspace_id"])),
        credential_id=UUID(str(snapshot["credential_id"])),
        scopes=frozenset(str(value) for value in snapshot["scopes"]),
        label=str(snapshot["label"]),
        key_kind=str(snapshot["key_kind"]),
        parent_credential_id=(
            UUID(str(snapshot["parent_credential_id"]))
            if snapshot.get("parent_credential_id")
            else None
        ),
    )
    credential.require("deploy:write")
    target = workspace_source_upload_target(credential, settings)
    if str(target["storage_provider"]) != str(snapshot["storage_provider"]):
        raise HTTPException(status_code=409, detail="Workspace code storage changed during upload")
    expected_size = int(snapshot["expected_size_bytes"])
    if credential.key_kind == "primary":
        ensure_capacity(
            credential,
            required_free_bytes=expected_size + SOURCE_UPLOAD_HEADROOM_BYTES,
            reason="automatic_primary_resumable_source_verification",
        )
    store = object_store_for_provider(settings, str(snapshot["storage_provider"]))
    paths = [
        store.source_upload_part_path(
            tenant_id=tenant_id,
            upload_id=upload_id,
            part_no=part_no,
        )
        for part_no in range(int(snapshot["part_count"]))
    ]
    if any(not path.is_file() for path in paths):
        raise HTTPException(status_code=409, detail="A queued source upload part is missing")
    stream = _PartSequenceStream(paths)
    try:
        stored = store.put_stream(
            tenant_id=tenant_id,
            stream=stream,
            max_bytes=expected_size,
            expected_sha256=str(snapshot["expected_sha256"]),
        )
    finally:
        stream.close()
    if stored.size_bytes != expected_size:
        raise HTTPException(
            status_code=422,
            detail="Uploaded source size changed during verification",
        )
    remaining = int(target["remaining_bytes"])
    archive_limit = max(
        remaining,
        stored.size_bytes,
        min(settings.source_max_upload_bytes * 200, 64 * 1024 * 1024 * 1024),
    )
    archive = inspect_source_archive(
        store.path_for(stored.object_key),
        max_uncompressed_bytes=archive_limit,
    )
    if credential.key_kind == "primary":
        ensure_capacity(
            credential,
            required_free_bytes=(
                stored.size_bytes + archive.uncompressed_bytes + SOURCE_UPLOAD_HEADROOM_BYTES
            ),
            reason="automatic_primary_resumable_source_materialization",
        )
    result = register_workspace_source(
        credential,
        stored,
        filename=str(snapshot["filename"]),
        content_type=str(snapshot.get("content_type") or "application/octet-stream"),
        version_no=str(snapshot.get("version_no") or "").strip() or None,
        component_name=str(snapshot.get("component_name") or "").strip() or None,
        archive=archive,
    )
    source = result.get("source") if isinstance(result.get("source"), dict) else {}
    source_id = source.get("uuid")
    with tenant_session(tenant_id) as session:
        session.execute(
            text(
                """
                UPDATE digital_asset.source_upload_jobs
                SET status='verified',updated_at=now(),source_version_id=:source_version_id,
                    result=CAST(:result AS jsonb),error='{}'::jsonb,
                    lease_owner=NULL,lease_expires_at=NULL,completed_at=now()
                WHERE id=:upload_id
                """
            ),
            {
                "upload_id": upload_id,
                "source_version_id": UUID(str(source_id)) if source_id else None,
                "result": json.dumps(result, ensure_ascii=False, default=str),
            },
        )
        _audit(
            session,
            None,
            "digital_asset.source_upload_verified",
            {
                "workspace_id": str(credential.workspace_id),
                "upload_id": str(upload_id),
                "source_version_id": str(source_id) if source_id else None,
                "sha256": stored.sha256,
            },
            tenant_id=tenant_id,
        )
    store.remove_source_upload(tenant_id=tenant_id, upload_id=upload_id)
    return result


def fail_claimed_source_upload(
    tenant_id: UUID,
    upload_id: UUID,
    exc: Exception,
) -> None:
    status_code = exc.status_code if isinstance(exc, HTTPException) else 500
    detail = exc.detail if isinstance(exc, HTTPException) else (str(exc) or exc.__class__.__name__)
    with tenant_session(tenant_id) as session:
        row = session.execute(
            text("SELECT attempt_count FROM digital_asset.source_upload_jobs WHERE id=:id"),
            {"id": upload_id},
        ).mappings().one_or_none()
        if row is None:
            return
        retryable = (
            int(status_code) >= 500
            and int(row["attempt_count"]) < SOURCE_UPLOAD_MAX_ATTEMPTS
        )
        next_status = "queued" if retryable else "failed"
        error = {
            "reason": "source_upload_verification_failed",
            "message": detail,
            "http_status": int(status_code),
            "retryable": retryable,
            "next_action": (
                "automatic_retry_queued"
                if retryable
                else "inspect_the_archive_or_submit_a_new_upload"
            ),
        }
        session.execute(
            text(
                "UPDATE digital_asset.source_upload_jobs SET status=:status,"
                "updated_at=now(),"
                "error=CAST(:error AS jsonb),lease_owner=NULL,lease_expires_at=NULL "
                "WHERE id=:upload_id"
            ),
            {
                "status": next_status,
                "error": json.dumps(error, ensure_ascii=False, default=str),
                "upload_id": upload_id,
            },
        )


def expire_source_uploads(settings: Settings, *, limit_per_tenant: int = 20) -> int:
    """Expire abandoned reservations and remove only their private staging parts."""

    with system_session() as session:
        tenants = [
            UUID(str(value))
            for value in session.execute(
                text("SELECT id FROM iam.tenants WHERE status='active' ORDER BY id")
            ).scalars()
        ]
    expired: list[tuple[UUID, UUID, str, str, bool]] = []
    for tenant_id in tenants:
        with tenant_session(tenant_id) as session:
            rows = session.execute(
                text(
                    """
                    SELECT id,storage_provider,status,expected_sha256
                    FROM digital_asset.source_upload_jobs
                    WHERE expires_at < now()
                      AND status IN ('created','uploading','failed','expired','cancelled')
                      AND NOT (result ? 'staging_cleaned_at')
                    ORDER BY expires_at LIMIT :limit
                    FOR UPDATE SKIP LOCKED
                    """
                ),
                {"limit": limit_per_tenant},
            ).mappings().all()
            for row in rows:
                if str(row["status"]) in {"created", "uploading"}:
                    session.execute(
                        text(
                            "UPDATE digital_asset.source_upload_jobs SET status='expired',"
                            "updated_at=now(),"
                            "error=jsonb_build_object('reason','source_upload_expired',"
                            "'retryable',false) WHERE id=:id"
                        ),
                        {"id": row["id"]},
                    )
                session.execute(
                    text(
                        "DELETE FROM digital_asset.source_upload_parts "
                        "WHERE upload_id=:upload_id"
                    ),
                    {"upload_id": row["id"]},
                )
                session.execute(
                    text(
                        "UPDATE digital_asset.source_upload_jobs SET "
                        "received_bytes=0,received_parts=0,updated_at=now() "
                        ",result=result || jsonb_build_object("
                        "'staging_cleaned_at',to_jsonb(now())) "
                        "WHERE id=:upload_id"
                    ),
                    {"upload_id": row["id"]},
                )
                referenced = bool(
                    session.execute(
                        text(
                            "SELECT EXISTS ("
                            "SELECT 1 FROM digital_asset.artifacts "
                            "WHERE sha256=:sha256 AND storage_provider=:provider"
                            ") OR EXISTS ("
                            "SELECT 1 FROM digital_asset.source_upload_jobs "
                            "WHERE id<>:upload_id AND expected_sha256=:sha256 "
                            "AND storage_provider=:provider "
                            "AND status IN ('created','uploading','queued','verifying','verified')"
                            ")"
                        ),
                        {
                            "upload_id": row["id"],
                            "sha256": row["expected_sha256"],
                            "provider": row["storage_provider"],
                        },
                    ).scalar_one()
                )
                expired.append(
                    (
                        tenant_id,
                        UUID(str(row["id"])),
                        str(row["storage_provider"]),
                        str(row["expected_sha256"]),
                        not referenced,
                    )
                )
    for tenant_id, upload_id, provider, sha256, remove_object in expired:
        store = object_store_for_provider(settings, provider)
        store.remove_source_upload(
            tenant_id=tenant_id,
            upload_id=upload_id,
        )
        if remove_object:
            store.path_for(store.object_key_for_sha256(tenant_id, sha256)).unlink(
                missing_ok=True
            )
    return len(expired)
