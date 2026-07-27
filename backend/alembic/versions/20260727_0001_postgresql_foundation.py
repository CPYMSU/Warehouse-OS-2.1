"""Create the PostgreSQL-first Warehouse OS 2.1 foundation.

Revision ID: 20260727_0001
Revises:
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "20260727_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS app;
        CREATE SCHEMA IF NOT EXISTS iam;
        CREATE SCHEMA IF NOT EXISTS warehouse;
        CREATE SCHEMA IF NOT EXISTS workflow;
        CREATE SCHEMA IF NOT EXISTS secretariat;
        CREATE SCHEMA IF NOT EXISTS audit;
        CREATE SCHEMA IF NOT EXISTS outbox;

        CREATE OR REPLACE FUNCTION app.current_tenant_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        AS $$
          SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid
        $$;

        CREATE OR REPLACE FUNCTION app.touch_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          NEW.updated_at = now();
          RETURN NEW;
        END;
        $$;

        CREATE TABLE iam.tenants (
          id uuid PRIMARY KEY,
          slug text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9][a-z0-9-]{1,62}$'),
          name text NOT NULL CHECK (length(trim(name)) > 0),
          status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'archived')),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE iam.users (
          id uuid PRIMARY KEY,
          username text NOT NULL UNIQUE CHECK (length(trim(username)) > 0),
          display_name text NOT NULL CHECK (length(trim(display_name)) > 0),
          password_hash text NOT NULL,
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE iam.memberships (
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          active boolean NOT NULL DEFAULT true,
          role_level smallint NOT NULL DEFAULT 1 CHECK (role_level BETWEEN 1 AND 10),
          topology_level smallint NOT NULL DEFAULT 1 CHECK (topology_level BETWEEN 1 AND 10),
          topology_title text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, user_id)
        );
        CREATE INDEX idx_iam_memberships_user ON iam.memberships(user_id, active);

        CREATE TABLE iam.roles (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          role_key text NOT NULL,
          name text NOT NULL,
          level smallint NOT NULL CHECK (level BETWEEN 1 AND 10),
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, role_key),
          UNIQUE (tenant_id, id)
        );

        CREATE TABLE iam.role_permissions (
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          role_id uuid NOT NULL,
          permission_key text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, role_id, permission_key),
          FOREIGN KEY (tenant_id, role_id) REFERENCES iam.roles(tenant_id, id) ON DELETE CASCADE
        );

        CREATE TABLE iam.membership_roles (
          tenant_id uuid NOT NULL,
          user_id uuid NOT NULL,
          role_id uuid NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, user_id, role_id),
          FOREIGN KEY (tenant_id, user_id) REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, role_id) REFERENCES iam.roles(tenant_id, id) ON DELETE CASCADE
        );

        CREATE TABLE warehouse.warehouses (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          code text NOT NULL,
          name text NOT NULL,
          warehouse_type text NOT NULL DEFAULT 'general',
          address text,
          lat numeric(9, 6),
          lng numeric(9, 6),
          storage_condition text,
          capacity_usage numeric(5, 2),
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, code),
          UNIQUE (tenant_id, id)
        );

        CREATE TABLE warehouse.warehouse_zones (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          warehouse_id uuid NOT NULL,
          zone_code text NOT NULL,
          zone_name text NOT NULL,
          zone_type text,
          floor_no text,
          geojson jsonb,
          capacity_usage numeric(5, 2),
          rack_count integer NOT NULL DEFAULT 0 CHECK (rack_count >= 0),
          item_count integer NOT NULL DEFAULT 0 CHECK (item_count >= 0),
          alert_count integer NOT NULL DEFAULT 0 CHECK (alert_count >= 0),
          color text,
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, warehouse_id, zone_code),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, warehouse_id) REFERENCES warehouse.warehouses(tenant_id, id) ON DELETE CASCADE
        );

        CREATE TABLE warehouse.warehouse_locations (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          warehouse_id uuid NOT NULL,
          zone_id uuid,
          location_code text NOT NULL,
          rack_code text,
          floor_no text,
          x_pos numeric(12, 4),
          y_pos numeric(12, 4),
          z_pos numeric(12, 4),
          geojson jsonb,
          capacity_usage numeric(5, 2),
          capacity_limit numeric(14, 3),
          alert_status text NOT NULL DEFAULT 'normal',
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, warehouse_id, location_code),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, warehouse_id) REFERENCES warehouse.warehouses(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, zone_id) REFERENCES warehouse.warehouse_zones(tenant_id, id) ON DELETE SET NULL
        );

        CREATE TABLE warehouse.map_zones (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          warehouse_id uuid,
          zone_id uuid,
          name text NOT NULL,
          kind text NOT NULL CHECK (kind IN ('area', 'line')),
          floor_no text,
          geojson jsonb NOT NULL,
          color text,
          note text,
          active boolean NOT NULL DEFAULT true,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, warehouse_id) REFERENCES warehouse.warehouses(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, zone_id) REFERENCES warehouse.warehouse_zones(tenant_id, id) ON DELETE CASCADE
        );

        CREATE TABLE workflow.definitions (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          workflow_key text NOT NULL,
          name text NOT NULL,
          version integer NOT NULL DEFAULT 1 CHECK (version > 0),
          definition jsonb NOT NULL,
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, workflow_key, version),
          UNIQUE (tenant_id, id)
        );

        CREATE TABLE workflow.instances (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          definition_id uuid NOT NULL,
          status text NOT NULL DEFAULT 'active',
          subject_type text NOT NULL,
          subject_id uuid NOT NULL,
          state jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, definition_id) REFERENCES workflow.definitions(tenant_id, id) ON DELETE RESTRICT
        );

        CREATE TABLE secretariat.conversations (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          owner_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          channel text NOT NULL DEFAULT 'agent',
          title text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id)
        );

        CREATE TABLE secretariat.runs (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          conversation_id uuid,
          actor_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          task text NOT NULL,
          status text NOT NULL CHECK (status IN ('created', 'running', 'waiting', 'succeeded', 'failed', 'cancelled')),
          context_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, conversation_id) REFERENCES secretariat.conversations(tenant_id, id) ON DELETE SET NULL
        );

        CREATE TABLE secretariat.operations (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          run_id uuid,
          actor_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          capability text NOT NULL,
          status text NOT NULL CHECK (status IN ('created', 'running', 'succeeded', 'failed', 'cancelled')),
          idempotency_key text NOT NULL,
          envelope jsonb NOT NULL,
          result jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, idempotency_key),
          FOREIGN KEY (tenant_id, run_id) REFERENCES secretariat.runs(tenant_id, id) ON DELETE SET NULL
        );

        CREATE TABLE secretariat.knowledge_chunks (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          source_type text NOT NULL CHECK (length(trim(source_type)) > 0),
          source_id text,
          chunk_index integer NOT NULL DEFAULT 0 CHECK (chunk_index >= 0),
          content text NOT NULL CHECK (length(trim(content)) > 0),
          content_sha256 char(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          embedding vector(1536),
          embedding_model text,
          embedded_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, content_sha256)
        );
        CREATE INDEX idx_secretariat_knowledge_chunks_source
          ON secretariat.knowledge_chunks(tenant_id, source_type, source_id, chunk_index);
        CREATE INDEX idx_secretariat_knowledge_chunks_embedding
          ON secretariat.knowledge_chunks USING hnsw (embedding vector_cosine_ops)
          WITH (m = 16, ef_construction = 64)
          WHERE embedding IS NOT NULL;

        CREATE TABLE secretariat.operation_events (
          operation_id uuid NOT NULL,
          tenant_id uuid NOT NULL,
          sequence integer NOT NULL CHECK (sequence > 0),
          event_type text NOT NULL,
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (operation_id, sequence),
          FOREIGN KEY (tenant_id, operation_id) REFERENCES secretariat.operations(tenant_id, id) ON DELETE CASCADE
        );

        CREATE TABLE audit.events (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          actor_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          event_type text NOT NULL,
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_audit_events_tenant_created ON audit.events(tenant_id, created_at DESC);

        CREATE TABLE outbox.events (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          topic text NOT NULL,
          aggregate_type text NOT NULL,
          aggregate_id uuid NOT NULL,
          payload jsonb NOT NULL,
          status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'delivered', 'failed')),
          available_at timestamptz NOT NULL DEFAULT now(),
          delivered_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_outbox_events_delivery ON outbox.events(status, available_at, created_at);

        CREATE TRIGGER trg_iam_tenants_updated BEFORE UPDATE ON iam.tenants FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_iam_users_updated BEFORE UPDATE ON iam.users FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_iam_memberships_updated BEFORE UPDATE ON iam.memberships FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_iam_roles_updated BEFORE UPDATE ON iam.roles FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_warehouses_updated BEFORE UPDATE ON warehouse.warehouses FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_warehouse_zones_updated BEFORE UPDATE ON warehouse.warehouse_zones FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_warehouse_locations_updated BEFORE UPDATE ON warehouse.warehouse_locations FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_map_zones_updated BEFORE UPDATE ON warehouse.map_zones FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_workflow_definitions_updated BEFORE UPDATE ON workflow.definitions FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_workflow_instances_updated BEFORE UPDATE ON workflow.instances FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_secretariat_conversations_updated BEFORE UPDATE ON secretariat.conversations FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_secretariat_runs_updated BEFORE UPDATE ON secretariat.runs FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_secretariat_operations_updated BEFORE UPDATE ON secretariat.operations FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_secretariat_knowledge_chunks_updated BEFORE UPDATE ON secretariat.knowledge_chunks FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        GRANT USAGE ON SCHEMA app, iam, warehouse, workflow, secretariat, audit, outbox TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app, iam, warehouse, workflow, secretariat, audit, outbox TO warehouse_os;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app, iam, warehouse, workflow, secretariat, audit, outbox TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA iam GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA warehouse GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA workflow GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA secretariat GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA outbox GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT USAGE, SELECT ON SEQUENCES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA iam GRANT USAGE, SELECT ON SEQUENCES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA warehouse GRANT USAGE, SELECT ON SEQUENCES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA workflow GRANT USAGE, SELECT ON SEQUENCES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA secretariat GRANT USAGE, SELECT ON SEQUENCES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT USAGE, SELECT ON SEQUENCES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA outbox GRANT USAGE, SELECT ON SEQUENCES TO warehouse_os;

        DO $$
        DECLARE scoped_table text;
        BEGIN
          FOREACH scoped_table IN ARRAY ARRAY[
            'iam.memberships', 'iam.roles', 'iam.role_permissions', 'iam.membership_roles',
            'warehouse.warehouses', 'warehouse.warehouse_zones', 'warehouse.warehouse_locations', 'warehouse.map_zones',
            'workflow.definitions', 'workflow.instances',
            'secretariat.conversations', 'secretariat.runs', 'secretariat.operations', 'secretariat.operation_events', 'secretariat.knowledge_chunks',
            'audit.events', 'outbox.events'
          ]
          LOOP
            EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', scoped_table);
            EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', scoped_table);
            EXECUTE format(
              'CREATE POLICY tenant_isolation ON %s USING (tenant_id = app.current_tenant_id()) WITH CHECK (tenant_id = app.current_tenant_id())',
              scoped_table
            );
          END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP SCHEMA IF EXISTS outbox CASCADE;
        DROP SCHEMA IF EXISTS audit CASCADE;
        DROP SCHEMA IF EXISTS secretariat CASCADE;
        DROP SCHEMA IF EXISTS workflow CASCADE;
        DROP SCHEMA IF EXISTS warehouse CASCADE;
        DROP SCHEMA IF EXISTS iam CASCADE;
        DROP SCHEMA IF EXISTS app CASCADE;
        """
    )
