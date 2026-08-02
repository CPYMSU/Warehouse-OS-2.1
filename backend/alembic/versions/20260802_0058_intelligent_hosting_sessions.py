"""Add the tenant-isolated intelligent hosting conversation ledger.

Revision ID: 20260802_0058
Revises: 20260802_0057
"""

from __future__ import annotations

from alembic import op

revision = "20260802_0058"
down_revision = "20260802_0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE digital_asset.hosting_agent_sessions (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          workspace_id uuid NOT NULL,
          actor_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          credential_id uuid,
          auth_kind text NOT NULL
            CHECK (auth_kind IN ('session', 'runtime_api_key', 'workspace_key')),
          client_kind text NOT NULL DEFAULT 'unknown'
            CHECK (client_kind IN (
              'unknown', 'web_secretary', 'terminal_ai', 'external_ai', 'automation'
            )),
          goal text NOT NULL CHECK (length(trim(goal)) BETWEEN 1 AND 16384),
          last_message text,
          status text NOT NULL DEFAULT 'observing'
            CHECK (status IN (
              'observing', 'planning', 'awaiting_source', 'awaiting_authorization',
              'running', 'blocked', 'completed', 'cancelled', 'failed'
            )),
          current_stage text NOT NULL DEFAULT 'observe',
          desired_state jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(desired_state) = 'object'),
          plan jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(plan) = 'object'),
          state jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(state) = 'object'),
          diagnosis jsonb
            CHECK (diagnosis IS NULL OR jsonb_typeof(diagnosis) = 'object'),
          authorization_scope jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(authorization_scope) = 'object'),
          revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          completed_at timestamptz,
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, credential_id)
            REFERENCES digital_asset.api_credentials(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_hosting_agent_sessions_workspace
          ON digital_asset.hosting_agent_sessions(
            tenant_id, workspace_id, updated_at DESC
          );
        CREATE INDEX idx_hosting_agent_sessions_active
          ON digital_asset.hosting_agent_sessions(tenant_id, status, updated_at DESC)
          WHERE status NOT IN ('completed', 'cancelled', 'failed');
        CREATE TRIGGER trg_hosting_agent_sessions_updated
          BEFORE UPDATE ON digital_asset.hosting_agent_sessions
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE digital_asset.hosting_agent_events (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL,
          session_id uuid NOT NULL,
          sequence integer NOT NULL CHECK (sequence > 0),
          event_type text NOT NULL
            CHECK (event_type IN (
              'understood', 'observed', 'plan', 'input_required',
              'authorization_required', 'step_started', 'step_succeeded',
              'step_failed', 'diagnosis', 'repairing', 'deployment_observed',
              'ready', 'cancelled', 'message'
            )),
          stage text NOT NULL,
          status text NOT NULL,
          payload jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(payload) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, session_id, sequence),
          FOREIGN KEY (tenant_id, session_id)
            REFERENCES digital_asset.hosting_agent_sessions(tenant_id, id)
            ON DELETE CASCADE
        );
        CREATE INDEX idx_hosting_agent_events_session
          ON digital_asset.hosting_agent_events(tenant_id, session_id, sequence);

        GRANT SELECT, INSERT, UPDATE, DELETE
          ON digital_asset.hosting_agent_sessions TO warehouse_os;
        GRANT SELECT, INSERT
          ON digital_asset.hosting_agent_events TO warehouse_os;
        GRANT USAGE, SELECT
          ON SEQUENCE digital_asset.hosting_agent_events_id_seq TO warehouse_os;

        ALTER TABLE digital_asset.hosting_agent_sessions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.hosting_agent_sessions FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation
          ON digital_asset.hosting_agent_sessions
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        ALTER TABLE digital_asset.hosting_agent_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.hosting_agent_events FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation
          ON digital_asset.hosting_agent_events
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        CREATE TRIGGER trg_hosting_agent_events_immutable
          BEFORE UPDATE OR DELETE ON digital_asset.hosting_agent_events
          FOR EACH ROW EXECUTE FUNCTION digital_asset.reject_immutable_mutation();

        INSERT INTO app.resource_types(
          resource_key, schema_version, label, description,
          storage_schema, storage_table, version_column, version_strategy,
          identity_fields, allowed_effects
        ) VALUES (
          'digital_asset.hosting_agent_session', 1, '智能託管會話',
          '綁定單一公司與工作區的可恢復託管目標、計畫、狀態及診斷',
          'digital_asset', 'hosting_agent_sessions', 'revision', 'integer',
          '["id"]'::jsonb, '["read"]'::jsonb
        ) ON CONFLICT (resource_key) DO UPDATE SET
          schema_version=EXCLUDED.schema_version,
          label=EXCLUDED.label,
          description=EXCLUDED.description,
          storage_schema=EXCLUDED.storage_schema,
          storage_table=EXCLUDED.storage_table,
          version_column=EXCLUDED.version_column,
          version_strategy=EXCLUDED.version_strategy,
          identity_fields=EXCLUDED.identity_fields,
          allowed_effects=EXCLUDED.allowed_effects,
          active=true;

        INSERT INTO app.resource_invariants(
          invariant_key, resource_key, description, enforcement, machine_contract
        ) VALUES (
          'digital_asset.hosting_agent.bounded_workspace_authority',
          'digital_asset.hosting_agent_session',
          '智能託管會話只能操作建立時綁定的同租戶工作區；工作區 Key 不能跨工作區',
          'database',
          jsonb_build_object(
            'workspace_binding', 'immutable',
            'workspace_key_scope_enforced', true,
            'events', 'append_only',
            'raw_reasoning_exposed', false
          )
        ) ON CONFLICT (invariant_key) DO UPDATE SET
          description=EXCLUDED.description,
          enforcement=EXCLUDED.enforcement,
          machine_contract=EXCLUDED.machine_contract,
          active=true;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM app.resource_types
        WHERE resource_key='digital_asset.hosting_agent_session';
        DROP TABLE IF EXISTS digital_asset.hosting_agent_events;
        DROP TABLE IF EXISTS digital_asset.hosting_agent_sessions;
        """
    )
