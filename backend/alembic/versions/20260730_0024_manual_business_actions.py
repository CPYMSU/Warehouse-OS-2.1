"""Record schema-generated manual business actions in the command ledger.

Revision ID: 20260730_0024
Revises: 20260728_0023
Create Date: 2026-07-30
"""

from __future__ import annotations

from alembic import op

revision = "20260730_0024"
down_revision = "20260728_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE terminal.command_executions
          DROP CONSTRAINT command_executions_origin_check;

        ALTER TABLE terminal.command_executions
          ADD CONSTRAINT command_executions_origin_check
            CHECK (
              origin IN (
                'terminal',
                'super_terminal',
                'manual_ui',
                'ai_tool',
                'auto_runtime'
              )
            );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE terminal.command_executions
          DROP CONSTRAINT command_executions_origin_check;

        ALTER TABLE terminal.command_executions
          ADD CONSTRAINT command_executions_origin_check
            CHECK (
              origin IN (
                'terminal',
                'super_terminal',
                'ai_tool',
                'auto_runtime'
              )
            );
        """
    )
