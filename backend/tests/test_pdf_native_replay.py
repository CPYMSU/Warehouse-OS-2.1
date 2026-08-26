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


def _write_bundle(module, path: Path) -> None:
    payloads: dict[str, bytes] = {}
    for name in sorted(module.EXPECTED_ARCHIVE_FILES - {"bundle-manifest.json"}):
        if name == "contract.json":
            payloads[name] = json.dumps(
                {
                    "schema": module.REPLAY_CONTRACT_SCHEMA,
                    "version": module.REPLAY_CONTRACT_VERSION,
                },
                sort_keys=True,
            ).encode()
        else:
            payloads[name] = f"synthetic:{name}\n".encode()
    manifest = {
        "schema": "tidi.pdf-product-replay-bundle.v1",
        "fully_synthetic_only": True,
        "business_data": False,
        "file_count": len(payloads),
        "files": [
            {
                "file": name,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for name, data in sorted(payloads.items())
        ],
    }
    payloads["bundle-manifest.json"] = json.dumps(manifest, sort_keys=True).encode()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payloads.items()):
            member = zipfile.ZipInfo(name)
            member.external_attr = stat.S_IFREG << 16 | 0o444 << 16
            member.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(member, data)


def _target_receipt(module) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema": module.TARGET_SCHEMA,
        "contract_version": module.REPLAY_CONTRACT_VERSION,
        "target": "linux-x86_64",
        "platform_system": "Linux",
        "platform_machine": "x86_64",
        "execution_mode": "native",
        "native_production_host_validation_deferred": False,
        "dependency": {
            "pypdfium2_version": "5.13.0",
            "pdfium_version": "153.0.7999.0",
            "native_elf_machine": 62,
        },
        "font_fallback": {"read_only_mount": True},
        "isolation": {
            "network_egress_denied": True,
            "root_filesystem_write_denied": True,
            "dedicated_tmpfs_noexec": True,
            "capabilities_dropped": True,
            "no_new_privileges": True,
            "seccomp_mode": 2,
            "non_root_user": True,
            "pids_limit": 64,
            "memory_limit_bytes": 536870912,
            "external_business_mounts_absent": True,
        },
        "fixture_matrix": {
            "fixture_count": 16,
            "success_count": 9,
            "rejection_count": 7,
            "repeat_count_per_fixture": 2,
            "semantic_output_map_sha256": (
                "7297c59cd5ccbb90b837b553287da149b5fa689b94a3f8565110eb4b76a28c68"
            ),
            "rejection_map_sha256": (
                "5ff6e6c5392f5967223df1ec73afe7c0e7a65a854dc4931a5d7ea26e99f96f88"
            ),
        },
        "controlled_corpus_used": False,
        "runtime_parser_registered": False,
        "product_isolation_proven_for_target": True,
    }
    receipt["receipt_sha256"] = module._canonical_sha256(receipt)
    return receipt


def test_manager_exposes_only_the_exact_bounded_command() -> None:
    source = MANAGER.read_text(encoding="utf-8")
    assert '[[ "$#" -eq 3 ]]' in source
    assert "warehouse-deploy pdf-native-replay ARCHIVE SHA256" in source
    assert "^pdf-native-replay-[a-f0-9]{16}\\.zip$" in source
    assert '[[ "${role}" == standby ]]' in source
    assert '"${action}" "${archive}" "${digest}"' in source
    assert "warehouse-pdf-native-replay.py" in source


def test_bundle_validation_is_exact_and_fails_closed(tmp_path: Path, monkeypatch) -> None:
    module = _load_action()
    archive = tmp_path / "bundle.zip"
    bundle = tmp_path / "bundle"
    _write_bundle(module, archive)
    module._extract_bundle(archive, bundle)
    module._verify_bundle(bundle)

    entrypoint = bundle / module.ENTRYPOINT
    entrypoint.chmod(0o644)
    entrypoint.write_text("changed", encoding="utf-8")
    with pytest.raises(module.ReplayFailure) as captured:
        module._verify_bundle(bundle)
    assert captured.value.code == "bundle_manifest_mismatch"


def test_target_receipt_requires_native_isolation_and_canonical_hash() -> None:
    module = _load_action()
    receipt = _target_receipt(module)
    module._verify_target_receipt(receipt)

    receipt["execution_mode"] = "hardware_emulated"
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

    def fake_docker(arguments, **_kwargs):
        calls.append(arguments)
        return json.dumps(_target_receipt(module), sort_keys=True).encode()

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
    _write_bundle(module, initial)
    digest = hashlib.sha256(initial.read_bytes()).hexdigest()
    archive = incoming / f"pdf-native-replay-{digest[:16]}.zip"
    initial.rename(archive)

    monkeypatch.setattr(module, "INCOMING_ROOT", incoming)
    monkeypatch.setattr(module, "WORK_ROOT", work_root)
    monkeypatch.setattr(module, "_verify_host", lambda: None)
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
    _write_bundle(module, temporary)
    digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
    archive = incoming / f"pdf-native-replay-{digest[:16]}.zip"
    temporary.rename(archive)

    monkeypatch.setattr(module, "INCOMING_ROOT", incoming)
    monkeypatch.setattr(module, "WORK_ROOT", work_root)
    monkeypatch.setattr(module, "_verify_host", lambda: None)
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
