from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = REPO_ROOT / "ops" / "macos" / "warehouse-deploy-ssh-gate"
DEPLOY = REPO_ROOT / "ops" / "deploy"


@pytest.fixture
def deploy_root(tmp_path: Path) -> Path:
    root = tmp_path / "bonfirework"
    manager = root / "bin" / "warehouse-deploy"
    manager.parent.mkdir(parents=True)
    (root / "incoming").mkdir()
    manager.write_text(
        "#!/usr/bin/env bash\nprintf 'manager=%s\\n' \"$*\"\n",
        encoding="utf-8",
    )
    manager.chmod(0o755)
    return root


def _gate(deploy_root: Path, original: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "WAREHOUSE_MAC_DEPLOY_ROOT": str(deploy_root),
            "SSH_ORIGINAL_COMMAND": original,
        }
    )
    return subprocess.run(
        [str(GATE)],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("operation", ["manifest", "status", "history", "rollback"])
def test_gate_allows_fixed_manager_operations(deploy_root: Path, operation: str) -> None:
    manager = deploy_root / "bin" / "warehouse-deploy"

    completed = _gate(deploy_root, f"{manager} {operation}")

    assert completed.returncode == 0
    assert completed.stdout == f"manager={operation}\n"


def test_gate_allows_a_valid_immutable_release_install(deploy_root: Path) -> None:
    manager = deploy_root / "bin" / "warehouse-deploy"
    release = "20260804T120000Z-abcdef123456-mac-primary-smart"

    completed = _gate(deploy_root, f"{manager} install {release} smart")

    assert completed.returncode == 0
    assert completed.stdout == f"manager=install {release} smart\n"


@pytest.mark.parametrize(
    "original",
    [
        "bash -lc id",
        "/bin/zsh",
        "warehouse-deploy install ../../escape smart",
        "warehouse-deploy install 20260804T120000Z-release unsafe",
    ],
)
def test_gate_denies_shells_and_malformed_installs(
    deploy_root: Path, original: str
) -> None:
    completed = _gate(deploy_root, original)

    assert completed.returncode == 126
    assert completed.stdout == ""
    assert "command denied" in completed.stderr


@pytest.mark.parametrize(
    ("manager_sudo", "expected_command"),
    [
        ("0", "/deploy/manager manifest"),
        ("1", "sudo -n /deploy/manager manifest"),
    ],
)
def test_plan_uses_the_target_manager_privilege_contract(
    tmp_path: Path, manager_sudo: str, expected_command: str
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    ssh_log = tmp_path / "ssh.log"
    identity = tmp_path / "id_ed25519"
    identity.write_text("test-only\n", encoding="utf-8")
    readme_hash = hashlib.sha256((REPO_ROOT / "README.md").read_bytes()).hexdigest()
    fake_ssh = fake_bin / "ssh"
    fake_ssh.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" > \"${FAKE_SSH_LOG}\"\n"
        "printf '%s  ./README.md\\n' \"${FAKE_MANIFEST_HASH}\"\n",
        encoding="utf-8",
    )
    fake_ssh.chmod(0o755)
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{fake_bin}:{environment['PATH']}",
            "FAKE_MANIFEST_HASH": readme_hash,
            "FAKE_SSH_LOG": str(ssh_log),
            "WAREHOUSE_DEPLOY_HOST": "100.64.0.10",
            "WAREHOUSE_DEPLOY_USER": "deploy-test",
            "WAREHOUSE_DEPLOY_IDENTITY": str(identity),
            "WAREHOUSE_REMOTE_DEPLOY_MANAGER": "/deploy/manager",
            "WAREHOUSE_DEPLOY_MANAGER_SUDO": manager_sudo,
        }
    )

    completed = subprocess.run(
        [str(DEPLOY), "plan"],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["deploy_required"] is True
    ssh_invocation = ssh_log.read_text(encoding="utf-8").strip()
    assert ssh_invocation.endswith(expected_command)
