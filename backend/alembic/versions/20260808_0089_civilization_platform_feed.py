"""Add the draft-free Bonfire Civilization publication projection.

Revision ID: 20260808_0089
Revises: 20260808_0088
"""

from __future__ import annotations

from alembic import op

revision = "20260808_0089"
down_revision = "20260808_0088"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE civilization.platform_publications (
          thought_id uuid PRIMARY KEY,
          source_tenant_id uuid NOT NULL,
          stable_key text NOT NULL,
          domain text NOT NULL CHECK (domain IN (
            'judgement', 'technology', 'organization', 'time', 'ethics'
          )),
          title jsonb NOT NULL CHECK (jsonb_typeof(title) = 'object'),
          prompt jsonb NOT NULL CHECK (jsonb_typeof(prompt) = 'object'),
          thesis jsonb NOT NULL CHECK (jsonb_typeof(thesis) = 'object'),
          relations jsonb NOT NULL CHECK (jsonb_typeof(relations) = 'array'),
          lenses jsonb NOT NULL CHECK (jsonb_typeof(lenses) = 'array'),
          occurred_on date NOT NULL,
          display_order integer NOT NULL,
          source text NOT NULL,
          created_at timestamptz NOT NULL,
          updated_at timestamptz NOT NULL,
          revision bigint NOT NULL,
          template_key text NOT NULL,
          published_content jsonb NOT NULL CHECK (jsonb_typeof(published_content) = 'object'),
          published_revision bigint NOT NULL,
          published_at timestamptz NOT NULL,
          public_share_enabled boolean NOT NULL DEFAULT false,
          public_share_key text,
          public_shared_at timestamptz,
          projected_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_civilization_platform_publications_timeline
          ON civilization.platform_publications(occurred_on, display_order, thought_id);

        ALTER TABLE civilization.platform_publications ENABLE ROW LEVEL SECURITY;
        CREATE POLICY platform_publications_owner
          ON civilization.platform_publications
          USING (
            source_tenant_id = app.current_tenant_id()
            AND EXISTS (
              SELECT 1 FROM iam.tenants AS tenant
              WHERE tenant.id = source_tenant_id
                AND tenant.slug = 'bonfire'
                AND tenant.status = 'active'
            )
          )
          WITH CHECK (
            source_tenant_id = app.current_tenant_id()
            AND EXISTS (
              SELECT 1 FROM iam.tenants AS tenant
              WHERE tenant.id = source_tenant_id
                AND tenant.slug = 'bonfire'
                AND tenant.status = 'active'
            )
          );

        REVOKE ALL ON civilization.platform_publications FROM PUBLIC;
        GRANT ALL PRIVILEGES ON civilization.platform_publications TO warehouse_os;

        CREATE VIEW civilization.platform_feed
          WITH (security_barrier = true, security_invoker = false)
        AS SELECT * FROM civilization.platform_publications;
        REVOKE ALL ON civilization.platform_feed FROM PUBLIC;
        GRANT SELECT ON civilization.platform_feed TO warehouse_os;
        """
    )
    op.create_foreign_key(
        "fk_civilization_platform_publications_thought",
        "platform_publications",
        "thoughts",
        ["thought_id"],
        ["id"],
        source_schema="civilization",
        referent_schema="civilization",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_civilization_platform_publications_tenant",
        "platform_publications",
        "tenants",
        ["source_tenant_id"],
        ["id"],
        source_schema="civilization",
        referent_schema="iam",
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.execute(
        """
        DROP VIEW IF EXISTS civilization.platform_feed;
        DROP TABLE IF EXISTS civilization.platform_publications;
        """
    )
