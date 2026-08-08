"""Backfill existing Bonfire publications into the shared feed.

Revision ID: 20260808_0090
Revises: 20260808_0089
"""

from __future__ import annotations

from alembic import op

revision = "20260808_0090"
down_revision = "20260808_0089"
branch_labels = None
depends_on = None
warehouse_scope = "primary_data"


def upgrade() -> None:
    op.execute(
        """
        SELECT set_config(
          'app.tenant_id',
          COALESCE((SELECT id::text FROM iam.tenants WHERE slug = 'bonfire'), ''),
          true
        )
        """
    )
    op.execute(
        """
        INSERT INTO civilization.platform_publications(
          thought_id, source_tenant_id, stable_key, domain,
          title, prompt, thesis, relations, lenses,
          occurred_on, display_order, source, created_at, updated_at,
          revision, template_key, published_content,
          published_revision, published_at,
          public_share_enabled, public_share_key, public_shared_at,
          projected_at
        )
        SELECT
          thought.id, thought.tenant_id, thought.stable_key, thought.domain,
          thought.title, thought.prompt, thought.thesis, thought.relations, thought.lenses,
          thought.occurred_on, thought.display_order, thought.source,
          thought.created_at, thought.updated_at, thought.revision,
          thought.template_key, thought.published_content,
          thought.published_revision, thought.published_at,
          thought.public_share_enabled,
          CASE WHEN thought.public_share_enabled THEN thought.public_share_key ELSE NULL END,
          thought.public_shared_at, now()
        FROM civilization.thoughts AS thought
        JOIN iam.tenants AS tenant ON tenant.id = thought.tenant_id
        WHERE tenant.slug = 'bonfire'
          AND tenant.status = 'active'
          AND thought.publication_status = 'published'
        ON CONFLICT (thought_id) DO UPDATE SET
          source_tenant_id = EXCLUDED.source_tenant_id,
          stable_key = EXCLUDED.stable_key,
          domain = EXCLUDED.domain,
          title = EXCLUDED.title,
          prompt = EXCLUDED.prompt,
          thesis = EXCLUDED.thesis,
          relations = EXCLUDED.relations,
          lenses = EXCLUDED.lenses,
          occurred_on = EXCLUDED.occurred_on,
          display_order = EXCLUDED.display_order,
          source = EXCLUDED.source,
          created_at = EXCLUDED.created_at,
          updated_at = EXCLUDED.updated_at,
          revision = EXCLUDED.revision,
          template_key = EXCLUDED.template_key,
          published_content = EXCLUDED.published_content,
          published_revision = EXCLUDED.published_revision,
          published_at = EXCLUDED.published_at,
          public_share_enabled = EXCLUDED.public_share_enabled,
          public_share_key = EXCLUDED.public_share_key,
          public_shared_at = EXCLUDED.public_shared_at,
          projected_at = now();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        SELECT set_config(
          'app.tenant_id',
          COALESCE((SELECT id::text FROM iam.tenants WHERE slug = 'bonfire'), ''),
          true
        )
        """
    )
    op.execute("DELETE FROM civilization.platform_publications")
