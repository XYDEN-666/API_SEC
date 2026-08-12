"""Alembic migration acceptance tests."""

import asyncio

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


def _run(coro):
    return asyncio.run(coro)


def test_alembic_upgrade_head_creates_users_table() -> None:
    """Running ``alembic upgrade head`` creates the users table."""
    config = Config("alembic.ini")
    command.upgrade(config, "head")

    async def verify() -> None:
        # Use a dedicated engine so pooled connections never leak across
        # test event loops.
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as connection:
                table = (
                    await connection.execute(
                        text("SELECT to_regclass('public.users')")
                    )
                ).scalar()
                assert table == "users"

                rows = (
                    await connection.execute(
                        text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_name = 'users' ORDER BY ordinal_position"
                        )
                    )
                ).all()
                columns = [row[0] for row in rows]
                assert columns == [
                    "id",
                    "email",
                    "hashed_password",
                    "role",
                    "created_at",
                ]
        finally:
            await engine.dispose()

    _run(verify())
