"""Add owner_id to documents — per-user document isolation.

Each document now belongs to the user who uploaded it.
Different users may upload identical files; they each get their own row.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-22
"""
from alembic import op
from sqlalchemy import text

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Add owner_id column (nullable so existing rows are preserved)
    conn.execute(text(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS owner_id INTEGER "
        "REFERENCES users(id) ON DELETE SET NULL"
    ))

    # 2. Add index for fast per-user queries
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_documents_owner_id ON documents (owner_id)"
    ))

    # 3. Drop the global UNIQUE constraint on content_hash so multiple users
    #    can independently own the same file content.
    #    We first check whether the constraint exists before trying to drop it.
    conn.execute(text("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'documents'
                  AND indexname = 'ix_documents_content_hash'
            ) THEN
                -- Only drop if it's a unique index
                IF EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = 'documents'
                      AND indexname = 'ix_documents_content_hash'
                      AND indexdef LIKE '%UNIQUE%'
                ) THEN
                    DROP INDEX ix_documents_content_hash;
                    CREATE INDEX ix_documents_content_hash ON documents (content_hash);
                END IF;
            END IF;
        END
        $$;
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DROP INDEX IF EXISTS ix_documents_owner_id"))
    conn.execute(text("ALTER TABLE documents DROP COLUMN IF EXISTS owner_id"))
    # Restore unique index (may fail if duplicates exist — acceptable in downgrade)
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_documents_content_hash ON documents (content_hash)"
    ))
