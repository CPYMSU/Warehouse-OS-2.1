"""Backfill 512 MiB workspace quota units inside each tenant RLS context.

Revision ID: 20260802_0049
Revises: 20260802_0048
"""

from sqlalchemy import text

from alembic import op

revision = "20260802_0049"
down_revision = "20260802_0048"
branch_labels = None
depends_on = None


QUOTA_STEP_BYTES = 512 * 1024 * 1024


def upgrade() -> None:
    bind = op.get_bind()
    tenant_ids = bind.execute(text("SELECT id FROM iam.tenants")).scalars().all()
    for tenant_id in tenant_ids:
        bind.execute(
            text("SELECT set_config('app.tenant_id', CAST(:tenant_id AS text), true)"),
            {"tenant_id": tenant_id},
        )
        bind.execute(
            text(
                f"""
                UPDATE digital_asset.workspaces
                SET storage_quota_bytes = (
                  CEIL(
                    GREATEST(storage_quota_bytes, {QUOTA_STEP_BYTES})::numeric
                    / {QUOTA_STEP_BYTES}
                  ) * {QUOTA_STEP_BYTES}
                )::bigint
                WHERE tenant_id = :tenant_id
                  AND (
                    storage_quota_bytes < {QUOTA_STEP_BYTES}
                    OR MOD(storage_quota_bytes, {QUOTA_STEP_BYTES}) != 0
                  )
                """
            ),
            {"tenant_id": tenant_id},
        )


def downgrade() -> None:
    # Never reduce customer storage allocations during rollback.
    pass
