from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PLANNER = REPO_ROOT / "ops" / "deploy-plan"


def test_hosting_smoke_uses_the_platform_health_contract() -> None:
    source = (REPO_ROOT / "backend/app/hosting_smoke.py").read_text(encoding="utf-8")

    assert "get_settings().public_origin}/api/health" in source
    assert "/api/biu/guide" not in source


def _plan(*paths: str) -> dict[str, object]:
    command = [str(PLANNER), "--format", "json"]
    for path in paths:
        command.extend(("--changed-file", path))
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_python_import_graph_selects_dependant_tests() -> None:
    plan = _plan("backend/app/services/auto_runtime.py")

    assert plan["mode"] == "quick"
    assert plan["risk"] == "normal"
    assert "backend/tests/test_auto_runtime.py" in plan["tests"]
    assert all(" 2." not in path for path in plan["tests"])
    assert plan["deploy_required"] is True


def test_migration_change_escalates_to_full_integration() -> None:
    plan = _plan("backend/alembic/versions/example.py")

    assert plan["mode"] == "full"
    assert plan["risk"] == "critical"
    assert {"backup", "integration", "migration"}.issubset(plan["impacts"])
    assert plan["tests"] == ["backend/tests"]


def test_runtime_controller_base_and_database_provider_restart_controller() -> None:
    plan = _plan(
        "backend/app/runtime_controller_base.py",
        "backend/app/services/hosted_database.py",
    )

    assert plan["mode"] == "standard"
    assert plan["risk"] == "high"
    assert {"api", "runtime_controller", "storage"}.issubset(plan["impacts"])
    assert "backend/tests/test_runtime_controller_docker_engine.py" in plan["tests"]


def test_research_executor_rebuild_follows_real_import_graph() -> None:
    api_only = _plan("backend/app/api/full_stack_business.py")
    shared_dependency = _plan("backend/app/core/config.py")
    executor = _plan("backend/app/research_executor.py")

    assert "research_executor" not in api_only["impacts"]
    assert "research_executor" in shared_dependency["impacts"]
    assert "research_executor" in executor["impacts"]


def test_research_dockerfile_does_not_force_api_rebuild() -> None:
    plan = _plan("backend/Dockerfile.research-executor")

    assert "research_executor" in plan["impacts"]
    assert "api" not in plan["impacts"]


def test_control_plane_change_does_not_rebuild_runtime_images() -> None:
    plan = _plan("ops/server/warehouse-shield-agent.py")

    assert "control_plane" in plan["impacts"]
    assert "api" not in plan["impacts"]
    assert "browser" not in plan["impacts"]
    assert "research_executor" not in plan["impacts"]


def test_non_runtime_change_stops_before_packaging() -> None:
    plan = _plan("docs/operations.md", "backend/tests/test_config.py")

    assert plan["mode"] == "none"
    assert plan["deploy_required"] is False
    assert set(plan["impacts"]) == {"docs_only", "tests_only"}


def test_unknown_packaged_file_fails_closed() -> None:
    plan = _plan("backend/unclassified.asset")

    assert plan["mode"] == "full"
    assert plan["risk"] == "critical"
    assert plan["unmatched_files"] == ["backend/unclassified.asset"]
    assert "integration" in plan["impacts"]


def test_active_manifest_can_be_compared_with_candidate_tree(tmp_path: Path) -> None:
    root = tmp_path / "candidate"
    (root / "ops").mkdir(parents=True)
    (root / "frontend" / "v2").mkdir(parents=True)
    (root / "backend" / ".venv" / "lib").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / "ops" / "deploy-impact.json", root / "ops")
    (root / "ops" / "deploy.exclude").write_text(
        "*.log\nbackend/.venv/\nbackend/warehouse_os_api.egg-info/\n",
        encoding="utf-8",
    )
    (root / "backend" / ".venv" / "lib" / "temporary.py").write_text(
        "generated = True\n", encoding="utf-8"
    )
    (root / "frontend" / "v2" / "app.jsx").write_text(
        "export const version = 2;\n", encoding="utf-8"
    )
    base_manifest = tmp_path / "active.sha256"
    base_manifest.write_text(
        "".join(
            (
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
                f"./{path.relative_to(root).as_posix()}\n"
            )
            for path in (
                root / "ops" / "deploy-impact.json",
                root / "ops" / "deploy.exclude",
            )
        )
        + f"{'a' * 64}  ./backend/warehouse_os_api.egg-info/PKG-INFO\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            str(PLANNER),
            "--root",
            str(root),
            "--base-manifest",
            str(base_manifest),
            "--candidate-root",
            str(root),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    plan = json.loads(completed.stdout)

    assert plan["changed_files"] == ["frontend/v2/app.jsx"]
    assert plan["mode"] == "quick"
    assert "frontend" in plan["impacts"]


def test_github_automation_is_basic_and_has_no_full_suite() -> None:
    workflows = REPO_ROOT / ".github" / "workflows"
    if not workflows.is_dir():
        pytest.skip(".github is intentionally excluded from production release archives")
    production = (workflows / "production-deploy.yml").read_text(encoding="utf-8")
    target = (workflows / "production-deploy-target.yml").read_text(encoding="utf-8")
    pull_request = (workflows / "backend-contract.yml").read_text(encoding="utf-8")
    automatic = f"{production}\n{target}\n{pull_request}"

    assert "WAREHOUSE_DEPLOY_LOCAL_VALIDATION: basic" in target
    assert "services:" not in automatic
    assert "pytest" not in automatic
    assert "docker compose" not in automatic
    assert "run-full-verification" not in f"{production}\n{target}"
    assert "hosting-smoke-matrix" not in automatic
    assert sorted(path.name for path in workflows.glob("*.yml")) == [
        "backend-contract.yml",
        "production-deploy-target.yml",
        "production-deploy.yml",
    ]


def test_github_deploys_mac_primary_before_vultr_standby() -> None:
    workflows = REPO_ROOT / ".github" / "workflows"
    if not workflows.is_dir():
        pytest.skip(".github is intentionally excluded from production release archives")
    production = (workflows / "production-deploy.yml").read_text(encoding="utf-8")
    target = (workflows / "production-deploy-target.yml").read_text(encoding="utf-8")

    assert "environment: mac-production" in production
    assert "target: mac-primary" in production
    assert "needs: [freshness, deploy-mac-primary]" in production
    assert "environment: production" in production
    assert "target: vultr-standby" in production
    assert "runs-on: [self-hosted, macOS, ARM64, warehouse-production]" in production
    assert "runs-on: ${{ fromJSON(inputs.runs_on) }}" in target
    assert "transport: local" in production
    assert "transport: ssh" in production
    assert "use_tailscale: true" not in production
    assert "tailscale/github-action" not in target
    assert "ops/deploy plan" in target
    assert "run: ops/deploy smart" in target


def test_deploy_entrypoint_has_target_neutral_transport_contract() -> None:
    source = (REPO_ROOT / "ops" / "deploy").read_text(encoding="utf-8")

    assert 'REMOTE_INCOMING="${WAREHOUSE_DEPLOY_INCOMING:' in source
    assert 'TRANSPORT="${WAREHOUSE_DEPLOY_TRANSPORT:' in source
    assert 'KNOWN_HOSTS="${WAREHOUSE_DEPLOY_KNOWN_HOSTS:' in source
    assert 'MANAGER_SUDO="${WAREHOUSE_DEPLOY_MANAGER_SUDO:' in source
    assert 'PREPARE_INCOMING="${WAREHOUSE_DEPLOY_PREPARE_INCOMING:' in source
    assert 'SCP_LEGACY="${WAREHOUSE_DEPLOY_SCP_LEGACY:' in source
    assert 'manager_remote install "${release_id}" "${INSTALL_MODE}"' in source
    assert 'if [[ "${TRANSPORT}" == local ]]' in source
    assert 'install -m 0600 "${package}" "${REMOTE_INCOMING}/$(basename "${package}")"' in source
    assert (
        'install -m 0600 "${checksum_file}" '
        '"${REMOTE_INCOMING}/$(basename "${checksum_file}")"' in source
    )
    assert '"${USER}@${HOST}:${REMOTE_INCOMING}/"' in source
    assert "${USER}@${HOST}:/var/lib/warehouse-deploy/incoming/" not in source


def test_deploy_plan_local_transport_does_not_require_ssh_identity(
    tmp_path: Path,
) -> None:
    manager = tmp_path / "warehouse-deploy"
    manager.write_text(
        "#!/bin/sh\n"
        "test \"$1\" = manifest || exit 2\n"
        "printf '%s  %s\\n' \"$(printf old | shasum -a 256 | awk '{print $1}')\" README.md\n",
        encoding="utf-8",
    )
    manager.chmod(0o700)
    environment = os.environ.copy()
    environment.update(
        {
            "WAREHOUSE_DEPLOY_TRANSPORT": "local",
            "WAREHOUSE_DEPLOY_TARGET": "local-test",
            "WAREHOUSE_REMOTE_DEPLOY_MANAGER": str(manager),
            "WAREHOUSE_DEPLOY_INCOMING": str(tmp_path / "incoming"),
            "WAREHOUSE_DEPLOY_MANAGER_SUDO": "0",
            "WAREHOUSE_DEPLOY_PREPARE_INCOMING": "0",
            "WAREHOUSE_DEPLOY_IDENTITY": str(tmp_path / "missing-identity"),
            "WAREHOUSE_DEPLOY_KNOWN_HOSTS": str(tmp_path / "missing-known-hosts"),
        }
    )

    completed = subprocess.run(
        [str(REPO_ROOT / "ops" / "deploy"), "plan"],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    plan = json.loads(completed.stdout)

    assert plan["deploy_required"] is True
    assert "README.md" in plan["changed_files"]
