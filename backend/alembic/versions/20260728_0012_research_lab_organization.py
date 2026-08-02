"""Refresh the research-lab organisation blueprint.

Revision ID: 20260728_0012
Revises: 20260727_0011
Create Date: 2026-07-28
"""

from __future__ import annotations

import json

from sqlalchemy import text

from alembic import op
from app.templates.industry_blueprints import get_blueprint

revision = "20260728_0012"
down_revision = "20260727_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    blueprint = get_blueprint("research_lab")
    op.get_bind().execute(
        text(
            """
            UPDATE iam.industry_templates
            SET name = :name,
                description = :description,
                schema_version = :schema_version,
                revision = :revision,
                blueprint = CAST(:blueprint AS jsonb)
            WHERE template_key = :template_key
            """
        ),
        {
            "template_key": blueprint["key"],
            "name": blueprint["name"],
            "description": blueprint["description"],
            "schema_version": blueprint["schema_version"],
            "revision": blueprint["revision"],
            "blueprint": json.dumps(blueprint, ensure_ascii=False),
        },
    )


def downgrade() -> None:
    # Older revisions remain valid organisation snapshots. Downgrading the
    # application does not destructively rewrite a tenant's chosen structure.
    pass
