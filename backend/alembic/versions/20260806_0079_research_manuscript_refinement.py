"""Add browser-local manuscript refinement drafts.

Revision ID: 20260806_0079
Revises: 20260805_0078
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260806_0079"
down_revision = "20260805_0078"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.drop_constraint(
        "document_blocks_block_type_check",
        "document_blocks",
        schema="research",
        type_="check",
    )
    op.create_check_constraint(
        "document_blocks_block_type_check",
        "document_blocks",
        "block_type IN ('title','heading','paragraph','list_item','table_row',"
        "'equation','caption','code','page','image')",
        schema="research",
    )
    op.create_table(
        "manuscript_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("base_file_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "blocks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("state", sa.Text(), nullable=False, server_default="active"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iam.users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iam.users.id", ondelete="SET NULL"),
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("revision >= 0", name="ck_manuscript_drafts_revision"),
        sa.CheckConstraint(
            "jsonb_typeof(blocks) = 'array' AND jsonb_array_length(blocks) <= 5000",
            name="ck_manuscript_drafts_blocks",
        ),
        sa.CheckConstraint(
            "state IN ('active', 'submitted')",
            name="ck_manuscript_drafts_state",
        ),
        sa.UniqueConstraint("tenant_id", "file_id", name="uq_manuscript_drafts_file"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "project_id", "file_id", "base_file_version_id"],
            [
                "research.file_versions.tenant_id",
                "research.file_versions.project_id",
                "research.file_versions.file_id",
                "research.file_versions.id",
            ],
            name="fk_manuscript_drafts_base_version",
            ondelete="CASCADE",
        ),
        schema="research",
    )
    op.create_index(
        "idx_research_manuscript_drafts_project",
        "manuscript_drafts",
        ["tenant_id", "project_id", sa.text("updated_at DESC")],
        schema="research",
    )
    op.execute("ALTER TABLE research.manuscript_drafts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE research.manuscript_drafts FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON research.manuscript_drafts "
        "USING (tenant_id = app.current_tenant_id()) "
        "WITH CHECK (tenant_id = app.current_tenant_id())"
    )
    op.execute(
        "GRANT ALL PRIVILEGES ON TABLE research.manuscript_drafts TO warehouse_os"
    )


def downgrade() -> None:
    op.drop_table("manuscript_drafts", schema="research")
