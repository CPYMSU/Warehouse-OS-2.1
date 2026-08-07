"""Add draft-scoped manuscript selection annotations.

Revision ID: 20260807_0082
Revises: 20260807_0081
"""

from __future__ import annotations

from alembic import op

revision = "20260807_0082"
down_revision = "20260807_0081"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE research.manuscript_annotations (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          file_id uuid NOT NULL,
          draft_id uuid NOT NULL,
          block_id text NOT NULL CHECK (length(block_id) BETWEEN 1 AND 180),
          source_sha256 char(64) NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
          field_name text NOT NULL DEFAULT 'text'
            CHECK (field_name IN ('text', 'cell')),
          cell_index integer CHECK (cell_index IS NULL OR cell_index >= 0),
          start_offset integer NOT NULL CHECK (start_offset >= 0),
          end_offset integer NOT NULL CHECK (end_offset > start_offset),
          quote text NOT NULL CHECK (length(quote) BETWEEN 1 AND 12000),
          prefix text NOT NULL DEFAULT '',
          suffix text NOT NULL DEFAULT '',
          annotation_type text NOT NULL DEFAULT 'note'
            CHECK (annotation_type IN ('highlight', 'note')),
          color text NOT NULL DEFAULT 'yellow'
            CHECK (color IN ('yellow', 'mint', 'blue', 'rose')),
          body text NOT NULL DEFAULT '' CHECK (length(body) <= 20000),
          status text NOT NULL DEFAULT 'open'
            CHECK (status IN ('open', 'resolved', 'stale')),
          created_by uuid,
          resolved_by uuid,
          resolved_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_research_manuscript_annotations_draft
          ON research.manuscript_annotations(
            tenant_id, draft_id, status, block_id, created_at DESC
          );

        ALTER TABLE research.manuscript_annotations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE research.manuscript_annotations FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON research.manuscript_annotations
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT ALL PRIVILEGES ON TABLE research.manuscript_annotations TO warehouse_os;
        """
    )
    op.create_foreign_key(
        "fk_manuscript_annotations_draft",
        "manuscript_annotations",
        "manuscript_drafts",
        ["draft_id"],
        ["id"],
        source_schema="research",
        referent_schema="research",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_manuscript_annotations_creator",
        "manuscript_annotations",
        "users",
        ["created_by"],
        ["id"],
        source_schema="research",
        referent_schema="iam",
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_manuscript_annotations_resolver",
        "manuscript_annotations",
        "users",
        ["resolved_by"],
        ["id"],
        source_schema="research",
        referent_schema="iam",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_table("manuscript_annotations", schema="research")
