"""Add tenant-isolated Warehouse and Lighthouse federation state.

Revision ID: 20260804_0071
Revises: 20260803_0070
"""

from alembic import op

revision = "20260804_0071"
down_revision = "20260803_0070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA lighthouse;

        CREATE TABLE lighthouse.pairing_challenges (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          owner_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
          public_id char(12) NOT NULL CHECK (public_id ~ '^[a-f0-9]{12}$'),
          code_hash char(64) NOT NULL CHECK (code_hash ~ '^[a-f0-9]{64}$'),
          requested_label text NOT NULL
            CHECK (length(trim(requested_label)) BETWEEN 1 AND 120),
          expires_at timestamptz NOT NULL,
          consumed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, public_id),
          UNIQUE (tenant_id, code_hash)
        );
        CREATE INDEX idx_lighthouse_pairing_active
          ON lighthouse.pairing_challenges(tenant_id, owner_user_id, expires_at DESC)
          WHERE consumed_at IS NULL;

        CREATE TABLE lighthouse.devices (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          owner_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
          instance_id uuid NOT NULL,
          label text NOT NULL CHECK (length(trim(label)) BETWEEN 1 AND 120),
          public_key text,
          token_public_id char(12) NOT NULL
            CHECK (token_public_id ~ '^[a-f0-9]{12}$'),
          token_hash char(64) NOT NULL CHECK (token_hash ~ '^[a-f0-9]{64}$'),
          token_hint text NOT NULL,
          protocol_version text NOT NULL DEFAULT 'warehouse-lighthouse-federation/v1',
          status text NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'revoked')),
          capabilities jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(capabilities) = 'array'),
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(metadata) = 'object'),
          connected_at timestamptz,
          last_seen_at timestamptz,
          revoked_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, owner_user_id, instance_id),
          UNIQUE (tenant_id, token_public_id),
          UNIQUE (tenant_id, token_hash)
        );
        CREATE INDEX idx_lighthouse_devices_owner
          ON lighthouse.devices(tenant_id, owner_user_id, status, updated_at DESC);
        CREATE TRIGGER trg_lighthouse_devices_updated
          BEFORE UPDATE ON lighthouse.devices
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE lighthouse.device_connections (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          device_id uuid NOT NULL,
          protocol_version text NOT NULL,
          connected_at timestamptz NOT NULL DEFAULT now(),
          last_seen_at timestamptz NOT NULL DEFAULT now(),
          disconnected_at timestamptz,
          close_reason text,
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, device_id)
            REFERENCES lighthouse.devices(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_lighthouse_connections_device
          ON lighthouse.device_connections(tenant_id, device_id, connected_at DESC);

        CREATE TABLE lighthouse.conversation_bindings (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          owner_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
          device_id uuid NOT NULL,
          conversation_ref text NOT NULL
            CHECK (length(trim(conversation_ref)) BETWEEN 1 AND 128),
          local_conversation_ref text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, owner_user_id, conversation_ref),
          FOREIGN KEY (tenant_id, device_id)
            REFERENCES lighthouse.devices(tenant_id, id) ON DELETE CASCADE
        );
        CREATE TRIGGER trg_lighthouse_conversation_bindings_updated
          BEFORE UPDATE ON lighthouse.conversation_bindings
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE lighthouse.runs (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          owner_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          device_id uuid NOT NULL,
          client_request_id text,
          conversation_ref text,
          workspace_ref text,
          goal text NOT NULL CHECK (length(trim(goal)) BETWEEN 1 AND 16384),
          policy jsonb NOT NULL DEFAULT
            jsonb_build_object('mode', 'read_only', 'allow_local_write', false)
            CHECK (jsonb_typeof(policy) = 'object'),
          status text NOT NULL DEFAULT 'queued'
            CHECK (status IN (
              'queued', 'offered', 'accepted', 'running', 'awaiting_approval', 'cancelling',
              'completed', 'failed', 'cancelled', 'rejected'
            )),
          local_run_ref text,
          result jsonb,
          error text,
          event_cursor integer NOT NULL DEFAULT 0 CHECK (event_cursor >= 0),
          offered_at timestamptz,
          accepted_at timestamptz,
          completed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, device_id)
            REFERENCES lighthouse.devices(tenant_id, id) ON DELETE RESTRICT
        );
        CREATE UNIQUE INDEX uq_lighthouse_run_client_request
          ON lighthouse.runs(tenant_id, owner_user_id, client_request_id)
          WHERE client_request_id IS NOT NULL;
        CREATE INDEX idx_lighthouse_runs_owner
          ON lighthouse.runs(tenant_id, owner_user_id, created_at DESC);
        CREATE INDEX idx_lighthouse_runs_device_pending
          ON lighthouse.runs(tenant_id, device_id, created_at)
          WHERE status IN (
            'queued', 'offered', 'accepted', 'running', 'awaiting_approval', 'cancelling'
          );
        CREATE TRIGGER trg_lighthouse_runs_updated
          BEFORE UPDATE ON lighthouse.runs
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE lighthouse.run_events (
          run_id uuid NOT NULL,
          tenant_id uuid NOT NULL,
          device_id uuid NOT NULL,
          sequence integer NOT NULL CHECK (sequence > 0),
          event_id uuid NOT NULL,
          event_type text NOT NULL CHECK (length(trim(event_type)) BETWEEN 1 AND 100),
          payload jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(payload) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (run_id, sequence),
          UNIQUE (run_id, event_id),
          FOREIGN KEY (tenant_id, run_id)
            REFERENCES lighthouse.runs(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, device_id)
            REFERENCES lighthouse.devices(tenant_id, id) ON DELETE RESTRICT
        );
        CREATE INDEX idx_lighthouse_run_events_tenant
          ON lighthouse.run_events(tenant_id, run_id, sequence);

        CREATE TABLE lighthouse.approvals (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          run_id uuid NOT NULL,
          device_id uuid NOT NULL,
          operation_digest char(64) NOT NULL
            CHECK (operation_digest ~ '^[a-f0-9]{64}$'),
          presentation jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(presentation) = 'object'),
          status text NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'granted', 'denied', 'expired', 'consumed')),
          proof jsonb,
          decided_by_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          expires_at timestamptz NOT NULL,
          decided_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, run_id, operation_digest),
          FOREIGN KEY (tenant_id, run_id)
            REFERENCES lighthouse.runs(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, device_id)
            REFERENCES lighthouse.devices(tenant_id, id) ON DELETE RESTRICT
        );

        CREATE TABLE lighthouse.receipt_projections (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          run_id uuid NOT NULL,
          device_id uuid NOT NULL,
          local_receipt_ref text NOT NULL,
          receipt_digest char(64) NOT NULL
            CHECK (receipt_digest ~ '^[a-f0-9]{64}$'),
          projection jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(projection) = 'object'),
          committed_at timestamptz NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, device_id, local_receipt_ref),
          FOREIGN KEY (tenant_id, run_id)
            REFERENCES lighthouse.runs(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, device_id)
            REFERENCES lighthouse.devices(tenant_id, id) ON DELETE RESTRICT
        );

        CREATE TABLE lighthouse.outbox (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL,
          device_id uuid NOT NULL,
          run_id uuid,
          message_id uuid NOT NULL,
          message_type text NOT NULL CHECK (length(trim(message_type)) BETWEEN 1 AND 100),
          payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
          available_at timestamptz NOT NULL DEFAULT now(),
          delivered_at timestamptz,
          delivery_attempts integer NOT NULL DEFAULT 0 CHECK (delivery_attempts >= 0),
          last_error text,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, message_id),
          FOREIGN KEY (tenant_id, device_id)
            REFERENCES lighthouse.devices(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, run_id)
            REFERENCES lighthouse.runs(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_lighthouse_outbox_pending
          ON lighthouse.outbox(tenant_id, device_id, id)
          WHERE delivered_at IS NULL;

        GRANT USAGE ON SCHEMA lighthouse TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA lighthouse TO warehouse_os;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA lighthouse TO warehouse_os;
        REVOKE UPDATE, DELETE ON lighthouse.run_events, lighthouse.receipt_projections
          FROM warehouse_os;

        DO $$
        DECLARE scoped_table text;
        BEGIN
          FOREACH scoped_table IN ARRAY ARRAY[
            'lighthouse.pairing_challenges',
            'lighthouse.devices',
            'lighthouse.device_connections',
            'lighthouse.conversation_bindings',
            'lighthouse.runs',
            'lighthouse.run_events',
            'lighthouse.approvals',
            'lighthouse.receipt_projections',
            'lighthouse.outbox'
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

        COMMENT ON SCHEMA lighthouse IS
          'Tenant-isolated federation relay for user-owned Lighthouse runtimes.';
        COMMENT ON TABLE lighthouse.run_events IS
          'Append-only, idempotent redacted projections of local Lighthouse Run events.';
        COMMENT ON TABLE lighthouse.receipt_projections IS
          'Append-only redacted Receipt projections; full Receipts stay on the user device.';
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS lighthouse CASCADE")
