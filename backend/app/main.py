"""Application entrypoint and factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.core.cache import close_redis, ping_redis
from app.core.config import settings
from app.core.db import close_database, ping_database
from app.routers.auth import router as auth_router
from app.routers.authorization_records import router as authorization_records_router
from app.routers.credentials import router as credentials_router
from app.routers.dashboard import router as dashboard_router
from app.routers.findings import router as findings_router
from app.routers.projects import router as projects_router
from app.routers.reports import router as reports_router
from app.routers.scans import router as scans_router
from app.routers.targets import router as targets_router
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(authorization_records_router)
    app.include_router(credentials_router)
    app.include_router(dashboard_router)
    app.include_router(findings_router)
    app.include_router(projects_router)
    app.include_router(reports_router)
    app.include_router(scans_router)
    app.include_router(targets_router)
    app.include_router(users_router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
