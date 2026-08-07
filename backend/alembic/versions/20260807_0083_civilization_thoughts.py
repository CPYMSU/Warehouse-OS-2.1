"""Add tenant-owned civilization thought objects.

Revision ID: 20260807_0083
Revises: 20260807_0082
"""

from __future__ import annotations

from alembic import op

revision = "20260807_0083"
down_revision = "20260807_0082"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS civilization;
        GRANT USAGE ON SCHEMA civilization TO warehouse_os;

        CREATE TABLE civilization.thoughts (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          stable_key text NOT NULL CHECK (stable_key ~ '^[a-z0-9][a-z0-9-]{2,79}$'),
          domain text NOT NULL CHECK (domain IN (
            'judgement', 'technology', 'organization', 'time', 'ethics'
          )),
          title jsonb NOT NULL CHECK (jsonb_typeof(title) = 'object'),
          prompt jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(prompt) = 'object'),
          thesis jsonb NOT NULL CHECK (jsonb_typeof(thesis) = 'object'),
          relations jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(relations) = 'array'),
          lenses jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(lenses) = 'array'),
          occurred_on date NOT NULL DEFAULT CURRENT_DATE,
          display_order integer NOT NULL CHECK (display_order > 0),
          source text NOT NULL DEFAULT 'member' CHECK (source IN ('seed', 'member', 'import')),
          created_by uuid,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
          UNIQUE (tenant_id, stable_key),
          UNIQUE (tenant_id, display_order)
        );
        CREATE INDEX idx_civilization_thoughts_timeline
          ON civilization.thoughts(tenant_id, occurred_on, display_order);

        ALTER TABLE civilization.thoughts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE civilization.thoughts FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON civilization.thoughts
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT ALL PRIVILEGES ON TABLE civilization.thoughts TO warehouse_os;
        """
    )
    op.create_foreign_key(
        "fk_civilization_thoughts_tenant",
        "thoughts",
        "tenants",
        ["tenant_id"],
        ["id"],
        source_schema="civilization",
        referent_schema="iam",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_civilization_thoughts_creator",
        "thoughts",
        "users",
        ["created_by"],
        ["id"],
        source_schema="civilization",
        referent_schema="iam",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_table("thoughts", schema="civilization")
    op.execute("DROP SCHEMA IF EXISTS civilization")
