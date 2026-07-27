"""Add the governed super-terminal execution audit store.

Revision ID: 20260727_0003
Revises: 20260727_0002
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "20260727_0003"
down_revision = "20260727_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS terminal;

        CREATE TABLE terminal.command_executions (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          actor_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          command text NOT NULL CHECK (length(trim(command)) > 0),
          tool_name text NOT NULL CHECK (tool_name ~ '^[a-z][a-z0-9_]{1,127}$'),
          origin text NOT NULL CHECK (origin IN ('terminal', 'super_terminal', 'ai_tool')),
          status text NOT NULL CHECK (
            status IN ('succeeded', 'failed', 'denied', 'awaiting_domain_adapter')
          ),
          request jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(request) = 'object'),
          response jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(response) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id)
        );
        CREATE INDEX idx_terminal_command_executions_tenant_created
          ON terminal.command_executions(tenant_id, created_at DESC);
        CREATE INDEX idx_terminal_command_executions_tool_created
          ON terminal.command_executions(tenant_id, tool_name, created_at DESC);

        ALTER TABLE terminal.command_executions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE terminal.command_executions FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON terminal.command_executions
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT USAGE ON SCHEMA terminal TO warehouse_os;
        GRANT SELECT, INSERT ON terminal.command_executions TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA terminal
          GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS terminal CASCADE;")
