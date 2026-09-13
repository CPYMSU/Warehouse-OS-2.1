"""Exact ZIP-record reuse for Source transport; never extracts or deploys an archive.

Promotes the historical raw-record delta design into a bounded, pinned tool.
The receiver requires an independently supplied patch/base/target digest.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import zipfile
from pathlib import Path

MAX_ARCHIVE = 128 * 1024 * 1024
MAX_EXPANDED = 512 * 1024 * 1024
MAX_PATCH = 16 * 1024 * 1024
MAX_ENTRIES = 10_000
SCHEMA = "tidi.source-raw-delta.v2"
FIXED_TIME = (2026, 8, 19, 0, 0, 0)


class TransferError(ValueError):
    """Safe codes only; never include paths, credentials or server response bodies."""


def require(ok, code):
    if not ok:
        raise TransferError(code)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def valid_hash(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), "invalid_digest")


def safe_path(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), "symlink_refused")
    return path


def read_bounded(path, maximum):
    path = safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode), "regular_file_required")
        require(info.st_size <= maximum, "size_limit")
        data = stream.read(maximum + 1)
    require(len(data) <= maximum, "size_limit")
    return data


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def archive_index(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        require(0 < len(infos) <= MAX_ENTRIES, "entry_limit")
        require(len({i.filename for i in infos}) == len(infos), "duplicate_zip_member")
        require(sum(i.file_size for i in infos) <= MAX_EXPANDED, "expanded_size_limit")
        for info in infos:
            name = info.filename
            require(
                name
                and not name.startswith("/")
                and "\\" not in name
                and ":" not in name
                and all(part not in {"", ".", ".."} for part in name.split("/")),
                "unsafe_archive_member",
            )
            require(not stat.S_ISLNK(info.external_attr >> 16), "archive_symlink_refused")
            require(not info.flag_bits & 1, "encrypted_archive_refused")
        require(archive.testzip() is None, "zip_crc_failed")
        return infos, archive.start_dir


def raw_records(path):
    data = read_bounded(path, MAX_ARCHIVE)
    infos, central_offset = archive_index(path)
    require(infos[0].header_offset == 0, "prefixed_zip_refused")
    records = {}
    for index, info in enumerate(infos):
        end = infos[index + 1].header_offset if index + 1 < len(infos) else central_offset
        require(0 <= info.header_offset < end <= len(data), "zip_record_order_invalid")
        records[info.filename] = (info.header_offset, data[info.header_offset : end])
    return data, records, data[central_offset:]


def _partial(output):
    output = safe_path(output)
    partial = safe_path(output.with_name(output.name + ".partial"))
    require(not output.exists() and not partial.exists(), "output_exists")
    return output, partial


def _promote(partial, output):
    # Hard-link publication is atomic and refuses an existing destination.
    partial.chmod(0o600)
    os.link(partial, output, follow_symlinks=False)
    partial.unlink()


def build_delta(base, target, output, *, base_sha256, target_sha256):
    valid_hash(base_sha256)
    valid_hash(target_sha256)
    old_data, old_records, _ = raw_records(base)
    new_data, new_records, central = raw_records(target)
    require(sha(old_data) == base_sha256 and sha(new_data) == target_sha256, "archive_digest_drift")
    operations, literals = [], []
    for ordinal, (name, (_, value)) in enumerate(new_records.items()):
        old = old_records.get(name)
        common = {"length": len(value), "sha256": sha(value)}
        if old and old[1] == value:
            operations.append({"kind": "base", "offset": old[0], **common})
        else:
            member = f"literal/{ordinal:06d}.bin"
            operations.append({"kind": "literal", "member": member, **common})
            literals.append((member, value))
    manifest = {
        "schema": SCHEMA,
        "base_sha256": base_sha256,
        "base_size": len(old_data),
        "target_sha256": target_sha256,
        "target_size": len(new_data),
        "target_entries": len(new_records),
        "central_sha256": sha(central),
        "central_size": len(central),
        "operations": operations,
    }
    output, partial = _partial(output)
    created = False
    try:
        with partial.open("xb") as stream:
            created = True
            with zipfile.ZipFile(
                stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
            ) as patch:
                values = [
                    (
                        "manifest.json",
                        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode(),
                    ),
                    *literals,
                    ("central.bin", central),
                ]
                for name, value in values:
                    info = zipfile.ZipInfo(name, FIXED_TIME)
                    info.external_attr = (stat.S_IFREG | 0o600) << 16
                    patch.writestr(info, value, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            stream.flush()
            os.fsync(stream.fileno())
        patch_data = read_bounded(partial, MAX_PATCH)
        _promote(partial, output)
    finally:
        if created and partial.exists():
            partial.unlink()
    return {
        "schema": SCHEMA,
        "base_sha256": base_sha256,
        "target_sha256": target_sha256,
        "target_bytes": len(new_data),
        "patch_sha256": sha(patch_data),
        "patch_bytes": len(patch_data),
        "reused_records": len(operations) - len(literals),
        "changed_records": len(literals),
        "target_entries": len(new_records),
        "transfer_reduction_percent": round((1 - len(patch_data) / len(new_data)) * 100, 3),
    }


def apply_delta(base, patch_path, output, *, base_sha256, patch_sha256, target_sha256):
    for digest in (base_sha256, patch_sha256, target_sha256):
        valid_hash(digest)
    base_data = read_bounded(base, MAX_ARCHIVE)
    patch_data = read_bounded(patch_path, MAX_PATCH)
    require(sha(base_data) == base_sha256, "base_digest_drift")
    require(sha(patch_data) == patch_sha256, "patch_digest_drift")
    archive_index(patch_path)
    output, partial = _partial(output)
    created = False
    try:
        with zipfile.ZipFile(patch_path) as patch:
            manifest = json.loads(patch.read("manifest.json"), object_pairs_hook=pairs)
            require(
                isinstance(manifest, dict) and manifest.get("schema") == SCHEMA,
                "delta_schema_invalid",
            )
            require(
                manifest.get("base_sha256") == base_sha256
                and manifest.get("base_size") == len(base_data)
                and manifest.get("target_sha256") == target_sha256,
                "manifest_binding_drift",
            )
            target_size = manifest.get("target_size")
            require(
                type(target_size) is int and 0 < target_size <= MAX_ARCHIVE, "target_size_invalid"
            )
            operations = manifest.get("operations")
            require(
                isinstance(operations, list)
                and 0 < len(operations) <= MAX_ENTRIES
                and type(manifest.get("target_entries")) is int
                and len(operations) == manifest["target_entries"],
                "operations_invalid",
            )
            digest, written, used = hashlib.sha256(), 0, {"manifest.json", "central.bin"}
            with partial.open("xb") as stream:
                created = True
                for operation in operations:
                    require(isinstance(operation, dict), "operation_invalid")
                    length = operation.get("length")
                    require(
                        type(length) is int and 0 < length <= target_size - written,
                        "record_length_invalid",
                    )
                    if operation.get("kind") == "base":
                        offset = operation.get("offset")
                        require(
                            type(offset) is int and 0 <= offset <= len(base_data) - length,
                            "base_range_invalid",
                        )
                        value = base_data[offset : offset + length]
                    elif operation.get("kind") == "literal":
                        member = operation.get("member")
                        require(
                            isinstance(member, str)
                            and re.fullmatch(r"literal/[0-9]{6}\.bin", member)
                            and member not in used,
                            "literal_invalid",
                        )
                        used.add(member)
                        require(patch.getinfo(member).file_size == length, "literal_length_invalid")
                        value = patch.read(member)
                    else:
                        raise TransferError("operation_kind_invalid")
                    require(sha(value) == operation.get("sha256"), "record_digest_drift")
                    stream.write(value)
                    digest.update(value)
                    written += len(value)
                require(set(patch.namelist()) == used, "unused_patch_member")
                central = patch.read("central.bin")
                require(
                    len(central) == manifest.get("central_size")
                    and sha(central) == manifest.get("central_sha256")
                    and written + len(central) == target_size,
                    "central_invalid",
                )
                stream.write(central)
                digest.update(central)
                stream.flush()
                os.fsync(stream.fileno())
            require(digest.hexdigest() == target_sha256, "target_digest_drift")
            infos, _ = archive_index(partial)
            require(len(infos) == manifest["target_entries"], "target_entries_invalid")
        _promote(partial, output)
    finally:
        if created and partial.exists():
            partial.unlink()
    return {
        "target_sha256": target_sha256,
        "target_bytes": target_size,
        "target_verified": True,
        "zip_crc_verified": True,
    }


def choose_transport(*, full_bytes, delta_bytes, verified_base_available):
    """Conservative, explicit choice; never uploads a delta as a runnable Source."""
    require(
        type(full_bytes) is int and full_bytes > 0 and type(delta_bytes) is int and delta_bytes > 0,
        "invalid_transport_sizes",
    )
    return (
        "verified_base_delta"
        if verified_base_available is True and delta_bytes < full_bytes * 0.8
        else "full_resumable"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "apply"))
    parser.add_argument("base")
    parser.add_argument("input", help="target ZIP for build; delta ZIP for apply")
    parser.add_argument("output")
    parser.add_argument("--base-sha256", required=True)
    parser.add_argument("--target-sha256", required=True)
    parser.add_argument("--patch-sha256")
    args = parser.parse_args()
    try:
        options = {"base_sha256": args.base_sha256, "target_sha256": args.target_sha256}
        if args.mode == "apply":
            options["patch_sha256"] = args.patch_sha256
        result = (build_delta if args.mode == "build" else apply_delta)(
            args.base, args.input, args.output, **options
        )
        print(json.dumps(result, sort_keys=True))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "stopped": True,
                    "error_code": str(exc)
                    if isinstance(exc, TransferError)
                    else type(exc).__name__,
                }
            )
        )
        raise SystemExit(1) from None
