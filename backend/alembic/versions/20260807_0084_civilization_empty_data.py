"""Keep Civilization empty for author-created tenant content.

Revision ID: 20260807_0084
Revises: 20260807_0083

The revision identifier is retained because the standby migration cursor saw
0084 during a failed, non-activated release.  No application rows are written.
"""

from __future__ import annotations

revision = "20260807_0084"
down_revision = "20260807_0083"
branch_labels = None
depends_on = None
warehouse_scope = "primary_data"


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
