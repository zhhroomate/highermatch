"""
Redis client helpers for the user service.
"""

import logging
import os
from typing import Optional

import redis.asyncio as redis


logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    """Return a shared Redis client or None when Redis is unavailable."""
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        client = redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        await client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable for user-service auth: %s", exc)
        return None


async def close_redis() -> None:
    """Close the shared Redis client."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
