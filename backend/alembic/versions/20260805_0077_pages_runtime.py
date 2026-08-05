"""Add the stable Warehouse OS Pages Runtime control plane.

Revision ID: 20260805_0077
Revises: 20260805_0076
"""

from __future__ import annotations

from alembic import op

revision = "20260805_0077"
down_revision = "20260805_0076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        CREATE TABLE platform.pages_routes (
          id uuid PRIMARY KEY,
          site_key text NOT NULL UNIQUE
            CHECK (site_key ~ '^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$'),
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          tenant_slug text NOT NULL
            CHECK (tenant_slug ~ '^[a-z0-9][a-z0-9-]{1,62}$'),
          workspace_id uuid NOT NULL,
          workspace_key text NOT NULL
            CHECK (workspace_key ~ '^[a-z0-9][a-z0-9-]{2,62}$'),
          active_deployment_id uuid REFERENCES digital_asset.deployments(id)
            ON DELETE SET NULL,
          status text NOT NULL DEFAULT 'reserved'
            CHECK (status IN ('reserved', 'active', 'disabled')),
          public_alias_enabled boolean NOT NULL DEFAULT false,
          config jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(config) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, workspace_id),
          CONSTRAINT pages_routes_workspace_fk
            FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_pages_routes_workspace
          ON platform.pages_routes(tenant_id, workspace_id);
        CREATE INDEX idx_pages_routes_active_deployment
          ON platform.pages_routes(active_deployment_id)
          WHERE active_deployment_id IS NOT NULL;
        CREATE TRIGGER trg_pages_routes_updated
          BEFORE UPDATE ON platform.pages_routes
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        GRANT SELECT, INSERT, UPDATE, DELETE
          ON platform.pages_routes TO warehouse_os;

        DO $$
        DECLARE
          tenant_row record;
          workspace_row record;
          candidate text;
          attempt integer;
        BEGIN
          FOR tenant_row IN SELECT id,slug FROM iam.tenants ORDER BY id LOOP
            PERFORM set_config('app.tenant_id', tenant_row.id::text, true);
            FOR workspace_row IN
              SELECT w.id, w.tenant_id, w.workspace_key, w.active_deployment_id
              FROM digital_asset.workspaces AS w
              WHERE w.tenant_id=tenant_row.id
              ORDER BY w.created_at, w.id
            LOOP
              candidate := workspace_row.workspace_key;
              attempt := 0;
              WHILE candidate IN (
                'admin', 'api', 'assets', 'docs', 'mail', 'static', 'status', 'www'
              ) OR EXISTS (
                SELECT 1 FROM platform.pages_routes WHERE site_key=candidate
              ) LOOP
                attempt := attempt + 1;
                candidate := left(workspace_row.workspace_key, 53) || '-' ||
                  substr(md5(workspace_row.id::text || ':' || attempt::text), 1, 8);
              END LOOP;
              INSERT INTO platform.pages_routes(
                id, site_key, tenant_id, tenant_slug, workspace_id, workspace_key,
                active_deployment_id, status, config
              ) VALUES (
                gen_random_uuid(), candidate, workspace_row.tenant_id,
                tenant_row.slug, workspace_row.id, workspace_row.workspace_key,
                workspace_row.active_deployment_id,
                CASE WHEN workspace_row.active_deployment_id IS NULL
                  THEN 'reserved' ELSE 'active' END,
                jsonb_build_object(
                  'delivery', 'static_assets',
                  'compute', 'browser',
                  'database', 'platform_api',
                  'source', 'immutable_versions',
                  'entry_mode', 'warehouse_os'
                )
              );
            END LOOP;
          END LOOP;
        END $$;

        INSERT INTO app.resource_invariants(
          invariant_key, resource_key, description, enforcement, machine_contract
        ) VALUES (
          'platform.pages_route.stable_active_pointer',
          'digital_asset.workspace',
          'Warehouse OS /apps 站点名全平台唯一并稳定指向工作区当前已验证发布；活动代码不得原地修改',
          'domain_adapter',
          '{"site_key_global_unique":true,"warehouse_os_entry":true,"optional_public_alias":true,"isolated_browser_origin":true,"active_deployment_pointer":true,"immutable_source_versions":true,"legacy_path_fallback":true}'::jsonb
        ) ON CONFLICT (invariant_key) DO UPDATE SET
          description=EXCLUDED.description,
          enforcement=EXCLUDED.enforcement,
          machine_contract=EXCLUDED.machine_contract,
          active=true;

        COMMENT ON TABLE platform.pages_routes IS
          'Globally unique Warehouse OS /apps routing metadata and optional public aliases. Source and tenant data remain in their RLS-protected schemas.';
        COMMENT ON COLUMN platform.pages_routes.site_key IS
          'The globally unique name used by /apps/{site_key}/ and the isolated runtime origin.';
        COMMENT ON COLUMN platform.pages_routes.public_alias_enabled IS
          'Whether the isolated Pages hostname is advertised as an additional public entry URL.';
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DELETE FROM app.resource_invariants
        WHERE invariant_key='platform.pages_route.stable_active_pointer';
        DROP TABLE IF EXISTS platform.pages_routes;
        """
    )
