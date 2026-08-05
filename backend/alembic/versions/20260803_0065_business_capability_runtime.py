"""Add the tenant business-capability system of record.

Revision ID: 20260803_0065
Revises: 20260803_0064
"""

from __future__ import annotations

from alembic import op

revision = "20260803_0065"
down_revision = "20260803_0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS business;

        CREATE TABLE business.entities (
          id uuid PRIMARY KEY,
          legacy_id bigint GENERATED ALWAYS AS IDENTITY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          resource_type text NOT NULL
            CHECK (resource_type ~ '^[a-z][a-z0-9_.-]{2,159}$'),
          entity_key text NOT NULL CHECK (length(trim(entity_key)) BETWEEN 1 AND 240),
          state text NOT NULL DEFAULT 'active'
            CHECK (length(trim(state)) BETWEEN 1 AND 80),
          payload jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(payload) = 'object'),
          revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          updated_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, resource_type, entity_key),
          UNIQUE (legacy_id),
          UNIQUE (tenant_id, id)
        );
        CREATE INDEX idx_business_entities_resource_state
          ON business.entities(tenant_id, resource_type, state, updated_at DESC);
        CREATE INDEX idx_business_entities_payload
          ON business.entities USING gin(payload jsonb_path_ops);
        CREATE TRIGGER trg_business_entities_updated
          BEFORE UPDATE ON business.entities
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE business.events (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          entity_id uuid,
          tool_name text NOT NULL CHECK (length(trim(tool_name)) BETWEEN 1 AND 160),
          resource_type text NOT NULL,
          entity_key text NOT NULL,
          operation text NOT NULL,
          request_key text,
          confirmation_mode text NOT NULL DEFAULT 'direct'
            CHECK (confirmation_mode IN ('direct', 'domain_workflow', 'passkey')),
          origin text NOT NULL,
          before_payload jsonb,
          after_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          actor_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          FOREIGN KEY (tenant_id, entity_id)
            REFERENCES business.entities(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_business_events_entity
          ON business.events(tenant_id, resource_type, entity_key, created_at DESC);
        CREATE UNIQUE INDEX uq_business_events_request
          ON business.events(tenant_id, tool_name, request_key)
          WHERE request_key IS NOT NULL;

        CREATE TABLE business.external_receipts (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          event_id uuid NOT NULL REFERENCES business.events(id) ON DELETE CASCADE,
          provider text NOT NULL,
          provider_reference text,
          status text NOT NULL
            CHECK (status IN ('accepted', 'completed', 'rejected', 'failed')),
          receipt jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(receipt) = 'object'),
          observed_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, event_id)
        );

        COMMENT ON TABLE business.entities IS
          'Canonical tenant-scoped state for retained business capabilities. '
          'Unlike compatibility projections, writes here are versioned domain mutations.';
        COMMENT ON TABLE business.events IS
          'Immutable mutation and idempotency ledger for the retained capability runtime.';
        COMMENT ON TABLE business.external_receipts IS
          'Provider evidence required before an adapter may claim an external effect.';

        GRANT USAGE ON SCHEMA business TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE, DELETE ON
          business.entities, business.events, business.external_receipts
          TO warehouse_os;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA business TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA business
          GRANT USAGE, SELECT ON SEQUENCES TO warehouse_os;

        ALTER TABLE business.entities ENABLE ROW LEVEL SECURITY;
        ALTER TABLE business.entities FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON business.entities
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        ALTER TABLE business.events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE business.events FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON business.events
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        ALTER TABLE business.external_receipts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE business.external_receipts FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON business.external_receipts
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS business.external_receipts;
        DROP TABLE IF EXISTS business.events;
        DROP TABLE IF EXISTS business.entities;
        DROP SCHEMA IF EXISTS business;
        """
    )
