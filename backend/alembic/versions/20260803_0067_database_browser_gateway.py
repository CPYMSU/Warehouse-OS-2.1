"""Add standalone database browser gateway security state.

Revision ID: 20260803_0067
Revises: 20260803_0066
"""

from __future__ import annotations

from alembic import op

revision = "20260803_0067"
down_revision = "20260803_0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE digital_asset.database_browser_apps (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          project_id uuid NOT NULL UNIQUE,
          enabled boolean NOT NULL DEFAULT false,
          allowed_origins text[] NOT NULL DEFAULT ARRAY[]::text[]
            CHECK (cardinality(allowed_origins) <= 20),
          rules jsonb NOT NULL DEFAULT '{
            "default":{"read":"deny","write":"deny"},
            "collections":{}
          }'::jsonb CHECK (jsonb_typeof(rules)='object'),
          access_token_ttl_seconds integer NOT NULL DEFAULT 900
            CHECK (access_token_ttl_seconds BETWEEN 300 AND 3600),
          refresh_session_ttl_days integer NOT NULL DEFAULT 30
            CHECK (refresh_session_ttl_days BETWEEN 1 AND 90),
          rate_limit_per_minute integer NOT NULL DEFAULT 120
            CHECK (rate_limit_per_minute BETWEEN 10 AND 10000),
          revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id,id),
          UNIQUE (tenant_id,workspace_id),
          FOREIGN KEY (tenant_id,workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id,id) ON DELETE CASCADE
        );

        CREATE TABLE digital_asset.database_browser_sessions (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          browser_app_id uuid NOT NULL,
          subject_id uuid NOT NULL,
          refresh_token_hash text NOT NULL CHECK (refresh_token_hash ~ '^[a-f0-9]{64}$'),
          origin text NOT NULL CHECK (length(origin) BETWEEN 8 AND 500),
          expires_at timestamptz NOT NULL,
          last_used_at timestamptz,
          revoked_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id,id),
          UNIQUE (tenant_id,refresh_token_hash),
          FOREIGN KEY (tenant_id,browser_app_id)
            REFERENCES digital_asset.database_browser_apps(tenant_id,id) ON DELETE CASCADE
        );
        CREATE INDEX idx_database_browser_sessions_active
          ON digital_asset.database_browser_sessions(
            tenant_id,browser_app_id,subject_id,expires_at
          ) WHERE revoked_at IS NULL;

        CREATE TABLE digital_asset.database_browser_rate_limits (
          tenant_id uuid NOT NULL,
          browser_app_id uuid NOT NULL,
          bucket_start timestamptz NOT NULL,
          identity_hash text NOT NULL CHECK (identity_hash ~ '^[a-f0-9]{64}$'),
          request_count integer NOT NULL DEFAULT 1 CHECK (request_count > 0),
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id,browser_app_id,bucket_start,identity_hash),
          FOREIGN KEY (tenant_id,browser_app_id)
            REFERENCES digital_asset.database_browser_apps(tenant_id,id) ON DELETE CASCADE
        );

        CREATE TRIGGER trg_database_browser_apps_updated
          BEFORE UPDATE ON digital_asset.database_browser_apps
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        ALTER TABLE digital_asset.database_browser_apps ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.database_browser_apps FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.database_browser_apps
          USING (tenant_id=app.current_tenant_id())
          WITH CHECK (tenant_id=app.current_tenant_id());
        ALTER TABLE digital_asset.database_browser_sessions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.database_browser_sessions FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.database_browser_sessions
          USING (tenant_id=app.current_tenant_id())
          WITH CHECK (tenant_id=app.current_tenant_id());
        ALTER TABLE digital_asset.database_browser_rate_limits ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.database_browser_rate_limits FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.database_browser_rate_limits
          USING (tenant_id=app.current_tenant_id())
          WITH CHECK (tenant_id=app.current_tenant_id());

        GRANT SELECT,INSERT,UPDATE,DELETE
          ON digital_asset.database_browser_apps TO warehouse_os;
        GRANT SELECT,INSERT,UPDATE,DELETE
          ON digital_asset.database_browser_sessions TO warehouse_os;
        GRANT SELECT,INSERT,UPDATE,DELETE
          ON digital_asset.database_browser_rate_limits TO warehouse_os;

        COMMENT ON TABLE digital_asset.database_browser_apps IS
          'Per-workspace browser Data API policy; the signed dbp_ locator is public.';
        COMMENT ON TABLE digital_asset.database_browser_sessions IS
          'Revocable anonymous browser principals with rotating opaque refresh tokens.';
        COMMENT ON TABLE digital_asset.database_browser_rate_limits IS
          'Database-backed minute buckets shared by all API workers.';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS digital_asset.database_browser_rate_limits;
        DROP TABLE IF EXISTS digital_asset.database_browser_sessions;
        DROP TABLE IF EXISTS digital_asset.database_browser_apps;
        """
    )
