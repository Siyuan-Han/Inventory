from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings


class Base(DeclarativeBase):
    pass


# Supabase's pooler does not support prepared statement caching, so it is
# disabled here to keep both the direct and pooled connection strings working.
# A sqlite+aiosqlite URL is accepted too, for offline development.
_connect_args = (
    {"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    if settings.database_url.startswith("postgresql")
    else {}
)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create any missing tables. Existing tables are left untouched."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
