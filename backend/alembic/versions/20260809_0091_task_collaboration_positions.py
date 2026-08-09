"""Persist TASK collaboration positions, live cursors and annotation threads.

Revision ID: 20260809_0091
Revises: 20260808_0090
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260809_0091"
down_revision = "20260808_0090"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.add_column(
        "task_collaboration_presence",
        sa.Column("position", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="workflow",
    )
    op.create_check_constraint(
        "ck_task_collab_presence_position_object",
        "task_collaboration_presence",
        "position IS NULL OR jsonb_typeof(position) = 'object'",
        schema="workflow",
    )
    op.create_table(
        "task_collaboration_positions",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(position) = 'object'",
            name="ck_task_collab_position_object",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["iam.tenants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id"],
            [
                "workflow.task_collaboration_spaces.tenant_id",
                "workflow.task_collaboration_spaces.id",
            ],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["iam.memberships.tenant_id", "iam.memberships.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("tenant_id", "space_id", "user_id"),
        schema="workflow",
    )
    op.create_index(
        "idx_task_collab_positions_space_updated",
        "task_collaboration_positions",
        ["tenant_id", "space_id", "updated_at"],
        schema="workflow",
    )
    op.create_table(
        "task_collaboration_annotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_annotation_id", sa.Text(), nullable=False),
        sa.Column("start_anchor", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("end_anchor", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("document_sequence", sa.BigInteger(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.CheckConstraint(
            "jsonb_typeof(start_anchor) = 'object' AND jsonb_typeof(end_anchor) = 'object'",
            name="ck_task_collab_annotation_anchors",
        ),
        sa.CheckConstraint(
            "start_offset >= 0 AND end_offset > start_offset AND end_offset <= 32000",
            name="ck_task_collab_annotation_offsets",
        ),
        sa.CheckConstraint(
            "document_sequence >= 0", name="ck_task_collab_annotation_sequence"
        ),
        sa.CheckConstraint(
            "length(trim(quote)) BETWEEN 1 AND 2000",
            name="ck_task_collab_annotation_quote",
        ),
        sa.CheckConstraint(
            "length(client_annotation_id) BETWEEN 1 AND 120",
            name="ck_task_collab_annotation_client_id",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'resolved')", name="ck_task_collab_annotation_status"
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam.tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "space_id"],
            [
                "workflow.task_collaboration_spaces.tenant_id",
                "workflow.task_collaboration_spaces.id",
            ],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "document_id"],
            [
                "workflow.task_collaboration_documents.tenant_id",
                "workflow.task_collaboration_documents.id",
            ],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "author_user_id"],
            ["iam.memberships.tenant_id", "iam.memberships.user_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"],
            ["iam.users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint(
            "tenant_id", "document_id", "author_user_id", "client_annotation_id",
            name="uq_task_collab_annotation_client",
        ),
        schema="workflow",
    )
    op.create_index(
        "idx_task_collab_annotations_document",
        "task_collaboration_annotations",
        ["tenant_id", "document_id", "status", "created_at"],
        schema="workflow",
    )
    op.create_table(
        "task_collaboration_annotation_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("annotation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_message_id", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.CheckConstraint(
            "length(client_message_id) BETWEEN 1 AND 120",
            name="ck_task_collab_annotation_message_client_id",
        ),
        sa.CheckConstraint(
            "length(trim(body)) BETWEEN 1 AND 4000",
            name="ck_task_collab_annotation_message_body",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam.tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "annotation_id"],
            ["workflow.task_collaboration_annotations.tenant_id", "workflow.task_collaboration_annotations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "author_user_id"],
            ["iam.memberships.tenant_id", "iam.memberships.user_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint(
            "tenant_id", "annotation_id", "author_user_id", "client_message_id",
            name="uq_task_collab_annotation_message_client",
        ),
        schema="workflow",
    )
    op.create_index(
        "idx_task_collab_annotation_messages_thread",
        "task_collaboration_annotation_messages",
        ["tenant_id", "annotation_id", "id"],
        schema="workflow",
    )
    op.execute(
        """
        GRANT ALL PRIVILEGES
          ON workflow.task_collaboration_positions,
             workflow.task_collaboration_annotations,
             workflow.task_collaboration_annotation_messages TO warehouse_os;
        GRANT USAGE, SELECT ON SEQUENCE
          workflow.task_collaboration_annotation_messages_id_seq TO warehouse_os;

        ALTER TABLE workflow.task_collaboration_positions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_positions FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_positions
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_annotations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_annotations FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_annotations
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_annotation_messages ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_annotation_messages FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_annotation_messages
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        """
    )


def downgrade() -> None:
    op.drop_table("task_collaboration_annotation_messages", schema="workflow")
    op.drop_table("task_collaboration_annotations", schema="workflow")
    op.drop_table("task_collaboration_positions", schema="workflow")
    op.drop_constraint(
        "ck_task_collab_presence_position_object",
        "task_collaboration_presence",
        schema="workflow",
        type_="check",
    )
    op.drop_column("task_collaboration_presence", "position", schema="workflow")
