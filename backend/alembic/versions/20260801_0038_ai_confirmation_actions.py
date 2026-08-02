"""Add durable AI command confirmations and one-time credential delivery.

Revision ID: 20260801_0038
Revises: 20260801_0037
Create Date: 2026-08-01
"""

from __future__ import annotations

from alembic import op

revision = "20260801_0038"
down_revision = "20260801_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE iam.step_up_grants (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
          token_hash char(64) NOT NULL CHECK (token_hash ~ '^[a-f0-9]{64}$'),
          purpose text NOT NULL CHECK (length(trim(purpose)) BETWEEN 1 AND 120),
          resource jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(resource) = 'object'),
          resource_digest char(64) NOT NULL
            CHECK (resource_digest ~ '^[a-f0-9]{64}$'),
          verification jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(verification) = 'object'),
          expires_at timestamptz NOT NULL,
          used_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (token_hash),
          UNIQUE (tenant_id, id)
        );
        CREATE INDEX idx_step_up_grants_lookup
          ON iam.step_up_grants(tenant_id, user_id, purpose, expires_at DESC)
          WHERE used_at IS NULL;

        CREATE TABLE secretariat.confirmation_actions (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          requester_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          conversation_id uuid,
          run_id uuid,
          source_step_no integer CHECK (source_step_no IS NULL OR source_step_no > 0),
          status text NOT NULL DEFAULT 'pending'
            CHECK (status IN (
              'pending', 'executing', 'completed', 'cancelled',
              'failed', 'expired', 'outcome_unknown'
            )),
          revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
          tool_name text NOT NULL CHECK (length(trim(tool_name)) BETWEEN 1 AND 180),
          command text NOT NULL CHECK (length(trim(command)) BETWEEN 1 AND 240),
          risk text NOT NULL DEFAULT 'high'
            CHECK (risk IN ('low', 'normal', 'high', 'critical')),
          confirmation_mode text NOT NULL DEFAULT 'passkey',
          confirmation_adapter text NOT NULL DEFAULT 'staged_action',
          arguments_ciphertext bytea NOT NULL,
          arguments_digest char(64) NOT NULL
            CHECK (arguments_digest ~ '^[a-f0-9]{64}$'),
          request_digest char(64) NOT NULL
            CHECK (request_digest ~ '^[a-f0-9]{64}$'),
          presentation jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(presentation) = 'object'),
          editable_fields jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(editable_fields) = 'array'),
          result jsonb,
          error text,
          verification jsonb,
          execution_id uuid,
          expires_at timestamptz NOT NULL,
          executing_at timestamptz,
          completed_at timestamptz,
          cancelled_at timestamptz,
          failed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, conversation_id)
            REFERENCES secretariat.conversations(tenant_id, id) ON DELETE SET NULL,
          FOREIGN KEY (tenant_id, run_id)
            REFERENCES secretariat.runs(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_confirmation_actions_actor
          ON secretariat.confirmation_actions(
            tenant_id, requester_user_id, conversation_id, created_at DESC
          );
        CREATE INDEX idx_confirmation_actions_pending
          ON secretariat.confirmation_actions(tenant_id, requester_user_id, expires_at)
          WHERE status IN ('pending', 'executing');
        CREATE UNIQUE INDEX uq_confirmation_action_runtime_request
          ON secretariat.confirmation_actions(
            tenant_id, requester_user_id, run_id, request_digest
          ) WHERE run_id IS NOT NULL;
        CREATE TRIGGER trg_confirmation_actions_updated
          BEFORE UPDATE ON secretariat.confirmation_actions
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE secretariat.confirmation_action_events (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL,
          action_id bigint NOT NULL,
          actor_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          event_type text NOT NULL CHECK (length(trim(event_type)) BETWEEN 1 AND 100),
          revision integer NOT NULL CHECK (revision > 0),
          payload jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(payload) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          FOREIGN KEY (tenant_id, action_id)
            REFERENCES secretariat.confirmation_actions(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_confirmation_action_events_action
          ON secretariat.confirmation_action_events(tenant_id, action_id, id);

        CREATE TABLE secretariat.confirmation_credential_deliveries (
          delivery_id text PRIMARY KEY
            CHECK (delivery_id ~ '^acd_[A-Za-z0-9_-]{20,80}$'),
          tenant_id uuid NOT NULL,
          action_id bigint NOT NULL,
          requester_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          conversation_id uuid,
          client_id_hash char(64) NOT NULL
            CHECK (client_id_hash ~ '^[a-f0-9]{64}$'),
          ciphertext bytea,
          credential_count integer NOT NULL CHECK (credential_count > 0),
          descriptors jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(descriptors) = 'array'),
          status text NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'acked', 'expired')),
          expires_at timestamptz NOT NULL,
          fetched_at timestamptz,
          acked_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, delivery_id),
          FOREIGN KEY (tenant_id, action_id)
            REFERENCES secretariat.confirmation_actions(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, conversation_id)
            REFERENCES secretariat.conversations(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_confirmation_credential_delivery_action
          ON secretariat.confirmation_credential_deliveries(
            tenant_id, action_id, status, expires_at
          );

        ALTER TABLE iam.step_up_grants ENABLE ROW LEVEL SECURITY;
        ALTER TABLE iam.step_up_grants FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam.step_up_grants
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        DO $$
        DECLARE scoped_table text;
        BEGIN
          FOREACH scoped_table IN ARRAY ARRAY[
            'secretariat.confirmation_actions',
            'secretariat.confirmation_action_events',
            'secretariat.confirmation_credential_deliveries'
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

        COMMENT ON TABLE secretariat.confirmation_actions IS
          'Actor-scoped, Passkey-confirmed command proposals. Arguments are encrypted at rest.';
        COMMENT ON TABLE secretariat.confirmation_credential_deliveries IS
          'Short-lived encrypted escrow for one-time credentials; plaintext is destroyed on acknowledgement.';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS secretariat.confirmation_credential_deliveries;
        DROP TABLE IF EXISTS secretariat.confirmation_action_events;
        DROP TABLE IF EXISTS secretariat.confirmation_actions;
        DROP TABLE IF EXISTS iam.step_up_grants;
        """
    )
