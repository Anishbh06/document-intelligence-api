"""
Database initialisation — Alembic-first.

In production/staging Alembic migrations run at container start-up via
  `alembic upgrade head`
which is the command in docker-compose.yml for the `api` service.

This file now only enables the pgvector extension (which Alembic also handles
in the first migration, but idempotent is safe) and is kept as a lifespan hook
for any future startup checks.
"""
from sqlalchemy import text
from app.db.session import engine


async def init_db() -> None:
    """Ensure the pgvector extension exists. Schema is managed by Alembic."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
