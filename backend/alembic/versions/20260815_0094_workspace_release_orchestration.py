"""Add durable workspace release orchestration sessions.

Revision ID: 20260815_0094
Revises: 20260814_0093
"""

from __future__ import annotations

from alembic import op

revision = "20260815_0094"
down_revision = "20260814_0093"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE digital_asset.release_sessions (
          id uuid PRIMARY KEY,
          legacy_id bigint GENERATED ALWAYS AS IDENTITY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          source_version_id uuid,
          component_id uuid,
          candidate_deployment_id uuid,
          current_job_deployment_id uuid,
          previous_deployment_id uuid,
          requested_credential_id uuid,
          requested_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          idempotency_key text NOT NULL
            CHECK (length(trim(idempotency_key)) BETWEEN 1 AND 200),
          request_digest text NOT NULL CHECK (request_digest ~ '^[a-f0-9]{64}$'),
          manifest_digest text,
          delivery_mode text NOT NULL
            CHECK (delivery_mode IN ('static', 'runtime')),
          runtime_type text NOT NULL,
          state text NOT NULL DEFAULT 'planned'
            CHECK (state IN (
              'planned', 'candidate_requested', 'candidate_ready',
              'jobs_running', 'accepted', 'awaiting_activation',
              'activating', 'public_verifying', 'verified', 'failed',
              'rolled_back', 'cancelled', 'blocked'
            )),
          request_payload jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(request_payload) = 'object'),
          release_plan jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(release_plan) = 'object'),
          required_jobs jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(required_jobs) = 'array'),
          completed_jobs jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(completed_jobs) = 'array'),
          evidence jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(evidence) = 'object'),
          last_error jsonb
            CHECK (last_error IS NULL OR jsonb_typeof(last_error) = 'object'),
          lease_owner text,
          lease_expires_at timestamptz,
          attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          completed_at timestamptz,
          UNIQUE (legacy_id),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, workspace_id, idempotency_key),
          FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, source_version_id)
            REFERENCES digital_asset.asset_versions(tenant_id, id) ON DELETE SET NULL,
          FOREIGN KEY (tenant_id, component_id)
            REFERENCES digital_asset.workspace_components(tenant_id, id) ON DELETE SET NULL,
          FOREIGN KEY (tenant_id, candidate_deployment_id)
            REFERENCES digital_asset.deployments(tenant_id, id) ON DELETE SET NULL,
          FOREIGN KEY (tenant_id, current_job_deployment_id)
            REFERENCES digital_asset.deployments(tenant_id, id) ON DELETE SET NULL,
          FOREIGN KEY (tenant_id, previous_deployment_id)
            REFERENCES digital_asset.deployments(tenant_id, id) ON DELETE SET NULL,
          FOREIGN KEY (tenant_id, requested_credential_id)
            REFERENCES digital_asset.api_credentials(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_release_sessions_workspace
          ON digital_asset.release_sessions(tenant_id, workspace_id, created_at DESC);
        CREATE INDEX idx_release_sessions_pending
          ON digital_asset.release_sessions(tenant_id, updated_at, id)
          WHERE state NOT IN ('awaiting_activation', 'verified', 'failed',
                              'rolled_back', 'cancelled', 'blocked');
        CREATE TRIGGER trg_release_sessions_updated
          BEFORE UPDATE ON digital_asset.release_sessions
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE digital_asset.release_events (
          release_id uuid NOT NULL,
          tenant_id uuid NOT NULL,
          sequence integer NOT NULL CHECK (sequence > 0),
          event_type text NOT NULL,
          stage text NOT NULL,
          status text NOT NULL,
          payload jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(payload) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (release_id, sequence),
          FOREIGN KEY (tenant_id, release_id)
            REFERENCES digital_asset.release_sessions(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_release_events_session
          ON digital_asset.release_events(tenant_id, release_id, sequence);
        CREATE TRIGGER trg_release_events_immutable
          BEFORE UPDATE OR DELETE ON digital_asset.release_events
          FOR EACH ROW EXECUTE FUNCTION digital_asset.reject_immutable_mutation();

        GRANT SELECT, INSERT, UPDATE, DELETE
          ON digital_asset.release_sessions TO warehouse_os;
        GRANT SELECT, INSERT
          ON digital_asset.release_events TO warehouse_os;
        GRANT USAGE, SELECT
          ON SEQUENCE digital_asset.release_sessions_legacy_id_seq TO warehouse_os;
        REVOKE UPDATE, DELETE ON digital_asset.release_events FROM warehouse_os;

        ALTER TABLE digital_asset.release_sessions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.release_sessions FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.release_sessions
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        ALTER TABLE digital_asset.release_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.release_events FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.release_events
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS digital_asset.release_events;
        DROP TABLE IF EXISTS digital_asset.release_sessions;
        """
    )
