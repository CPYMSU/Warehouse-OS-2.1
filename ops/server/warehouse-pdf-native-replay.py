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
PRODUCTION_ENV = Path("/opt/warehouse-os/shared/.env.production")
DOCKER = Path("/usr/bin/docker")

ARCHIVE_PATTERN = re.compile(r"^pdf-native-replay-[a-f0-9]{16}\.zip$")
HEX_SHA256 = re.compile(r"^[a-f0-9]{64}$")
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_UNPACKED_BYTES = 32 * 1024 * 1024
MAX_MEMBER_BYTES = 12 * 1024 * 1024
MAX_MEMBER_COUNT = 64
MAX_OUTPUT_BYTES = 1024 * 1024
MAX_ERROR_BYTES = 64 * 1024

TARGET_SCHEMA = "tidi.pdf-product-target-replay-receipt.v1"
HOST_SCHEMA = "tidi.pdf-native-x86-production-host-receipt.v1"
REPLAY_CONTRACT_SCHEMA = "tidi.pdf-product-dependency-isolation-contract.v1"
REPLAY_CONTRACT_VERSION = "2026-08-26.4"
X86_WHEEL = "pypdfium2-5.13.0-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
ARM_WHEEL = "pypdfium2-5.13.0-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.whl"
ENTRYPOINT = "scripts/run_pdf_product_target_replay.py"

EXPECTED_ARCHIVE_FILES = {
    "backend/app/__init__.py",
    "backend/app/poc/__init__.py",
    "backend/app/poc/pdf_layered.py",
    "backend/app/poc/pdf_product_candidate.py",
    "backend/app/poc/pdf_product_worker.py",
    "backend/app/poc/pdf_syntax.py",
    "bundle-manifest.json",
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
    "fonts/NotoSansSC-Regular.otf",
    "fonts/OFL-1.1.txt",
    ENTRYPOINT,
    f"wheels/{ARM_WHEEL}",
    f"wheels/{X86_WHEEL}",
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
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ReplayFailure("native_x86_standby_required")
    try:
        raw = PRODUCTION_ENV.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ReplayFailure("native_x86_standby_required") from error
    roles: list[str] = []
    for line in raw.splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "WAREHOUSE_NODE_ROLE":
            roles.append(value.strip().strip("'\""))
    if roles != ["standby"]:
        raise ReplayFailure("native_x86_standby_required")


def _verify_archive(path: Path, digest: str) -> None:
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
    if not hmac.compare_digest(_sha256(path), digest):
        raise ReplayFailure("archive_checksum_mismatch")


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


def _extract_bundle(archive: Path, bundle: Path) -> None:
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
        if names != EXPECTED_ARCHIVE_FILES:
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


def _verify_bundle(bundle: Path) -> None:
    manifest = _read_json(bundle / "bundle-manifest.json")
    entries = manifest.get("files")
    if (
        manifest.get("schema") != "tidi.pdf-product-replay-bundle.v1"
        or manifest.get("fully_synthetic_only") is not True
        or manifest.get("business_data") is not False
        or not isinstance(entries, list)
        or manifest.get("file_count") != len(entries)
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

    contract = _read_json(bundle / "contract.json")
    if (
        contract.get("schema") != REPLAY_CONTRACT_SCHEMA
        or contract.get("version") != REPLAY_CONTRACT_VERSION
    ):
        raise ReplayFailure("replay_contract_invalid")


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
    if (
        receipt.get("schema") != TARGET_SCHEMA
        or receipt.get("contract_version") != REPLAY_CONTRACT_VERSION
        or receipt.get("target") != "linux-x86_64"
        or receipt.get("platform_system") != "Linux"
        or receipt.get("platform_machine") != "x86_64"
        or receipt.get("execution_mode") != "native"
        or receipt.get("native_production_host_validation_deferred") is not False
        or receipt.get("product_isolation_proven_for_target") is not True
        or receipt.get("controlled_corpus_used") is not False
        or receipt.get("runtime_parser_registered") is not False
        or dependency.get("pypdfium2_version") != "5.13.0"
        or dependency.get("pdfium_version") != "153.0.7999.0"
        or dependency.get("native_elf_machine") != 62
        or font.get("read_only_mount") is not True
        or isolation.get("network_egress_denied") is not True
        or isolation.get("root_filesystem_write_denied") is not True
        or isolation.get("dedicated_tmpfs_noexec") is not True
        or isolation.get("capabilities_dropped") is not True
        or isolation.get("no_new_privileges") is not True
        or isolation.get("seccomp_mode") != 2
        or isolation.get("non_root_user") is not True
        or isolation.get("pids_limit") != 64
        or isolation.get("memory_limit_bytes") != 536870912
        or isolation.get("external_business_mounts_absent") is not True
        or matrix.get("fixture_count") != 16
        or matrix.get("success_count") != 9
        or matrix.get("rejection_count") != 7
        or matrix.get("repeat_count_per_fixture") != 2
        or matrix.get("semantic_output_map_sha256")
        != "7297c59cd5ccbb90b837b553287da149b5fa689b94a3f8565110eb4b76a28c68"
        or matrix.get("rejection_map_sha256")
        != "5ff6e6c5392f5967223df1ec73afe7c0e7a65a854dc4931a5d7ea26e99f96f88"
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


def execute(archive: Path, digest: str) -> dict[str, Any]:
    work: Path | None = None
    install_container = f"warehouse-pdf-native-install-{digest[:16]}"
    replay_container = f"warehouse-pdf-native-replay-{digest[:16]}"
    target_receipt: dict[str, Any] | None = None
    api_unchanged = False
    restart_unchanged = False
    archive_cleanup_allowed = False
    cleanup_archive = False
    cleanup_work = False
    try:
        _verify_host()
        _verify_archive(archive, digest)
        archive_cleanup_allowed = True
        WORK_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
        WORK_ROOT.chmod(0o700)
        work = Path(tempfile.mkdtemp(prefix="run-", dir=WORK_ROOT))
        work.chmod(0o755)
        claimed_archive = _claim_archive(archive, work, digest)
        before = _api_snapshot()
        bundle = work / "bundle"
        site = work / "site"
        _extract_bundle(claimed_archive, bundle)
        _verify_bundle(bundle)
        site.mkdir(mode=0o750)
        os.chown(site, 65532, 65532)
        _remove_container(install_container)
        _remove_container(replay_container)
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

    if target_receipt is None:
        raise ReplayFailure("target_receipt_missing")
    if not cleanup_archive or not cleanup_work:
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
