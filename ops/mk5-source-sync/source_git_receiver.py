"""MK5-only Git delivery receiver. Data transport never activates a release.

Runs on the existing private-data host. It accepts data manifests, not commands.
Credentials remain in memory and the host's existing private credential file.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import stat
from pathlib import Path

from source_delta import (MAX_ARCHIVE, MAX_PATCH, TransferError, apply_delta,
                          archive_index, pairs, read_bounded, require, safe_path, sha, valid_hash)
from source_sync_receiver import download_base
from source_transport import PREFIX, SourceAPI, _read, upload_source

SCHEMA = "tidi.source-git-delivery.v1"
WORKSPACE_UUID = "db3d612c-a53f-4ac8-8412-62ff8199a7ff"
PART_BYTES = 16 * 1024 * 1024


def workspace_info(key):
    connection = http.client.HTTPConnection("127.0.0.1", 8081, timeout=15)
    try:
        connection.request("GET", PREFIX + "/info", headers={"Authorization": "Bearer " + key})
        response = connection.getresponse()
        raw = response.read(1024 * 1024 + 1)
        require(response.status == 200 and len(raw) <= 1024 * 1024, "workspace_read_failed")
        value = json.loads(raw)["workspace"]
        require(value["uuid"] == WORKSPACE_UUID, "workspace_identity_mismatch")
        return value
    finally:
        connection.close()


def host_key():
    path = safe_path(Path.home() / "Server/bonfirework/secrets/digital-asset-workspace-keys.json")
    require(path.is_file(), "host_workspace_key_file_missing")
    require(stat.S_IMODE(path.stat().st_mode) == 0o600, "credential_permissions_invalid")
    require(not stat.S_IMODE(path.parent.stat().st_mode) & 0o077, "credential_directory_permissions_invalid")
    values = json.loads(read_bounded(path, 128 * 1024), object_pairs_hook=pairs)
    matches = [v for k, v in values.items() if k in {"mk5", "mk5-ledger-system"}]
    require(len(matches) == 1 and isinstance(matches[0], str) and matches[0].startswith("wak_"),
            "mk5_host_key_binding_missing")
    workspace_info(matches[0])
    return matches[0]


def parse_manifest(path, expected_sha):
    valid_hash(expected_sha)
    raw = read_bounded(path, 64 * 1024)
    require(sha(raw) == expected_sha, "manifest_digest_drift")
    plan = json.loads(raw, object_pairs_hook=pairs)
    require(plan.get("schema") == SCHEMA and plan.get("mode") == "source_only"
            and plan.get("workspace_uuid") == WORKSPACE_UUID, "manifest_scope_invalid")
    require(plan.get("transport") in {"github_delta", "github_full"}, "transport_invalid")
    target = plan["target"]
    valid_hash(target["sha256"])
    require(type(target["size_bytes"]) is int and 0 < target["size_bytes"] <= MAX_ARCHIVE,
            "target_size_invalid")
    require(type(target["file_count"]) is int and 0 < target["file_count"] <= 10000,
            "target_count_invalid")
    require(re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", target["version_no"]), "target_version_invalid")
    valid_hash(plan["payload_sha256"])
    maximum = MAX_PATCH if plan["transport"] == "github_delta" else MAX_ARCHIVE
    require(type(plan["payload_bytes"]) is int and 0 < plan["payload_bytes"] <= maximum,
            "payload_size_invalid")
    chunks = plan["chunks"]
    require(isinstance(chunks, list) and 0 < len(chunks) <= 8, "chunk_count_invalid")
    total = 0
    for item in chunks:
        valid_hash(item["sha256"])
        require(item["path"] == "objects/" + item["sha256"] + ".bin", "chunk_path_invalid")
        require(type(item["size_bytes"]) is int and 0 < item["size_bytes"] <= PART_BYTES,
                "chunk_size_invalid")
        total += item["size_bytes"]
    require(total == plan["payload_bytes"], "payload_length_invalid")
    if plan["transport"] == "github_delta":
        base = plan["base"]
        valid_hash(base["sha256"])
        require(type(base["id"]) is int and base["id"] > 0
                and re.fullmatch(r"[0-9a-f-]{36}", base["uuid"])
                and type(base["size_bytes"]) is int and 0 < base["size_bytes"] <= MAX_ARCHIVE,
                "base_metadata_invalid")
    else:
        require(plan["payload_sha256"] == target["sha256"]
                and plan["payload_bytes"] == target["size_bytes"], "full_payload_target_mismatch")
    return plan


def verified_source(rows, target):
    matches = [r for r in rows if r.get("artifact_sha256") == target["sha256"]]
    require(len(matches) <= 1, "ambiguous_source_digest")
    if not matches:
        return None
    row = matches[0]
    require(row.get("state") == "verified" and row.get("size_bytes") == target["size_bytes"],
            "existing_source_not_verified")
    return row


def assemble(delivery, plan, work):
    payload = b"".join(read_bounded(safe_path(delivery / item["path"]), PART_BYTES)
                       for item in plan["chunks"])
    offset = 0
    for item in plan["chunks"]:
        part = payload[offset:offset + item["size_bytes"]]
        require(len(part) == item["size_bytes"] and sha(part) == item["sha256"], "chunk_digest_drift")
        offset += len(part)
    require(len(payload) == plan["payload_bytes"] and sha(payload) == plan["payload_sha256"],
            "payload_digest_drift")
    output = safe_path(work / "payload.zip")
    if output.exists():
        require(sha(read_bounded(output, MAX_ARCHIVE)) == plan["payload_sha256"], "cached_payload_drift")
    else:
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
    return output


def reconstruct(delivery, plan, work, key):
    payload = assemble(delivery, plan, work)
    target = plan["target"]
    output = payload
    if plan["transport"] == "github_delta":
        base = plan["base"]
        base_path, _ = download_base(work, base, key)
        output = safe_path(work / "target.zip")
        if not output.exists():
            apply_delta(base_path, payload, output, base_sha256=base["sha256"],
                        patch_sha256=plan["payload_sha256"], target_sha256=target["sha256"])
    content = read_bounded(output, MAX_ARCHIVE)
    require(len(content) == target["size_bytes"] and sha(content) == target["sha256"], "target_digest_drift")
    infos, _ = archive_index(output)
    require(len(infos) == target["file_count"], "target_count_drift")
    return output


def run(action, delivery=None, manifest_sha=None):
    os.umask(0o077)
    key = host_key()
    initial = workspace_info(key)
    if action == "probe":
        return {"phase": "ready", "workspace_verified": True, "source_only": True,
                "activation_requested": False}
    require(action in {"verify", "upload"}, "action_invalid")
    delivery = safe_path(delivery)
    plan = parse_manifest(delivery / "delivery.json", manifest_sha)
    work = safe_path(Path.home() / "Server/bonfirework/cache/mk5-source-sync" / manifest_sha)
    work.mkdir(parents=True, exist_ok=True, mode=0o700)
    api = SourceAPI("http://127.0.0.1:8081", key)
    try:
        rows = _read(api, PREFIX + "/sources")["sources"]
        existing = verified_source(rows, plan["target"])
        if plan["transport"] == "github_delta":
            base = verified_source(rows, plan["base"])
            require(base and base["id"] == plan["base"]["id"] and base["uuid"] == plan["base"]["uuid"],
                    "verified_base_missing")
        # Verification deliberately exercises the real Git download + reconstruction even for an existing target.
        output = None if existing and action == "upload" else reconstruct(delivery, plan, work, key)
        if action == "upload" and not existing:
            upload_source(api, output, plan["target"], work / "upload.json", budget_seconds=1200)
            existing = verified_source(_read(api, PREFIX + "/sources")["sources"], plan["target"])
            require(existing is not None, "source_readback_missing")
        final = workspace_info(key)
        require(initial.get("active_deployment_id") == final.get("active_deployment_id"), "active_pointer_changed")
        result = {"phase": "reconstruction_verified" if action == "verify" else "source_verified",
                  "manifest_sha256": manifest_sha, "target_sha256": plan["target"]["sha256"],
                  "transport": plan["transport"], "payload_bytes": plan["payload_bytes"],
                  "source_id": existing.get("id") if existing else None,
                  "traffic_changed": False, "activation_requested": False, "business_writes": False}
        return result
    finally:
        api.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("probe", "verify", "upload"))
    parser.add_argument("--delivery", type=Path)
    parser.add_argument("--manifest-sha")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.action, args.delivery, args.manifest_sha), sort_keys=True))
    except Exception as exc:
        print(json.dumps({"phase": "stopped", "error_code": str(exc) if isinstance(exc, TransferError)
                          else type(exc).__name__}))
        raise SystemExit(1) from None
