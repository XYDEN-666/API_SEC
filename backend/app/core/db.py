"""Async SQLAlchemy engine, session factory, and FastAPI dependency."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        yield session


async def ping_database() -> None:
    """Raise if PostgreSQL is unreachable; otherwise do nothing."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def close_database() -> None:
    """Dispose of the connection pool on shutdown."""
    await engine.dispose()
