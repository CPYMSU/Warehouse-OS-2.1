"""Execute the real cluster/controller scripts against local disposable managers."""
from __future__ import annotations

import os
import runpy
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _script(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
    path.chmod(0o700)


@pytest.fixture
def cluster(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    for command in ("git", "node", "python3", "rsync", "shasum"):
        if shutil.which(command) is None:
            pytest.skip(f"{command} is required for the isolated cluster contract")
    root = tmp_path / "warehouse"
    for directory in (
        "backend/app/api", "backend/alembic/versions", "browser-runtime", "frontend",
        "infra/backup", "scripts", "ops/cluster", "ops/macos", "ops/server", "docs",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)
    for relative in (
        "ops/deploy", "ops/deploy-plan", "ops/deploy-impact.json", "ops/deploy.exclude",
        "ops/cluster/rolling-deploy", "ops/cluster/set-vultr-reverse-subscriptions",
        "ops/macos/warehouse-deploy-macos", "ops/macos/warehouse-deploy-ssh-gate",
        "ops/server/warehouse-deploy", "ops/run-full-verification",
        "infra/backup/warehouse-postgres-backup.sh",
    ):
        shutil.copy2(REPO_ROOT / relative, root / relative)
    for relative in (".dockerignore", "compose.production.yaml", "README.md"):
        (root / relative).write_text("fixture\n", encoding="utf-8")
    (root / "scripts/build_v2_frontend.cjs").write_text("// fixture\n", encoding="utf-8")
    _script(root / "ops/alembic-head", "#!/bin/sh\nprintf '20260815_0095 (head)\\n'\n")
    # This step may be called by the original full/conservative DB path. It
    # records the gate instead of contacting a database or publication server.
    _script(root / "ops/cluster/configure-control-publication-macos", """\
        #!/bin/sh
        set -eu
        printf 'publication fixture-only\n' >> "$WAREHOUSE_TEST_ACTION_LOG"
        """)
    _script(tmp_path / "bin/node", "#!/bin/sh\nexit 0\n")
    gateway = root / "backend/app/api/hosted_runtime_gateway.py"
    gateway.write_text("VALUE = 'old'\n", encoding="utf-8")
    planner = runpy.run_path(str(root / "ops/deploy-plan"))
    tree_manifest = planner["_tree_manifest"]
    active = tmp_path / "active.sha256"
    active.write_text("".join(
        f"{digest}  ./{name}\n" for name, digest in sorted(tree_manifest(root).items())
    ), encoding="utf-8")
    # Both targets have the old, real manifest; the committed candidate API is
    # new while the controller's working tree is completely clean.
    gateway.write_text("VALUE = 'new'\n", encoding="utf-8")
    for args in (
        ["init", "-q"], ["config", "user.name", "Warehouse Fixture"],
        ["config", "user.email", "fixture@example.invalid"], ["add", "."],
        ["commit", "-qm", "Isolated candidate"],
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    candidate_sha = subprocess.check_output(
        ["git", "rev-parse", "--short=12", "HEAD"], cwd=root, text=True
    ).strip()
    manager = tmp_path / "manager"
    _script(manager, """\
        #!/usr/bin/env bash
        set -Eeuo pipefail
        target="${WAREHOUSE_DEPLOY_TARGET:?}"
        action="${1:?}"
        printf '%s %s strict=%s\n' "$target" "$*" \
          "${WAREHOUSE_REQUIRE_ACTIVE_MANIFEST:-unset}" >> "$WAREHOUSE_TEST_ACTION_LOG"
        case "$action" in
          manifest)
            if [[ "$target" == "${WAREHOUSE_TEST_MANIFEST_FAILURE_TARGET:-none}" ]]; then
              [[ "${WAREHOUSE_TEST_MANIFEST_FAILURE_KIND:-failed}" == empty ]] && exit 0
              exit 42
            fi
            cat "$WAREHOUSE_TEST_ACTIVE_MANIFEST"
            ;;
          prepare-deferred)
            [[ "${3:?}" =~ ^(smart|quick|standard|full)$ ]]
            ;;
          activate)
            printf '%s\n' "$WAREHOUSE_TEST_CANDIDATE_SHA" > "$WAREHOUSE_TEST_STATE_DIR/$target.sha"
            ;;
          prepared-status|migration-start|migration-wait|migration-status|migration-reconcile)
            ;;
          status)
            identity=000000000000
            if [[ -f "$WAREHOUSE_TEST_STATE_DIR/$target.sha" ]]; then
              identity="$(cat "$WAREHOUSE_TEST_STATE_DIR/$target.sha")"
            fi
            printf 'readiness={"node_id":"%s","git_sha":"%s","alembic_head":"20260815_0095","status":"ready","database":"ready"}\n' \
              "$target" "$identity"
            ;;
          *) exit 64 ;;
        esac
        """)
    log = tmp_path / "actions.log"
    (tmp_path / "state").mkdir()
    env = {key: value for key, value in os.environ.items() if not key.startswith("WAREHOUSE_")}
    env.update({
        "PATH": f"{tmp_path / 'bin'}:{env['PATH']}",
        "WAREHOUSE_CLUSTER_PREFLIGHT": "basic",
        "WAREHOUSE_CLUSTER_ACTIVATION_SLO_SECONDS": "10",
        "WAREHOUSE_TEST_ACTION_LOG": str(log),
        "WAREHOUSE_TEST_ACTIVE_MANIFEST": str(active),
        "WAREHOUSE_TEST_CANDIDATE_SHA": candidate_sha,
        "WAREHOUSE_TEST_STATE_DIR": str(tmp_path / "state"),
        # Test-only deterministic value, never a production credential.
        "WAREHOUSE_CONTROL_REPL_PASSWORD": "a" * 64,
    })
    for prefix in ("WAREHOUSE_PRIMARY", "WAREHOUSE_STANDBY"):
        incoming = tmp_path / f"{prefix.lower()}-incoming"
        incoming.mkdir()
        env.update({
            f"{prefix}_TRANSPORT": "local", f"{prefix}_REMOTE_MANAGER": str(manager),
            f"{prefix}_MANAGER_SUDO": "0", f"{prefix}_PREPARE_INCOMING": "0",
            f"{prefix}_INCOMING": str(incoming),
        })
    return root, env, log


def _run(cluster: tuple[Path, dict[str, str], Path], mode: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    root, env, log = cluster
    completed = subprocess.run(
        [str(root / "ops/cluster/rolling-deploy"), mode], cwd=root, env=env,
        check=False, capture_output=True, text=True, timeout=40,
    )
    return completed, log.read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("target", ["mac-primary", "vultr-standby"])
@pytest.mark.parametrize("failure_kind", ["failed", "empty"])
def test_smart_manifest_failure_never_activates_either_node(cluster, target, failure_kind):
    root, env, _ = cluster
    env["WAREHOUSE_TEST_MANIFEST_FAILURE_TARGET"] = target
    env["WAREHOUSE_TEST_MANIFEST_FAILURE_KIND"] = failure_kind
    # Even an inherited opt-out cannot turn a production smart comparison into
    # a clean-Git-worktree fallback.
    env["WAREHOUSE_REQUIRE_ACTIVE_MANIFEST"] = "0"
    completed, actions = _run(cluster, "smart")
    assert completed.returncode != 0
    assert "active release manifest is required but unavailable" in completed.stdout + completed.stderr
    assert "parallel prepare failed" in completed.stderr
    assert "git_fallback" not in completed.stdout
    assert not any(" activate " in action for action in actions)
    assert not any(" migration-" in action for action in actions)
    manifests = [action for action in actions if " manifest " in action]
    assert len(manifests) == 2
    assert all(action.endswith("strict=1") for action in manifests)
    assert subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=root, text=True) == ""


def test_smart_real_manifest_changes_prepare_and_activate_both_nodes(cluster):
    completed, actions = _run(cluster, "smart")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.count("plan: source=active_release") == 2
    assert "prepare decisions primary_deploy=1 standby_deploy=1" in completed.stdout
    assert "database phase skipped (code-only release)" in completed.stdout
    assert "cluster deployment complete" in completed.stdout
    for target in ("mac-primary", "vultr-standby"):
        assert sum(action.startswith(target + " activate ") for action in actions) == 1
        assert any(action.startswith(target + " prepare-deferred ") and action.endswith("smart strict=1") for action in actions)
    assert not any(" migration-" in action for action in actions)


def test_full_manifest_bootstrap_retains_existing_conservative_lane(cluster):
    _, env, _ = cluster
    env["WAREHOUSE_TEST_MANIFEST_FAILURE_TARGET"] = "vultr-standby"
    completed, actions = _run(cluster, "full")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "impact: active manifest unavailable; database gate retained" in completed.stdout + completed.stderr
    assert "background database gate" in completed.stdout
    assert "cluster deployment complete" in completed.stdout
    assert all(action.endswith("strict=0") for action in actions if " manifest " in action)
    assert any(action.startswith("vultr-standby prepare-deferred ") and action.endswith("full strict=0") for action in actions)
    for target in ("mac-primary", "vultr-standby"):
        assert sum(action.startswith(target + " activate ") for action in actions) == 1
    last_migration = max(index for index, action in enumerate(actions) if " migration-" in action)
    first_activation = min(index for index, action in enumerate(actions) if " activate " in action)
    assert last_migration < first_activation


def test_macos_code_only_migration_actions_are_safe_noops(tmp_path: Path):
    source = (REPO_ROOT / "ops/macos/warehouse-deploy-macos").read_text(encoding="utf-8")
    definitions = []
    for function, following in (
        ("start_prepared_migration", "show_prepared_migration"),
        ("show_prepared_migration", "wait_prepared_migration"),
        ("wait_prepared_migration", "require_arm64_image"),
    ):
        start = source.index(function + "() {")
        end = source.index("\n" + following + "() {", start)
        definitions.append(source[start:end])
    script = tmp_path / "no-migration.sh"
    _script(script, """\
        #!/usr/bin/env bash
        set -Eeuo pipefail
        load_prepared_migration() { PREPARED_PLAN_MIGRATION=0; PREPARED_ALEMBIC_HEAD=20260815_0095; }
        start_database_migration() { printf 'forbidden-migration-start\n' >&2; exit 91; }
        wait_database_migration() { printf 'forbidden-migration-wait\n' >&2; exit 92; }
        """ + "\n".join(definitions) + "\n" + """\
        start_prepared_migration fixture
        wait_prepared_migration fixture
        show_prepared_migration fixture
        """)
    completed = subprocess.run([str(script)], check=True, capture_output=True, text=True)
    assert completed.stdout.count("database_migration=not_required") == 3
    assert "target=20260815_0095" in completed.stdout
    assert "forbidden" not in completed.stderr
