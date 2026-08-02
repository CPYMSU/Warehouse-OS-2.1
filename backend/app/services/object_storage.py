"""Object storage provider boundary for custodied application artifacts."""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from fastapi import HTTPException, status

from app.core.config import Settings

HDD_PROVIDER_KEY = "content_addressed_hdd"
SSD_PROVIDER_KEY = "content_addressed_ssd"
LEGACY_PROVIDER_KEY = "content_addressed_local"
LOCAL_PROVIDER_KEYS = frozenset(
    {HDD_PROVIDER_KEY, SSD_PROVIDER_KEY, LEGACY_PROVIDER_KEY}
)


@dataclass(frozen=True)
class StoredObject:
    provider_key: str
    object_key: str
    sha256: str
    size_bytes: int


class LocalContentAddressedObjectStore:
    """Development provider with the same immutable object-key contract as S3.

    Database rows only retain ``provider_key`` and ``object_key``.  Replacing
    this adapter with S3/MinIO therefore does not change asset or API schemas.
    """

    provider_key = LEGACY_PROVIDER_KEY

    def __init__(self, root: Path, *, provider_key: str = LEGACY_PROVIDER_KEY) -> None:
        if provider_key not in LOCAL_PROVIDER_KEYS:
            raise ValueError("Unsupported local object storage provider")
        self.provider_key = provider_key
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink() or not self.root.is_dir():
            raise RuntimeError("Digital asset storage root is unsafe")

    def _key(self, tenant_id: UUID, sha256: str) -> str:
        return f"tenants/{tenant_id}/sha256/{sha256[:2]}/{sha256}"

    def probe_writable(self) -> dict[str, object]:
        """Prove create/write/fsync/read/delete instead of trusting configuration."""

        started = time.perf_counter()
        probe_root = self.root / ".probes"
        probe_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        payload = os.urandom(64)
        descriptor, name = tempfile.mkstemp(prefix="probe-", dir=probe_root)
        path = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            if path.read_bytes() != payload:
                raise OSError("storage probe read-back mismatch")
        finally:
            path.unlink(missing_ok=True)
        return {
            "writable": True,
            "provider_key": self.provider_key,
            "probe": "create_write_fsync_read_delete",
            "observed_at": datetime.now(UTC).isoformat(),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    def path_for(self, object_key: str) -> Path:
        candidate = (self.root / object_key).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Unsafe object key") from exc
        return candidate

    def put_stream(
        self,
        *,
        tenant_id: UUID,
        stream: BinaryIO,
        max_bytes: int,
        expected_sha256: str | None = None,
    ) -> StoredObject:
        digest = hashlib.sha256()
        size = 0
        staging = self.root / ".staging"
        staging.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary_name = tempfile.mkstemp(prefix="upload-", dir=staging)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as output:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Artifact exceeds {max_bytes} bytes",
                        )
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            sha256 = digest.hexdigest()
            if expected_sha256 and expected_sha256.lower() != sha256:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "message": "Artifact SHA-256 mismatch",
                        "expected": expected_sha256.lower(),
                        "actual": sha256,
                    },
                )
            object_key = self._key(tenant_id, sha256)
            target = self.path_for(object_key)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if target.exists():
                temporary.unlink()
            else:
                os.replace(temporary, target)
                target.chmod(0o600)
            return StoredObject(
                provider_key=self.provider_key,
                object_key=object_key,
                sha256=sha256,
                size_bytes=size,
            )
        finally:
            if temporary.exists():
                temporary.unlink()


def object_store_for_provider(
    settings: Settings, provider_key: str
) -> LocalContentAddressedObjectStore:
    """Resolve a database provider key to a server-owned storage root."""

    if provider_key == SSD_PROVIDER_KEY:
        return LocalContentAddressedObjectStore(
            settings.asset_code_ssd_root,
            provider_key=SSD_PROVIDER_KEY,
        )
    if provider_key in {HDD_PROVIDER_KEY, LEGACY_PROVIDER_KEY}:
        return LocalContentAddressedObjectStore(
            settings.asset_storage_root,
            provider_key=provider_key,
        )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Artifact is stored by an external object provider",
    )


def object_store_read_candidates(
    settings: Settings, provider_key: str
) -> tuple[LocalContentAddressedObjectStore, ...]:
    """Return safe local read candidates during the one-way HDD migration."""

    primary = object_store_for_provider(settings, provider_key)
    if provider_key != LEGACY_PROVIDER_KEY or settings.asset_legacy_storage_root is None:
        return (primary,)
    legacy = LocalContentAddressedObjectStore(
        settings.asset_legacy_storage_root,
        provider_key=LEGACY_PROVIDER_KEY,
    )
    if legacy.root == primary.root:
        return (primary,)
    return (primary, legacy)
