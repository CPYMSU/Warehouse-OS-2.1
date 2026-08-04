"""Record capability gaps even when no semantic resource exists yet.

Revision ID: 20260803_0064
Revises: 20260803_0063
"""

from __future__ import annotations

from alembic import op

revision = "20260803_0064"
down_revision = "20260803_0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE terminal.capability_gaps
          ALTER COLUMN resource_key DROP NOT NULL,
          ADD COLUMN capability_key text,
          ADD COLUMN domain_key text,
          ADD COLUMN semantic_contract jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(semantic_contract) = 'object'),
          ADD COLUMN last_error jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(last_error) = 'object');

        ALTER TABLE terminal.capability_gaps
          ADD CONSTRAINT capability_gaps_target_check
          CHECK (resource_key IS NOT NULL OR capability_key IS NOT NULL);

        CREATE INDEX idx_capability_gaps_capability
          ON terminal.capability_gaps(
            tenant_id, capability_key, status, last_seen_at DESC
          )
          WHERE capability_key IS NOT NULL;
        """
    )


def downgrade() -> None:
    # A gap without a registered resource cannot fit the old schema. Preserve
    # resource-backed history and remove only the newly representable rows.
    op.execute(
        """
        DELETE FROM terminal.capability_gaps WHERE resource_key IS NULL;
        DROP INDEX IF EXISTS terminal.idx_capability_gaps_capability;
        ALTER TABLE terminal.capability_gaps
          DROP CONSTRAINT IF EXISTS capability_gaps_target_check,
          DROP COLUMN IF EXISTS last_error,
          DROP COLUMN IF EXISTS semantic_contract,
          DROP COLUMN IF EXISTS domain_key,
          DROP COLUMN IF EXISTS capability_key,
          ALTER COLUMN resource_key SET NOT NULL;
        """
    )
