"""Add tenant-isolated task, schedule and plan persistence.

Revision ID: 20260727_0009
Revises: 20260727_0008
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "20260727_0009"
down_revision = "20260727_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE workflow.tasks (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          created_by uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          title text NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 240),
          description text,
          kind text NOT NULL CHECK (kind IN ('task', 'event', 'plan')),
          category text NOT NULL DEFAULT 'work',
          status text NOT NULL DEFAULT 'planned'
            CHECK (status IN ('planned', 'in_progress', 'waiting', 'completed', 'cancelled')),
          priority text NOT NULL DEFAULT 'normal'
            CHECK (priority IN ('urgent', 'high', 'normal', 'low')),
          visibility text NOT NULL DEFAULT 'private'
            CHECK (visibility IN ('private', 'team', 'company')),
          start_at timestamptz,
          end_at timestamptz,
          due_at timestamptz,
          all_day boolean NOT NULL DEFAULT false,
          timezone text NOT NULL DEFAULT 'UTC',
          location text,
          owner_org_unit_id uuid,
          plan_id uuid,
          source_type text,
          source_entity_id text,
          client_request_id text,
          version integer NOT NULL DEFAULT 1 CHECK (version > 0),
          completed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE NULLS NOT DISTINCT (tenant_id, created_by, client_request_id),
          FOREIGN KEY (tenant_id, owner_org_unit_id)
            REFERENCES iam.organizational_units(tenant_id, id) ON DELETE SET NULL,
          FOREIGN KEY (tenant_id, plan_id)
            REFERENCES workflow.tasks(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_workflow_tasks_tenant_created
          ON workflow.tasks(tenant_id, created_at DESC);
        CREATE INDEX idx_workflow_tasks_tenant_status_due
          ON workflow.tasks(tenant_id, status, due_at);

        CREATE TABLE workflow.task_assignees (
          tenant_id uuid NOT NULL,
          task_id uuid NOT NULL,
          user_id uuid NOT NULL,
          assigned_by uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          created_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, task_id, user_id),
          FOREIGN KEY (tenant_id, task_id)
            REFERENCES workflow.tasks(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE
        );
        CREATE INDEX idx_workflow_task_assignees_tenant_user
          ON workflow.task_assignees(tenant_id, user_id, task_id);

        CREATE TRIGGER trg_workflow_tasks_updated
          BEFORE UPDATE ON workflow.tasks
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        GRANT SELECT, INSERT, UPDATE, DELETE ON workflow.tasks, workflow.task_assignees
          TO warehouse_os;

        ALTER TABLE workflow.tasks ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.tasks FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.tasks
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_assignees ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_assignees FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_assignees
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workflow.task_assignees;")
    op.execute("DROP TABLE IF EXISTS workflow.tasks;")
