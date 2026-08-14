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


def test_python_service_change_selects_complete_backend_tests() -> None:
    plan = _plan("backend/app/services/auto_runtime.py")

    assert plan["mode"] == "quick"
    assert plan["risk"] == "normal"
    assert plan["tests"] == ["backend/tests"]
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
    pull_request = (workflows / "backend-contract.yml").read_text(encoding="utf-8")
    automatic = f"{production}\n{pull_request}"

    assert "WAREHOUSE_CLUSTER_PREFLIGHT: basic" in production
    assert "services:" not in automatic
    assert "pytest" not in automatic
    assert "docker compose" not in automatic
    assert "run-full-verification" not in production
    assert "hosting-smoke-matrix" not in automatic
    assert sorted(path.name for path in workflows.glob("*.yml")) == [
        "backend-contract.yml",
        "production-deploy.yml",
    ]


def test_github_uses_one_coordinated_dual_node_route() -> None:
    workflows = REPO_ROOT / ".github" / "workflows"
    if not workflows.is_dir():
        pytest.skip(".github is intentionally excluded from production release archives")
    production = (workflows / "production-deploy.yml").read_text(encoding="utf-8")

    assert "runs-on: [self-hosted, macOS, ARM64, warehouse-production]" in production
    assert "workflow_dispatch:" in production
    assert "WAREHOUSE_PRIMARY_TRANSPORT: local" in production
    assert "WAREHOUSE_STANDBY_TRANSPORT: ssh" in production
    assert 'ops/cluster/rolling-deploy "${DEPLOY_MODE}"' in production
    assert "run-full-verification" not in production
    assert "tailscale/github-action" not in production
    assert "primary-recovery" in production
    assert "ACTIVATE_PRIMARY_ONLY" in production
    assert '"${manager}" prepared-status "${PREPARED_RELEASE}"' in production
    assert '"${manager}" activate "${PREPARED_RELEASE}"' in production
    assert "database-migration-state" not in production

    fast_deploy = (REPO_ROOT / "ops" / "fast-deploy").read_text(encoding="utf-8")
    assert 'WORKFLOW="production-deploy.yml"' in fast_deploy
    assert "gh workflow run" in fast_deploy
    assert "gh run watch" in fast_deploy
    assert 'if [[ -x "${primary_manager}" ]]' in fast_deploy
    assert 'primary_transport="ssh"' in fast_deploy
    assert 'WAREHOUSE_PRIMARY_TRANSPORT="${WAREHOUSE_PRIMARY_TRANSPORT:-${primary_transport}}"' in fast_deploy


def test_deploy_entrypoint_has_target_neutral_transport_contract() -> None:
    source = (REPO_ROOT / "ops" / "deploy").read_text(encoding="utf-8")

    assert 'REMOTE_INCOMING="${WAREHOUSE_DEPLOY_INCOMING:' in source
    assert 'TRANSPORT="${WAREHOUSE_DEPLOY_TRANSPORT:' in source
    assert 'KNOWN_HOSTS="${WAREHOUSE_DEPLOY_KNOWN_HOSTS:' in source
    assert "-F /dev/null" in source
    assert 'MANAGER_SUDO="${WAREHOUSE_DEPLOY_MANAGER_SUDO:' in source
    assert 'PREPARE_INCOMING="${WAREHOUSE_DEPLOY_PREPARE_INCOMING:' in source
    assert 'SCP_LEGACY="${WAREHOUSE_DEPLOY_SCP_LEGACY:' in source
    assert 'manager_action=prepare-deferred' in source
    assert 'manager_remote "${manager_action}" "${release_id}" "${INSTALL_MODE}"' in source
    assert 'if [[ "${TRANSPORT}" == local ]]' in source
    assert 'install -m 0600 "${package}" "${REMOTE_INCOMING}/$(basename "${package}")"' in source
    assert (
        'install -m 0600 "${checksum_file}" '
        '"${REMOTE_INCOMING}/$(basename "${checksum_file}")"' in source
    )
    assert '"${USER}@${HOST}:${REMOTE_INCOMING}/"' in source
    assert "${USER}@${HOST}:/var/lib/warehouse-deploy/incoming/" not in source


def test_cluster_deploy_prepares_and_activates_both_nodes_in_parallel() -> None:
    source = (REPO_ROOT / "ops" / "cluster" / "rolling-deploy").read_text(
        encoding="utf-8"
    )

    assert "parallel prepare: mac-primary + vultr-standby" in source
    assert 'run_node WAREHOUSE_PRIMARY mac-primary "prepare ${MODE}"' in source
    assert 'run_node WAREHOUSE_STANDBY vultr-standby "prepare ${MODE}"' in source
    assert 'run_node WAREHOUSE_PRIMARY mac-primary "activate ${primary_release}"' in source
    assert 'run_node WAREHOUSE_STANDBY vultr-standby "activate ${standby_release}"' in source
    assert "activation_duration <= ACTIVATION_SLO_SECONDS" in source
    assert 'if [[ "${transport}" == ssh ]]; then' in source
    assert 'identity is missing for ${label}: ${identity}' in source


def test_dependency_free_alembic_head_matches_the_declared_graph() -> None:
    completed = subprocess.run(
        [str(REPO_ROOT / "ops" / "alembic-head"), "heads"],
        cwd=REPO_ROOT / "backend",
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "20260814_0093 (head)"

    policy = json.loads(
        (REPO_ROOT / "backend" / "alembic" / "migration-policy.json").read_text(
            encoding="utf-8"
        )
    )
    assert policy["legacy_head"] == "20260805_0078"


def test_full_verification_can_use_an_ephemeral_environment() -> None:
    source = (REPO_ROOT / "ops" / "run-full-verification").read_text(
        encoding="utf-8"
    )

    assert 'VENV="${WAREHOUSE_TEST_VENV:-${ROOT}/backend/.venv}"' in source
    assert "export PYTHONDONTWRITEBYTECODE=1" in source
    assert '"${VENV}/bin/alembic" upgrade head' in source
    assert '"${VENV}/bin/pytest" -q' in source


def test_macos_manager_versions_the_forced_command_gate() -> None:
    source = (REPO_ROOT / "ops" / "macos" / "warehouse-deploy-macos").read_text(
        encoding="utf-8"
    )

    assert 'gate_source="${CURRENT}/ops/macos/warehouse-deploy-ssh-gate"' in source
    assert '"${DEPLOY_ROOT}/actions/warehouse-deploy-ssh-gate"' in source


def test_macos_manager_rejects_mutable_runtime_code_overrides() -> None:
    source = (REPO_ROOT / "ops" / "macos" / "warehouse-deploy-macos").read_text(
        encoding="utf-8"
    )

    assert "reject_runtime_code_overrides()" in source
    assert '("/service/app", "/service/alembic", "/frontend/v2")' in source
    assert "mutable runtime code override is forbidden" in source
    assert source.count("reject_runtime_code_overrides\n") == 3


def test_standby_deploy_skips_database_writing_workers() -> None:
    source = (REPO_ROOT / "ops" / "server" / "warehouse-deploy").read_text(
        encoding="utf-8"
    )

    assert 'node_role="$(configured_node_role)"' in source
    assert 'if [[ "${node_role}" == primary ]]; then\n    install_browser_runtime_config' in source
    assert 'log_event deploy_phase skipped "${release}" browser_worker' in source
    assert 'if [[ "${node_role}" == standby ]]; then\n    log_event deploy_phase skipped' in source
    assert '"${release}" runtime_controller "${next_slot}" 0' in source
    assert 'standby_smoke "${PREPARED_NEXT_PORT}"' in source
    assert 'public_smoke || smoke_result=$?' in source
    assert 'startup_command=\'exec uvicorn' in source


def test_standby_reseed_uses_the_prepared_candidate_action() -> None:
    source = (REPO_ROOT / "ops" / "server" / "warehouse-deploy").read_text(
        encoding="utf-8"
    )

    assert 'reseed_action="${RELEASES}/${release}/ops/server/warehouse-standby-reseed"' in source
    assert 'reseed_action="${CURRENT}/ops/server/warehouse-standby-reseed"' not in source
    assert "WAREHOUSE_NODE_ROLE=standby" in source
    assert "prepare-deferred)" in source

    reseed = (REPO_ROOT / "ops" / "server" / "warehouse-standby-reseed").read_text(
        encoding="utf-8"
    )
    assert "publisher_command()" in reseed
    assert "publisher_environment=(-e PGUSER -e PGPASSWORD -e PGDATABASE)" in reseed
    assert 'PGDATABASE="${conninfo}"' not in reseed
    assert 'publisher_command pg_dump --schema-only --no-owner' in reseed
    assert "--no-publications --no-subscriptions" in reseed
    assert '--exclude-extension=${extension}' in reseed
    assert 'CREATE DATABASE ${DATABASE} OWNER warehouse_migrator' in reseed
    assert "CREATE EXTENSION IF NOT EXISTS" in reseed
    assert "SET ROLE warehouse_migrator" in reseed
    assert 'WAREHOUSE_STANDBY_RESEED_MAX_WAIT_SECONDS:-3600' in reseed
    assert 'WAREHOUSE_STANDBY_RESEED_SYNC_WORKERS:-3' in reseed
    assert "max_sync_workers_per_subscription" in reseed
    assert "max_logical_replication_workers" in reseed
    assert "standby_reseed_parallelism=" in reseed
    assert 'last_progress_second="${elapsed}"' in reseed
    assert "initial copy made no table progress" in reseed


def test_database_migrations_are_detached_from_web_startup_and_deploy_process() -> None:
    compose = (REPO_ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    macos = (REPO_ROOT / "ops" / "macos" / "warehouse-deploy-macos").read_text(
        encoding="utf-8"
    )
    server = (REPO_ROOT / "ops" / "server" / "warehouse-deploy").read_text(
        encoding="utf-8"
    )
    deploy = (REPO_ROOT / "ops" / "deploy").read_text(encoding="utf-8")

    assert "alembic upgrade head && exec uvicorn" not in compose
    assert "alembic upgrade head && exec uvicorn" not in server
    assert "run_control_migrations" not in macos
    assert "backup_control_database" not in macos
    assert "python -m app.database_migration_controller" in macos
    publication = (
        REPO_ROOT / "ops" / "cluster" / "configure-control-publication-macos"
    ).read_text(encoding="utf-8")
    assert "warehouse_control_backup" in publication
    assert "NOLOGIN INHERIT NOREPLICATION BYPASSRLS" in publication
    assert "GRANT pg_read_all_data TO warehouse_control_backup" in publication
    assert "GRANT warehouse_control_backup TO warehouse_migrator" in publication
    assert "python -m app.database_migration_controller" in server
    assert "WAREHOUSE_MIGRATION_DATABASE_URL: \"\"" in compose
    assert "WAREHOUSE_MIGRATOR_DB_PASSWORD: \"\"" in compose
    assert "migration-start|migration-status|migration-wait" in deploy
    assert 'WAREHOUSE_DEPLOY_PLAN_FILE' in deploy
    assert 'migration_required=%s' in deploy
    assert 'PLAN_MIGRATION=1' in deploy
    assert 'PLAN_SOURCE="explicit_conservative"' in deploy
    assert 'impact: source=%s risk=%s migration=%s files=%s' in deploy
    assert 'INSTALL_MODE="smart"' in deploy


def test_code_only_release_does_not_inspect_or_reconcile_databases() -> None:
    macos = (REPO_ROOT / "ops" / "macos" / "warehouse-deploy-macos").read_text(
        encoding="utf-8"
    )
    server = (REPO_ROOT / "ops" / "server" / "warehouse-deploy").read_text(
        encoding="utf-8"
    )
    cluster = (REPO_ROOT / "ops" / "cluster" / "rolling-deploy").read_text(
        encoding="utf-8"
    )

    primary_validation = macos[
        macos.index("validate_primary_api()") : macos.index("acquire_lock()")
    ]
    candidate_validation = server[
        server.index("validate_candidate()") : server.index("switch_upstream()")
    ]
    assert "alembic current" not in primary_validation
    assert "alembic current" not in candidate_validation
    assert 'hosted_database=unchanged action=skipped reason=code_only' in server
    assert 'if [[ "${migration_required}" == 1 ]]; then' in cluster
    assert '"${primary_migration}" == 1 || "${standby_migration}" == 1' in cluster
    assert "node migration impact plans disagree" not in cluster
    assert 'database phase skipped (code-only release)' in cluster


def test_cluster_database_gate_runs_standby_schema_before_primary_data() -> None:
    source = (REPO_ROOT / "ops" / "cluster" / "rolling-deploy").read_text(
        encoding="utf-8"
    )

    prepare = source.index("parallel prepare: mac-primary + vultr-standby")
    database_gate = source.index("background database gate: standby schema, then primary data")
    activation = source.index("coordinated activation")
    assert prepare < database_gate < activation
    assert "WAREHOUSE_DATABASE_MIGRATION_DEFER" in source
    standby_start = source.index(
        'run_node WAREHOUSE_STANDBY vultr-standby '
        '"migration-start ${standby_release}"'
    )
    publication_bootstrap = source.index(
        '"${ROOT}/ops/cluster/configure-control-publication-macos"', database_gate
    )
    secret_handoff = source.index(
        "upload_node_secret WAREHOUSE_STANDBY vultr-standby", database_gate
    )
    primary_start = source.index(
        'run_node WAREHOUSE_PRIMARY mac-primary '
        '"migration-start ${primary_release}"'
    )
    assert (
        database_gate
        < publication_bootstrap
        < secret_handoff
        < standby_start
        < primary_start
        < activation
    )
    assert 'run_node WAREHOUSE_PRIMARY mac-primary "migration-start ${primary_release}"' in source
    assert 'run_node WAREHOUSE_PRIMARY mac-primary "migration-wait ${primary_release}"' in source
    assert (
        'run_node WAREHOUSE_STANDBY vultr-standby '
        '"migration-reconcile ${standby_release}"' in source
    )
    assert "database_replication_gate" in (
        REPO_ROOT / "ops" / "server" / "warehouse-deploy"
    ).read_text(encoding="utf-8")


def test_mac_release_installs_the_visible_fast_route_and_optimizer() -> None:
    source = (REPO_ROOT / "ops" / "macos" / "warehouse-deploy-macos").read_text(
        encoding="utf-8"
    )

    assert "install_operator_routes()" in source
    assert 'bin/warehouse-fast-deploy' in source
    assert "org.bonfirework.clash-route-optimizer.plist" in source
    assert "deployment_route=GitHub_to_Mac_runner_to_coordinated_Mac_Vultr" in source


def test_standby_validation_never_writes_a_passkey_challenge() -> None:
    source = (REPO_ROOT / "ops" / "server" / "warehouse-deploy").read_text(
        encoding="utf-8"
    )

    assert 'if [[ "${node_role}" != standby \\' in source
    assert '"${base}/api/auth/passkeys/login/options"' in source


def test_standby_reseed_is_bounded_to_the_disposable_control_subscriber() -> None:
    source = (REPO_ROOT / "ops" / "server" / "warehouse-standby-reseed").read_text(
        encoding="utf-8"
    )
    manager = (REPO_ROOT / "ops" / "server" / "warehouse-deploy").read_text(
        encoding="utf-8"
    )

    assert 'WAREHOUSE_CONFIRM_STANDBY_RESEED:-}" == YES' in source
    assert 'WAREHOUSE_NODE_ROLE:-}" == standby' in source
    assert "standby application role is not fenced read-only" in source
    assert "standby migrator role is not fenced read-only" in source
    assert 'DATABASE=warehouse_os' in source
    assert 'CONTROL_CONTAINER=warehouse-os-postgres-1' in source
    assert "warehouse-os-hosted-postgres" not in source
    assert "standby-before-reseed.dump" in source
    assert (
        'pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" '
        "--format custom" in source
    )
    assert "copy_data=true" in source
    assert 'prepare-control' in source
    assert 'control-replication-${RELEASE_ID}.env' in source
    assert "warehouse-deploy:600" in source
    assert "rm -f -- \"${SECRET_FILE}\"" in source
    assert "critical table counts differ after reseed" in source
    assert "reseed_standby_control_database" in manager
    assert "standby-reseed-attempted" in manager


def test_control_replication_bootstrap_is_control_only_and_secret_backed() -> None:
    subscriptions = (
        REPO_ROOT / "ops" / "cluster" / "set-vultr-reverse-subscriptions"
    ).read_text(encoding="utf-8")
    publication = (
        REPO_ROOT / "ops" / "cluster" / "configure-control-publication-macos"
    ).read_text(encoding="utf-8")
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "production-deploy.yml"
    ).read_text(encoding="utf-8")
    manager = (REPO_ROOT / "ops" / "server" / "warehouse-deploy").read_text(
        encoding="utf-8"
    )

    control_mode = subscriptions[
        subscriptions.index("prepare-control)") : subscriptions.index(
            "prepare)\n", subscriptions.index("prepare-control)")
        )
    ]
    assert "prepare_control 1" in control_mode
    assert "prepare_hosted" not in control_mode
    assert "WAREHOUSE_HOSTED_REPL_PASSWORD" not in publication
    assert "WAREHOUSE_HOSTED_DB_ADMIN_PASSWORD" not in publication
    assert "warehouse_control_pub" in publication
    assert "secrets.WAREHOUSE_CONTROL_REPL_PASSWORD" in workflow
    assert "timeout-minutes: 70" in workflow
    assert "ALTER SUBSCRIPTION warehouse_from_mac ENABLE" in manager


def test_server_deploy_has_a_persistent_prepare_activate_contract() -> None:
    source = (REPO_ROOT / "ops" / "server" / "warehouse-deploy").read_text(
        encoding="utf-8"
    )

    assert "prepare_release()" in source
    assert "prepared_status()" in source
    assert "activate_release()" in source
    assert 'status=prepared\\n' in source
    assert 'prepared-${release}.env' in source
    assert 'switch_upstream "${PREPARED_NEXT_PORT}"' in source


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
