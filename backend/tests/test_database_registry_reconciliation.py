from pathlib import Path

from app.main import app
from app.terminal.catalog import entry_by_tool_name


def test_database_registry_reconcile_is_a_native_auto_runtime_capability() -> None:
    paths = app.openapi()["paths"]
    assert "post" in paths["/api/database-projects/reconcile"]
    entry = entry_by_tool_name("digital_market_database_registry_reconcile")
    assert entry is not None
    assert entry["semantic_contract"] == {
        "effect": "reconcile_existing_only",
        "resource": "digital_asset.database_project_registry",
        "canonical_identity": "workspace_existing_database_binding",
        "ambiguity_policy": "observe_without_guessing",
        "identity_invariant": (
            "existing_workspace_database_identity_is_resolved_without_guessing"
        ),
        "success_evidence": "canonical_database_project_registry_binding_readback",
        "workflow_prescribed": False,
    }


def test_database_registry_migration_backfills_only_unambiguous_bindings() -> None:
    migration = (
        Path(__file__).parents[1]
        / "alembic/versions/20260805_0073_database_registry_reconciliation.py"
    ).read_text()

    assert "HAVING count(*)=1" in migration
    assert "count(*) FILTER (WHERE is_default)=0" in migration
    assert "SET is_default=true" in migration
    assert "digital_asset.database_registry_backfilled" in migration
    assert "DEFERRABLE INITIALLY DEFERRED" in migration
    assert "default_count<>1" in migration


def test_database_registry_backfill_runs_inside_every_tenant_rls_context() -> None:
    migration = (
        Path(__file__).parents[1]
        / "alembic/versions/20260805_0074_tenant_database_registry_backfill.py"
    ).read_text()

    assert "FOR tenant_row IN SELECT id FROM iam.tenants" in migration
    assert "set_config('app.tenant_id', tenant_row.id::text, true)" in migration
    assert "HAVING count(binding.id)=1" in migration
    assert "count(binding.id) FILTER (WHERE binding.is_default)=0" in migration
    assert "SET is_default=true" in migration
    assert "'rls_context','tenant_migration'" in migration
