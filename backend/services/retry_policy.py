from core.config import settings


class RetryPolicy:
    """Manages retry configuration and exponential backoff calculation."""

    def __init__(
        self,
        max_retries: int | None = None,
        base_delay: int | None = None,
        max_delay: int | None = None,
    ) -> None:
        self.max_retries = max_retries or settings.VTON_MAX_RETRIES
        self.base_delay = base_delay or settings.VTON_RETRY_BASE_DELAY_SECONDS
        self.max_delay = max_delay or settings.VTON_RETRY_MAX_DELAY_SECONDS

    def get_delay(self, retry_count: int) -> int:
        """Calculate exponential backoff delay for a given retry attempt.

        Formula: delay = min(base_delay * 2^retry_count, max_delay)
        """
        delay = self.base_delay * (2 ** retry_count)
        return min(delay, self.max_delay)

    def should_retry(self, retry_count: int) -> bool:
        """Determine if another retry attempt is allowed."""
        return retry_count < self.max_retries


def is_retriable_error(exc: Exception) -> bool:
    """Determine if an error should trigger a retry.

    Retriable errors:
    - TimeoutError, asyncio.TimeoutError
    - ConnectionError, httpx.ConnectError
    - Replicate 429 (rate limit)
    - Replicate 5xx (server error)
    - httpx.HTTPStatusError with status >= 500 or == 429

    Non-retriable errors:
    - Replicate 4xx (except 429)
    - httpx.HTTPStatusError with 4xx status (except 429)
    - ValueError with specific messages (bad input)
    """
    import asyncio

    # Timeout errors → retriable
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return True

    # Connection errors → retriable
    if isinstance(exc, (ConnectionError, OSError)):
        return True

    # Try to import httpx for HTTP error classification
    try:
        import httpx

        if isinstance(exc, httpx.ConnectError):
            return True

        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            if status == 429:
                return True
            if status >= 500:
                return True
            return False  # 4xx (except 429) → not retriable
    except ImportError:
        pass

    # Try to import replicate for ReplicateError classification
    try:
        from replicate.exceptions import ReplicateError

        if isinstance(exc, ReplicateError):
            status = getattr(exc, "status", None)
            if status == 429:
                return True
            if status is not None and status >= 500:
                return True
            if status is not None and status >= 400:
                return False  # 4xx (except 429) → not retriable
    except ImportError:
        pass

    # ValueError with bad input → not retriable
    if isinstance(exc, ValueError):
        error_msg = str(exc).lower()
        if any(
            keyword in error_msg
            for keyword in ["not found", "invalid", "bad input", "unauthorized"]
        ):
            return False

    # Default: retriable (safe fallback for unknown errors)
    return True
