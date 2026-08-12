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


def test_alembic_upgrade_head_creates_project_tables_with_fks() -> None:
    """Upgrade creates projects/targets/authorization_records with FKs."""
    command.upgrade(Config("alembic.ini"), "head")

    async def verify() -> None:
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as connection:
                for table in (
                    "projects",
                    "targets",
                    "authorization_records",
                ):
                    exists = (
                        await connection.execute(
                            text(f"SELECT to_regclass('public.{table}')")
                        )
                    ).scalar()
                    assert exists == table, f"{table} was not created"

                expected_fks = {
                    "projects": "FOREIGN KEY (owner_id) REFERENCES users(id)",
                    "targets": (
                        "FOREIGN KEY (project_id) REFERENCES projects(id)"
                    ),
                    "authorization_records": (
                        "FOREIGN KEY (project_id) REFERENCES projects(id)"
                    ),
                }
                for table, expected in expected_fks.items():
                    rows = (
                        await connection.execute(
                            text(
                                "SELECT pg_get_constraintdef(oid) "
                                "FROM pg_constraint "
                                "WHERE conrelid = CAST(:table AS regclass) "
                                "AND contype = 'f'"
                            ),
                            {"table": table},
                        )
                    ).all()
                    definitions = [row[0] for row in rows]
                    assert any(
                        expected in definition
                        for definition in definitions
                    ), (
                        f"{table} missing FK {expected}; "
                        f"found {definitions}"
                    )
        finally:
            await engine.dispose()

    _run(verify())
