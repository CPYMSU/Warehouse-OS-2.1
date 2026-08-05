"""Validation and safe materialisation of immutable workspace source archives."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, status

from app.services.hosting_compatibility import (
    MANIFEST_FILENAME,
    MAX_MANIFEST_BYTES,
    validate_hosting_manifest,
)

MAX_ARCHIVE_ENTRIES = 20_000
MAX_COMPRESSION_RATIO = 200


@dataclass(frozen=True)
class SourceArchive:
    format: str
    entries: int
    files: int
    uncompressed_bytes: int
    top_level: tuple[str, ...]
    signals: dict[str, object]

    def public(self) -> dict[str, object]:
        return {
            "format": self.format,
            "entries": self.entries,
            "files": self.files,
            "uncompressed_bytes": self.uncompressed_bytes,
            "top_level": list(self.top_level),
            "signals": self.signals,
            "validated": True,
        }


def _safe_member(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized in {".", "./"}
        or not path.parts
        or normalized.startswith("/")
        or path.is_absolute()
    ):
        raise HTTPException(status_code=422, detail="Source archive contains an absolute path")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise HTTPException(status_code=422, detail="Source archive contains an unsafe path")
    return path


def inspect_source_archive(path: Path, *, max_uncompressed_bytes: int) -> SourceArchive:
    """Verify paths, special files and expansion limits before registration."""

    entries = files = unpacked = 0
    top_level: set[str] = set()
    source_paths: set[str] = set()
    manifest_candidates: list[tuple[str, bytes]] = []
    packed = max(path.stat().st_size, 1)
    archive_format: str
    if zipfile.is_zipfile(path):
        archive_format = "zip"
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist():
                entries += 1
                if entries > MAX_ARCHIVE_ENTRIES:
                    raise HTTPException(
                        status_code=422, detail="Source archive has too many entries"
                    )
                raw_name = item.filename.rstrip("/")
                if raw_name in {"", "."} and item.is_dir():
                    continue
                member = _safe_member(raw_name)
                top_level.add(member.parts[0])
                mode = item.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise HTTPException(
                        status_code=422, detail="Source archive may not contain links"
                    )
                if not item.is_dir():
                    files += 1
                    unpacked += int(item.file_size)
                    member_path = member.as_posix()
                    source_paths.add(member_path.lower())
                    if member.name == MANIFEST_FILENAME:
                        if item.file_size > MAX_MANIFEST_BYTES:
                            raise HTTPException(
                                status_code=422,
                                detail={
                                    "reason": "hosting_manifest_invalid",
                                    "field": "manifest",
                                    "message": "warehouse.hosting.json exceeds 256 KiB",
                                },
                            )
                        manifest_candidates.append((member_path, archive.read(item)))
    elif tarfile.is_tarfile(path):
        archive_format = "tar"
        with tarfile.open(path, mode="r:*") as archive:
            for item in archive:
                entries += 1
                if entries > MAX_ARCHIVE_ENTRIES:
                    raise HTTPException(
                        status_code=422, detail="Source archive has too many entries"
                    )
                raw_name = item.name.rstrip("/")
                if raw_name in {"", "."} and item.isdir():
                    continue
                member = _safe_member(raw_name)
                top_level.add(member.parts[0])
                if item.issym() or item.islnk() or item.isdev() or item.isfifo():
                    raise HTTPException(
                        status_code=422,
                        detail="Source archive may not contain links or special files",
                    )
                if item.isfile():
                    files += 1
                    unpacked += int(item.size)
                    member_path = member.as_posix()
                    source_paths.add(member_path.lower())
                    if member.name == MANIFEST_FILENAME:
                        if item.size > MAX_MANIFEST_BYTES:
                            raise HTTPException(
                                status_code=422,
                                detail={
                                    "reason": "hosting_manifest_invalid",
                                    "field": "manifest",
                                    "message": "warehouse.hosting.json exceeds 256 KiB",
                                },
                            )
                        stream = archive.extractfile(item)
                        if stream is None:
                            raise HTTPException(
                                status_code=422,
                                detail="Hosting manifest is unreadable",
                            )
                        manifest_candidates.append((member_path, stream.read()))
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Source must be a ZIP or TAR archive",
        )
    if files == 0:
        raise HTTPException(status_code=422, detail="Source archive contains no files")
    if unpacked > max_uncompressed_bytes:
        raise HTTPException(status_code=413, detail="Expanded source exceeds workspace quota")
    if unpacked > packed * MAX_COMPRESSION_RATIO:
        raise HTTPException(status_code=422, detail="Source archive expansion ratio is unsafe")
    basenames = {PurePosixPath(name).name for name in source_paths}
    single_root = next(iter(top_level)) if len(top_level) == 1 else None
    allowed_manifest_paths = {MANIFEST_FILENAME}
    if single_root:
        allowed_manifest_paths.add(f"{single_root}/{MANIFEST_FILENAME}")
    misplaced_manifests = [
        name for name, _content in manifest_candidates if name not in allowed_manifest_paths
    ]
    selected_manifests = [
        (name, content)
        for name, content in manifest_candidates
        if name in allowed_manifest_paths
    ]
    if misplaced_manifests or len(selected_manifests) > 1:
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "hosting_manifest_invalid",
                "field": "manifest",
                "message": (
                    "provide exactly one warehouse.hosting.json at the application root"
                ),
                "paths": sorted(name for name, _content in manifest_candidates),
            },
        )
    hosting_manifest: dict[str, object] | None = None
    hosting_contract: dict[str, object] | None = None
    if selected_manifests:
        manifest_path, content = selected_manifests[0]
        try:
            decoded = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "reason": "hosting_manifest_invalid",
                    "field": "manifest",
                    "message": "warehouse.hosting.json must be valid UTF-8 JSON",
                },
            ) from exc
        hosting_manifest = validate_hosting_manifest(decoded, source_paths=source_paths)
        hosting_contract = {
            "schema": hosting_manifest["schema"],
            "contract_digest": hosting_manifest["contract_digest"],
            "manifest_sha256": hashlib.sha256(content).hexdigest(),
            "path": manifest_path,
            "declared": True,
        }
    candidate_entrypoints = sorted(
        name
        for name in source_paths
        if PurePosixPath(name).name
        in {
            "index.html",
            "app.py",
            "main.py",
            "server.py",
            "asgi.py",
            "wsgi.py",
            "worker.py",
            "agent.py",
            "server.js",
            "index.js",
        }
    )[:50]
    return SourceArchive(
        format=archive_format,
        entries=entries,
        files=files,
        uncompressed_bytes=unpacked,
        top_level=tuple(sorted(top_level)[:100]),
        signals={
            "single_root": single_root,
            "index_html": "index.html" in basenames,
            "package_json": "package.json" in basenames,
            "dockerfile": "dockerfile" in basenames,
            "compose_file": next(
                (
                    name
                    for name in source_paths
                    if PurePosixPath(name).name
                    in {
                        "compose.yaml",
                        "compose.yml",
                        "docker-compose.yaml",
                        "docker-compose.yml",
                    }
                ),
                None,
            ),
            "requirements_txt": "requirements.txt" in basenames,
            "pyproject_toml": "pyproject.toml" in basenames,
            "python_source": any(name.endswith(".py") for name in source_paths),
            "node_source": any(name.endswith((".js", ".mjs", ".cjs")) for name in source_paths),
            "worker_entry": any(
                PurePosixPath(name).name in {"worker.py", "worker.js"} for name in source_paths
            ),
            "worker_family": (
                "python"
                if any(PurePosixPath(name).name == "worker.py" for name in source_paths)
                else "node"
                if any(PurePosixPath(name).name == "worker.js" for name in source_paths)
                else None
            ),
            "agent_entry": any(
                PurePosixPath(name).name in {"agent.py", "agent.js"} for name in source_paths
            ),
            "agent_family": (
                "python"
                if any(PurePosixPath(name).name == "agent.py" for name in source_paths)
                else "node"
                if any(PurePosixPath(name).name == "agent.js" for name in source_paths)
                else None
            ),
            "candidate_entrypoints": candidate_entrypoints,
            "hosting_manifest": hosting_manifest,
            "hosting_contract": hosting_contract,
        },
    )


def materialize_source_archive(
    archive_path: Path,
    destination: Path,
    *,
    max_uncompressed_bytes: int,
) -> SourceArchive:
    """Extract a previously validated archive without following archive links."""

    manifest = inspect_source_archive(
        archive_path,
        max_uncompressed_bytes=max_uncompressed_bytes,
    )
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=False, mode=0o750)
    try:
        if manifest.format == "zip":
            with zipfile.ZipFile(archive_path) as archive:
                for item in archive.infolist():
                    raw_name = item.filename.rstrip("/")
                    if raw_name in {"", "."} and item.is_dir():
                        continue
                    member = _safe_member(raw_name)
                    target = destination.joinpath(*member.parts)
                    if item.is_dir():
                        target.mkdir(parents=True, exist_ok=True, mode=0o750)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
                    with archive.open(item) as source, target.open("xb") as output:
                        shutil.copyfileobj(source, output, length=1024 * 1024)
                    target.chmod(0o640)
        else:
            with tarfile.open(archive_path, mode="r:*") as archive:
                for item in archive:
                    raw_name = item.name.rstrip("/")
                    if raw_name in {"", "."} and item.isdir():
                        continue
                    member = _safe_member(raw_name)
                    target = destination.joinpath(*member.parts)
                    if item.isdir():
                        target.mkdir(parents=True, exist_ok=True, mode=0o750)
                        continue
                    if not item.isfile():
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
                    source = archive.extractfile(item)
                    if source is None:
                        raise HTTPException(status_code=422, detail="Source member is unreadable")
                    with source, target.open("xb") as output:
                        shutil.copyfileobj(source, output, length=1024 * 1024)
                    target.chmod(0o640)
        for root, directories, _files in os.walk(destination):
            Path(root).chmod(0o750)
            for directory in directories:
                (Path(root) / directory).chmod(0o750)
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return manifest


def application_root(destination: Path) -> Path:
    """Collapse one ordinary wrapper directory without guessing deeper layout."""

    visible = [item for item in destination.iterdir() if item.name not in {"__MACOSX"}]
    if len(visible) == 1 and visible[0].is_dir():
        return visible[0]
    return destination
