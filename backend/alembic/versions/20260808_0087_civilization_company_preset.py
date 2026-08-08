"""Add creator-isolated Civilization draft policy.

Revision ID: 20260808_0087
Revises: 20260808_0086
"""

from __future__ import annotations

from alembic import op

revision = "20260808_0087"
down_revision = "20260808_0086"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.current_actor_user_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        AS $$
          SELECT NULLIF(current_setting('app.actor_user_id', true), '')::uuid
        $$;
        REVOKE ALL ON FUNCTION app.current_actor_user_id() FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION app.current_actor_user_id() TO warehouse_os;

        DROP POLICY tenant_isolation ON civilization.thoughts;
        CREATE POLICY tenant_isolation ON civilization.thoughts
          USING (
            tenant_id = app.current_tenant_id()
            AND (
              publication_status = 'published'
              OR COALESCE((
                SELECT tenant.industry_template_key
                FROM iam.tenants AS tenant
                WHERE tenant.id = civilization.thoughts.tenant_id
              ), '') <> 'civilization'
              OR created_by = app.current_actor_user_id()
            )
          )
          WITH CHECK (
            tenant_id = app.current_tenant_id()
            AND (
              COALESCE((
                SELECT tenant.industry_template_key
                FROM iam.tenants AS tenant
                WHERE tenant.id = civilization.thoughts.tenant_id
              ), '') <> 'civilization'
              OR created_by = app.current_actor_user_id()
            )
          );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP POLICY tenant_isolation ON civilization.thoughts;
        CREATE POLICY tenant_isolation ON civilization.thoughts
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        DROP FUNCTION IF EXISTS app.current_actor_user_id();

        """
    )
