"""Allow durable source evidence in intelligent hosting conversations.

Revision ID: 20260802_0059
Revises: 20260802_0058
"""

from __future__ import annotations

from alembic import op

revision = "20260802_0059"
down_revision = "20260802_0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE digital_asset.hosting_agent_events
          DROP CONSTRAINT IF EXISTS hosting_agent_events_event_type_check;
        ALTER TABLE digital_asset.hosting_agent_events
          ADD CONSTRAINT hosting_agent_events_event_type_check
          CHECK (event_type IN (
            'understood', 'observed', 'plan', 'input_required',
            'authorization_required', 'step_started', 'step_succeeded',
            'step_failed', 'diagnosis', 'repairing', 'deployment_observed',
            'source_attached', 'ready', 'cancelled', 'message'
          ));

        REVOKE DELETE ON digital_asset.hosting_agent_sessions FROM warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE digital_asset.hosting_agent_events
          DROP CONSTRAINT IF EXISTS hosting_agent_events_event_type_check;
        ALTER TABLE digital_asset.hosting_agent_events
          ADD CONSTRAINT hosting_agent_events_event_type_check
          CHECK (event_type IN (
            'understood', 'observed', 'plan', 'input_required',
            'authorization_required', 'step_started', 'step_succeeded',
            'step_failed', 'diagnosis', 'repairing', 'deployment_observed',
            'ready', 'cancelled', 'message'
          ));

        GRANT DELETE ON digital_asset.hosting_agent_sessions TO warehouse_os;
        """
    )
