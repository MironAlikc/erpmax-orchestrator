"""Redis connection utilities"""

import redis.asyncio as redis
from app.core.config import get_settings

settings = get_settings()


async def get_redis() -> redis.Redis:
    """Get Redis connection"""
    client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        decode_responses=False,
        encoding="utf-8",
    )
    try:
        yield client
    finally:
        await client.close()
