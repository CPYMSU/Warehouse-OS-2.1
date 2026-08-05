"""Persist verified WebAuthn credential material.

Revision ID: 20260728_0013
Revises: 20260728_0012
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op

revision = "20260728_0013"
down_revision = "20260728_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE iam.passkeys
          ADD COLUMN credential_public_key bytea,
          ADD COLUMN sign_count bigint NOT NULL DEFAULT 0 CHECK (sign_count >= 0),
          ADD COLUMN rp_id text,
          ADD COLUMN aaguid text,
          ADD COLUMN device_type text,
          ADD COLUMN backed_up boolean NOT NULL DEFAULT false;

        CREATE INDEX idx_passkeys_user_rp
          ON iam.passkeys(user_id, rp_id, created_at DESC);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS iam.idx_passkeys_user_rp;
        ALTER TABLE iam.passkeys
          DROP COLUMN IF EXISTS backed_up,
          DROP COLUMN IF EXISTS device_type,
          DROP COLUMN IF EXISTS aaguid,
          DROP COLUMN IF EXISTS rp_id,
          DROP COLUMN IF EXISTS sign_count,
          DROP COLUMN IF EXISTS credential_public_key;
        """
    )
