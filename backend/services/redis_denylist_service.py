"""Redis denylist service for refresh token revocation.

Provides atomic operations for adding JTIs to the denylist and checking
revocation status. Implements fail-closed behavior on Redis outage (ADR-027).
"""

import logging

from core.redis_client import get_redis

logger = logging.getLogger(__name__)


class RedisUnavailableError(Exception):
    """Raised when Redis is unavailable for a critical denylist operation."""


class RedisDenylistService:
    """Manages the Redis denylist for revoked refresh token JTIs."""

    @staticmethod
    async def add(jti: str, ttl_seconds: int) -> bool:
        """Add a JTI to the denylist with the given TTL.

        Uses SETNX to ensure atomic addition (prevents race conditions).
        Returns True if the JTI was newly added, False if already present.
        """
        redis = await get_redis()
        if redis is None:
            logger.error("Redis unavailable — cannot add JTI to denylist")
            return False

        key = f"denylist:{jti}"
        result = await redis.set(key, "1", nx=True, ex=ttl_seconds)
        return result is True

    @staticmethod
    async def is_denied(jti: str) -> bool:
        """Check if a JTI is in the denylist.

        Returns True if denied, False if not found.
        If Redis is unavailable, returns False (caller should handle fail-closed).
        """
        redis = await get_redis()
        if redis is None:
            logger.warning("Redis unavailable — denylist check skipped")
            return False

        key = f"denylist:{jti}"
        return await redis.exists(key)

    @staticmethod
    async def check_and_fail_closed(jti: str) -> bool:
        """Check denylist with fail-closed behavior.

        Returns True if the JTI is denied.
        Raises RedisUnavailableError if Redis is unavailable.

        Use this method for critical operations where allowing a
        potentially revoked token is unacceptable (ADR-027).
        """
        redis = await get_redis()
        if redis is None:
            raise RedisUnavailableError(
                "Redis denylist unavailable — cannot validate token revocation"
            )

        key = f"denylist:{jti}"
        return await redis.exists(key)

    @staticmethod
    async def add_batch(jti_list: list[str], ttl_seconds: int) -> int:
        """Add multiple JTIs to the denylist in a single pipeline.

        Returns the count of JTIs successfully added.
        """
        redis = await get_redis()
        if redis is None:
            logger.error("Redis unavailable — cannot add JTIs to denylist")
            return 0

        pipe = redis.pipeline()
        for jti in jti_list:
            key = f"denylist:{jti}"
            pipe.set(key, "1", nx=True, ex=ttl_seconds)

        results = await pipe.execute()
        return sum(1 for r in results if r is True)
