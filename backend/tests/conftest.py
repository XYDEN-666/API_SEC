"""Shared test fixtures."""

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.core.db as db_module
from app.core.config import settings
from app.main import create_app
from tests.scanner_harness import (  # noqa: F401 - fixture registration
    http_target,
    http_target_factory,
    http_idor_target,
    http_multi_endpoint_target,
    http_sqli_target,
)
from tests.helpers import cleanup_test_users


def _unique_email() -> str:
    return f"test-{uuid.uuid4().hex}@example.com"


@pytest.fixture(autouse=True)
def _null_pool_engine(monkeypatch):
    """Give every test a fresh NullPool engine so pooled connections never
    leak across event loops (TestClient opens a new loop per test)."""
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    test_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "async_session_factory", test_factory)
    yield
    asyncio.run(test_engine.dispose())


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client
    cleanup_test_users()


@pytest.fixture
def unique_email() -> str:
    return _unique_email()
