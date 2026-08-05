"""Add the tenant-isolated digital asset hosting control and data planes.

Revision ID: 20260728_0017
Revises: 20260728_0016
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op

revision = "20260728_0017"
down_revision = "20260728_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS digital_asset;

        CREATE TABLE digital_asset.assets (
          id uuid PRIMARY KEY,
          legacy_id bigint GENERATED ALWAYS AS IDENTITY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          asset_no text NOT NULL,
          asset_kind text NOT NULL DEFAULT 'software'
            CHECK (asset_kind IN (
              'data', 'process', 'knowledge', 'software', 'model',
              'agent', 'project', 'other'
            )),
          name text NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 200),
          summary text,
          source_module text,
          source_ref_type text,
          source_ref_id text,
          owner_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          owner_name text,
          status text NOT NULL DEFAULT 'registered'
            CHECK (status IN (
              'draft', 'registered', 'custodied', 'active', 'listed', 'archived'
            )),
          lifecycle_stage text NOT NULL DEFAULT 'discover'
            CHECK (lifecycle_stage IN (
              'discover', 'standardize', 'custody', 'provisioned',
              'deployed', 'valuation', 'listing', 'trading', 'retired'
            )),
          risk_level text NOT NULL DEFAULT 'medium'
            CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
          tags jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(tags) = 'array'),
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(metadata) = 'object'),
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (legacy_id),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, asset_no)
        );
        CREATE INDEX idx_digital_asset_assets_tenant_updated
          ON digital_asset.assets(tenant_id, updated_at DESC);
        CREATE INDEX idx_digital_asset_assets_kind_status
          ON digital_asset.assets(tenant_id, asset_kind, status);

        CREATE TABLE digital_asset.asset_versions (
          id uuid PRIMARY KEY,
          legacy_id bigint GENERATED ALWAYS AS IDENTITY,
          tenant_id uuid NOT NULL,
          asset_id uuid NOT NULL,
          version_no text NOT NULL CHECK (length(trim(version_no)) BETWEEN 1 AND 80),
          title text,
          artifact_uri text,
          artifact_sha256 text
            CHECK (
              artifact_sha256 IS NULL
              OR artifact_sha256 ~ '^[a-f0-9]{64}$'
            ),
          dependencies jsonb NOT NULL DEFAULT '[]'::jsonb,
          change_log text,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (legacy_id),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, asset_id, version_no),
          FOREIGN KEY (tenant_id, asset_id)
            REFERENCES digital_asset.assets(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_digital_asset_versions_asset
          ON digital_asset.asset_versions(tenant_id, asset_id, created_at DESC);

        CREATE TABLE digital_asset.artifacts (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          asset_id uuid NOT NULL,
          version_id uuid,
          artifact_kind text NOT NULL DEFAULT 'package'
            CHECK (artifact_kind IN (
              'package', 'source', 'frontend', 'backend', 'dataset',
              'model', 'agent', 'document', 'other'
            )),
          filename text,
          content_type text,
          size_bytes bigint NOT NULL DEFAULT 0 CHECK (size_bytes >= 0),
          sha256 text NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
          storage_provider text NOT NULL DEFAULT 'external',
          object_key text NOT NULL,
          state text NOT NULL DEFAULT 'verified'
            CHECK (state IN ('pending', 'stored', 'verified', 'quarantined', 'released')),
          verification jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, asset_id, sha256, object_key),
          FOREIGN KEY (tenant_id, asset_id)
            REFERENCES digital_asset.assets(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, version_id)
            REFERENCES digital_asset.asset_versions(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_digital_asset_artifacts_asset
          ON digital_asset.artifacts(tenant_id, asset_id, created_at DESC);

        CREATE TABLE digital_asset.custody_events (
          id uuid PRIMARY KEY,
          sequence bigint GENERATED ALWAYS AS IDENTITY,
          tenant_id uuid NOT NULL,
          asset_id uuid NOT NULL,
          version_id uuid,
          artifact_id uuid,
          event_type text NOT NULL
            CHECK (event_type IN (
              'registered', 'deposit', 'update', 'verify',
              'quarantine', 'release', 'migration'
            )),
          artifact_sha256 text
            CHECK (
              artifact_sha256 IS NULL
              OR artifact_sha256 ~ '^[a-f0-9]{64}$'
            ),
          details jsonb NOT NULL DEFAULT '{}'::jsonb,
          previous_event_hash text,
          event_hash text NOT NULL CHECK (event_hash ~ '^[a-f0-9]{64}$'),
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (sequence),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, asset_id, event_hash),
          FOREIGN KEY (tenant_id, asset_id)
            REFERENCES digital_asset.assets(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, version_id)
            REFERENCES digital_asset.asset_versions(tenant_id, id) ON DELETE SET NULL,
          FOREIGN KEY (tenant_id, artifact_id)
            REFERENCES digital_asset.artifacts(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_digital_asset_custody_asset
          ON digital_asset.custody_events(tenant_id, asset_id, sequence DESC);

        CREATE TABLE digital_asset.workspaces (
          id uuid PRIMARY KEY,
          legacy_id bigint GENERATED ALWAYS AS IDENTITY,
          tenant_id uuid NOT NULL,
          asset_id uuid NOT NULL,
          workspace_key text NOT NULL
            CHECK (workspace_key ~ '^[a-z0-9][a-z0-9-]{2,62}$'),
          service_plan text NOT NULL DEFAULT 'hosted'
            CHECK (service_plan IN ('custody', 'hosted', 'managed', 'dedicated')),
          status text NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'suspended', 'archived')),
          runtime_status text NOT NULL DEFAULT 'provisioned'
            CHECK (runtime_status IN (
              'planned', 'provisioned', 'building', 'deploying',
              'ready', 'failed', 'suspended'
            )),
          region text NOT NULL DEFAULT 'local',
          public_url text,
          storage_quota_bytes bigint NOT NULL DEFAULT 104857600
            CHECK (storage_quota_bytes > 0),
          config jsonb NOT NULL DEFAULT '{}'::jsonb,
          revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (legacy_id),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, workspace_key),
          FOREIGN KEY (tenant_id, asset_id)
            REFERENCES digital_asset.assets(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_digital_asset_workspaces_asset
          ON digital_asset.workspaces(tenant_id, asset_id, updated_at DESC);

        CREATE TABLE digital_asset.workspace_components (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          component_name text NOT NULL
            CHECK (component_name ~ '^[a-z][a-z0-9-]{0,62}$'),
          component_kind text NOT NULL
            CHECK (component_kind IN ('frontend', 'backend', 'worker', 'agent')),
          runtime text NOT NULL DEFAULT 'static',
          entrypoint text,
          build_command text,
          start_command text,
          source_version_id uuid,
          config jsonb NOT NULL DEFAULT '{}'::jsonb,
          status text NOT NULL DEFAULT 'configured'
            CHECK (status IN (
              'configured', 'building', 'ready', 'failed', 'suspended'
            )),
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, workspace_id, component_name),
          FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, source_version_id)
            REFERENCES digital_asset.asset_versions(tenant_id, id) ON DELETE SET NULL
        );

        CREATE TABLE digital_asset.storage_bindings (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          provider_key text NOT NULL DEFAULT 'content_addressed_local',
          bucket_ref text,
          object_prefix text NOT NULL,
          encryption_key_ref text,
          status text NOT NULL DEFAULT 'ready'
            CHECK (status IN ('provisioning', 'ready', 'failed', 'suspended')),
          config jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, workspace_id),
          FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id) ON DELETE CASCADE
        );

        CREATE TABLE digital_asset.database_bindings (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          logical_name text NOT NULL
            CHECK (logical_name ~ '^[a-z][a-z0-9_]{1,62}$'),
          engine text NOT NULL DEFAULT 'postgresql',
          provider_key text NOT NULL DEFAULT 'warehouse_postgresql_data_api',
          isolation_mode text NOT NULL DEFAULT 'workspace_rls'
            CHECK (isolation_mode IN (
              'workspace_rls', 'dedicated_schema', 'dedicated_database',
              'dedicated_cluster'
            )),
          status text NOT NULL DEFAULT 'ready'
            CHECK (status IN ('provisioning', 'ready', 'failed', 'suspended')),
          endpoint_ref text NOT NULL,
          config jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, workspace_id, logical_name),
          FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id) ON DELETE CASCADE
        );

        CREATE TABLE digital_asset.workspace_records (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          database_binding_id uuid NOT NULL,
          collection_name text NOT NULL
            CHECK (collection_name ~ '^[a-z][a-z0-9_.-]{0,119}$'),
          record_key text NOT NULL CHECK (length(trim(record_key)) BETWEEN 1 AND 240),
          payload jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(payload) = 'object'),
          version integer NOT NULL DEFAULT 1 CHECK (version > 0),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (
            tenant_id, workspace_id, database_binding_id,
            collection_name, record_key
          ),
          FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, database_binding_id)
            REFERENCES digital_asset.database_bindings(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_digital_asset_workspace_records_collection
          ON digital_asset.workspace_records(
            tenant_id, workspace_id, collection_name, updated_at DESC
          );
        CREATE INDEX idx_digital_asset_workspace_records_payload
          ON digital_asset.workspace_records USING gin(payload jsonb_path_ops);

        CREATE TABLE digital_asset.api_credentials (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          label text NOT NULL CHECK (length(trim(label)) BETWEEN 1 AND 120),
          token_hash text NOT NULL CHECK (token_hash ~ '^[a-f0-9]{64}$'),
          token_hint text NOT NULL,
          scopes text[] NOT NULL DEFAULT ARRAY['data:read']::text[],
          issued_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          issued_at timestamptz NOT NULL DEFAULT now(),
          expires_at timestamptz,
          last_used_at timestamptz,
          revoked_at timestamptz,
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, token_hash),
          FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_digital_asset_credentials_workspace
          ON digital_asset.api_credentials(tenant_id, workspace_id, revoked_at);

        CREATE TABLE digital_asset.deployments (
          id uuid PRIMARY KEY,
          legacy_id bigint GENERATED ALWAYS AS IDENTITY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          component_id uuid,
          source_version_id uuid,
          revision integer NOT NULL CHECK (revision > 0),
          provider_key text NOT NULL DEFAULT 'runtime_queue',
          release_digest text,
          status text NOT NULL DEFAULT 'queued'
            CHECK (status IN (
              'queued', 'building', 'deploying', 'ready',
              'failed', 'rolled_back', 'cancelled'
            )),
          health text NOT NULL DEFAULT 'pending'
            CHECK (health IN ('pending', 'healthy', 'unhealthy', 'unknown')),
          public_url text,
          requested_config jsonb NOT NULL DEFAULT '{}'::jsonb,
          result jsonb NOT NULL DEFAULT '{}'::jsonb,
          requested_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (legacy_id),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, workspace_id, component_id, revision),
          FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, component_id)
            REFERENCES digital_asset.workspace_components(tenant_id, id) ON DELETE SET NULL,
          FOREIGN KEY (tenant_id, source_version_id)
            REFERENCES digital_asset.asset_versions(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_digital_asset_deployments_workspace
          ON digital_asset.deployments(tenant_id, workspace_id, created_at DESC);

        CREATE TABLE digital_asset.deployment_events (
          deployment_id uuid NOT NULL,
          tenant_id uuid NOT NULL,
          sequence integer NOT NULL CHECK (sequence > 0),
          event_type text NOT NULL,
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (deployment_id, sequence),
          FOREIGN KEY (tenant_id, deployment_id)
            REFERENCES digital_asset.deployments(tenant_id, id) ON DELETE CASCADE
        );

        CREATE TRIGGER trg_digital_asset_assets_updated
          BEFORE UPDATE ON digital_asset.assets
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_digital_asset_workspaces_updated
          BEFORE UPDATE ON digital_asset.workspaces
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_digital_asset_components_updated
          BEFORE UPDATE ON digital_asset.workspace_components
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_digital_asset_storage_updated
          BEFORE UPDATE ON digital_asset.storage_bindings
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_digital_asset_databases_updated
          BEFORE UPDATE ON digital_asset.database_bindings
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_digital_asset_records_updated
          BEFORE UPDATE ON digital_asset.workspace_records
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_digital_asset_deployments_updated
          BEFORE UPDATE ON digital_asset.deployments
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE OR REPLACE FUNCTION digital_asset.reject_immutable_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$;
        CREATE TRIGGER trg_digital_asset_custody_immutable
          BEFORE UPDATE OR DELETE ON digital_asset.custody_events
          FOR EACH ROW EXECUTE FUNCTION digital_asset.reject_immutable_mutation();
        CREATE TRIGGER trg_digital_asset_deployment_events_immutable
          BEFORE UPDATE OR DELETE ON digital_asset.deployment_events
          FOR EACH ROW EXECUTE FUNCTION digital_asset.reject_immutable_mutation();

        GRANT USAGE ON SCHEMA digital_asset TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE, DELETE
          ON ALL TABLES IN SCHEMA digital_asset TO warehouse_os;
        GRANT USAGE, SELECT
          ON ALL SEQUENCES IN SCHEMA digital_asset TO warehouse_os;
        REVOKE UPDATE, DELETE
          ON digital_asset.custody_events, digital_asset.deployment_events
          FROM warehouse_os;

        DO $$
        DECLARE scoped_table text;
        BEGIN
          FOREACH scoped_table IN ARRAY ARRAY[
            'digital_asset.assets',
            'digital_asset.asset_versions',
            'digital_asset.artifacts',
            'digital_asset.custody_events',
            'digital_asset.workspaces',
            'digital_asset.workspace_components',
            'digital_asset.storage_bindings',
            'digital_asset.database_bindings',
            'digital_asset.workspace_records',
            'digital_asset.api_credentials',
            'digital_asset.deployments',
            'digital_asset.deployment_events'
          ]
          LOOP
            EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', scoped_table);
            EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', scoped_table);
            EXECUTE format(
              'CREATE POLICY tenant_isolation ON %s '
              'USING (tenant_id = app.current_tenant_id()) '
              'WITH CHECK (tenant_id = app.current_tenant_id())',
              scoped_table
            );
          END LOOP;
        END $$;

        COMMENT ON SCHEMA digital_asset IS
          'Digital asset custody, full-stack workspace control plane, and '
          'tenant/workspace-isolated Data API.';
        COMMENT ON TABLE digital_asset.workspace_records IS
          'Portable Firebase-style JSON data plane. A dedicated PostgreSQL '
          'provider can replace this binding without changing the public API.';
        COMMENT ON TABLE digital_asset.custody_events IS
          'Append-only, hash-chained digital asset custody evidence.';
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS digital_asset CASCADE")
