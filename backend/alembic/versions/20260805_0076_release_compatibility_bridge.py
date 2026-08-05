"""Bridge the clean 0075 release to revisions created after restoration.

Some restored databases already carry the historical 20260805_0076 revision
marker, while the clean source baseline intentionally ends at 0075.  Keeping
this no-op revision makes both states converge on 0077 without restoring the
withdrawn implementation or replaying its schema mutations.

Revision ID: 20260805_0076
Revises: 20260805_0075
"""

from __future__ import annotations

revision = "20260805_0076"
down_revision = "20260805_0075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
