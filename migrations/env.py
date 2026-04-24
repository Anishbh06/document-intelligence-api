"""Alembic env.py — configured for async SQLAlchemy + pgvector.

Migrations run synchronously via a psycopg2 connection (standard for Alembic).
The async engine is used by the application at runtime; migrations use the
equivalent sync URL so we don't need anyio/asyncio inside env.py.
"""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── import all models so Alembic can detect schema changes ───────────────────
from app.db.session import Base  # noqa: F401
import app.models.document  # noqa: F401
import app.models.job       # noqa: F401
import app.models.user      # noqa: F401

# Alembic Config object (gives access to the .ini file values)
config = context.config

# Override sqlalchemy.url from the environment at runtime.
raw_url = os.environ.get("DATABASE_URL", "")
# Alembic needs a sync driver; swap asyncpg → psycopg2
sync_url = raw_url.replace("postgresql+asyncpg://", "postgresql://")
if sync_url:
    config.set_main_option("sqlalchemy.url", sync_url)

# Wire up Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
