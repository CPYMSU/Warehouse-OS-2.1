"""Receive a pinned delta in a dedicated staging directory; Source-only registration.

Credentials are prompted without echo and never persisted. The local Warehouse
endpoint is fixed; there is no arbitrary host, shell, job or activation input.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import http.client
import json
import os
import time
from pathlib import Path

from source_delta import (
    MAX_ARCHIVE,
    TransferError,
    apply_delta,
    archive_index,
    read_bounded,
    require,
    safe_path,
    sha,
)
from source_transport import PREFIX, SourceAPI, _read, upload_source


def emit(value):
    print("TIDI_SYNC:" + json.dumps(value, sort_keys=True), flush=True)


def download_base(directory, base, key):
    output = safe_path(directory / "base.zip")
    if output.exists():
        data = read_bounded(output, MAX_ARCHIVE)
        require(
            len(data) == base["size_bytes"] and sha(data) == base["sha256"], "cached_base_drift"
        )
        return output, True
    require(
        type(base["id"]) is int
        and base["id"] > 0
        and type(base["size_bytes"]) is int
        and 0 < base["size_bytes"] <= MAX_ARCHIVE,
        "base_metadata_invalid",
    )
    temporary = safe_path(directory / "base.download")
    require(not temporary.exists(), "base_partial_requires_review")
    connection = http.client.HTTPConnection("127.0.0.1", 8081, timeout=60)
    created = False
    try:
        connection.request(
            "GET",
            PREFIX + "/sources/" + str(base["id"]) + "/download",
            headers={"Authorization": "Bearer " + key},
        )
        response = connection.getresponse()
        require(
            response.status == 200 and response.getheader("Content-SHA256") == base["sha256"],
            "base_download_header_drift",
        )
        size, digest = 0, hashlib.sha256()
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(fd, "wb") as stream:
            while True:
                chunk = response.read(min(1024 * 1024, base["size_bytes"] - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                require(size <= base["size_bytes"], "base_download_size_limit")
                digest.update(chunk)
                stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        require(
            size == base["size_bytes"] and digest.hexdigest() == base["sha256"],
            "base_download_digest_drift",
        )
        os.link(temporary, output, follow_symlinks=False)
        temporary.unlink()
    finally:
        connection.close()
        if created and temporary.exists():
            temporary.unlink()
    return output, False


def run(plan_path, expected_plan_sha256):
    started = time.monotonic()
    plan_path = safe_path(plan_path)
    raw = read_bounded(plan_path, 64 * 1024)
    require(sha(raw) == expected_plan_sha256, "plan_digest_drift")
    plan = json.loads(raw)
    require(
        plan.get("schema") == "tidi.source-delta-sync-plan.v1"
        and plan.get("mode") == "source_only",
        "plan_scope_invalid",
    )
    directory = plan_path.parent
    base, target = plan["base"], plan["target"]
    patch = safe_path(directory / "delta.zip")
    require(
        sha(read_bounded(patch, 16 * 1024 * 1024)) == plan["patch_sha256"], "patch_digest_drift"
    )
    key = getpass.getpass("workspace_key: ").strip()
    require(key.startswith("wak_"), "workspace_credential_missing")
    metrics = []
    api = SourceAPI("http://127.0.0.1:8081", key, observe=metrics.append)
    try:
        rows = _read(api, PREFIX + "/sources").get("sources")
        require(
            isinstance(rows, list)
            and any(
                row.get("id") == base["id"]
                and row.get("uuid") == base["uuid"]
                and row.get("state") == "verified"
                and row.get("artifact_sha256") == base["sha256"]
                and row.get("size_bytes") == base["size_bytes"]
                for row in rows
            ),
            "verified_base_missing",
        )
        base_path, reused = download_base(directory, base, key)
        emit(
            {
                "phase": "base_verified",
                "cached_base_reused": reused,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        )
        output = safe_path(directory / "target.zip")
        if output.exists():
            content = read_bounded(output, MAX_ARCHIVE)
            require(
                sha(content) == target["sha256"] and len(content) == target["size_bytes"],
                "cached_target_drift",
            )
            archive_index(output)
        else:
            apply_delta(
                base_path,
                patch,
                output,
                base_sha256=base["sha256"],
                patch_sha256=plan["patch_sha256"],
                target_sha256=target["sha256"],
            )
        emit(
            {
                "phase": "target_rebuilt",
                "sha256": target["sha256"],
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        )
        result = upload_source(api, output, target, directory / "upload.json", progress=emit)
        source = result["source"]
        receipt = {
            "phase": "verified",
            "source_id": source["id"],
            "source_uuid": source["uuid"],
            "source_reused": result["source_reused"],
            "sha256": target["sha256"],
            "wide_area_patch_bytes": patch.stat().st_size,
            "loopback_uploaded_bytes": result["uploaded_bytes"],
            "request_count": len(metrics),
            "request_elapsed_seconds": round(sum(x["elapsed_seconds"] for x in metrics), 3),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "activation_requested": False,
            "business_writes": False,
        }
        receipt_path = directory / "verified.json"
        if not receipt_path.exists():
            with receipt_path.open("x") as stream:
                json.dump(receipt, stream, sort_keys=True)
        emit(receipt)
        return receipt
    finally:
        api.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("plan")
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args()
    try:
        run(Path(args.plan), args.plan_sha256)
    except Exception as exc:
        emit(
            {
                "phase": "stopped",
                "error_code": str(exc) if isinstance(exc, TransferError) else type(exc).__name__,
            }
        )
        raise SystemExit(1) from None
