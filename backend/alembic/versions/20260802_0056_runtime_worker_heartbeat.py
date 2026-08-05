"""Observe Runtime Controller liveness independently from deployment claims.

Revision ID: 20260802_0056
Revises: 20260802_0055
"""

from __future__ import annotations

from alembic import op

revision = "20260802_0056"
down_revision = "20260802_0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE platform.runtime_workers (
          worker_id text PRIMARY KEY,
          provider_key text NOT NULL,
          release_id text,
          status text NOT NULL DEFAULT 'online'
            CHECK (status IN ('online', 'degraded', 'draining')),
          started_at timestamptz NOT NULL DEFAULT now(),
          last_seen_at timestamptz NOT NULL DEFAULT now(),
          last_poll_at timestamptz,
          last_claim_at timestamptz,
          last_success_at timestamptz,
          last_error text,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_runtime_workers_freshness
          ON platform.runtime_workers(last_seen_at DESC);
        GRANT SELECT, INSERT, UPDATE ON platform.runtime_workers TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS platform.runtime_workers")
