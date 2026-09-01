from typing import AsyncGenerator

from sqlalchemy import text
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
    """Create any missing tables, then apply small additive schema patches.

    `create_all` only adds whole tables, so columns added to models.py after
    a table already exists (like `dress.archived_at`) need an explicit patch
    here. Each statement is safe to run every time the app starts.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "postgresql":
            await conn.execute(
                text("ALTER TABLE dress ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP")
            )
            await conn.execute(
                text("ALTER TABLE sale ADD COLUMN IF NOT EXISTS cash_amount NUMERIC(10, 2)")
            )
            await conn.execute(
                text("ALTER TABLE dress_order ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(100)")
            )
            await conn.execute(
                text(
                    "ALTER TABLE dress ADD COLUMN IF NOT EXISTS category VARCHAR(20) "
                    "NOT NULL DEFAULT 'new'"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE dress_order ADD COLUMN IF NOT EXISTS "
                    "shipping_center_received_at TIMESTAMP"
                )
            )
            await conn.execute(
                text("ALTER TABLE sale ADD COLUMN IF NOT EXISTS received_by VARCHAR(20)")
            )
