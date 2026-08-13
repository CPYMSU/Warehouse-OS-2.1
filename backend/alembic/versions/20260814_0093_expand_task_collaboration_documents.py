"""Expand TASK collaboration documents for long-form manuscripts.

Revision ID: 20260814_0093
Revises: 20260809_0092
"""

from __future__ import annotations

from alembic import op

revision = "20260814_0093"
down_revision = "20260809_0092"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.drop_constraint(
        "task_collaboration_documents_visible_length_check",
        "task_collaboration_documents",
        schema="workflow",
        type_="check",
    )
    op.drop_constraint(
        "task_collaboration_documents_node_count_check",
        "task_collaboration_documents",
        schema="workflow",
        type_="check",
    )
    op.create_check_constraint(
        "task_collaboration_documents_visible_length_check",
        "task_collaboration_documents",
        "visible_length BETWEEN 0 AND 100000",
        schema="workflow",
    )
    op.create_check_constraint(
        "task_collaboration_documents_node_count_check",
        "task_collaboration_documents",
        "node_count BETWEEN 0 AND 200000",
        schema="workflow",
    )
    op.drop_constraint(
        "task_collaboration_document_snapshots_visible_length_check",
        "task_collaboration_document_snapshots",
        schema="workflow",
        type_="check",
    )
    op.drop_constraint(
        "task_collaboration_document_snapshots_node_count_check",
        "task_collaboration_document_snapshots",
        schema="workflow",
        type_="check",
    )
    op.create_check_constraint(
        "task_collaboration_document_snapshots_visible_length_check",
        "task_collaboration_document_snapshots",
        "visible_length BETWEEN 0 AND 100000",
        schema="workflow",
    )
    op.create_check_constraint(
        "task_collaboration_document_snapshots_node_count_check",
        "task_collaboration_document_snapshots",
        "node_count BETWEEN 0 AND 200000",
        schema="workflow",
    )
    op.drop_constraint(
        "ck_task_collab_annotation_offsets",
        "task_collaboration_annotations",
        schema="workflow",
        type_="check",
    )
    op.create_check_constraint(
        "ck_task_collab_annotation_offsets",
        "task_collaboration_annotations",
        "start_offset >= 0 AND end_offset > start_offset AND end_offset <= 100000",
        schema="workflow",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_task_collab_annotation_offsets",
        "task_collaboration_annotations",
        schema="workflow",
        type_="check",
    )
    op.create_check_constraint(
        "ck_task_collab_annotation_offsets",
        "task_collaboration_annotations",
        "start_offset >= 0 AND end_offset > start_offset AND end_offset <= 32000",
        schema="workflow",
    )
    op.drop_constraint(
        "task_collaboration_document_snapshots_node_count_check",
        "task_collaboration_document_snapshots",
        schema="workflow",
        type_="check",
    )
    op.drop_constraint(
        "task_collaboration_document_snapshots_visible_length_check",
        "task_collaboration_document_snapshots",
        schema="workflow",
        type_="check",
    )
    op.create_check_constraint(
        "task_collaboration_document_snapshots_node_count_check",
        "task_collaboration_document_snapshots",
        "node_count BETWEEN 0 AND 50000",
        schema="workflow",
    )
    op.create_check_constraint(
        "task_collaboration_document_snapshots_visible_length_check",
        "task_collaboration_document_snapshots",
        "visible_length BETWEEN 0 AND 32000",
        schema="workflow",
    )
    op.drop_constraint(
        "task_collaboration_documents_node_count_check",
        "task_collaboration_documents",
        schema="workflow",
        type_="check",
    )
    op.drop_constraint(
        "task_collaboration_documents_visible_length_check",
        "task_collaboration_documents",
        schema="workflow",
        type_="check",
    )
    op.create_check_constraint(
        "task_collaboration_documents_node_count_check",
        "task_collaboration_documents",
        "node_count BETWEEN 0 AND 50000",
        schema="workflow",
    )
    op.create_check_constraint(
        "task_collaboration_documents_visible_length_check",
        "task_collaboration_documents",
        "visible_length BETWEEN 0 AND 32000",
        schema="workflow",
    )
