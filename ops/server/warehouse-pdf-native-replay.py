#!/usr/bin/env python3
"""Run the frozen synthetic PDF replay on the native standby host.

This is deliberately not a general job runner.  It accepts one exact replay
bundle shape, uses the active API image only as an immutable Python base, and
starts separate containers with no network, production mounts, or inherited
environment.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import re
import resource
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

INCOMING_ROOT = Path("/var/lib/warehouse-deploy/incoming")
WORK_ROOT = Path("/var/lib/warehouse-deploy/pdf-native-replay")
STATE_ROOT = Path("/opt/warehouse-os/shared/deploy-state")
DOCKER = Path("/usr/bin/docker")
MANAGER_ROLE_ENV = "WAREHOUSE_PDF_NATIVE_EFFECTIVE_NODE_ROLE"

ARCHIVE_PATTERN = re.compile(r"^pdf-native-replay-[a-f0-9]{16}\.zip$")
AUTHORIZATION_PATTERN = re.compile(
    r"^pdf-native-replay-[a-f0-9]{16}\.authorization\.json$"
)
HEX_SHA256 = re.compile(r"^[a-f0-9]{64}$")
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_UNPACKED_BYTES = 32 * 1024 * 1024
MAX_MEMBER_BYTES = 12 * 1024 * 1024
MAX_MEMBER_COUNT = 64
MAX_OUTPUT_BYTES = 1024 * 1024
MAX_ERROR_BYTES = 64 * 1024

PRODUCT_PROFILE = "pdf-subset-compatibility"
DIAGNOSTIC_PROFILE = "pdf-sanitized-failure-family"

PRODUCT_ARCHIVE_BYTES = 14_653_155
PRODUCT_ARCHIVE_SHA256 = (
    "381fb733b4959dd7eae49c7002adbb811ee12bdea50d53cbb5463a242416daa6"
)
DIAGNOSTIC_ARCHIVE_BYTES = 41_323
DIAGNOSTIC_ARCHIVE_SHA256 = (
    "cb0a1f107e5a16865bf0d0eae751a2db21ea4dc309820f50eb1150c4f3c53223"
)
BUNDLE_MANIFEST_SCHEMA = "tidi.pdf-subset-compatibility-replay-bundle.v1"
BUNDLE_MANIFEST_VERSION = "2026-08-28.1"
EXPECTED_PAYLOAD_ROOT_SHA256 = (
    "98db9610d18ef893b5cca797880f431f2a896d1c528fc1b8a9bc6f0eb8ed0f45"
)
BUNDLE_CONTRACT_SCHEMA = "tidi.pdf-subset-compatibility-replay-bundle-contract.v1"
BUNDLE_CONTRACT_VERSION = "2026-08-28.1"
BUNDLE_CONTRACT_SHA256 = (
    "cc40a460577bbf167f8de6471dcdb2fe25c8656d96da45acc1e11a10fc27c6ee"
)
TARGET_SCHEMA = "tidi.pdf-product-target-replay-receipt.v1"
HOST_SCHEMA = "tidi.pdf-native-x86-production-host-receipt.v1"
REPLAY_CONTRACT_SCHEMA = "tidi.pdf-product-dependency-isolation-contract.v1"
REPLAY_CONTRACT_VERSION = "2026-08-26.4"
REPLAY_CONTRACT_SHA256 = (
    "785a64a6c77f730e56404db99c4007b77762fbb2d2032d792bf8e9f108e16dc7"
)
COMPATIBILITY_CONTRACT_SCHEMA = "tidi.pdf-subset-compatibility-repair-contract.v1"
COMPATIBILITY_CONTRACT_VERSION = "2026-08-27.1"
COMPATIBILITY_CONTRACT_SHA256 = (
    "8b5489a11dd5af6856d3d149d5858196e2c18127a2e555aa51e0614ecd2e1150"
)
X86_WHEEL = "pypdfium2-5.13.0-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
ARM_WHEEL = "pypdfium2-5.13.0-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.whl"
ENTRYPOINT = "scripts/run_pdf_product_target_replay.py"
EXPECTED_FIXTURE_MANIFEST_SHA256S = {
    "pdf_poc": "3b884adddae14ff2fec7f6259c4a47ad69f6b3e508994a59a9d99a85b672b540",
    "pdf_advanced_poc": (
        "6b4d496825125c9a1cacbcd23f2998abff6ef5d27d61913fb280f7496f63389e"
    ),
    "pdf_subset_compatibility_poc": (
        "9cd3513ec8928cf9b804d3b366bf0ce98dadd57557897a2f900d63bfc08561b8"
    ),
}
EXPECTED_MAP_SHA256 = "06a62f1cd8504c8804fac065a2426bc085f2aee7f4b4734b4396dfe3ce138401"
EXPECTED_SEMANTIC_MAP_SHA256 = (
    "bc2986d639f98fea4107897c04139fbe1801e38b4066bdf365f5256805699bcb"
)
EXPECTED_REJECTION_MAP_SHA256 = (
    "0682da0a30bcaff8718d8b73a123ecbb420e3a2f1f0a107d42beb8f2b476de93"
)

DIAGNOSTIC_BUNDLE_MANIFEST_SCHEMA = "tidi.pdf-sanitized-failure-family-replay-bundle.v1"
DIAGNOSTIC_BUNDLE_VERSION = "2026-08-28.1"
DIAGNOSTIC_PAYLOAD_ROOT_SHA256 = (
    "a439c5c483c893c794d8313a9fe32f642e3f49d01fc77842d6cff1232ad07e90"
)
DIAGNOSTIC_BUNDLE_CONTRACT_SCHEMA = (
    "tidi.pdf-sanitized-failure-family-replay-bundle-contract.v1"
)
DIAGNOSTIC_BUNDLE_CONTRACT_SHA256 = (
    "01b5fec33aae216d8d2000d9ab56d5eb3d059f1c0c290e6857ff0090eff0ee60"
)
DIAGNOSTIC_CONTRACT_SCHEMA = "tidi.pdf-sanitized-failure-family-diagnostic-contract.v1"
DIAGNOSTIC_CONTRACT_SHA256 = (
    "f3a4ae2d28d71099adec1ce5d01728fe4fc8ae6e2468e43402afa7e227a96582"
)
DIAGNOSTIC_POC_CONTRACT_SCHEMA = (
    "tidi.pdf-sanitized-failure-family-synthetic-poc-contract.v1"
)
DIAGNOSTIC_POC_CONTRACT_SHA256 = (
    "b741aa4d0403db713d23c2774ce595c3599c784a92d3a03d409638fac5b1b2ef"
)
DIAGNOSTIC_FIXTURE_MANIFEST_SHA256 = (
    "5aa97165b471c996149238716b56a1304acd3ff666486cd93f09b937724f1515"
)
DIAGNOSTIC_FIXED_EVENT_MAP_SHA256 = (
    "52ef770e57647d94719e285e51cbd520b0e0d877ae50c495cff0d3325debea08"
)
DIAGNOSTIC_EXPECTED_FAMILY_MAP_SHA256 = (
    "f0dc6e0b72aefa2440013312ec84f8037dec6c514dbe9f624f0aca9e2b34acf1"
)
DIAGNOSTIC_EXPECTED_RECEIPT_SHA256 = (
    "a14fb789cde6e91ec192053375d1185d10760a8a43fe8e237d3d24c59d823554"
)
DIAGNOSTIC_EXPECTED_RECEIPT_FILE_SHA256 = (
    "84d0cfb700a1e5ff16a6eca47e0efad5853a96f878d5c971850f929563ab630c"
)
DIAGNOSTIC_ENTRYPOINT = "scripts/run_pdf_sanitized_failure_family_target_replay.py"
DIAGNOSTIC_ENTRYPOINT_SHA256 = (
    "eaff859dc6b018a826b2b0bc034052885c03752d0ba4ed988b17675818220cb4"
)
DIAGNOSTIC_AUTHORIZATION_SCHEMA = (
    "tidi.pdf-sanitized-failure-family-replay-authorization.v1"
)
DIAGNOSTIC_ATTESTATION_SCHEMA = (
    "tidi.pdf-sanitized-failure-family-target-attestation.v1"
)
DIAGNOSTIC_RECEIPT_SCHEMA = "tidi.pdf-sanitized-failure-family-receipt.v1"
DIAGNOSTIC_TARGET_KEY = "warehouse-linux-x86_64-native"
DIAGNOSTIC_EXECUTION_MODE = "warehouse_native_isolated"
DIAGNOSTIC_AUTHORIZATION_FIELDS = {
    "schema",
    "version",
    "payload_root_sha256",
    "bundle_contract_sha256",
    "target_key",
    "execution_mode",
    "synthetic_replay_allowed",
    "controlled_pdf_allowed",
    "warehouse_native_x86_allowed",
    "ocr_allowed",
    "runtime_parser_registration_allowed",
}

EXPECTED_ARCHIVE_FILES = {
    "backend/app/__init__.py",
    "backend/app/poc/__init__.py",
    "backend/app/poc/pdf_layered.py",
    "backend/app/poc/pdf_product_candidate.py",
    "backend/app/poc/pdf_product_worker.py",
    "backend/app/poc/pdf_syntax.py",
    "bundle-contract.json",
    "bundle-manifest.json",
    "compatibility-contract.json",
    "contract.json",
    "fixtures/pdf_advanced_poc/form_xobject_cycle.pdf",
    "fixtures/pdf_advanced_poc/manifest.json",
    "fixtures/pdf_advanced_poc/nested_form_xobject.pdf",
    "fixtures/pdf_advanced_poc/truetype_tounicode.pdf",
    "fixtures/pdf_advanced_poc/type0_missing_tounicode.pdf",
    "fixtures/pdf_advanced_poc/type0_tounicode_horizontal.pdf",
    "fixtures/pdf_advanced_poc/type0_tounicode_vertical.pdf",
    "fixtures/pdf_advanced_poc/type3_tounicode.pdf",
    "fixtures/pdf_advanced_poc/xref_object_stream.pdf",
    "fixtures/pdf_poc/active_open_action.pdf",
    "fixtures/pdf_poc/image_only.pdf",
    "fixtures/pdf_poc/invisible_text.pdf",
    "fixtures/pdf_poc/manifest.json",
    "fixtures/pdf_poc/mixed_text_image.pdf",
    "fixtures/pdf_poc/mixed_text_vector.pdf",
    "fixtures/pdf_poc/multiple_content_streams.pdf",
    "fixtures/pdf_poc/native_text_complete.pdf",
    "fixtures/pdf_poc/rotated_native_text.pdf",
    "fixtures/pdf_subset_compatibility_poc/combined_transparent_container_text.pdf",
    "fixtures/pdf_subset_compatibility_poc/double_quote_text_operator.pdf",
    "fixtures/pdf_subset_compatibility_poc/identity_decode_parameters_text.pdf",
    "fixtures/pdf_subset_compatibility_poc/identity_params_embedded_content.pdf",
    "fixtures/pdf_subset_compatibility_poc/incremental_xref_resource_limit.pdf",
    "fixtures/pdf_subset_compatibility_poc/incremental_xref_signature.pdf",
    "fixtures/pdf_subset_compatibility_poc/incremental_xref_text.pdf",
    "fixtures/pdf_subset_compatibility_poc/incremental_xref_text_plus_image.pdf",
    "fixtures/pdf_subset_compatibility_poc/indirect_length_active_action.pdf",
    "fixtures/pdf_subset_compatibility_poc/indirect_length_text.pdf",
    "fixtures/pdf_subset_compatibility_poc/indirect_length_text_plus_vector.pdf",
    "fixtures/pdf_subset_compatibility_poc/inline_image_operator.pdf",
    "fixtures/pdf_subset_compatibility_poc/manifest.json",
    "fixtures/pdf_subset_compatibility_poc/single_quote_text_operator.pdf",
    "fixtures/pdf_subset_compatibility_poc/unknown_content_operator.pdf",
    "fixtures/pdf_subset_compatibility_poc/unsupported_decode_predictor.pdf",
    "fixtures/pdf_subset_compatibility_poc/unsupported_stream_filter.pdf",
    "fonts/NotoSansSC-Regular.otf",
    "fonts/OFL-1.1.txt",
    ENTRYPOINT,
    f"wheels/{ARM_WHEEL}",
    f"wheels/{X86_WHEEL}",
}

DIAGNOSTIC_ARCHIVE_FILES = {
    "backend/app/__init__.py",
    "backend/app/poc/__init__.py",
    "backend/app/poc/pdf_sanitized_failure_family.py",
    "bundle-contract.json",
    "bundle-manifest.json",
    "expected-sanitized-receipt.json",
    "fixtures/pdf_sanitized_failure_family_poc/manifest.json",
    *{
        "fixtures/pdf_sanitized_failure_family_poc/"
        f"synthetic_diagnostic_{index:03d}.pdf"
        for index in range(1, 25)
    },
    "frozen-diagnostic-contract.json",
    "poc-contract.json",
    DIAGNOSTIC_ENTRYPOINT,
}


class ReplayFailure(RuntimeError):
    """A sanitized, machine-safe failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ApiSnapshot:
    slot: str
    container: str
    container_id: str
    restart_count: int
    image_id: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        if not raw or len(raw) > MAX_OUTPUT_BYTES:
            raise ReplayFailure("bundle_json_invalid")
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReplayFailure("bundle_json_invalid") from error
    if not isinstance(value, dict):
        raise ReplayFailure("bundle_json_invalid")
    return value


def _verify_host() -> None:
    if (
        platform.system() != "Linux"
        or platform.machine() != "x86_64"
        or os.environ.get(MANAGER_ROLE_ENV) != "standby"
    ):
        raise ReplayFailure("native_x86_standby_required")


def _verify_archive(path: Path, digest: str) -> str:
    if not HEX_SHA256.fullmatch(digest):
        raise ReplayFailure("archive_digest_invalid")
    if path.parent != INCOMING_ROOT or not ARCHIVE_PATTERN.fullmatch(path.name):
        raise ReplayFailure("archive_name_invalid")
    if path.name != f"pdf-native-replay-{digest[:16]}.zip":
        raise ReplayFailure("archive_name_digest_mismatch")
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ReplayFailure("archive_missing") from error
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise ReplayFailure("archive_type_invalid")
    if not 1 <= metadata.st_size <= MAX_ARCHIVE_BYTES:
        raise ReplayFailure("archive_size_invalid")
    if metadata.st_size == PRODUCT_ARCHIVE_BYTES and hmac.compare_digest(
        digest, PRODUCT_ARCHIVE_SHA256
    ):
        profile = PRODUCT_PROFILE
    elif metadata.st_size == DIAGNOSTIC_ARCHIVE_BYTES and hmac.compare_digest(
        digest, DIAGNOSTIC_ARCHIVE_SHA256
    ):
        profile = DIAGNOSTIC_PROFILE
    else:
        raise ReplayFailure("archive_identity_not_allowlisted")
    if not hmac.compare_digest(_sha256(path), digest):
        raise ReplayFailure("archive_checksum_mismatch")
    return profile


def _claim_archive(path: Path, work: Path, digest: str) -> Path:
    """Move the verified upload out of the writable handoff directory."""
    claimed = work / "input.zip"
    try:
        os.replace(path, claimed)
        metadata = claimed.lstat()
    except OSError as error:
        raise ReplayFailure("archive_claim_failed") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or claimed.is_symlink()
        or not 1 <= metadata.st_size <= MAX_ARCHIVE_BYTES
        or not hmac.compare_digest(_sha256(claimed), digest)
    ):
        raise ReplayFailure("archive_claim_failed")
    claimed.chmod(0o400)
    return claimed


def _authorization_path_for_archive(archive: Path) -> Path:
    return archive.with_name(f"{archive.stem}.authorization.json")


def _verify_diagnostic_authorization(path: Path) -> str:
    if (
        path.parent != INCOMING_ROOT
        or not AUTHORIZATION_PATTERN.fullmatch(path.name)
        or path.is_symlink()
    ):
        raise ReplayFailure("external_authorization_invalid")
    try:
        metadata = path.lstat()
        raw = path.read_bytes()
        authorization = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReplayFailure("external_authorization_invalid") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or not 1 <= metadata.st_size <= 16 * 1024
        or metadata.st_size != len(raw)
        or not isinstance(authorization, dict)
        or set(authorization) != DIAGNOSTIC_AUTHORIZATION_FIELDS
        or authorization.get("schema") != DIAGNOSTIC_AUTHORIZATION_SCHEMA
        or authorization.get("version") != DIAGNOSTIC_BUNDLE_VERSION
        or authorization.get("payload_root_sha256") != DIAGNOSTIC_PAYLOAD_ROOT_SHA256
        or authorization.get("bundle_contract_sha256")
        != DIAGNOSTIC_BUNDLE_CONTRACT_SHA256
        or authorization.get("target_key") != DIAGNOSTIC_TARGET_KEY
        or authorization.get("execution_mode") != DIAGNOSTIC_EXECUTION_MODE
        or authorization.get("synthetic_replay_allowed") is not True
        or authorization.get("controlled_pdf_allowed") is not False
        or authorization.get("warehouse_native_x86_allowed") is not True
        or authorization.get("ocr_allowed") is not False
        or authorization.get("runtime_parser_registration_allowed") is not False
    ):
        raise ReplayFailure("external_authorization_invalid")
    return hashlib.sha256(raw).hexdigest()


def _claim_authorization(path: Path, work: Path, expected_sha256: str) -> Path:
    claimed = work / "authorization.json"
    try:
        os.replace(path, claimed)
        metadata = claimed.lstat()
    except OSError as error:
        raise ReplayFailure("external_authorization_claim_failed") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or claimed.is_symlink()
        or not 1 <= metadata.st_size <= 16 * 1024
        or not hmac.compare_digest(_sha256(claimed), expected_sha256)
    ):
        raise ReplayFailure("external_authorization_claim_failed")
    claimed.chmod(0o444)
    if not hmac.compare_digest(
        _verify_diagnostic_authorization_claimed(claimed), expected_sha256
    ):
        raise ReplayFailure("external_authorization_claim_failed")
    return claimed


def _verify_diagnostic_authorization_claimed(path: Path) -> str:
    try:
        raw = path.read_bytes()
        authorization = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReplayFailure("external_authorization_invalid") from error
    if (
        not isinstance(authorization, dict)
        or set(authorization) != DIAGNOSTIC_AUTHORIZATION_FIELDS
        or authorization.get("schema") != DIAGNOSTIC_AUTHORIZATION_SCHEMA
        or authorization.get("version") != DIAGNOSTIC_BUNDLE_VERSION
        or authorization.get("payload_root_sha256") != DIAGNOSTIC_PAYLOAD_ROOT_SHA256
        or authorization.get("bundle_contract_sha256")
        != DIAGNOSTIC_BUNDLE_CONTRACT_SHA256
        or authorization.get("target_key") != DIAGNOSTIC_TARGET_KEY
        or authorization.get("execution_mode") != DIAGNOSTIC_EXECUTION_MODE
        or authorization.get("synthetic_replay_allowed") is not True
        or authorization.get("controlled_pdf_allowed") is not False
        or authorization.get("warehouse_native_x86_allowed") is not True
        or authorization.get("ocr_allowed") is not False
        or authorization.get("runtime_parser_registration_allowed") is not False
    ):
        raise ReplayFailure("external_authorization_invalid")
    return hashlib.sha256(raw).hexdigest()


def _safe_member_name(raw_name: str) -> str:
    if (
        not raw_name
        or len(raw_name) > 240
        or not raw_name.isascii()
        or "\\" in raw_name
        or not re.fullmatch(r"[A-Za-z0-9._/-]+", raw_name)
    ):
        raise ReplayFailure("archive_member_invalid")
    path = PurePosixPath(raw_name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ReplayFailure("archive_member_invalid")
    return path.as_posix()


def _extract_bundle(
    archive: Path,
    bundle: Path,
    expected_files: set[str] = EXPECTED_ARCHIVE_FILES,
) -> None:
    try:
        opened = zipfile.ZipFile(archive)
    except (OSError, zipfile.BadZipFile) as error:
        raise ReplayFailure("archive_zip_invalid") from error
    with opened:
        members = opened.infolist()
        if not 1 <= len(members) <= MAX_MEMBER_COUNT:
            raise ReplayFailure("archive_member_count_invalid")
        names: set[str] = set()
        total = 0
        for member in members:
            name = _safe_member_name(member.filename)
            if name in names or member.is_dir() or member.flag_bits & 0x1:
                raise ReplayFailure("archive_member_invalid")
            names.add(name)
            unix_mode = (member.external_attr >> 16) & 0xFFFF
            if unix_mode and not stat.S_ISREG(unix_mode):
                raise ReplayFailure("archive_member_type_invalid")
            if not 0 <= member.file_size <= MAX_MEMBER_BYTES:
                raise ReplayFailure("archive_member_size_invalid")
            if member.file_size and member.compress_size == 0:
                raise ReplayFailure("archive_compression_invalid")
            if member.compress_size and member.file_size > member.compress_size * 200:
                raise ReplayFailure("archive_compression_invalid")
            total += member.file_size
            if total > MAX_UNPACKED_BYTES:
                raise ReplayFailure("archive_unpacked_size_invalid")
        if names != expected_files:
            raise ReplayFailure("archive_file_set_invalid")

        bundle.mkdir(mode=0o755)
        for member in members:
            name = _safe_member_name(member.filename)
            destination = bundle.joinpath(*PurePosixPath(name).parts)
            destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            try:
                with (
                    opened.open(member, "r") as source,
                    destination.open("xb") as target,
                ):
                    shutil.copyfileobj(source, target, length=1024 * 1024)
            except (OSError, RuntimeError, zipfile.BadZipFile) as error:
                raise ReplayFailure("archive_extract_failed") from error
            destination.chmod(0o444)
        for directory in sorted(
            (item for item in bundle.rglob("*") if item.is_dir()),
            key=lambda item: len(item.parts),
            reverse=True,
        ):
            directory.chmod(0o555)
        bundle.chmod(0o555)


def _verify_product_bundle(bundle: Path) -> None:
    manifest = _read_json(bundle / "bundle-manifest.json")
    entries = manifest.get("files")
    matrix = manifest.get("fixture_matrix")
    targets = manifest.get("targets")
    if (
        manifest.get("schema") != BUNDLE_MANIFEST_SCHEMA
        or manifest.get("version") != BUNDLE_MANIFEST_VERSION
        or manifest.get("preparation_only") is not True
        or manifest.get("execution_authorized") is not False
        or manifest.get("warehouse_native_x86_execution_authorized") is not False
        or manifest.get("warehouse_platform_activation_authorized") is not False
        or manifest.get("current_warehouse_platform_compatible") is not False
        or manifest.get("controlled_corpus_used") is not False
        or manifest.get("runtime_parser_registered") is not False
        or manifest.get("ocr_invoked") is not False
        or manifest.get("fully_synthetic_only") is not True
        or manifest.get("business_data") is not False
        or not isinstance(entries, list)
        or len(entries) != 49
        or manifest.get("payload_file_count") != len(entries)
        or manifest.get("archive_entry_count") != len(EXPECTED_ARCHIVE_FILES)
        or manifest.get("payload_root_sha256") != EXPECTED_PAYLOAD_ROOT_SHA256
        or manifest.get("product_contract_sha256") != REPLAY_CONTRACT_SHA256
        or manifest.get("compatibility_contract_sha256")
        != COMPATIBILITY_CONTRACT_SHA256
        or manifest.get("bundle_contract_sha256") != BUNDLE_CONTRACT_SHA256
        or not isinstance(matrix, dict)
        or not isinstance(targets, dict)
    ):
        raise ReplayFailure("bundle_manifest_invalid")
    if (
        matrix.get("fixture_count") != 32
        or matrix.get("existing_fixture_count") != 16
        or matrix.get("new_fixture_count") != 16
        or matrix.get("success_count") != 15
        or matrix.get("rejection_count") != 17
        or matrix.get("worker_execution_count") != 64
        or matrix.get("repeat_count_per_fixture") != 2
        or matrix.get("fixture_manifest_sha256s") != EXPECTED_FIXTURE_MANIFEST_SHA256S
        or matrix.get("expected_map_sha256") != EXPECTED_MAP_SHA256
        or matrix.get("semantic_output_map_sha256") != EXPECTED_SEMANTIC_MAP_SHA256
        or matrix.get("rejection_map_sha256") != EXPECTED_REJECTION_MAP_SHA256
        or targets.get("linux-arm64") != "native-isolated-pending-separate-confirmation"
        or targets.get("linux-x86_64")
        != "hardware-emulated-diagnostic-pending-separate-confirmation"
        or targets.get("warehouse-linux-x86_64")
        != "native-pending-new-platform-and-separate-confirmation"
    ):
        raise ReplayFailure("bundle_manifest_invalid")
    expected_payloads = EXPECTED_ARCHIVE_FILES - {"bundle-manifest.json"}
    observed: set[str] = set()
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"file", "bytes", "sha256"}:
            raise ReplayFailure("bundle_manifest_invalid")
        name = _safe_member_name(str(item["file"]))
        if name in observed or name not in expected_payloads:
            raise ReplayFailure("bundle_manifest_invalid")
        observed.add(name)
        path = bundle.joinpath(*PurePosixPath(name).parts)
        if (
            not isinstance(item["bytes"], int)
            or not 0 <= item["bytes"] <= MAX_MEMBER_BYTES
            or not isinstance(item["sha256"], str)
            or not HEX_SHA256.fullmatch(item["sha256"])
            or path.stat().st_size != item["bytes"]
            or not hmac.compare_digest(_sha256(path), item["sha256"])
        ):
            raise ReplayFailure("bundle_manifest_mismatch")
    if observed != expected_payloads:
        raise ReplayFailure("bundle_manifest_invalid")
    if not hmac.compare_digest(
        _canonical_sha256(entries), EXPECTED_PAYLOAD_ROOT_SHA256
    ):
        raise ReplayFailure("bundle_manifest_mismatch")

    contract_path = bundle / "contract.json"
    contract = _read_json(contract_path)
    if (
        contract.get("schema") != REPLAY_CONTRACT_SCHEMA
        or contract.get("version") != REPLAY_CONTRACT_VERSION
        or not hmac.compare_digest(_sha256(contract_path), REPLAY_CONTRACT_SHA256)
    ):
        raise ReplayFailure("replay_contract_invalid")

    compatibility_path = bundle / "compatibility-contract.json"
    compatibility = _read_json(compatibility_path)
    if (
        compatibility.get("schema") != COMPATIBILITY_CONTRACT_SCHEMA
        or compatibility.get("version") != COMPATIBILITY_CONTRACT_VERSION
        or not hmac.compare_digest(
            _sha256(compatibility_path), COMPATIBILITY_CONTRACT_SHA256
        )
    ):
        raise ReplayFailure("compatibility_contract_invalid")

    bundle_contract_path = bundle / "bundle-contract.json"
    bundle_contract = _read_json(bundle_contract_path)
    authorization = bundle_contract.get("authorization")
    bundle_specification = bundle_contract.get("bundle")
    target_handoff = bundle_contract.get("target_handoff")
    if not all(
        isinstance(value, dict)
        for value in (authorization, bundle_specification, target_handoff)
    ):
        raise ReplayFailure("bundle_contract_invalid")
    if (
        bundle_contract.get("schema") != BUNDLE_CONTRACT_SCHEMA
        or bundle_contract.get("version") != BUNDLE_CONTRACT_VERSION
        or bundle_contract.get("status")
        != "bundle_preparation_only_execution_confirmation_pending"
        or not hmac.compare_digest(
            _sha256(bundle_contract_path), BUNDLE_CONTRACT_SHA256
        )
        or authorization.get("confirmed_scope") != "prepare_immutable_bundle_only"
        or authorization.get("warehouse_native_x86_replay_allowed") is not False
        or authorization.get("warehouse_platform_activation_allowed") is not False
        or authorization.get("controlled_pdf_read_allowed") is not False
        or bundle_specification.get("payload_file_count") != 49
        or bundle_specification.get("archive_entry_count") != 50
        or bundle_specification.get("execution_authorized") is not False
        or target_handoff.get("current_warehouse_platform_accepts_this_bundle")
        is not False
        or target_handoff.get(
            "new_bounded_platform_candidate_required_before_native_execution"
        )
        is not True
        or target_handoff.get("prior_16_fixture_native_receipt_reusable") is not False
    ):
        raise ReplayFailure("bundle_contract_invalid")


def _verify_diagnostic_sanitized_receipt(receipt: dict[str, Any]) -> None:
    _verify_canonical_receipt(receipt)
    documents = receipt.get("documents")
    aggregate = receipt.get("aggregate")
    if (
        receipt.get("schema") != DIAGNOSTIC_RECEIPT_SCHEMA
        or receipt.get("version") != DIAGNOSTIC_BUNDLE_VERSION
        or receipt.get("checkpoint")
        != "M3-A2-4d-3-synthetic-pdf-sanitized-failure-family-poc"
        or receipt.get("gate_status") != "passed"
        or receipt.get("receipt_sha256") != DIAGNOSTIC_EXPECTED_RECEIPT_SHA256
        or not isinstance(documents, list)
        or len(documents) != 24
        or not isinstance(aggregate, dict)
        or aggregate
        != {
            "document_count": 24,
            "deterministic_count": 24,
            "success_count": 0,
            "rejection_count": 24,
            "unresolved_count": 4,
            "privacy_gate_passed": True,
        }
    ):
        raise ReplayFailure("diagnostic_receipt_invalid")
    expected_ids = {f"syn-pdf-{index:03d}" for index in range(1, 25)}
    observed_ids: set[str] = set()
    allowed_families = {
        "pdf_failure_family_security_or_resource",
        "pdf_failure_family_container_or_stream",
        "pdf_failure_family_text_semantics",
        "pdf_failure_family_locator_proof",
        "pdf_failure_family_coverage_or_native_crosscheck",
        "pdf_failure_family_unresolved",
    }
    for document in documents:
        if (
            not isinstance(document, dict)
            or set(document)
            != {
                "document_id",
                "replay_count",
                "deterministic",
                "outcome",
                "failure_family",
                "candidate_output_suppressed",
            }
            or document.get("document_id") in observed_ids
            or document.get("replay_count") != 2
            or document.get("deterministic") is not True
            or document.get("outcome") != "rejected"
            or document.get("failure_family") not in allowed_families
            or document.get("candidate_output_suppressed") is not True
        ):
            raise ReplayFailure("diagnostic_receipt_invalid")
        observed_ids.add(str(document["document_id"]))
    if observed_ids != expected_ids:
        raise ReplayFailure("diagnostic_receipt_invalid")


def _verify_diagnostic_bundle(bundle: Path) -> None:
    manifest = _read_json(bundle / "bundle-manifest.json")
    entries = manifest.get("files")
    matrix = manifest.get("fixture_matrix")
    targets = manifest.get("targets")
    if (
        manifest.get("schema") != DIAGNOSTIC_BUNDLE_MANIFEST_SCHEMA
        or manifest.get("version") != DIAGNOSTIC_BUNDLE_VERSION
        or manifest.get("preparation_only") is not True
        or manifest.get("execution_authorized_by_bundle") is not False
        or manifest.get("external_execution_authorization_required") is not True
        or manifest.get("bundle_uploaded_to_warehouse_platform") is not False
        or manifest.get("target_runner_executed") is not False
        or manifest.get("warehouse_platform_changed") is not False
        or manifest.get("warehouse_platform_activated") is not False
        or manifest.get("current_warehouse_platform_compatible") is not False
        or manifest.get("controlled_corpus_used") is not False
        or manifest.get("controlled_filesystem_access_count") != 0
        or manifest.get("raw_exception_recovery") is not False
        or manifest.get("runtime_parser_registered") is not False
        or manifest.get("ocr_invoked") is not False
        or manifest.get("fully_synthetic_only") is not True
        or manifest.get("business_data") is not False
        or manifest.get("third_party_dependency_count") != 0
        or not isinstance(entries, list)
        or len(entries) != 33
        or manifest.get("payload_file_count") != len(entries)
        or manifest.get("archive_entry_count") != len(DIAGNOSTIC_ARCHIVE_FILES)
        or manifest.get("payload_root_sha256") != DIAGNOSTIC_PAYLOAD_ROOT_SHA256
        or manifest.get("frozen_diagnostic_contract_sha256")
        != DIAGNOSTIC_CONTRACT_SHA256
        or manifest.get("poc_contract_sha256") != DIAGNOSTIC_POC_CONTRACT_SHA256
        or manifest.get("bundle_contract_sha256") != DIAGNOSTIC_BUNDLE_CONTRACT_SHA256
        or manifest.get("expected_sanitized_receipt_sha256")
        != DIAGNOSTIC_EXPECTED_RECEIPT_SHA256
        or not isinstance(matrix, dict)
        or not isinstance(targets, dict)
    ):
        raise ReplayFailure("diagnostic_bundle_manifest_invalid")
    if (
        matrix.get("fixture_count") != 24
        or matrix.get("family_count") != 6
        or matrix.get("fixture_count_per_family") != 4
        or matrix.get("minimum_distinct_subfamilies_per_family") != 2
        or matrix.get("repeat_count_per_fixture") != 2
        or matrix.get("observation_count_per_target") != 48
        or matrix.get("manifest_sha256") != DIAGNOSTIC_FIXTURE_MANIFEST_SHA256
        or matrix.get("fixed_event_map_sha256") != DIAGNOSTIC_FIXED_EVENT_MAP_SHA256
        or matrix.get("expected_family_map_sha256")
        != DIAGNOSTIC_EXPECTED_FAMILY_MAP_SHA256
        or matrix.get("expected_sanitized_receipt_sha256")
        != DIAGNOSTIC_EXPECTED_RECEIPT_SHA256
        or targets
        != {
            "macos-arm64-native": "pending_separate_confirmation",
            "linux-arm64-native": "pending_separate_confirmation",
            "linux-x86_64-hardware-emulated": "pending_separate_confirmation",
            "warehouse-linux-x86_64-native": (
                "pending_new_platform_candidate_and_separate_confirmation"
            ),
        }
    ):
        raise ReplayFailure("diagnostic_bundle_manifest_invalid")

    expected_payloads = DIAGNOSTIC_ARCHIVE_FILES - {"bundle-manifest.json"}
    observed: set[str] = set()
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"file", "bytes", "sha256"}:
            raise ReplayFailure("diagnostic_bundle_manifest_invalid")
        name = _safe_member_name(str(item["file"]))
        if name in observed or name not in expected_payloads:
            raise ReplayFailure("diagnostic_bundle_manifest_invalid")
        observed.add(name)
        path = bundle.joinpath(*PurePosixPath(name).parts)
        if (
            not isinstance(item["bytes"], int)
            or not 0 <= item["bytes"] <= MAX_MEMBER_BYTES
            or not isinstance(item["sha256"], str)
            or not HEX_SHA256.fullmatch(item["sha256"])
            or path.stat().st_size != item["bytes"]
            or not hmac.compare_digest(_sha256(path), item["sha256"])
        ):
            raise ReplayFailure("diagnostic_bundle_manifest_mismatch")
    if observed != expected_payloads or not hmac.compare_digest(
        _canonical_sha256(entries), DIAGNOSTIC_PAYLOAD_ROOT_SHA256
    ):
        raise ReplayFailure("diagnostic_bundle_manifest_mismatch")

    diagnostic_path = bundle / "frozen-diagnostic-contract.json"
    diagnostic_contract = _read_json(diagnostic_path)
    if (
        diagnostic_contract.get("schema") != DIAGNOSTIC_CONTRACT_SCHEMA
        or diagnostic_contract.get("version") != DIAGNOSTIC_BUNDLE_VERSION
        or diagnostic_contract.get("status")
        != "contract_frozen_implementation_confirmation_pending"
        or not hmac.compare_digest(_sha256(diagnostic_path), DIAGNOSTIC_CONTRACT_SHA256)
    ):
        raise ReplayFailure("diagnostic_contract_invalid")

    poc_path = bundle / "poc-contract.json"
    poc_contract = _read_json(poc_path)
    if (
        poc_contract.get("schema") != DIAGNOSTIC_POC_CONTRACT_SCHEMA
        or poc_contract.get("version") != DIAGNOSTIC_BUNDLE_VERSION
        or poc_contract.get("status") != "synthetic_implementation_contract_frozen"
        or not hmac.compare_digest(_sha256(poc_path), DIAGNOSTIC_POC_CONTRACT_SHA256)
    ):
        raise ReplayFailure("diagnostic_poc_contract_invalid")

    bundle_contract_path = bundle / "bundle-contract.json"
    bundle_contract = _read_json(bundle_contract_path)
    authorization = bundle_contract.get("authorization")
    bundle_specification = bundle_contract.get("bundle")
    external_authorization = bundle_contract.get("external_execution_authorization")
    target_handoff = bundle_contract.get("target_handoff")
    runtime = bundle_contract.get("runtime")
    if not all(
        isinstance(value, dict)
        for value in (
            authorization,
            bundle_specification,
            external_authorization,
            target_handoff,
            runtime,
        )
    ):
        raise ReplayFailure("diagnostic_bundle_contract_invalid")
    if (
        bundle_contract.get("schema") != DIAGNOSTIC_BUNDLE_CONTRACT_SCHEMA
        or bundle_contract.get("version") != DIAGNOSTIC_BUNDLE_VERSION
        or bundle_contract.get("status")
        != "bundle_preparation_only_execution_confirmation_pending"
        or not hmac.compare_digest(
            _sha256(bundle_contract_path), DIAGNOSTIC_BUNDLE_CONTRACT_SHA256
        )
        or authorization.get("bundle_target_runner_execution_allowed") is not False
        or authorization.get("warehouse_native_x86_replay_allowed") is not False
        or authorization.get("bundle_upload_to_warehouse_platform_allowed") is not False
        or authorization.get("controlled_pdf_read_allowed") is not False
        or authorization.get("ocr_allowed") is not False
        or authorization.get("runtime_parser_registration_allowed") is not False
        or bundle_specification.get("payload_file_count") != 33
        or bundle_specification.get("archive_entry_count") != 34
        or bundle_specification.get("fully_synthetic_only") is not True
        or bundle_specification.get("business_data") is not False
        or bundle_specification.get("execution_authorized_by_bundle") is not False
        or bundle_specification.get("external_execution_authorization_required")
        is not True
        or external_authorization.get("schema") != DIAGNOSTIC_AUTHORIZATION_SCHEMA
        or external_authorization.get("must_be_outside_bundle") is not True
        or external_authorization.get("must_bind_exact_target_key") is not True
        or external_authorization.get("not_created_in_current_step") is not True
        or target_handoff.get("current_warehouse_platform_accepts_this_bundle")
        is not False
        or target_handoff.get(
            "new_bounded_platform_candidate_required_before_warehouse_native_execution"
        )
        is not True
        or target_handoff.get("prior_product_or_compatibility_receipts_reusable")
        is not False
        or runtime.get("python_implementation") != "cpython"
        or runtime.get("python_major_minor") != "3.12"
        or runtime.get("third_party_dependency_count") != 0
        or runtime.get("network_install_allowed") is not False
        or runtime.get("network_runtime_required") is not False
    ):
        raise ReplayFailure("diagnostic_bundle_contract_invalid")

    fixture_manifest_path = (
        bundle / "fixtures/pdf_sanitized_failure_family_poc/manifest.json"
    )
    fixture_manifest = _read_json(fixture_manifest_path)
    if (
        not hmac.compare_digest(
            _sha256(fixture_manifest_path), DIAGNOSTIC_FIXTURE_MANIFEST_SHA256
        )
        or fixture_manifest.get("schema")
        != "tidi.pdf-sanitized-failure-family-synthetic-fixture-manifest.v1"
        or fixture_manifest.get("version") != DIAGNOSTIC_BUNDLE_VERSION
        or fixture_manifest.get("fixture_count") != 24
        or fixture_manifest.get("fully_synthetic") is not True
        or fixture_manifest.get("business_data") is not False
        or fixture_manifest.get("fixed_event_map_sha256")
        != DIAGNOSTIC_FIXED_EVENT_MAP_SHA256
        or fixture_manifest.get("expected_family_map_sha256")
        != DIAGNOSTIC_EXPECTED_FAMILY_MAP_SHA256
    ):
        raise ReplayFailure("diagnostic_fixture_manifest_invalid")

    expected_receipt_path = bundle / "expected-sanitized-receipt.json"
    if not hmac.compare_digest(
        _sha256(expected_receipt_path), DIAGNOSTIC_EXPECTED_RECEIPT_FILE_SHA256
    ):
        raise ReplayFailure("diagnostic_receipt_invalid")
    _verify_diagnostic_sanitized_receipt(_read_json(expected_receipt_path))
    if not hmac.compare_digest(
        _sha256(bundle / DIAGNOSTIC_ENTRYPOINT), DIAGNOSTIC_ENTRYPOINT_SHA256
    ):
        raise ReplayFailure("diagnostic_entrypoint_invalid")


def _verify_bundle(bundle: Path, profile: str = PRODUCT_PROFILE) -> None:
    if profile == PRODUCT_PROFILE:
        _verify_product_bundle(bundle)
        return
    if profile == DIAGNOSTIC_PROFILE:
        _verify_diagnostic_bundle(bundle)
        return
    raise ReplayFailure("bundle_profile_invalid")


def _limit_output() -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))


def _run_docker(
    arguments: list[str],
    *,
    timeout: int,
    allow_output: bool = False,
    tolerate_failure: bool = False,
) -> bytes:
    if not DOCKER.is_file() or not os.access(DOCKER, os.X_OK):
        raise ReplayFailure("docker_unavailable")
    environment = {
        "HOME": "/root",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
    }
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            completed = subprocess.run(
                [str(DOCKER), *arguments],
                check=False,
                close_fds=True,
                env=environment,
                preexec_fn=_limit_output,
                start_new_session=True,
                stderr=stderr,
                stdout=stdout,
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            if tolerate_failure:
                return b""
            raise ReplayFailure("docker_execution_failed") from error
        stdout.seek(0)
        stderr.seek(0)
        output = stdout.read(MAX_OUTPUT_BYTES + 1)
        error_output = stderr.read(MAX_ERROR_BYTES + 1)
    if tolerate_failure:
        return output
    if completed.returncode != 0:
        raise ReplayFailure("docker_execution_failed")
    if len(output) > MAX_OUTPUT_BYTES or len(error_output) > MAX_ERROR_BYTES:
        raise ReplayFailure("docker_output_limit_exceeded")
    if error_output:
        raise ReplayFailure("docker_stderr_not_empty")
    if not allow_output and output:
        raise ReplayFailure("docker_stdout_not_empty")
    return output


def _docker_text(arguments: list[str]) -> str:
    output = _run_docker(arguments, timeout=20, allow_output=True)
    try:
        return output.decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise ReplayFailure("docker_output_invalid") from error


def _api_snapshot() -> ApiSnapshot:
    try:
        slot = (STATE_ROOT / "active-slot").read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError) as error:
        raise ReplayFailure("production_api_identity_unavailable") from error
    if slot not in {"blue", "green"}:
        raise ReplayFailure("production_api_identity_unavailable")
    container = f"warehouse-os-api-{slot}"
    raw = _docker_text(
        [
            "inspect",
            "--format",
            "{{.Id}}|{{.RestartCount}}|{{.Image}}|{{.State.Running}}",
            container,
        ]
    )
    parts = raw.split("|")
    if len(parts) != 4:
        raise ReplayFailure("production_api_identity_unavailable")
    container_id, restart_raw, image_id, running = parts
    if (
        not re.fullmatch(r"[a-f0-9]{64}", container_id)
        or not re.fullmatch(r"sha256:[a-f0-9]{64}", image_id)
        or not restart_raw.isdigit()
        or running != "true"
    ):
        raise ReplayFailure("production_api_identity_unavailable")
    image_platform = _docker_text(
        ["image", "inspect", "--format", "{{.Os}}/{{.Architecture}}", image_id]
    )
    if image_platform != "linux/amd64":
        raise ReplayFailure("native_x86_image_required")
    return ApiSnapshot(
        slot=slot,
        container=container,
        container_id=container_id,
        restart_count=int(restart_raw),
        image_id=image_id,
    )


def _container_base(name: str, image_id: str) -> list[str]:
    return [
        "run",
        "--rm",
        "--name",
        name,
        "--pull=never",
        "--platform",
        "linux/amd64",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--pids-limit",
        "64",
        "--memory",
        "512m",
        "--memory-swap",
        "512m",
        "--cpus",
        "1",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=67108864,mode=1777",
        "--user",
        "65532:65532",
        "--workdir",
        "/tmp",
        "--entrypoint",
        "/usr/bin/env",
        image_id,
        "-i",
    ]


def _remove_container(name: str) -> None:
    try:
        _run_docker(["rm", "-f", name], timeout=20, tolerate_failure=True)
    except ReplayFailure:
        pass


def _install_dependency(
    *, bundle: Path, site: Path, image_id: str, container_name: str
) -> None:
    arguments = _container_base(container_name, image_id)
    mount_at = arguments.index("--entrypoint")
    arguments[mount_at:mount_at] = [
        "--mount",
        f"type=bind,src={bundle},dst=/bundle,readonly",
        "--mount",
        f"type=bind,src={site},dst=/runtime/site",
    ]
    arguments.extend(
        [
            "HOME=/tmp",
            "LANG=C.UTF-8",
            "LC_ALL=C.UTF-8",
            "PATH=/usr/local/bin:/usr/bin:/bin",
            "PIP_DISABLE_PIP_VERSION_CHECK=1",
            "PIP_NO_CACHE_DIR=1",
            "PYTHONDONTWRITEBYTECODE=1",
            "/usr/local/bin/python",
            "-I",
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-index",
            "--no-deps",
            "--no-compile",
            "--target",
            "/runtime/site",
            f"/bundle/wheels/{X86_WHEEL}",
        ]
    )
    _run_docker(arguments, timeout=180, allow_output=True)


def _run_replay(
    *, bundle: Path, site: Path, image_id: str, container_name: str
) -> dict[str, Any]:
    arguments = _container_base(container_name, image_id)
    mount_at = arguments.index("--entrypoint")
    arguments[mount_at:mount_at] = [
        "--mount",
        f"type=bind,src={bundle},dst=/bundle,readonly",
        "--mount",
        f"type=bind,src={site},dst=/runtime/site,readonly",
        "--mount",
        (
            f"type=bind,src={bundle / 'fonts'},"
            "dst=/usr/share/fonts/opentype/tidi,readonly"
        ),
    ]
    arguments.extend(
        [
            "LANG=C.UTF-8",
            "LC_ALL=C.UTF-8",
            "PATH=/usr/local/bin:/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE=1",
            "PYTHONHASHSEED=0",
            "PYTHONUTF8=1",
            "TIDI_PDF_EXECUTION_MODE=native",
            "TIDI_PDF_OS_SANDBOX=linux-container-product-v1",
            "TIDI_PDF_SITE_ROOT=/runtime/site",
            "TIDI_PDF_TARGET=linux-x86_64",
            "/usr/local/bin/python",
            "-I",
            f"/bundle/{ENTRYPOINT}",
            "--backend-root",
            "/bundle/backend",
            "--fixture-root",
            "/bundle/fixtures",
            "--contract",
            "/bundle/contract.json",
            "--compatibility-contract",
            "/bundle/compatibility-contract.json",
            "--wheel",
            f"/bundle/wheels/{X86_WHEEL}",
            "--site-root",
            "/runtime/site",
            "--font-file",
            "/usr/share/fonts/opentype/tidi/NotoSansSC-Regular.otf",
            "--font-license",
            "/usr/share/fonts/opentype/tidi/OFL-1.1.txt",
            "--target",
            "linux-x86_64",
            "--expected-machine",
            "x86_64",
            "--execution-mode",
            "native",
        ]
    )
    output = _run_docker(arguments, timeout=600, allow_output=True)
    try:
        value = json.loads(output)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReplayFailure("target_receipt_invalid") from error
    if not isinstance(value, dict):
        raise ReplayFailure("target_receipt_invalid")
    _verify_target_receipt(value)
    return value


def _verify_diagnostic_attestation(
    attestation: dict[str, Any], authorization_sha256: str
) -> None:
    observed = attestation.get("attestation_sha256")
    if not isinstance(observed, str) or not HEX_SHA256.fullmatch(observed):
        raise ReplayFailure("diagnostic_attestation_invalid")
    canonical = dict(attestation)
    del canonical["attestation_sha256"]
    if (
        not hmac.compare_digest(_canonical_sha256(canonical), observed)
        or attestation.get("schema") != DIAGNOSTIC_ATTESTATION_SCHEMA
        or attestation.get("version") != DIAGNOSTIC_BUNDLE_VERSION
        or attestation.get("target_key") != DIAGNOSTIC_TARGET_KEY
        or attestation.get("python_implementation") != "cpython"
        or attestation.get("python_version") != "3.12"
        or attestation.get("system") != "Linux"
        or attestation.get("machine") != "x86_64"
        or attestation.get("execution_mode") != DIAGNOSTIC_EXECUTION_MODE
        or attestation.get("payload_root_sha256") != DIAGNOSTIC_PAYLOAD_ROOT_SHA256
        or attestation.get("bundle_contract_sha256")
        != DIAGNOSTIC_BUNDLE_CONTRACT_SHA256
        or attestation.get("fixture_manifest_sha256")
        != DIAGNOSTIC_FIXTURE_MANIFEST_SHA256
        or attestation.get("sanitized_receipt_sha256")
        != DIAGNOSTIC_EXPECTED_RECEIPT_SHA256
        or attestation.get("authorization_receipt_sha256") != authorization_sha256
        or attestation.get("fixture_count") != 24
        or attestation.get("observation_count") != 48
        or attestation.get("fully_synthetic_only") is not True
        or attestation.get("business_data") is not False
        or attestation.get("controlled_corpus_used") is not False
        or attestation.get("pdf_bytes_used_for_classification") is not False
        or attestation.get("raw_exception_recovery") is not False
        or attestation.get("ocr_invoked") is not False
        or attestation.get("runtime_parser_registered") is not False
        or attestation.get("external_isolation_attestation_required") is not True
    ):
        raise ReplayFailure("diagnostic_attestation_invalid")


def _run_diagnostic_replay(
    *,
    bundle: Path,
    authorization: Path,
    authorization_sha256: str,
    output: Path,
    image_id: str,
    container_name: str,
) -> dict[str, Any]:
    arguments = _container_base(container_name, image_id)
    mount_at = arguments.index("--entrypoint")
    arguments[mount_at:mount_at] = [
        "--mount",
        f"type=bind,src={bundle},dst=/bundle,readonly",
        "--mount",
        f"type=bind,src={authorization},dst=/authorization.json,readonly",
        "--mount",
        f"type=bind,src={output},dst=/output",
    ]
    arguments.extend(
        [
            "LANG=C.UTF-8",
            "LC_ALL=C.UTF-8",
            "PATH=/usr/local/bin:/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE=1",
            "PYTHONHASHSEED=0",
            "PYTHONUTF8=1",
            "/usr/local/bin/python",
            "-I",
            f"/bundle/{DIAGNOSTIC_ENTRYPOINT}",
            "--bundle-root",
            "/bundle",
            "--target-key",
            DIAGNOSTIC_TARGET_KEY,
            "--authorization-receipt",
            "/authorization.json",
            "--output-dir",
            "/output",
        ]
    )
    raw_summary = _run_docker(arguments, timeout=180, allow_output=True)
    try:
        summary = json.loads(raw_summary)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReplayFailure("diagnostic_summary_invalid") from error
    if (
        not isinstance(summary, dict)
        or summary
        != {
            "target_key": DIAGNOSTIC_TARGET_KEY,
            "fixture_count": 24,
            "observation_count": 48,
            "sanitized_receipt_sha256": DIAGNOSTIC_EXPECTED_RECEIPT_SHA256,
            "attestation_sha256": summary.get("attestation_sha256"),
            "controlled_corpus_used": False,
        }
        or not isinstance(summary.get("attestation_sha256"), str)
        or not HEX_SHA256.fullmatch(summary["attestation_sha256"])
    ):
        raise ReplayFailure("diagnostic_summary_invalid")
    expected_names = {"sanitized-receipt.json", "target-attestation.json"}
    try:
        observed_names = {item.name for item in output.iterdir()}
    except OSError as error:
        raise ReplayFailure("diagnostic_output_invalid") from error
    if observed_names != expected_names:
        raise ReplayFailure("diagnostic_output_invalid")
    receipt_path = output / "sanitized-receipt.json"
    attestation_path = output / "target-attestation.json"
    if (
        not receipt_path.is_file()
        or receipt_path.is_symlink()
        or not attestation_path.is_file()
        or attestation_path.is_symlink()
    ):
        raise ReplayFailure("diagnostic_output_invalid")
    receipt = _read_json(receipt_path)
    expected_receipt = _read_json(bundle / "expected-sanitized-receipt.json")
    _verify_diagnostic_sanitized_receipt(receipt)
    if receipt != expected_receipt:
        raise ReplayFailure("diagnostic_receipt_invalid")
    attestation = _read_json(attestation_path)
    _verify_diagnostic_attestation(attestation, authorization_sha256)
    if summary.get("attestation_sha256") != attestation.get("attestation_sha256"):
        raise ReplayFailure("diagnostic_attestation_invalid")
    return {
        "sanitized_receipt": receipt,
        "target_attestation": attestation,
    }


def _verify_canonical_receipt(receipt: dict[str, Any]) -> None:
    observed = receipt.get("receipt_sha256")
    if not isinstance(observed, str) or not HEX_SHA256.fullmatch(observed):
        raise ReplayFailure("target_receipt_invalid")
    canonical = dict(receipt)
    del canonical["receipt_sha256"]
    if not hmac.compare_digest(_canonical_sha256(canonical), observed):
        raise ReplayFailure("target_receipt_invalid")


def _verify_target_receipt(receipt: dict[str, Any]) -> None:
    _verify_canonical_receipt(receipt)
    dependency = receipt.get("dependency")
    font = receipt.get("font_fallback")
    isolation = receipt.get("isolation")
    matrix = receipt.get("fixture_matrix")
    if not all(
        isinstance(value, dict) for value in (dependency, font, isolation, matrix)
    ):
        raise ReplayFailure("target_receipt_invalid")
    successes = matrix.get("success_outputs")
    rejections = matrix.get("rejections")
    seccomp_filters = isolation.get("seccomp_filters")
    if (
        receipt.get("schema") != TARGET_SCHEMA
        or receipt.get("contract_version") != REPLAY_CONTRACT_VERSION
        or receipt.get("compatibility_contract_version")
        != COMPATIBILITY_CONTRACT_VERSION
        or receipt.get("compatibility_contract_sha256") != COMPATIBILITY_CONTRACT_SHA256
        or receipt.get("target") != "linux-x86_64"
        or receipt.get("platform_system") != "Linux"
        or receipt.get("platform_machine") != "x86_64"
        or receipt.get("execution_mode") != "native"
        or receipt.get("native_production_host_validation_deferred") is not False
        or receipt.get("product_isolation_proven_for_target") is not True
        or receipt.get("controlled_corpus_used") is not False
        or receipt.get("runtime_parser_registered") is not False
        or dependency.get("wheel_file") != X86_WHEEL
        or dependency.get("wheel_bytes") != 3_730_077
        or dependency.get("wheel_sha256")
        != "81df25c1ab4c13ff773102d3cbea1967511d079123b067fc077bd0c4d57d91d8"
        or dependency.get("offline_file_install") is not True
        or dependency.get("license_file_count") != 19
        or dependency.get("pypdfium2_version") != "5.13.0"
        or dependency.get("pdfium_version") != "153.0.7999.0"
        or dependency.get("pdfium_flags") != []
        or dependency.get("native_elf_machine") != 62
        or font.get("file") != "NotoSansSC-Regular.otf"
        or font.get("bytes") != 8_331_336
        or font.get("sha256")
        != "faa6c9df652116dde789d351359f3d7e5d2285a2b2a1f04a2d7244df706d5ea9"
        or font.get("license_file") != "OFL-1.1.txt"
        or font.get("license_bytes") != 4_301
        or font.get("license_sha256")
        != "6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2"
        or font.get("read_only_mount") is not True
        or font.get("network_resolution_used") is not False
        or font.get("semantic_authority") is not False
        or font.get("proves_embedded_font_truth") is not False
        or isolation.get("network_egress_denied") is not True
        or isolation.get("root_filesystem_write_denied") is not True
        or isolation.get("dedicated_tmpfs_noexec") is not True
        or isolation.get("capabilities_dropped") is not True
        or isolation.get("cap_eff_hex") != "0000000000000000"
        or isolation.get("no_new_privileges") is not True
        or isolation.get("seccomp_active") is not True
        or isolation.get("seccomp_mode") != 2
        or not isinstance(seccomp_filters, int)
        or isinstance(seccomp_filters, bool)
        or seccomp_filters < 1
        or isolation.get("non_root_user") is not True
        or isolation.get("pids_limit") != 64
        or isolation.get("process_limit_bounded") is not True
        or isolation.get("memory_limit_bytes") != 536870912
        or isolation.get("memory_limit_bounded") is not True
        or isolation.get("external_business_mounts_absent") is not True
        or isolation.get("environment_allowlisted") is not True
        or isolation.get("product_isolation_proven_for_target") is not True
        or matrix.get("fixture_count") != 32
        or matrix.get("existing_fixture_count") != 16
        or matrix.get("new_fixture_count") != 16
        or matrix.get("success_count") != 15
        or matrix.get("rejection_count") != 17
        or matrix.get("worker_execution_count") != 64
        or matrix.get("repeat_count_per_fixture") != 2
        or matrix.get("fixture_manifest_sha256s") != EXPECTED_FIXTURE_MANIFEST_SHA256S
        or matrix.get("expected_map_sha256") != EXPECTED_MAP_SHA256
        or matrix.get("semantic_output_map_sha256") != EXPECTED_SEMANTIC_MAP_SHA256
        or matrix.get("rejection_map_sha256") != EXPECTED_REJECTION_MAP_SHA256
        or not isinstance(successes, dict)
        or len(successes) != 15
        or _canonical_sha256(successes) != EXPECTED_SEMANTIC_MAP_SHA256
        or not isinstance(rejections, dict)
        or len(rejections) != 17
        or _canonical_sha256(rejections) != EXPECTED_REJECTION_MAP_SHA256
    ):
        raise ReplayFailure("target_receipt_invalid")


def _safe_cleanup_work(work: Path | None) -> bool:
    if work is None:
        return True
    try:
        if work.parent != WORK_ROOT or not work.name.startswith("run-"):
            return False
        for directory in [work, *(item for item in work.rglob("*") if item.is_dir())]:
            directory.chmod(0o700)
        shutil.rmtree(work)
        return not work.exists()
    except OSError:
        return False


def _safe_cleanup_archive(archive: Path) -> bool:
    if archive.parent != INCOMING_ROOT or not ARCHIVE_PATTERN.fullmatch(archive.name):
        return False
    try:
        archive.unlink(missing_ok=True)
        return not archive.exists()
    except OSError:
        return False


def _safe_cleanup_authorization(path: Path | None) -> bool:
    if path is None:
        return True
    if path.parent != INCOMING_ROOT or not AUTHORIZATION_PATTERN.fullmatch(path.name):
        return False
    try:
        path.unlink(missing_ok=True)
        return not path.exists()
    except OSError:
        return False


def execute(archive: Path, digest: str) -> dict[str, Any]:
    work: Path | None = None
    install_container = f"warehouse-pdf-native-install-{digest[:16]}"
    replay_container = f"warehouse-pdf-native-replay-{digest[:16]}"
    target_receipt: dict[str, Any] | None = None
    profile: str | None = None
    authorization_path: Path | None = None
    authorization_sha256: str | None = None
    api_unchanged = False
    restart_unchanged = False
    archive_cleanup_allowed = False
    authorization_cleanup_allowed = False
    cleanup_archive = False
    cleanup_authorization = True
    cleanup_work = False
    try:
        _verify_host()
        profile = _verify_archive(archive, digest)
        archive_cleanup_allowed = True
        if profile == DIAGNOSTIC_PROFILE:
            authorization_path = _authorization_path_for_archive(archive)
            authorization_cleanup_allowed = True
            authorization_sha256 = _verify_diagnostic_authorization(authorization_path)
        WORK_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
        WORK_ROOT.chmod(0o700)
        work = Path(tempfile.mkdtemp(prefix="run-", dir=WORK_ROOT))
        work.chmod(0o755)
        claimed_archive = _claim_archive(archive, work, digest)
        claimed_authorization: Path | None = None
        if authorization_path is not None and authorization_sha256 is not None:
            claimed_authorization = _claim_authorization(
                authorization_path, work, authorization_sha256
            )
        before = _api_snapshot()
        bundle = work / "bundle"
        expected_files = (
            DIAGNOSTIC_ARCHIVE_FILES
            if profile == DIAGNOSTIC_PROFILE
            else EXPECTED_ARCHIVE_FILES
        )
        _extract_bundle(claimed_archive, bundle, expected_files)
        _verify_bundle(bundle, profile)
        _remove_container(install_container)
        _remove_container(replay_container)
        if profile == PRODUCT_PROFILE:
            site = work / "site"
            site.mkdir(mode=0o750)
            os.chown(site, 65532, 65532)
            _install_dependency(
                bundle=bundle,
                site=site,
                image_id=before.image_id,
                container_name=install_container,
            )
            for path in site.rglob("*"):
                if path.is_symlink():
                    raise ReplayFailure("dependency_site_symlink_forbidden")
            target_receipt = _run_replay(
                bundle=bundle,
                site=site,
                image_id=before.image_id,
                container_name=replay_container,
            )
        elif (
            profile == DIAGNOSTIC_PROFILE
            and claimed_authorization is not None
            and authorization_sha256 is not None
        ):
            output = work / "output"
            output.mkdir(mode=0o750)
            os.chown(output, 65532, 65532)
            target_receipt = _run_diagnostic_replay(
                bundle=bundle,
                authorization=claimed_authorization,
                authorization_sha256=authorization_sha256,
                output=output,
                image_id=before.image_id,
                container_name=replay_container,
            )
        else:
            raise ReplayFailure("bundle_profile_invalid")
        after = _api_snapshot()
        api_unchanged = (
            after.slot == before.slot
            and after.container == before.container
            and after.container_id == before.container_id
            and after.image_id == before.image_id
        )
        restart_unchanged = after.restart_count == before.restart_count
        if not api_unchanged or not restart_unchanged:
            raise ReplayFailure("production_api_boundary_changed")
    finally:
        _remove_container(install_container)
        _remove_container(replay_container)
        cleanup_work = _safe_cleanup_work(work)
        cleanup_archive = (
            _safe_cleanup_archive(archive)
            if archive_cleanup_allowed
            else not archive.exists()
        )
        cleanup_authorization = (
            _safe_cleanup_authorization(authorization_path)
            if authorization_cleanup_allowed
            else authorization_path is None or not authorization_path.exists()
        )

    if target_receipt is None:
        raise ReplayFailure("target_receipt_missing")
    if not cleanup_archive or not cleanup_authorization or not cleanup_work:
        raise ReplayFailure("temporary_material_cleanup_failed")
    receipt: dict[str, Any] = {
        "schema": HOST_SCHEMA,
        "host_class": "warehouse-vultr-standby-production-homogeneous",
        "node_role": "standby",
        "platform_system": "Linux",
        "platform_machine": "x86_64",
        "execution_mode": "native",
        "production_homogeneous": True,
        "hardware_emulation_used": False,
        "production_secrets_injected": False,
        "production_database_attached": False,
        "production_object_storage_attached": False,
        "target_replay": target_receipt,
        "production_boundary": {
            "api_identity_unchanged": api_unchanged,
            "api_restart_count_unchanged": restart_unchanged,
        },
        "cleanup": {
            "archive_removed": cleanup_archive,
            "work_directory_removed": cleanup_work,
        },
    }
    if profile == DIAGNOSTIC_PROFILE:
        if authorization_sha256 is None:
            raise ReplayFailure("external_authorization_invalid")
        receipt["replay_profile"] = DIAGNOSTIC_PROFILE
        receipt["external_authorization_receipt_sha256"] = authorization_sha256
        receipt["cleanup"] = {
            "archive_removed": cleanup_archive,
            "authorization_receipt_removed": cleanup_authorization,
            "work_directory_removed": cleanup_work,
        }
    receipt["receipt_sha256"] = _canonical_sha256(receipt)
    return receipt


def main() -> int:
    if len(sys.argv) != 3:
        print("pdf-native-replay: usage_invalid", file=sys.stderr)
        return 2
    archive = Path(sys.argv[1])
    digest = sys.argv[2]
    try:
        receipt = execute(archive, digest)
    except ReplayFailure as error:
        print(f"pdf-native-replay: {error.code}", file=sys.stderr)
        return 1
    except Exception:  # noqa: BLE001 - never expose an unexpected traceback or host detail
        print("pdf-native-replay: internal_error", file=sys.stderr)
        return 1
    print(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
