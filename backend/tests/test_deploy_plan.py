from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

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
    assert plan["deploy_required"] is True


def test_migration_change_escalates_to_full_integration() -> None:
    plan = _plan("backend/alembic/versions/example.py")

    assert plan["mode"] == "full"
    assert plan["risk"] == "critical"
    assert {"backup", "integration", "migration"}.issubset(plan["impacts"])
    assert plan["tests"] == ["backend/tests"]


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
    shutil.copy2(REPO_ROOT / "ops" / "deploy-impact.json", root / "ops")
    (root / "ops" / "deploy.exclude").write_text(
        "*.log\nbackend/warehouse_os_api.egg-info/\n",
        encoding="utf-8",
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
    production = (workflows / "production-deploy.yml").read_text(encoding="utf-8")
    pull_request = (workflows / "backend-contract.yml").read_text(encoding="utf-8")
    automatic = f"{production}\n{pull_request}"

    assert "WAREHOUSE_DEPLOY_LOCAL_VALIDATION: basic" in production
    assert "services:" not in automatic
    assert "pytest" not in automatic
    assert "docker compose" not in automatic
    assert "run-full-verification" not in production
    assert "hosting-smoke-matrix" not in automatic
    assert sorted(path.name for path in workflows.glob("*.yml")) == [
        "backend-contract.yml",
        "production-deploy.yml",
    ]
