"""Initial schema — documents, document_chunks, jobs, users.

Idempotent: uses IF NOT EXISTS everywhere so this migration is safe to run
against a database that was previously bootstrapped with SQLAlchemy's
create_all (which is the case for existing deployments).

Revision ID: 0001
Revises: 
Create Date: 2026-04-22
"""
from alembic import op
from sqlalchemy import text

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── pgvector extension ────────────────────────────────────────────────────
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # ── documents ─────────────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS documents (
            id          SERIAL PRIMARY KEY,
            filename    VARCHAR(255) NOT NULL,
            content_hash VARCHAR(64) UNIQUE,
            original_text TEXT NOT NULL,
            created_at  TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """))
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_documents_content_hash "
        "ON documents (content_hash)"
    ))

    # ── document_chunks ───────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id           SERIAL PRIMARY KEY,
            document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index  INTEGER NOT NULL,
            content      TEXT NOT NULL,
            embedding    vector(768),
            created_at   TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """))

    # ── jobs ──────────────────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS jobs (
            id               SERIAL PRIMARY KEY,
            status           VARCHAR(50) NOT NULL DEFAULT 'pending',
            progress         INTEGER NOT NULL DEFAULT 0,
            total_chunks     INTEGER NOT NULL DEFAULT 0,
            processed_chunks INTEGER NOT NULL DEFAULT 0,
            filename         VARCHAR(255) NOT NULL,
            content_hash     VARCHAR(64),
            document_id      INTEGER,
            error_message    TEXT,
            created_at       TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at       TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_jobs_content_hash ON jobs (content_hash)"
    ))

    # Add any columns introduced after initial create_all (idempotent ALTER)
    conn.execute(text(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)"
    ))
    conn.execute(text(
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)"
    ))
    conn.execute(text(
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS total_chunks INTEGER DEFAULT 0"
    ))
    conn.execute(text(
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS processed_chunks INTEGER DEFAULT 0"
    ))

    # ── users (NEW — not in old create_all) ───────────────────────────────────
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id              SERIAL PRIMARY KEY,
            username        VARCHAR(50) NOT NULL UNIQUE,
            email           VARCHAR(255) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """))
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"
    ))
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DROP TABLE IF EXISTS users"))
    conn.execute(text("DROP TABLE IF EXISTS jobs"))
    conn.execute(text("DROP TABLE IF EXISTS document_chunks"))
    conn.execute(text("DROP TABLE IF EXISTS documents"))
    conn.execute(text("DROP EXTENSION IF EXISTS vector"))
