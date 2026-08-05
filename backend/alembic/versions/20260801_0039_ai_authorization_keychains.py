"""Separate Passkey authorization from Runtime business execution.

Revision ID: 20260801_0039
Revises: 20260801_0038
Create Date: 2026-08-01
"""

from __future__ import annotations

from alembic import op

revision = "20260801_0039"
down_revision = "20260801_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE secretariat.confirmation_actions
          DROP CONSTRAINT confirmation_actions_status_check;
        ALTER TABLE secretariat.confirmation_actions
          ADD CONSTRAINT confirmation_actions_status_check CHECK (status IN (
            'pending', 'authorized', 'executing', 'completed', 'cancelled',
            'failed', 'expired', 'outcome_unknown'
          ));
        ALTER TABLE secretariat.confirmation_actions
          ADD COLUMN authorized_at timestamptz;

        CREATE TABLE secretariat.execution_keychains (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          action_id bigint NOT NULL,
          requester_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          conversation_id uuid,
          run_id uuid,
          action_revision integer NOT NULL CHECK (action_revision > 0),
          request_digest char(64) NOT NULL
            CHECK (request_digest ~ '^[a-f0-9]{64}$'),
          scope jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(scope) = 'object'),
          credential_client_id_hash char(64)
            CHECK (
              credential_client_id_hash IS NULL
              OR credential_client_id_hash ~ '^[a-f0-9]{64}$'
            ),
          status text NOT NULL DEFAULT 'authorized'
            CHECK (status IN (
              'authorized', 'claimed', 'consumed', 'revoked', 'expired',
              'outcome_unknown'
            )),
          expires_at timestamptz NOT NULL,
          claimed_at timestamptz,
          consumed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, action_id),
          FOREIGN KEY (tenant_id, action_id)
            REFERENCES secretariat.confirmation_actions(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, conversation_id)
            REFERENCES secretariat.conversations(tenant_id, id) ON DELETE SET NULL,
          FOREIGN KEY (tenant_id, run_id)
            REFERENCES secretariat.runs(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_execution_keychains_claim
          ON secretariat.execution_keychains(
            tenant_id, requester_user_id, status, expires_at, created_at
          ) WHERE status IN ('authorized', 'claimed');
        CREATE TRIGGER trg_execution_keychains_updated
          BEFORE UPDATE ON secretariat.execution_keychains
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        ALTER TABLE secretariat.execution_keychains ENABLE ROW LEVEL SECURITY;
        ALTER TABLE secretariat.execution_keychains FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON secretariat.execution_keychains
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        COMMENT ON TABLE secretariat.execution_keychains IS
          'One-use, actor-scoped Runtime authorization handles created by Passkey confirmation. They contain no reusable bearer secret.';
        COMMENT ON COLUMN secretariat.execution_keychains.scope IS
          'Exact immutable action/tool/digest scope the Runtime may consume once.';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS secretariat.execution_keychains;
        ALTER TABLE secretariat.confirmation_actions
          DROP COLUMN IF EXISTS authorized_at;
        ALTER TABLE secretariat.confirmation_actions
          DROP CONSTRAINT confirmation_actions_status_check;
        ALTER TABLE secretariat.confirmation_actions
          ADD CONSTRAINT confirmation_actions_status_check CHECK (status IN (
            'pending', 'executing', 'completed', 'cancelled',
            'failed', 'expired', 'outcome_unknown'
          ));
        """
    )
