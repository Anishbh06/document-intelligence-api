from sqlalchemy import text

from app.models.document import Document, DocumentChunk  # noqa: F401
from app.models.job import Job  # noqa: F401
from app.db.session import engine, Base


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "ALTER TABLE documents "
                "ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)"
            )
        )
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_documents_content_hash "
                "ON documents (content_hash)"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE jobs "
                "ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE jobs "
                "ADD COLUMN IF NOT EXISTS total_chunks INTEGER DEFAULT 0"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE jobs "
                "ADD COLUMN IF NOT EXISTS processed_chunks INTEGER DEFAULT 0"
            )
        )
