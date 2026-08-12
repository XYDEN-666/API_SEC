"""Redis connection for the application."""

import redis.asyncio as aioredis

from app.core.config import settings

redis_client = aioredis.from_url(
    settings.redis_url,
    decode_responses=True,
)


async def ping_redis() -> None:
    """Raise if Redis is unreachable; otherwise do nothing."""
    await redis_client.ping()


async def close_redis() -> None:
    """Close the Redis connection pool on shutdown."""
    await redis_client.aclose()
