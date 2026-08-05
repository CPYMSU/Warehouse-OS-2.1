"""Authorize immutable collaboration-ledger cleanup only from a TASK root delete.

Revision ID: 20260804_0072
Revises: 20260804_0071
"""

from alembic import op

revision = "20260804_0072"
down_revision = "20260804_0071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION workflow.authorize_task_collaboration_cascade_delete()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          PERFORM set_config('app.task_delete_cascade', 'on', true);
          RETURN OLD;
        END;
        $$;

        CREATE TRIGGER trg_tasks_authorize_collaboration_cascade
          BEFORE DELETE ON workflow.tasks
          FOR EACH ROW
          EXECUTE FUNCTION workflow.authorize_task_collaboration_cascade_delete();

        CREATE OR REPLACE FUNCTION workflow.reject_task_document_ledger_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE'
             AND current_setting('app.task_delete_cascade', true) = 'on' THEN
            RETURN OLD;
          END IF;
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$;

        -- Collaboration spaces have no independent destructive lifecycle.  A
        -- space can only disappear through its governed TASK root so callers
        -- cannot manufacture the transaction-local cascade signal and purge an
        -- immutable document ledger directly.
        REVOKE DELETE ON workflow.task_collaboration_spaces FROM warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        GRANT DELETE ON workflow.task_collaboration_spaces TO warehouse_os;

        CREATE OR REPLACE FUNCTION workflow.reject_task_document_ledger_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$;

        DROP TRIGGER IF EXISTS trg_tasks_authorize_collaboration_cascade
          ON workflow.tasks;
        DROP FUNCTION IF EXISTS
          workflow.authorize_task_collaboration_cascade_delete();
        """
    )
