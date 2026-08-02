"""Merge research review and browser runtime migration heads.

Revision ID: 20260801_0035
Revises: 20260731_0034, 20260801_0034
Create Date: 2026-08-01
"""

revision = "20260801_0035"
down_revision = ("20260731_0034", "20260801_0034")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Join both schema branches without changing data."""


def downgrade() -> None:
    """Split the migration graph back into its two parent heads."""
