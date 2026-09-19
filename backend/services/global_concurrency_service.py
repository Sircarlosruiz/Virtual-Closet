"""Deployment-wide cap on in-flight image-generation provider calls (ADR-065)."""

import logging
from uuid import UUID

from core.config import settings
from core.redis_client import get_redis

logger = logging.getLogger(__name__)

IN_FLIGHT_KEY = "imggen:global_in_flight"
SLOT_KEY_PREFIX = "imggen:slot:"

_ACQUIRE_SCRIPT = """
local members = redis.call('SMEMBERS', KEYS[1])
for _, member in ipairs(members) do
  if redis.call('EXISTS', 'imggen:slot:' .. member) == 0 then
    redis.call('SREM', KEYS[1], member)
  end
end
if redis.call('SISMEMBER', KEYS[1], ARGV[1]) == 1 then
  redis.call('SET', KEYS[2], '1', 'EX', ARGV[3])
  return 1
end
if redis.call('SCARD', KEYS[1]) < tonumber(ARGV[2]) then
  redis.call('SADD', KEYS[1], ARGV[1])
  redis.call('SET', KEYS[2], '1', 'EX', ARGV[3])
  return 1
end
return 0
"""


class RedisUnavailableError(Exception):
    """Raised when the global cap cannot be evaluated (fail closed)."""


_UNSET = object()


class GlobalConcurrencyService:
    """Non-blocking Redis SET semaphore. Denied acquire means reschedule, not fail."""

    def __init__(
        self,
        redis=_UNSET,
        cap: int | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        self._redis = redis
        self._cap = cap if cap is not None else settings.IMAGE_GENERATION_GLOBAL_CONCURRENCY
        default_ttl = (
            settings.IMAGE_GENERATION_REPLICATE_TIMEOUT_SECONDS
            + settings.IMAGE_GENERATION_CELERY_TIME_LIMIT_BUFFER_SECONDS
        )
        self._ttl_seconds = ttl_seconds if ttl_seconds is not None else default_ttl

    async def try_acquire(self, job_id: UUID) -> bool:
        redis = await self._client()
        job_key = str(job_id)
        ttl_key = f"{SLOT_KEY_PREFIX}{job_key}"
        try:
            result = await redis.eval(
                _ACQUIRE_SCRIPT,
                2,
                IN_FLIGHT_KEY,
                ttl_key,
                job_key,
                self._cap,
                self._ttl_seconds,
            )
        except Exception as exc:
            logger.error("Global concurrency acquire failed for job %s", job_id)
            raise RedisUnavailableError("Redis unavailable for global concurrency cap") from exc
        return int(result) == 1

    async def release(self, job_id: UUID) -> None:
        redis = await self._client()
        job_key = str(job_id)
        try:
            await redis.srem(IN_FLIGHT_KEY, job_key)
            await redis.delete(f"{SLOT_KEY_PREFIX}{job_key}")
        except Exception as exc:
            logger.warning("Global concurrency release failed for job %s: %s", job_id, exc)

    async def in_flight_count(self) -> int:
        redis = await self._client()
        return int(await redis.scard(IN_FLIGHT_KEY))

    async def _client(self):
        if self._redis is not _UNSET:
            if self._redis is None:
                raise RedisUnavailableError("Redis unavailable for global concurrency cap")
            return self._redis
        redis = await get_redis()
        if redis is None:
            raise RedisUnavailableError("Redis unavailable for global concurrency cap")
        return redis
