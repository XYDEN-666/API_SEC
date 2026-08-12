"""Shared test helpers for direct database access."""

import asyncio

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models import Project, User


def cleanup_test_users() -> None:
    """Delete every row whose email starts with 'test-'."""

    async def _run() -> None:
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.begin() as connection:
                # Projects first (and their cascading targets/authorization
                # records), so user deletion never trips the owner FK.
                await connection.execute(
                    delete(Project).where(
                        Project.owner_id.in_(
                            select(User.id).where(User.email.like("test-%"))
                        )
                    )
                )
                await connection.execute(
                    delete(User).where(User.email.like("test-%"))
                )
        finally:
            await engine.dispose()

    asyncio.run(_run())


def create_user(email: str, password: str, role: str = "user") -> int:
    """Insert a user directly (bypassing the API) and return its id."""

    async def _run() -> int:
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.begin() as connection:
                result = await connection.execute(
                    insert(User)
                    .values(
                        email=email,
                        hashed_password=hash_password(password),
                        role=role,
                    )
                    .returning(User.id)
                )
                return result.scalar_one()
        finally:
            await engine.dispose()

    return asyncio.run(_run())
