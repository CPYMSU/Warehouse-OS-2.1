"""Filesystem-backed workspace occupancy measurement.

The Runtime Controller and the customer Workspace API share this scanner so
quota facts and displayed occupancy use the same boundaries.  Symlinks are
never followed: a workload-controlled DATA volume must not make the control
plane traverse outside the governed workspace root.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.core.config import Settings


@dataclass(frozen=True)
class _TreeUsage:
    bytes: int
    files: int
    errors: int


def _tree_usage(path: Path, *, excluded_root_names: frozenset[str] = frozenset()) -> _TreeUsage:
    if not path.exists():
        return _TreeUsage(bytes=0, files=0, errors=0)
    total_bytes = 0
    files = 0
    errors = 0
    pending: list[tuple[Path, bool]] = [(path, True)]
    while pending:
        current, is_root = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if is_root and entry.name in excluded_root_names:
                        continue
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            pending.append((Path(entry.path), False))
                        elif entry.is_file(follow_symlinks=False):
                            total_bytes += max(0, int(entry.stat(follow_symlinks=False).st_size))
                            files += 1
                    except OSError:
                        errors += 1
        except FileNotFoundError:
            continue
        except OSError:
            errors += 1
    return _TreeUsage(bytes=total_bytes, files=files, errors=errors)


def measure_workspace_runtime_storage(
    settings: Settings,
    *,
    tenant_id: object,
    workspace_id: object,
) -> dict[str, object]:
    """Measure every retained Release plus the governed persistent DATA volume.

    Dependency caches live physically below ``DATA/.runtime`` but are reported
    as Runtime occupancy.  Customer-created DATA excludes that reserved subtree,
    preventing double counting while preserving the single writable mount.
    """

    tenant = UUID(str(tenant_id))
    workspace = UUID(str(workspace_id))
    governed_root = settings.hosted_runtime_data_root.resolve()
    workspace_root = (
        governed_root
        / "tenants"
        / str(tenant)
        / "workspaces"
        / str(workspace)
    ).resolve()
    workspace_root.relative_to(governed_root)
    releases = _tree_usage(workspace_root / "releases")
    runtime_cache = _tree_usage(workspace_root / "data" / ".runtime")
    data = _tree_usage(
        workspace_root / "data",
        excluded_root_names=frozenset({".runtime"}),
    )
    errors = releases.errors + runtime_cache.errors + data.errors
    return {
        "runtime_release_bytes": releases.bytes + runtime_cache.bytes,
        "runtime_release_files": releases.files + runtime_cache.files,
        "data_volume_bytes": data.bytes,
        "data_volume_files": data.files,
        "measured_at": datetime.now(UTC),
        "measurement_status": "complete" if errors == 0 else "partial",
        "scan_error_count": errors,
        "symlinks_followed": False,
        "runtime_cache_classified_as": "runtime_release",
    }
