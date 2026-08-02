"""Queue existing complete conversation history for incremental distillation.

Revision ID: 20260728_0020
Revises: 20260728_0019
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op

revision = "20260728_0020"
down_revision = "20260728_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO secretariat.memory_jobs(
          id, tenant_id, owner_user_id, conversation_id,
          job_type, status, requested_level, source_cursor
        )
        SELECT
          md5(
            'memory-job:' || conversation.tenant_id::text || ':'
            || conversation.id::text
          )::uuid,
          conversation.tenant_id,
          conversation.owner_user_id,
          conversation.id,
          'conversation_distill',
          'pending',
          2,
          max(message.sequence)
        FROM secretariat.conversations conversation
        JOIN secretariat.messages message
          ON message.tenant_id = conversation.tenant_id
         AND message.conversation_id = conversation.id
        WHERE conversation.status = 'active'
        GROUP BY
          conversation.tenant_id,
          conversation.owner_user_id,
          conversation.id
        HAVING bool_or(message.role = 'assistant')
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    # Distillation jobs may have advanced after deployment. They are durable
    # operational state and are intentionally not removed by a data backfill
    # downgrade.
    pass
