from pathlib import Path


def test_task_delete_cascade_keeps_ledger_append_only_outside_root_delete() -> None:
    migration = (
        Path(__file__).parents[1]
        / "alembic/versions/20260804_0072_task_delete_collaboration_cascade.py"
    ).read_text()

    assert "BEFORE DELETE ON workflow.tasks" in migration
    assert "set_config('app.task_delete_cascade', 'on', true)" in migration
    assert "TG_OP = 'DELETE'" in migration
    assert "current_setting('app.task_delete_cascade', true) = 'on'" in migration
    assert "RAISE EXCEPTION '% is append-only'" in migration
    assert "REVOKE DELETE ON workflow.task_collaboration_spaces FROM warehouse_os" in migration
