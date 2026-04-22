from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


from sqlalchemy.pool import NullPool
import sys

engine_kwargs = {"echo": settings.APP_ENV == "development"}
if "pytest" in sys.modules:
    engine_kwargs["poolclass"] = NullPool
if "render.com" in settings.DATABASE_URL:
    engine_kwargs["connect_args"] = {"ssl": "require"}

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise