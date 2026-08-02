"""Persist tenant-isolated AI secretary conversations and messages.

Revision ID: 20260728_0018
Revises: 20260728_0017
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op

revision = "20260728_0018"
down_revision = "20260728_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE secretariat.conversations
          ADD COLUMN status text NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'archived')),
          ADD COLUMN last_message_at timestamptz,
          ADD COLUMN archived_at timestamptz,
          ADD COLUMN summary text,
          ADD COLUMN metadata jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(metadata) = 'object');

        UPDATE secretariat.conversations
        SET last_message_at = COALESCE(updated_at, created_at)
        WHERE last_message_at IS NULL;

        CREATE INDEX idx_secretariat_conversations_owner_recent
          ON secretariat.conversations(
            tenant_id, owner_user_id, status,
            last_message_at DESC NULLS LAST, updated_at DESC
          );

        CREATE TABLE secretariat.messages (
          id uuid PRIMARY KEY,
          sequence bigint GENERATED ALWAYS AS IDENTITY,
          tenant_id uuid NOT NULL,
          conversation_id uuid NOT NULL,
          turn_id text
            CHECK (turn_id IS NULL OR length(turn_id) BETWEEN 1 AND 128),
          role text NOT NULL
            CHECK (role IN ('user', 'assistant', 'system', 'tool')),
          content text NOT NULL
            CHECK (length(trim(content)) BETWEEN 1 AND 100000),
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(metadata) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (sequence),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, conversation_id, turn_id, role),
          FOREIGN KEY (tenant_id, conversation_id)
            REFERENCES secretariat.conversations(tenant_id, id)
            ON DELETE CASCADE
        );

        CREATE INDEX idx_secretariat_messages_conversation
          ON secretariat.messages(tenant_id, conversation_id, sequence DESC);

        ALTER TABLE secretariat.messages ENABLE ROW LEVEL SECURITY;
        ALTER TABLE secretariat.messages FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON secretariat.messages
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        CREATE OR REPLACE FUNCTION secretariat.reject_message_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION 'secretariat messages are append-only';
        END;
        $$;

        CREATE TRIGGER trg_secretariat_messages_append_only
          BEFORE UPDATE OR DELETE ON secretariat.messages
          FOR EACH ROW EXECUTE FUNCTION secretariat.reject_message_mutation();

        GRANT SELECT, INSERT ON secretariat.messages TO warehouse_os;
        GRANT USAGE, SELECT ON SEQUENCE secretariat.messages_sequence_seq
          TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_secretariat_messages_append_only
          ON secretariat.messages;
        DROP TABLE IF EXISTS secretariat.messages;
        DROP FUNCTION IF EXISTS secretariat.reject_message_mutation();
        DROP INDEX IF EXISTS secretariat.idx_secretariat_conversations_owner_recent;
        ALTER TABLE secretariat.conversations
          DROP COLUMN IF EXISTS metadata,
          DROP COLUMN IF EXISTS summary,
          DROP COLUMN IF EXISTS archived_at,
          DROP COLUMN IF EXISTS last_message_at,
          DROP COLUMN IF EXISTS status;
        """
    )
