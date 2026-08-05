"""Align AI authorization hand-off lifetime and resource semantics.

Revision ID: 20260801_0045
Revises: 20260801_0044
Create Date: 2026-08-01
"""

from __future__ import annotations

from alembic import op

revision = "20260801_0045"
down_revision = "20260801_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE secretariat.execution_keychains AS keychain
        SET expires_at = action.expires_at
        FROM secretariat.confirmation_actions AS action
        WHERE keychain.tenant_id = action.tenant_id
          AND keychain.action_id = action.id
          AND keychain.status = 'authorized'
          AND action.status = 'authorized'
          AND action.expires_at > now()
          AND keychain.expires_at < action.expires_at;

        UPDATE app.resource_fields
        SET semantic_description =
          'Warehouse OS 數字資產編號，格式 DMA-...；DMA 在本平台不是 Data Management Agreement'
        WHERE resource_key = 'digital_asset.asset'
          AND field_key = 'asset_no';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE app.resource_fields
        SET semantic_description = '穩定企業資產編號'
        WHERE resource_key = 'digital_asset.asset'
          AND field_key = 'asset_no';
        """
    )
