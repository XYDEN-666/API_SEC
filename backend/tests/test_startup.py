"""Startup/lifespan tests: DB + Redis connectivity, happy and failure paths."""

import pytest
import redis.asyncio as aioredis
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

import app.core.cache as cache_module
import app.core.db as db_module
from app.main import create_app


def test_startup_succeeds_with_reachable_services() -> None:
    """Lifespan connects to real PostgreSQL and Redis, then serves /health."""
    with TestClient(create_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_startup_fails_fast_when_database_unreachable(monkeypatch) -> None:
    """Startup raises a clear error when PostgreSQL is unreachable."""
    bad_engine = create_async_engine(
        "postgresql+asyncpg://apishield:apishield@127.0.0.1:1/apishield",
        pool_pre_ping=False,
    )
    monkeypatch.setattr(db_module, "engine", bad_engine)

    with pytest.raises(RuntimeError, match="PostgreSQL unreachable"):
        with TestClient(create_app()):
            pass


def test_startup_fails_fast_when_redis_unreachable(monkeypatch) -> None:
    """Startup raises a clear error when Redis is unreachable."""
    bad_client = aioredis.from_url("redis://127.0.0.1:1/0")
    monkeypatch.setattr(cache_module, "redis_client", bad_client)

    with pytest.raises(RuntimeError, match="Redis unreachable"):
        with TestClient(create_app()):
            pass
