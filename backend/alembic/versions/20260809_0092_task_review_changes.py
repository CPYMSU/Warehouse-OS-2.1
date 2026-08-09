"""Add Word-style review changes to TASK collaboration annotations.

Revision ID: 20260809_0092
Revises: 20260809_0091
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260809_0092"
down_revision = "20260809_0091"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.add_column(
        "task_collaboration_annotations",
        sa.Column("kind", sa.Text(), nullable=False, server_default="comment"),
        schema="workflow",
    )
    op.add_column(
        "task_collaboration_annotations",
        sa.Column("proposed_text", sa.Text(), nullable=True),
        schema="workflow",
    )
    op.add_column(
        "task_collaboration_annotations",
        sa.Column("review_state", sa.Text(), nullable=False, server_default="none"),
        schema="workflow",
    )
    op.add_column(
        "task_collaboration_annotations",
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="workflow",
    )
    op.add_column(
        "task_collaboration_annotations",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        schema="workflow",
    )
    op.add_column(
        "task_collaboration_annotations",
        sa.Column("accepted_sequence", sa.BigInteger(), nullable=True),
        schema="workflow",
    )
    op.create_check_constraint(
        "ck_task_collab_annotation_kind",
        "task_collaboration_annotations",
        "kind IN ('comment', 'suggestion')",
        schema="workflow",
    )
    op.create_check_constraint(
        "ck_task_collab_annotation_review_state",
        "task_collaboration_annotations",
        "review_state IN ('none', 'pending', 'accepted', 'rejected', 'conflicted')",
        schema="workflow",
    )
    op.create_check_constraint(
        "ck_task_collab_annotation_review_payload",
        "task_collaboration_annotations",
        "(kind = 'comment' AND proposed_text IS NULL AND review_state = 'none') OR "
        "(kind = 'suggestion' AND proposed_text IS NOT NULL AND "
        "length(proposed_text) <= 2000 AND review_state <> 'none')",
        schema="workflow",
    )
    op.create_check_constraint(
        "ck_task_collab_annotation_review_terminal",
        "task_collaboration_annotations",
        "(review_state = 'accepted' AND reviewed_by_user_id IS NOT NULL "
        "AND reviewed_at IS NOT NULL AND accepted_sequence IS NOT NULL) OR "
        "(review_state = 'rejected' AND reviewed_by_user_id IS NOT NULL "
        "AND reviewed_at IS NOT NULL AND accepted_sequence IS NULL) OR "
        "(review_state IN ('none', 'pending', 'conflicted') "
        "AND reviewed_by_user_id IS NULL AND reviewed_at IS NULL "
        "AND accepted_sequence IS NULL)",
        schema="workflow",
    )
    op.create_foreign_key(
        "fk_task_collab_annotation_reviewer",
        "task_collaboration_annotations",
        "users",
        ["reviewed_by_user_id"],
        ["id"],
        source_schema="workflow",
        referent_schema="iam",
        ondelete="RESTRICT",
    )
    op.create_index(
        "idx_task_collab_annotations_review",
        "task_collaboration_annotations",
        ["tenant_id", "document_id", "kind", "review_state", "created_at"],
        schema="workflow",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_task_collab_annotations_review",
        table_name="task_collaboration_annotations",
        schema="workflow",
    )
    op.drop_constraint(
        "fk_task_collab_annotation_reviewer",
        "task_collaboration_annotations",
        schema="workflow",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_task_collab_annotation_review_terminal",
        "task_collaboration_annotations",
        schema="workflow",
        type_="check",
    )
    op.drop_constraint(
        "ck_task_collab_annotation_review_payload",
        "task_collaboration_annotations",
        schema="workflow",
        type_="check",
    )
    op.drop_constraint(
        "ck_task_collab_annotation_review_state",
        "task_collaboration_annotations",
        schema="workflow",
        type_="check",
    )
    op.drop_constraint(
        "ck_task_collab_annotation_kind",
        "task_collaboration_annotations",
        schema="workflow",
        type_="check",
    )
    op.drop_column("task_collaboration_annotations", "accepted_sequence", schema="workflow")
    op.drop_column("task_collaboration_annotations", "reviewed_at", schema="workflow")
    op.drop_column("task_collaboration_annotations", "reviewed_by_user_id", schema="workflow")
    op.drop_column("task_collaboration_annotations", "review_state", schema="workflow")
    op.drop_column("task_collaboration_annotations", "proposed_text", schema="workflow")
    op.drop_column("task_collaboration_annotations", "kind", schema="workflow")
