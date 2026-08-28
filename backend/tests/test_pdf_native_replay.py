from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTION = REPO_ROOT / "ops" / "server" / "warehouse-pdf-native-replay.py"
MANAGER = REPO_ROOT / "ops" / "server" / "warehouse-deploy"


def _load_action():
    specification = importlib.util.spec_from_file_location("warehouse_pdf_native_replay", ACTION)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def _write_bundle(module, path: Path) -> dict[str, str]:
    product_contract = {
        "schema": module.REPLAY_CONTRACT_SCHEMA,
        "version": module.REPLAY_CONTRACT_VERSION,
    }
    compatibility_contract = {
        "schema": module.COMPATIBILITY_CONTRACT_SCHEMA,
        "version": module.COMPATIBILITY_CONTRACT_VERSION,
    }
    bundle_contract = {
        "schema": module.BUNDLE_CONTRACT_SCHEMA,
        "version": module.BUNDLE_CONTRACT_VERSION,
        "status": "bundle_preparation_only_execution_confirmation_pending",
        "authorization": {
            "confirmed_scope": "prepare_immutable_bundle_only",
            "warehouse_native_x86_replay_allowed": False,
            "warehouse_platform_activation_allowed": False,
            "controlled_pdf_read_allowed": False,
        },
        "bundle": {
            "payload_file_count": 49,
            "archive_entry_count": 50,
            "execution_authorized": False,
        },
        "target_handoff": {
            "current_warehouse_platform_accepts_this_bundle": False,
            "new_bounded_platform_candidate_required_before_native_execution": True,
            "prior_16_fixture_native_receipt_reusable": False,
        },
    }
    encoded_contracts = {
        "contract.json": json.dumps(product_contract, sort_keys=True).encode(),
        "compatibility-contract.json": json.dumps(compatibility_contract, sort_keys=True).encode(),
        "bundle-contract.json": json.dumps(bundle_contract, sort_keys=True).encode(),
    }
    payloads: dict[str, bytes] = {}
    for name in sorted(module.EXPECTED_ARCHIVE_FILES - {"bundle-manifest.json"}):
        payloads[name] = encoded_contracts.get(name, f"synthetic:{name}\n".encode())
    entries = [
        {
            "file": name,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        for name, data in sorted(payloads.items())
    ]
    identities = {
        "payload_root_sha256": module._canonical_sha256(entries),
        "replay_contract_sha256": hashlib.sha256(payloads["contract.json"]).hexdigest(),
        "compatibility_contract_sha256": hashlib.sha256(
            payloads["compatibility-contract.json"]
        ).hexdigest(),
        "bundle_contract_sha256": hashlib.sha256(payloads["bundle-contract.json"]).hexdigest(),
    }
    manifest = {
        "schema": module.BUNDLE_MANIFEST_SCHEMA,
        "version": module.BUNDLE_MANIFEST_VERSION,
        "preparation_only": True,
        "execution_authorized": False,
        "warehouse_native_x86_execution_authorized": False,
        "warehouse_platform_activation_authorized": False,
        "current_warehouse_platform_compatible": False,
        "controlled_corpus_used": False,
        "runtime_parser_registered": False,
        "ocr_invoked": False,
        "fully_synthetic_only": True,
        "business_data": False,
        "payload_file_count": len(payloads),
        "archive_entry_count": len(module.EXPECTED_ARCHIVE_FILES),
        "payload_root_sha256": identities["payload_root_sha256"],
        "product_contract_sha256": identities["replay_contract_sha256"],
        "compatibility_contract_sha256": identities["compatibility_contract_sha256"],
        "bundle_contract_sha256": identities["bundle_contract_sha256"],
        "fixture_matrix": {
            "fixture_count": 32,
            "existing_fixture_count": 16,
            "new_fixture_count": 16,
            "success_count": 15,
            "rejection_count": 17,
            "worker_execution_count": 64,
            "repeat_count_per_fixture": 2,
            "fixture_manifest_sha256s": module.EXPECTED_FIXTURE_MANIFEST_SHA256S,
            "expected_map_sha256": module.EXPECTED_MAP_SHA256,
            "semantic_output_map_sha256": module.EXPECTED_SEMANTIC_MAP_SHA256,
            "rejection_map_sha256": module.EXPECTED_REJECTION_MAP_SHA256,
        },
        "targets": {
            "linux-arm64": "native-isolated-pending-separate-confirmation",
            "linux-x86_64": ("hardware-emulated-diagnostic-pending-separate-confirmation"),
            "warehouse-linux-x86_64": ("native-pending-new-platform-and-separate-confirmation"),
        },
        "files": entries,
    }
    payloads["bundle-manifest.json"] = json.dumps(manifest, sort_keys=True).encode()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payloads.items()):
            member = zipfile.ZipInfo(name)
            member.external_attr = stat.S_IFREG << 16 | 0o444 << 16
            member.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(member, data)
    return identities


def _target_receipt(module) -> dict[str, object]:
    successes = {
        f"synthetic/success-{index:02d}.pdf": hashlib.sha256(
            f"success:{index}".encode()
        ).hexdigest()
        for index in range(15)
    }
    rejections = {
        f"synthetic/rejection-{index:02d}.pdf": {
            "reason": "pdf_poc_subset_unsupported",
            "details": {"stage": "synthetic_test"},
        }
        for index in range(17)
    }
    receipt: dict[str, object] = {
        "schema": module.TARGET_SCHEMA,
        "contract_version": module.REPLAY_CONTRACT_VERSION,
        "compatibility_contract_version": module.COMPATIBILITY_CONTRACT_VERSION,
        "compatibility_contract_sha256": module.COMPATIBILITY_CONTRACT_SHA256,
        "target": "linux-x86_64",
        "platform_system": "Linux",
        "platform_machine": "x86_64",
        "execution_mode": "native",
        "native_production_host_validation_deferred": False,
        "dependency": {
            "wheel_file": module.X86_WHEEL,
            "wheel_bytes": 3_730_077,
            "wheel_sha256": ("81df25c1ab4c13ff773102d3cbea1967511d079123b067fc077bd0c4d57d91d8"),
            "offline_file_install": True,
            "license_file_count": 19,
            "pypdfium2_version": "5.13.0",
            "pdfium_version": "153.0.7999.0",
            "pdfium_flags": [],
            "native_elf_machine": 62,
        },
        "font_fallback": {
            "file": "NotoSansSC-Regular.otf",
            "bytes": 8_331_336,
            "sha256": ("faa6c9df652116dde789d351359f3d7e5d2285a2b2a1f04a2d7244df706d5ea9"),
            "license_file": "OFL-1.1.txt",
            "license_bytes": 4_301,
            "license_sha256": ("6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2"),
            "read_only_mount": True,
            "network_resolution_used": False,
            "semantic_authority": False,
            "proves_embedded_font_truth": False,
        },
        "isolation": {
            "network_egress_denied": True,
            "root_filesystem_write_denied": True,
            "dedicated_tmpfs_noexec": True,
            "capabilities_dropped": True,
            "cap_eff_hex": "0000000000000000",
            "no_new_privileges": True,
            "seccomp_active": True,
            "seccomp_mode": 2,
            "seccomp_filters": 1,
            "non_root_user": True,
            "pids_limit": 64,
            "process_limit_bounded": True,
            "memory_limit_bytes": 536870912,
            "memory_limit_bounded": True,
            "external_business_mounts_absent": True,
            "environment_allowlisted": True,
            "product_isolation_proven_for_target": True,
        },
        "fixture_matrix": {
            "fixture_count": 32,
            "existing_fixture_count": 16,
            "new_fixture_count": 16,
            "success_count": 15,
            "rejection_count": 17,
            "worker_execution_count": 64,
            "repeat_count_per_fixture": 2,
            "fixture_manifest_sha256s": module.EXPECTED_FIXTURE_MANIFEST_SHA256S,
            "expected_map_sha256": module.EXPECTED_MAP_SHA256,
            "success_outputs": successes,
            "rejections": rejections,
            "semantic_output_map_sha256": module._canonical_sha256(successes),
            "rejection_map_sha256": module._canonical_sha256(rejections),
        },
        "controlled_corpus_used": False,
        "runtime_parser_registered": False,
        "product_isolation_proven_for_target": True,
    }
    receipt["receipt_sha256"] = module._canonical_sha256(receipt)
    return receipt


def _allow_test_bundle(module, monkeypatch, identities: dict[str, str]) -> None:
    monkeypatch.setattr(module, "EXPECTED_PAYLOAD_ROOT_SHA256", identities["payload_root_sha256"])
    monkeypatch.setattr(module, "REPLAY_CONTRACT_SHA256", identities["replay_contract_sha256"])
    monkeypatch.setattr(
        module,
        "COMPATIBILITY_CONTRACT_SHA256",
        identities["compatibility_contract_sha256"],
    )
    monkeypatch.setattr(module, "BUNDLE_CONTRACT_SHA256", identities["bundle_contract_sha256"])


def _allow_test_receipt(module, monkeypatch, receipt: dict[str, object]) -> None:
    matrix = receipt["fixture_matrix"]
    assert isinstance(matrix, dict)
    monkeypatch.setattr(
        module, "EXPECTED_SEMANTIC_MAP_SHA256", matrix["semantic_output_map_sha256"]
    )
    monkeypatch.setattr(module, "EXPECTED_REJECTION_MAP_SHA256", matrix["rejection_map_sha256"])


def test_manager_exposes_only_the_exact_bounded_command() -> None:
    source = MANAGER.read_text(encoding="utf-8")
    assert '[[ "$#" -eq 3 ]]' in source
    assert "warehouse-deploy pdf-native-replay ARCHIVE SHA256" in source
    assert "^pdf-native-replay-[a-f0-9]{16}\\.zip$" in source
    assert '[[ "${role}" == standby ]]' in source
    assert 'WAREHOUSE_PDF_NATIVE_EFFECTIVE_NODE_ROLE="${role}"' in source
    assert '"${action}" "${archive}" "${digest}"' in source
    assert "warehouse-pdf-native-replay.py" in source


def test_host_requires_native_x86_and_normalized_manager_role(monkeypatch) -> None:
    module = _load_action()
    assert not hasattr(module, "PRODUCTION_ENV")

    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.platform, "machine", lambda: "x86_64")
    monkeypatch.delenv(module.MANAGER_ROLE_ENV, raising=False)
    with pytest.raises(module.ReplayFailure) as captured:
        module._verify_host()
    assert captured.value.code == "native_x86_standby_required"

    monkeypatch.setenv(module.MANAGER_ROLE_ENV, "primary")
    with pytest.raises(module.ReplayFailure) as captured:
        module._verify_host()
    assert captured.value.code == "native_x86_standby_required"

    monkeypatch.setenv(module.MANAGER_ROLE_ENV, "standby")
    module._verify_host()

    monkeypatch.setattr(module.platform, "machine", lambda: "aarch64")
    with pytest.raises(module.ReplayFailure) as captured:
        module._verify_host()
    assert captured.value.code == "native_x86_standby_required"


def test_archive_identity_is_exactly_allowlisted(tmp_path: Path, monkeypatch) -> None:
    module = _load_action()
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    content = b"expanded-synthetic-bundle"
    digest = hashlib.sha256(content).hexdigest()
    archive = incoming / f"pdf-native-replay-{digest[:16]}.zip"
    archive.write_bytes(content)
    monkeypatch.setattr(module, "INCOMING_ROOT", incoming)
    monkeypatch.setattr(module, "EXPECTED_ARCHIVE_BYTES", len(content))
    monkeypatch.setattr(module, "EXPECTED_ARCHIVE_SHA256", digest)

    module._verify_archive(archive, digest)

    monkeypatch.setattr(module, "EXPECTED_ARCHIVE_SHA256", "0" * 64)
    with pytest.raises(module.ReplayFailure) as captured:
        module._verify_archive(archive, digest)
    assert captured.value.code == "archive_identity_not_allowlisted"


def test_bundle_validation_is_exact_and_fails_closed(tmp_path: Path, monkeypatch) -> None:
    module = _load_action()
    archive = tmp_path / "bundle.zip"
    bundle = tmp_path / "bundle"
    identities = _write_bundle(module, archive)
    _allow_test_bundle(module, monkeypatch, identities)
    module._extract_bundle(archive, bundle)
    module._verify_bundle(bundle)

    entrypoint = bundle / module.ENTRYPOINT
    entrypoint.chmod(0o644)
    entrypoint.write_text("changed", encoding="utf-8")
    with pytest.raises(module.ReplayFailure) as captured:
        module._verify_bundle(bundle)
    assert captured.value.code == "bundle_manifest_mismatch"


def test_compatibility_contract_version_is_independently_bound(tmp_path: Path, monkeypatch) -> None:
    module = _load_action()
    archive = tmp_path / "bundle.zip"
    bundle = tmp_path / "bundle"
    identities = _write_bundle(module, archive)
    _allow_test_bundle(module, monkeypatch, identities)
    module._extract_bundle(archive, bundle)

    compatibility_path = bundle / "compatibility-contract.json"
    compatibility_path.chmod(0o644)
    compatibility = json.loads(compatibility_path.read_text(encoding="utf-8"))
    compatibility["version"] = "unexpected"
    compatibility_bytes = json.dumps(compatibility, sort_keys=True).encode()
    compatibility_path.write_bytes(compatibility_bytes)
    compatibility_sha256 = hashlib.sha256(compatibility_bytes).hexdigest()

    manifest_path = bundle / "bundle-manifest.json"
    manifest_path.chmod(0o644)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest["files"]:
        if item["file"] == "compatibility-contract.json":
            item["bytes"] = len(compatibility_bytes)
            item["sha256"] = compatibility_sha256
            break
    manifest["compatibility_contract_sha256"] = compatibility_sha256
    payload_root_sha256 = module._canonical_sha256(manifest["files"])
    manifest["payload_root_sha256"] = payload_root_sha256
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(module, "COMPATIBILITY_CONTRACT_SHA256", compatibility_sha256)
    monkeypatch.setattr(module, "EXPECTED_PAYLOAD_ROOT_SHA256", payload_root_sha256)

    with pytest.raises(module.ReplayFailure) as captured:
        module._verify_bundle(bundle)
    assert captured.value.code == "compatibility_contract_invalid"


def test_target_receipt_requires_native_isolation_and_canonical_hash(monkeypatch) -> None:
    module = _load_action()
    receipt = _target_receipt(module)
    _allow_test_receipt(module, monkeypatch, receipt)
    module._verify_target_receipt(receipt)

    receipt["execution_mode"] = "hardware_emulated"
    receipt["receipt_sha256"] = module._canonical_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )
    with pytest.raises(module.ReplayFailure) as captured:
        module._verify_target_receipt(receipt)
    assert captured.value.code == "target_receipt_invalid"

    receipt["execution_mode"] = "native"
    isolation = receipt["isolation"]
    assert isinstance(isolation, dict)
    isolation["seccomp_filters"] = True
    receipt["receipt_sha256"] = module._canonical_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )
    with pytest.raises(module.ReplayFailure) as captured:
        module._verify_target_receipt(receipt)
    assert captured.value.code == "target_receipt_invalid"


def test_replay_container_has_no_network_production_mounts_or_inherited_environment(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_action()
    bundle = tmp_path / "bundle"
    site = tmp_path / "site"
    (bundle / "fonts").mkdir(parents=True)
    site.mkdir()
    calls: list[list[str]] = []
    target_receipt = _target_receipt(module)
    _allow_test_receipt(module, monkeypatch, target_receipt)

    def fake_docker(arguments, **_kwargs):
        calls.append(arguments)
        return json.dumps(target_receipt, sort_keys=True).encode()

    monkeypatch.setattr(module, "_run_docker", fake_docker)
    image_id = f"sha256:{'b' * 64}"
    module._install_dependency(
        bundle=bundle,
        site=site,
        image_id=image_id,
        container_name="warehouse-pdf-native-install-test",
    )
    module._run_replay(
        bundle=bundle,
        site=site,
        image_id=image_id,
        container_name="warehouse-pdf-native-replay-test",
    )

    assert len(calls) == 2
    for arguments in calls:
        assert arguments[arguments.index("--network") + 1] == "none"
        assert "--read-only" in arguments
        assert arguments[arguments.index("--cap-drop") + 1] == "ALL"
        assert "no-new-privileges:true" in arguments
        assert arguments[arguments.index("--pids-limit") + 1] == "64"
        assert arguments[arguments.index("--memory") + 1] == "512m"
        assert arguments[arguments.index("--user") + 1] == "65532:65532"
        assert "--env-file" not in arguments
        assert not any("/var/run/docker.sock" in item or "/data" in item for item in arguments)

    replay = calls[1]
    compatibility_index = replay.index("--compatibility-contract")
    assert replay[compatibility_index + 1] == "/bundle/compatibility-contract.json"
    environment_start = replay.index("-i") + 1
    python_start = replay.index("/usr/local/bin/python", environment_start)
    assert set(replay[environment_start:python_start]) == {
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
    }


def test_execute_cleans_archive_and_work_before_emitting_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_action()
    incoming = tmp_path / "incoming"
    work_root = tmp_path / "work"
    incoming.mkdir()
    digest_placeholder = "0" * 64
    initial = incoming / f"pdf-native-replay-{digest_placeholder[:16]}.zip"
    identities = _write_bundle(module, initial)
    _allow_test_bundle(module, monkeypatch, identities)
    digest = hashlib.sha256(initial.read_bytes()).hexdigest()
    archive = incoming / f"pdf-native-replay-{digest[:16]}.zip"
    initial.rename(archive)

    monkeypatch.setattr(module, "INCOMING_ROOT", incoming)
    monkeypatch.setattr(module, "WORK_ROOT", work_root)
    monkeypatch.setattr(module, "_verify_host", lambda: None)
    monkeypatch.setattr(module, "_verify_archive", lambda *_args: None)
    snapshot = module.ApiSnapshot(
        slot="blue",
        container="warehouse-os-api-blue",
        container_id="a" * 64,
        restart_count=0,
        image_id=f"sha256:{'b' * 64}",
    )
    monkeypatch.setattr(module, "_api_snapshot", lambda: snapshot)
    monkeypatch.setattr(module, "_remove_container", lambda _name: None)
    monkeypatch.setattr(module, "_install_dependency", lambda **_kwargs: None)
    monkeypatch.setattr(module, "_run_replay", lambda **_kwargs: _target_receipt(module))
    monkeypatch.setattr(module.os, "chown", lambda *_args: None)

    receipt = module.execute(archive, digest)

    assert not archive.exists()
    assert not any(work_root.iterdir())
    assert receipt["schema"] == module.HOST_SCHEMA
    assert receipt["production_secrets_injected"] is False
    assert receipt["production_database_attached"] is False
    assert receipt["production_object_storage_attached"] is False
    assert receipt["production_boundary"] == {
        "api_identity_unchanged": True,
        "api_restart_count_unchanged": True,
    }
    assert receipt["cleanup"] == {
        "archive_removed": True,
        "work_directory_removed": True,
    }
    observed = receipt.pop("receipt_sha256")
    assert observed == module._canonical_sha256(receipt)


def test_failure_still_removes_verified_archive_and_work(tmp_path: Path, monkeypatch) -> None:
    module = _load_action()
    incoming = tmp_path / "incoming"
    work_root = tmp_path / "work"
    incoming.mkdir()
    temporary = incoming / "pdf-native-replay-0000000000000000.zip"
    identities = _write_bundle(module, temporary)
    _allow_test_bundle(module, monkeypatch, identities)
    digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
    archive = incoming / f"pdf-native-replay-{digest[:16]}.zip"
    temporary.rename(archive)

    monkeypatch.setattr(module, "INCOMING_ROOT", incoming)
    monkeypatch.setattr(module, "WORK_ROOT", work_root)
    monkeypatch.setattr(module, "_verify_host", lambda: None)
    monkeypatch.setattr(module, "_verify_archive", lambda *_args: None)
    monkeypatch.setattr(
        module,
        "_api_snapshot",
        lambda: module.ApiSnapshot(
            "blue",
            "warehouse-os-api-blue",
            "a" * 64,
            0,
            f"sha256:{'b' * 64}",
        ),
    )
    monkeypatch.setattr(module, "_remove_container", lambda _name: None)
    monkeypatch.setattr(
        module,
        "_install_dependency",
        lambda **_kwargs: (_ for _ in ()).throw(module.ReplayFailure("install_failed")),
    )
    monkeypatch.setattr(module.os, "chown", lambda *_args: None)

    with pytest.raises(module.ReplayFailure) as captured:
        module.execute(archive, digest)
    assert captured.value.code == "install_failed"
    assert not archive.exists()
    assert not any(work_root.iterdir())
