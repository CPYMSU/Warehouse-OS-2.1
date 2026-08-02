"""Allow research-only audience credentials in the shared Runtime key table.

Revision ID: 20260731_0029
Revises: 20260731_0028
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op

revision = "20260731_0029"
down_revision = "20260731_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE iam.runtime_api_keys
          DROP CONSTRAINT runtime_api_keys_scopes_check;

        ALTER TABLE iam.runtime_api_keys
          ADD CONSTRAINT runtime_api_keys_scopes_check CHECK (
            jsonb_typeof(scopes) = 'array'
            AND scopes <@ '["assistant", "terminal", "research"]'::jsonb
            AND jsonb_array_length(scopes) BETWEEN 1 AND 3
          );
        """
    )


def downgrade() -> None:
    # Never silently delete issued credentials just to make an old constraint
    # fit. Operators must revoke/remove research keys explicitly before a
    # downgrade.
    op.execute(
        """
        DO $downgrade$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM iam.runtime_api_keys
            WHERE scopes ? 'research'
          ) THEN
            RAISE EXCEPTION
              'revoke research Runtime API Keys before downgrading 20260731_0029';
          END IF;
        END
        $downgrade$;

        ALTER TABLE iam.runtime_api_keys
          DROP CONSTRAINT runtime_api_keys_scopes_check;

        ALTER TABLE iam.runtime_api_keys
          ADD CONSTRAINT runtime_api_keys_scopes_check CHECK (
            jsonb_typeof(scopes) = 'array'
            AND scopes <@ '["assistant", "terminal"]'::jsonb
            AND jsonb_array_length(scopes) BETWEEN 1 AND 2
          );
        """
    )
