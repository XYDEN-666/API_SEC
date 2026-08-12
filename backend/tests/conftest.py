"""Shared test fixtures."""

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.main import create_app
from app.models import User


def _unique_email() -> str:
    return f"test-{uuid.uuid4().hex}@example.com"


async def _delete_test_users() -> None:
    """Remove rows created by tests, using a dedicated engine to avoid
    leaking connections across test event loops."""
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                delete(User).where(User.email.like("test-%"))
            )
    finally:
        await engine.dispose()


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client
    asyncio.run(_delete_test_users())


@pytest.fixture
def unique_email() -> str:
    return _unique_email()
