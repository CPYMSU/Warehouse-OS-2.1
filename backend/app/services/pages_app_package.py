"""Portable Warehouse Pages package observation and deterministic export."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException

from app.core.config import Settings
from app.services.digital_asset_hosting import WorkspaceCredential
from app.services.object_storage import object_store_read_candidates
from app.services.pages_app_contract import (
    PAGES_APP_MANIFEST_FILENAME,
    PAGES_APP_SCHEMA,
    portable_pages_app_manifest,
    synthesize_pages_app_manifest,
)
from app.services.pages_runtime import (
    _archive_members,
    _is_sensitive,
    pages_design_context,
)
from app.services.source_packages import (
    application_root,
    inspect_source_archive,
    materialize_source_archive,
)
from app.services.workspace_deployments import workspace_source_download_target

PAGES_APP_PACKAGE_SCHEMA = "warehouse.pages-app-package.v1"
MAX_PACKAGE_EXPANDED_BYTES = 512 * 1024 * 1024
_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class GeneratedPagesAppPackage:
    path: Path
    filename: str
    size_bytes: int
    sha256: str
    manifest_digest: str
    excluded_sensitive_files: int


def _source_path(descriptor: dict[str, object], settings: Settings) -> Path:
    for store in object_store_read_candidates(
        settings,
        str(descriptor["storage_provider"]),
    ):
        candidate = store.path_for(str(descriptor["object_key"]))
        if candidate.is_file():
            return candidate
    raise HTTPException(status_code=404, detail="Source object is unavailable")


def _package_inputs(
    credential: WorkspaceCredential,
    settings: Settings,
    *,
    source_ref: str | None,
) -> tuple[dict[str, object], dict[str, object], Path, dict[str, object], bool]:
    design = pages_design_context(
        credential,
        settings,
        source_ref=source_ref,
    )
    source = design["source"]
    source_id = str(source["id"])
    descriptor = workspace_source_download_target(credential, source_id)
    archive_path = _source_path(descriptor, settings)
    archive = inspect_source_archive(
        archive_path,
        max_uncompressed_bytes=MAX_PACKAGE_EXPANDED_BYTES,
    )
    declared = archive.signals.get("pages_manifest")
    source_paths = {member.path for member in _archive_members(archive_path)}
    single_root = str(archive.signals.get("single_root") or "")
    if single_root:
        prefix = single_root.rstrip("/") + "/"
        source_paths = {
            path.removeprefix(prefix) if path.startswith(prefix) else path for path in source_paths
        }
    if isinstance(declared, dict):
        manifest = dict(declared)
        is_declared = True
    else:
        site = design.get("site") if isinstance(design.get("site"), dict) else {}
        candidates = [
            str(value).replace("\\", "/")
            for value in archive.signals.get("candidate_entrypoints") or []
        ]
        candidate_names = {Path(value).name.lower() for value in candidates}
        legacy_runtime = None
        legacy_handler = None
        if archive.signals.get("python_source") and (
            archive.signals.get("requirements_txt")
            or {"app.py", "main.py", "server.py", "asgi.py", "wsgi.py"}
            & candidate_names
        ):
            legacy_runtime = "python"
            for module in ("app", "main", "server", "asgi", "wsgi"):
                if f"{module}.py" in candidate_names:
                    legacy_handler = f"{module}:app"
                    break
        elif archive.signals.get("package_json") or archive.signals.get("node_source"):
            legacy_runtime = "node"
        manifest = synthesize_pages_app_manifest(
            source_paths,
            name=str(site.get("site_key") or descriptor.get("filename") or "Pages application"),
            version=str(source.get("version_no") or "1.0.0"),
            legacy_runtime=legacy_runtime,
            legacy_handler=legacy_handler,
        )
        is_declared = False
    return design, descriptor, archive_path, manifest, is_declared


def pages_app_package_contract(
    credential: WorkspaceCredential,
    settings: Settings,
    *,
    source_ref: str | None = None,
    account_workspace_ref: str | None = None,
) -> dict[str, object]:
    """Return the effective package contract without secrets or source bytes."""

    design, descriptor, _archive_path, manifest, declared = _package_inputs(
        credential,
        settings,
        source_ref=source_ref,
    )
    source = design["source"]
    if account_workspace_ref:
        base = f"/api/workspaces/{account_workspace_ref}/pages/package"
    else:
        base = "/api/workspaces/v1/pages/package"
    return {
        "ok": True,
        "schema": PAGES_APP_PACKAGE_SCHEMA,
        "package_format": "zip",
        "manifest_filename": PAGES_APP_MANIFEST_FILENAME,
        "manifest": manifest,
        "manifest_declared": declared,
        "source": {
            "id": str(source["id"]),
            "version_no": source.get("version_no"),
            "filename": descriptor.get("filename"),
            "size_bytes": int(descriptor["size_bytes"]),
            "sha256": descriptor["sha256"],
        },
        "endpoints": {
            "contract": base,
            "download": base + "/download",
            "design": base.removesuffix("/package") + "/design",
        },
        "execution": {
            "web": "static_pages",
            "data": manifest["data"],
            "functions": manifest["functions"],
            "device": manifest["device"],
            "server_runtime_residency": "none_for_static_and_serverless",
        },
        "security": {
            "secrets_embedded": False,
            "secret_values_allowed": False,
            "browser_database_default": "deny",
            "sensitive_source_paths_exported": False,
        },
        "operations": {
            "code_deploy": "immutable_release",
            "database_reconcile": "background_control_plane",
            "database_schema_blocks_code_deploy": False,
        },
        "design_context": {
            "schema": design["schema"],
            "file_count": design["file_count"],
            "excluded_sensitive_files": design["excluded_sensitive_files"],
            "read_file": design["read_file"],
        },
    }


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=_FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100640 << 16
    info.create_system = 3
    return info


def _safe_filename(value: object) -> str:
    rendered = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "pages-app")).strip("-.")
    return (rendered[:100] or "pages-app") + ".warehouse-pages.zip"


def _copy_and_hash(source: BinaryIO, destination: BinaryIO) -> str:
    digest = hashlib.sha256()
    while chunk := source.read(1024 * 1024):
        digest.update(chunk)
        destination.write(chunk)
    return digest.hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _write_bytes(package: zipfile.ZipFile, relative: str, content: bytes) -> None:
    package.writestr(
        _zip_info(relative),
        content,
        compress_type=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    )


def build_pages_app_zip(
    source_root: Path,
    output: Path,
    *,
    manifest: dict[str, object],
    package_metadata: dict[str, object],
) -> tuple[int, dict[str, str]]:
    """Build deterministic package bytes from one already verified source tree."""

    source_files: list[tuple[str, Path]] = []
    checksums: dict[str, str] = {}
    excluded_sensitive = 0
    for path in sorted(item for item in source_root.rglob("*") if item.is_file()):
        relative = path.relative_to(source_root).as_posix()
        if relative == PAGES_APP_MANIFEST_FILENAME or relative.startswith(".warehouse/"):
            continue
        if _is_sensitive(relative):
            excluded_sensitive += 1
            continue
        source_files.append((relative, path))
        checksums[relative] = _file_hash(path)

    portable_manifest = portable_pages_app_manifest(manifest)
    manifest_bytes = (
        json.dumps(portable_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    checksums[PAGES_APP_MANIFEST_FILENAME] = hashlib.sha256(manifest_bytes).hexdigest()

    effective_metadata = dict(package_metadata)
    security = (
        dict(effective_metadata.get("security"))
        if isinstance(effective_metadata.get("security"), dict)
        else {}
    )
    security["excluded_sensitive_files"] = excluded_sensitive
    effective_metadata["security"] = security
    metadata_bytes = (
        json.dumps(effective_metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    checksums[".warehouse/package.json"] = hashlib.sha256(metadata_bytes).hexdigest()
    checksum_bytes = (
        json.dumps(
            {"algorithm": "sha256", "files": checksums},
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    with zipfile.ZipFile(output, "w", allowZip64=True) as package:
        for relative, path in source_files:
            with (
                path.open("rb") as source,
                package.open(_zip_info(relative), "w", force_zip64=True) as destination,
            ):
                copied_digest = _copy_and_hash(source, destination)
            if copied_digest != checksums[relative]:
                raise HTTPException(status_code=409, detail="Source changed during export")
        _write_bytes(package, PAGES_APP_MANIFEST_FILENAME, manifest_bytes)
        _write_bytes(package, ".warehouse/package.json", metadata_bytes)
        _write_bytes(package, ".warehouse/checksums.json", checksum_bytes)
    return excluded_sensitive, checksums


def materialize_pages_app_package(
    credential: WorkspaceCredential,
    settings: Settings,
    *,
    source_ref: str | None = None,
) -> GeneratedPagesAppPackage:
    """Export one deterministic, portable and secret-free application ZIP."""

    design, descriptor, archive_path, manifest, declared = _package_inputs(
        credential,
        settings,
        source_ref=source_ref,
    )
    handle, raw_output = tempfile.mkstemp(prefix="warehouse-pages-app-", suffix=".zip")
    os.close(handle)
    output = Path(raw_output)
    try:
        with tempfile.TemporaryDirectory(prefix="warehouse-pages-source-") as raw_directory:
            extracted = Path(raw_directory) / "source"
            materialize_source_archive(
                archive_path,
                extracted,
                max_uncompressed_bytes=MAX_PACKAGE_EXPANDED_BYTES,
            )
            root = application_root(extracted)
            package_metadata = {
                "schema": PAGES_APP_PACKAGE_SCHEMA,
                "manifest_schema": PAGES_APP_SCHEMA,
                "manifest_digest": manifest["contract_digest"],
                "manifest_declared": declared,
                "source": {
                    "id": str(design["source"]["id"]),
                    "sha256": descriptor["sha256"],
                },
                "security": {
                    "secrets_embedded": False,
                },
                "database_reconcile": "background_control_plane",
            }
            excluded_sensitive, _checksums = build_pages_app_zip(
                root,
                output,
                manifest=manifest,
                package_metadata=package_metadata,
            )
        digest = _file_hash(output)
        return GeneratedPagesAppPackage(
            path=output,
            filename=_safe_filename(manifest.get("name")),
            size_bytes=output.stat().st_size,
            sha256=digest,
            manifest_digest=str(manifest["contract_digest"]),
            excluded_sensitive_files=excluded_sensitive,
        )
    except Exception:
        output.unlink(missing_ok=True)
        raise
