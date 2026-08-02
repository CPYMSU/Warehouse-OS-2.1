"""Replace cross-tenant browser session lookup with tenant-scoped verification.

Revision ID: 20260801_0036
Revises: 20260801_0035
Create Date: 2026-08-01
"""

from alembic import op

revision = "20260801_0036"
down_revision = "20260801_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS app.browser_run_session_actor(uuid, text)")


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.browser_run_session_actor(
          p_run_id uuid, p_worker_id text
        ) RETURNS TABLE(tenant_id uuid, actor_user_id uuid, tenant_slug text)
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public, app, browser_runtime, iam
        AS $$
        DECLARE tenant_record record; actor_record record;
        BEGIN
          FOR tenant_record IN SELECT id, slug FROM iam.tenants WHERE status = 'active' LOOP
            PERFORM set_config('app.tenant_id', tenant_record.id::text, true);
            actor_record := NULL;
            SELECT r.requested_by INTO actor_record
            FROM browser_runtime.runs r
            WHERE r.id = p_run_id
              AND r.claimed_by = p_worker_id
              AND r.status IN ('claimed', 'running')
              AND r.auth_mode = 'actor'
              AND r.requested_by IS NOT NULL
              AND r.heartbeat_at > now() - interval '3 minutes'
            LIMIT 1;
            IF actor_record.requested_by IS NOT NULL THEN
              tenant_id := tenant_record.id;
              actor_user_id := actor_record.requested_by;
              tenant_slug := tenant_record.slug;
              RETURN NEXT;
              RETURN;
            END IF;
          END LOOP;
          RETURN;
        END;
        $$;
        REVOKE ALL ON FUNCTION app.browser_run_session_actor(uuid, text) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION app.browser_run_session_actor(uuid, text) TO warehouse_os;
        """
    )
