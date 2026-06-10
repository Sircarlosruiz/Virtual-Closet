"""Redis client for session denylist and ephemeral data."""

import logging

import redis.asyncio as redis

from core.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton, initialized on first use
_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get or create the Redis connection.

    Returns a shared async Redis client.
    If Redis is unavailable, logs a warning and returns None.
    """
    global _client
    if _client is None:
        try:
            _client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await _client.ping()
            logger.info("Redis connected at %s", settings.REDIS_URL)
        except redis.ConnectionError:
            logger.warning(
                "Redis unavailable at %s — session denylist will be skipped",
                settings.REDIS_URL,
            )
            return None
    return _client


async def close_redis() -> None:
    """Close the Redis connection."""
    global _client
    if _client:
        await _client.close()
        _client = None
