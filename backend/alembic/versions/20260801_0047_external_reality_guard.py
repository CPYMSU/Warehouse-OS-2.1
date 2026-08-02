"""Guard semantic fields that claim externally observable runtime reality.

Revision ID: 20260801_0047
Revises: 20260801_0046
"""

from alembic import op

revision = "20260801_0047"
down_revision = "20260801_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE app.resource_fields
        SET editable_mode = 'adapter_only',
            semantic_description =
              '工作區目前由部署提供者或反向代理實際驗證的公開網址；不可由通用資料修改宣稱已生效'
        WHERE resource_key = 'digital_asset.workspace'
          AND field_key = 'public_url';

        INSERT INTO app.resource_invariants(
          invariant_key, resource_key, description,
          enforcement, machine_contract, active
        ) VALUES (
          'digital_asset.workspace.public_url_external_reality',
          'digital_asset.workspace',
          'public_url 必須來自部署提供者、反向代理配置與探活證據；通用資料修改不可偽造',
          'external_verification',
          '{"fields":["public_url"]}'::jsonb,
          true
        )
        ON CONFLICT (invariant_key) DO UPDATE SET
          description = EXCLUDED.description,
          enforcement = EXCLUDED.enforcement,
          machine_contract = EXCLUDED.machine_contract,
          active = true;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM app.resource_invariants
        WHERE invariant_key = 'digital_asset.workspace.public_url_external_reality';

        UPDATE app.resource_fields
        SET editable_mode = 'direct',
            semantic_description = '工作區目前登記的公開網址'
        WHERE resource_key = 'digital_asset.workspace'
          AND field_key = 'public_url';
        """
    )
