#!/usr/bin/env python3
"""Install a verified reading edition into one tenant's durable research volume.

Run inside the API image with its ordinary settings. No database writes or
credential exports are needed. Previous editions are kept for rollback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from app.core.config import get_settings
from app.db.session import get_engine
from sqlalchemy import text


def install(bundle: Path, tenant_slug: str) -> dict:
    source = bundle.resolve()
    catalog = json.loads((source / "catalog.json").read_text(encoding="utf-8"))
    files = catalog.get("files", {})
    if not catalog.get("available") or not files or len(files) > 500:
        raise ValueError("Invalid or empty research edition")
    verified = {}
    for logical_path, metadata in files.items():
        path = PurePosixPath(logical_path)
        if path.is_absolute() or ".." in path.parts or "\\" in logical_path:
            raise ValueError("Unsafe research edition path")
        original = (source / "content" / path).resolve()
        if not original.is_relative_to(source / "content") or not original.is_file():
            raise ValueError("Research edition file is outside its bundle")
        data = original.read_bytes()
        if (
            len(data) != metadata["bytes"]
            or hashlib.sha256(data).hexdigest() != metadata["sha256"]
        ):
            raise ValueError("Research edition checksum mismatch: " + logical_path)
        verified[logical_path] = data
    if any(item.get("path") not in files for item in catalog.get("documents", [])):
        raise ValueError("Research catalogue references a missing document")
    with get_engine().connect() as connection:
        tenant_id = connection.execute(
            text("SELECT id FROM iam.tenants WHERE slug = :slug AND status = 'active'"),
            {"slug": tenant_slug},
        ).scalar_one()
    base = get_settings().research_repository_root.resolve()
    tenant_root = (base / str(tenant_id)).resolve()
    if not tenant_root.is_relative_to(base):
        raise ValueError("Tenant research root escaped its storage volume")
    editions = tenant_root / "_showcase-editions"
    editions.mkdir(parents=True, exist_ok=True)
    edition_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]
    destination = editions / edition_id
    destination.mkdir()
    for logical_path, data in verified.items():
        target = destination / "content" / logical_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (destination / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    active = tenant_root / "_showcase"
    if active.exists() and not active.is_symlink():
        raise ValueError("Existing research showcase is not a managed edition link")
    temporary = tenant_root / (".showcase-" + uuid4().hex)
    temporary.symlink_to(destination.relative_to(tenant_root), target_is_directory=True)
    previous = os.readlink(active) if active.is_symlink() else None
    os.replace(temporary, active)
    return {
        "tenant": tenant_slug,
        "edition": edition_id,
        "documents": len(catalog.get("documents", [])),
        "files": len(files),
        "previous": previous,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--tenant", required=True)
    options = parser.parse_args()
    try:
        print(json.dumps(install(options.bundle, options.tenant)))
    except Exception as error:
        print("Research edition install failed: " + str(error), file=sys.stderr)
        raise SystemExit(1) from error
