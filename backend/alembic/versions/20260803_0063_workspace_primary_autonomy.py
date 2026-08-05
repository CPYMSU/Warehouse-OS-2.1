"""Make existing primary workspace keys durable complete authorities.

Revision ID: 20260803_0063
Revises: 20260803_0062
"""

from __future__ import annotations

from alembic import op

revision = "20260803_0063"
down_revision = "20260803_0062"
branch_labels = None
depends_on = None

_PRIMARY_SCOPES = (
    "workspace:read",
    "data:read",
    "data:write",
    "deploy:read",
    "deploy:write",
    "logs:read",
    "infra:read",
    "infra:write",
    "domain:write",
    "secrets:write",
    "database:admin",
    "repository:write",
    "backup:write",
    "accelerator:use",
)


def upgrade() -> None:
    scopes_sql = ",".join(f"'{scope}'" for scope in _PRIMARY_SCOPES)
    op.execute(
        f"""
        UPDATE digital_asset.api_credentials AS credential
        SET scopes = (
              SELECT array_agg(scope ORDER BY scope)
              FROM (
                SELECT DISTINCT unnest(
                  COALESCE(credential.scopes, ARRAY[]::text[])
                  || ARRAY[{scopes_sql}]::text[]
                ) AS scope
              ) AS complete_scopes
            ),
            expires_at = CASE
              WHEN credential.revoked_at IS NULL THEN NULL
              ELSE credential.expires_at
            END
        WHERE credential.key_kind='primary';
        """
    )


def downgrade() -> None:
    # Scope removal or reintroducing expiry would invalidate existing programs.
    pass
