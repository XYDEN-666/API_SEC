"""Application entrypoint and factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.core.cache import close_redis, ping_redis
from app.core.config import settings
from app.core.db import close_database, ping_database
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router

logger = logging.getLogger("apishield")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Verify infrastructure on startup; fail fast if it is unreachable."""
    try:
        await ping_database()
    except (SQLAlchemyError, OSError) as exc:
        message = f"FATAL: PostgreSQL unreachable at {settings.database_url}: {exc}"
        logger.critical(message)
        raise RuntimeError(message) from exc
    logger.info("PostgreSQL connection OK")

    try:
        await ping_redis()
    except RedisError as exc:
        message = f"FATAL: Redis unreachable at {settings.redis_url}: {exc}"
        logger.critical(message)
        raise RuntimeError(message) from exc
    logger.info("Redis connection OK")

    logger.info("Backend startup complete: PostgreSQL and Redis connected")

    yield

    await close_database()
    await close_redis()
    logger.info("Backend shutdown complete")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.include_router(auth_router)
    app.include_router(users_router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
