"""Add tenant-isolated layered conversation memory and resolution caches.

Revision ID: 20260728_0019
Revises: 20260728_0018
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op

revision = "20260728_0019"
down_revision = "20260728_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE secretariat.conversation_distillations (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          conversation_id uuid NOT NULL,
          owner_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          source_sequence_start bigint NOT NULL CHECK (source_sequence_start > 0),
          source_sequence_end bigint NOT NULL
            CHECK (source_sequence_end >= source_sequence_start),
          source_hash char(64) NOT NULL
            CHECK (source_hash ~ '^[0-9a-f]{64}$'),
          distillation_level integer NOT NULL DEFAULT 2
            CHECK (distillation_level BETWEEN 0 AND 9),
          summary text NOT NULL CHECK (length(trim(summary)) > 0),
          entities jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(entities) = 'array'),
          facts jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(facts) = 'array'),
          relations jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(relations) = 'array'),
          inferences jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(inferences) = 'array'),
          uncertainties jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(uncertainties) = 'array'),
          open_questions jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(open_questions) = 'array'),
          model text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (
            tenant_id, conversation_id, source_sequence_end,
            distillation_level, source_hash
          ),
          FOREIGN KEY (tenant_id, conversation_id)
            REFERENCES secretariat.conversations(tenant_id, id)
            ON DELETE CASCADE
        );

        CREATE INDEX idx_conversation_distillations_recent
          ON secretariat.conversation_distillations(
            tenant_id, owner_user_id, conversation_id,
            source_sequence_end DESC, distillation_level DESC
          );

        CREATE TABLE secretariat.memory_units (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          owner_user_id uuid REFERENCES iam.users(id) ON DELETE RESTRICT,
          conversation_id uuid,
          kind text NOT NULL CHECK (
            kind IN (
              'semantic', 'episodic', 'procedural', 'preference',
              'entity', 'inference', 'uncertainty'
            )
          ),
          scope text NOT NULL DEFAULT 'private'
            CHECK (scope IN ('private', 'company')),
          content text NOT NULL CHECK (length(trim(content)) BETWEEN 1 AND 100000),
          content_sha256 char(64) NOT NULL
            CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
          confidence double precision NOT NULL DEFAULT 0.5
            CHECK (confidence BETWEEN 0 AND 1),
          salience double precision NOT NULL DEFAULT 0.5
            CHECK (salience BETWEEN 0 AND 1),
          status text NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'superseded', 'forgotten')),
          source_sequence_start bigint,
          source_sequence_end bigint,
          evidence jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(evidence) = 'array'),
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(metadata) = 'object'),
          embedding vector(1536),
          embedding_model text,
          embedded_at timestamptz,
          valid_from timestamptz NOT NULL DEFAULT now(),
          valid_to timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          CHECK (
            (scope = 'private' AND owner_user_id IS NOT NULL)
            OR scope = 'company'
          ),
          CHECK (
            source_sequence_start IS NULL
            OR source_sequence_end IS NULL
            OR source_sequence_end >= source_sequence_start
          ),
          FOREIGN KEY (tenant_id, conversation_id)
            REFERENCES secretariat.conversations(tenant_id, id)
            ON DELETE SET NULL
        );

        CREATE UNIQUE INDEX idx_memory_units_deduplicate
          ON secretariat.memory_units(
            tenant_id,
            COALESCE(owner_user_id, '00000000-0000-0000-0000-000000000000'::uuid),
            scope, kind, content_sha256
          );
        CREATE INDEX idx_memory_units_resolution
          ON secretariat.memory_units(
            tenant_id, owner_user_id, scope, status,
            salience DESC, confidence DESC, updated_at DESC
          );
        CREATE INDEX idx_memory_units_conversation
          ON secretariat.memory_units(
            tenant_id, conversation_id, status, updated_at DESC
          );
        CREATE INDEX idx_memory_units_embedding
          ON secretariat.memory_units USING hnsw (embedding vector_cosine_ops)
          WITH (m = 16, ef_construction = 64)
          WHERE embedding IS NOT NULL AND status = 'active';

        CREATE TABLE secretariat.memory_relations (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          subject_memory_id uuid NOT NULL,
          object_memory_id uuid NOT NULL,
          relation_type text NOT NULL CHECK (
            relation_type IN (
              'supports', 'contradicts', 'supersedes',
              'derived_from', 'related_to'
            )
          ),
          confidence double precision NOT NULL DEFAULT 0.5
            CHECK (confidence BETWEEN 0 AND 1),
          evidence jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(evidence) = 'array'),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (
            tenant_id, subject_memory_id, object_memory_id, relation_type
          ),
          CHECK (subject_memory_id <> object_memory_id),
          FOREIGN KEY (tenant_id, subject_memory_id)
            REFERENCES secretariat.memory_units(tenant_id, id)
            ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, object_memory_id)
            REFERENCES secretariat.memory_units(tenant_id, id)
            ON DELETE CASCADE
        );
        CREATE INDEX idx_memory_relations_subject
          ON secretariat.memory_relations(
            tenant_id, subject_memory_id, relation_type
          );
        CREATE INDEX idx_memory_relations_object
          ON secretariat.memory_relations(
            tenant_id, object_memory_id, relation_type
          );

        CREATE TABLE secretariat.memory_jobs (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          owner_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          conversation_id uuid NOT NULL,
          job_type text NOT NULL DEFAULT 'conversation_distill'
            CHECK (job_type IN ('conversation_distill', 'memory_reconcile')),
          status text NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'running', 'completed', 'failed')),
          requested_level integer NOT NULL DEFAULT 2
            CHECK (requested_level BETWEEN 1 AND 9),
          source_cursor bigint NOT NULL DEFAULT 0 CHECK (source_cursor >= 0),
          attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
          available_at timestamptz NOT NULL DEFAULT now(),
          lease_until timestamptz,
          last_error text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, conversation_id)
            REFERENCES secretariat.conversations(tenant_id, id)
            ON DELETE CASCADE
        );
        CREATE UNIQUE INDEX idx_memory_jobs_coalesce
          ON secretariat.memory_jobs(tenant_id, conversation_id, job_type)
          WHERE status IN ('pending', 'running');
        CREATE INDEX idx_memory_jobs_queue
          ON secretariat.memory_jobs(
            tenant_id, owner_user_id, status, available_at, created_at
          );

        CREATE TABLE secretariat.context_snapshots (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          owner_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          conversation_id uuid NOT NULL,
          query_hash char(64) NOT NULL
            CHECK (query_hash ~ '^[0-9a-f]{64}$'),
          source_cursor char(64) NOT NULL
            CHECK (source_cursor ~ '^[0-9a-f]{64}$'),
          memory_depth text NOT NULL
            CHECK (memory_depth IN ('index', 'focused', 'deep')),
          distillation_level integer NOT NULL DEFAULT 1
            CHECK (distillation_level BETWEEN 0 AND 9),
          payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          expires_at timestamptz,
          UNIQUE (
            tenant_id, owner_user_id, conversation_id,
            query_hash, source_cursor, memory_depth
          ),
          FOREIGN KEY (tenant_id, conversation_id)
            REFERENCES secretariat.conversations(tenant_id, id)
            ON DELETE CASCADE
        );
        CREATE INDEX idx_context_snapshots_lookup
          ON secretariat.context_snapshots(
            tenant_id, owner_user_id, conversation_id,
            query_hash, source_cursor, memory_depth, created_at DESC
          );

        CREATE TRIGGER trg_conversation_distillations_updated
          BEFORE UPDATE ON secretariat.conversation_distillations
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_memory_units_updated
          BEFORE UPDATE ON secretariat.memory_units
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_memory_jobs_updated
          BEFORE UPDATE ON secretariat.memory_jobs
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        ALTER TABLE secretariat.conversation_distillations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE secretariat.conversation_distillations FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation
          ON secretariat.conversation_distillations
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        ALTER TABLE secretariat.memory_units ENABLE ROW LEVEL SECURITY;
        ALTER TABLE secretariat.memory_units FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON secretariat.memory_units
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        ALTER TABLE secretariat.memory_relations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE secretariat.memory_relations FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON secretariat.memory_relations
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        ALTER TABLE secretariat.memory_jobs ENABLE ROW LEVEL SECURITY;
        ALTER TABLE secretariat.memory_jobs FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON secretariat.memory_jobs
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        ALTER TABLE secretariat.context_snapshots ENABLE ROW LEVEL SECURITY;
        ALTER TABLE secretariat.context_snapshots FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON secretariat.context_snapshots
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT SELECT, INSERT, UPDATE, DELETE
          ON secretariat.conversation_distillations,
             secretariat.memory_units,
             secretariat.memory_relations,
             secretariat.memory_jobs,
             secretariat.context_snapshots
          TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS secretariat.context_snapshots;
        DROP TABLE IF EXISTS secretariat.memory_jobs;
        DROP TABLE IF EXISTS secretariat.memory_relations;
        DROP TABLE IF EXISTS secretariat.memory_units;
        DROP TABLE IF EXISTS secretariat.conversation_distillations;
        """
    )
