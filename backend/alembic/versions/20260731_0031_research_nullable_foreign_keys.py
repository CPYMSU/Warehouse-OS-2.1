"""Keep tenant and project scope when nullable research references are removed.

Revision ID: 20260731_0031
Revises: 20260731_0030
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op

revision = "20260731_0031"
down_revision = "20260731_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE research.protocols
          DROP CONSTRAINT IF EXISTS protocols_tenant_id_project_id_previous_protocol_id_fkey;
        ALTER TABLE research.protocols
          DROP CONSTRAINT IF EXISTS fk_research_protocol_previous;
        ALTER TABLE research.protocols
          ADD CONSTRAINT fk_research_protocol_previous
          FOREIGN KEY (tenant_id, project_id, previous_protocol_id)
          REFERENCES research.protocols(tenant_id, project_id, id)
          ON DELETE SET NULL (previous_protocol_id);

        ALTER TABLE research.runs
          DROP CONSTRAINT IF EXISTS runs_tenant_id_project_id_protocol_id_fkey;
        ALTER TABLE research.runs
          DROP CONSTRAINT IF EXISTS fk_research_run_protocol;
        ALTER TABLE research.runs
          ADD CONSTRAINT fk_research_run_protocol
          FOREIGN KEY (tenant_id, project_id, protocol_id)
          REFERENCES research.protocols(tenant_id, project_id, id)
          ON DELETE SET NULL (protocol_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE research.runs
          DROP CONSTRAINT IF EXISTS fk_research_run_protocol;
        ALTER TABLE research.runs
          ADD CONSTRAINT fk_research_run_protocol
          FOREIGN KEY (tenant_id, project_id, protocol_id)
          REFERENCES research.protocols(tenant_id, project_id, id)
          ON DELETE NO ACTION;

        ALTER TABLE research.protocols
          DROP CONSTRAINT IF EXISTS fk_research_protocol_previous;
        ALTER TABLE research.protocols
          ADD CONSTRAINT fk_research_protocol_previous
          FOREIGN KEY (tenant_id, project_id, previous_protocol_id)
          REFERENCES research.protocols(tenant_id, project_id, id)
          ON DELETE NO ACTION;
        """
    )
