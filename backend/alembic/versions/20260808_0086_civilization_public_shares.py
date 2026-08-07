"""Add the explicit Civilization public-sharing boundary.

Revision ID: 20260808_0086
Revises: 20260808_0085

The tenant row keeps the stable share key and opt-in state.  The unscoped
public table contains only active snapshots of already-published content, so
the public endpoint never needs to bypass tenant RLS and can never see drafts.
"""

from __future__ import annotations

from alembic import op

revision = "20260808_0086"
down_revision = "20260808_0085"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE civilization.thoughts
          ADD COLUMN public_share_enabled boolean NOT NULL DEFAULT false,
          ADD COLUMN public_share_key text
            CHECK (
              public_share_key IS NULL
              OR public_share_key ~ '^[a-z0-9_-]{12,64}$'
            ),
          ADD COLUMN public_shared_at timestamptz;

        CREATE UNIQUE INDEX uq_civilization_thoughts_public_share_key
          ON civilization.thoughts(public_share_key)
          WHERE public_share_key IS NOT NULL;

        CREATE TABLE civilization.public_shares (
          share_key text PRIMARY KEY
            CHECK (share_key ~ '^[a-z0-9_-]{12,64}$'),
          tenant_id uuid NOT NULL,
          thought_id uuid NOT NULL UNIQUE,
          domain text NOT NULL,
          content jsonb NOT NULL CHECK (jsonb_typeof(content) = 'object'),
          lenses jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(lenses) = 'array'),
          occurred_on date NOT NULL,
          published_revision bigint NOT NULL CHECK (published_revision >= 0),
          shared_by uuid,
          shared_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_civilization_public_shares_updated
          ON civilization.public_shares(updated_at DESC);

        GRANT ALL PRIVILEGES ON TABLE civilization.public_shares TO warehouse_os;
        """
    )
    op.create_foreign_key(
        "fk_civilization_public_shares_tenant",
        "public_shares",
        "tenants",
        ["tenant_id"],
        ["id"],
        source_schema="civilization",
        referent_schema="iam",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_civilization_public_shares_thought",
        "public_shares",
        "thoughts",
        ["thought_id"],
        ["id"],
        source_schema="civilization",
        referent_schema="civilization",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_civilization_public_shares_actor",
        "public_shares",
        "users",
        ["shared_by"],
        ["id"],
        source_schema="civilization",
        referent_schema="iam",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_table("public_shares", schema="civilization")
    op.execute(
        """
        DROP INDEX civilization.uq_civilization_thoughts_public_share_key;
        ALTER TABLE civilization.thoughts
          DROP COLUMN public_shared_at,
          DROP COLUMN public_share_key,
          DROP COLUMN public_share_enabled;
        """
    )
