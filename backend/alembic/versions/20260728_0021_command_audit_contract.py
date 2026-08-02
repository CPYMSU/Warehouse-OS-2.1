"""Synchronize command audit constraints with every execution path.

Revision ID: 20260728_0021
Revises: 20260728_0020
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op

revision = "20260728_0021"
down_revision = "20260728_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE terminal.command_executions
          DROP CONSTRAINT command_executions_origin_check,
          DROP CONSTRAINT command_executions_status_check;

        ALTER TABLE terminal.command_executions
          ADD CONSTRAINT command_executions_origin_check
            CHECK (
              origin IN (
                'terminal',
                'super_terminal',
                'ai_tool',
                'auto_runtime'
              )
            ),
          ADD CONSTRAINT command_executions_status_check
            CHECK (
              status IN (
                'succeeded',
                'failed',
                'denied',
                'awaiting_domain_adapter',
                'invalid_contract',
                'confirmation_required',
                'target_rejected',
                'invalid',
                'invalid_arguments',
                'unknown_tool',
                'requires_l11_governance'
              )
            );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE terminal.command_executions
          DROP CONSTRAINT command_executions_origin_check,
          DROP CONSTRAINT command_executions_status_check;

        ALTER TABLE terminal.command_executions
          ADD CONSTRAINT command_executions_origin_check
            CHECK (origin IN ('terminal', 'super_terminal', 'ai_tool'))
            NOT VALID,
          ADD CONSTRAINT command_executions_status_check
            CHECK (
              status IN (
                'succeeded', 'failed', 'denied', 'awaiting_domain_adapter'
              )
            )
            NOT VALID;
        """
    )
