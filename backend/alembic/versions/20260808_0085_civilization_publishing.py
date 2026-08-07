"""Add the Civilization fixed-template publishing contract.

Revision ID: 20260808_0085
Revises: 20260807_0084

This is a schema-only revision. Existing Civilization rows remain untouched;
the application projects their legacy title/prompt/thesis fields into the
Swiss B template until an author saves a structured draft.
"""

from __future__ import annotations

from alembic import op

revision = "20260808_0085"
down_revision = "20260807_0084"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE civilization.thoughts
          ADD COLUMN template_key text NOT NULL DEFAULT 'swiss_b_longform_v1'
            CHECK (template_key = 'swiss_b_longform_v1'),
          ADD COLUMN published_content jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(published_content) = 'object'),
          ADD COLUMN draft_content jsonb
            CHECK (draft_content IS NULL OR jsonb_typeof(draft_content) = 'object'),
          ADD COLUMN publication_status text NOT NULL DEFAULT 'published'
            CHECK (publication_status IN ('draft', 'published')),
          ADD COLUMN published_revision bigint NOT NULL DEFAULT 0
            CHECK (published_revision >= 0),
          ADD COLUMN published_at timestamptz;

        CREATE TABLE civilization.thought_revisions (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          thought_id uuid NOT NULL,
          revision_no bigint NOT NULL CHECK (revision_no > 0),
          template_key text NOT NULL CHECK (template_key = 'swiss_b_longform_v1'),
          snapshot jsonb NOT NULL CHECK (jsonb_typeof(snapshot) = 'object'),
          published_by uuid,
          published_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, thought_id, revision_no)
        );
        CREATE INDEX idx_civilization_revisions_lineage
          ON civilization.thought_revisions(tenant_id, thought_id, revision_no DESC);

        ALTER TABLE civilization.thought_revisions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE civilization.thought_revisions FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON civilization.thought_revisions
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT ALL PRIVILEGES ON TABLE civilization.thought_revisions TO warehouse_os;
        """
    )
    op.create_foreign_key(
        "fk_civilization_revisions_tenant",
        "thought_revisions",
        "tenants",
        ["tenant_id"],
        ["id"],
        source_schema="civilization",
        referent_schema="iam",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_civilization_revisions_thought",
        "thought_revisions",
        "thoughts",
        ["thought_id"],
        ["id"],
        source_schema="civilization",
        referent_schema="civilization",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_civilization_revisions_publisher",
        "thought_revisions",
        "users",
        ["published_by"],
        ["id"],
        source_schema="civilization",
        referent_schema="iam",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_table("thought_revisions", schema="civilization")
    op.execute(
        """
        ALTER TABLE civilization.thoughts
          DROP COLUMN published_at,
          DROP COLUMN published_revision,
          DROP COLUMN publication_status,
          DROP COLUMN draft_content,
          DROP COLUMN published_content,
          DROP COLUMN template_key;
        """
    )
