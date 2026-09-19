from dataclasses import dataclass

MAX_TRANSIENT_RETRIES = 2
DEFAULT_RETRY_DELAY_SECONDS = 5


@dataclass(frozen=True)
class ErrorClassification:
    code: str
    category: str  # "transient" | "terminal"
    retryable: bool


@dataclass(frozen=True)
class RetryDecision:
    should_retry: bool
    delay_seconds: int
    next_attempt_number: int


class RetryPolicyService:
    """Classifies provider outcomes and decides whether to auto-retry.

    Timeouts are intentionally excluded from auto-retry (ADR-049): the
    outcome is unknown, and a blind retry risks duplicating a provider call
    that may have already completed. Only staff-initiated retry can recover
    from a timeout.
    """

    def classify_http_error(self, status_code: int) -> ErrorClassification:
        if status_code == 429:
            return ErrorClassification(
                code="PROVIDER_RATE_LIMITED", category="transient", retryable=True
            )
        return ErrorClassification(code="PROVIDER_ERROR", category="terminal", retryable=False)

    def classify_timeout(self) -> ErrorClassification:
        return ErrorClassification(code="PROVIDER_TIMEOUT", category="transient", retryable=False)

    def classify_no_result(self) -> ErrorClassification:
        return ErrorClassification(
            code="PROVIDER_NO_RESULT", category="terminal", retryable=False
        )

    def classify_request_error(self) -> ErrorClassification:
        return ErrorClassification(
            code="PROVIDER_REQUEST_ERROR", category="terminal", retryable=False
        )

    def classify_credential_missing(self) -> ErrorClassification:
        return ErrorClassification(
            code="PROVIDER_CREDENTIAL_MISSING", category="terminal", retryable=False
        )

    def classify_concurrency_wait_exhausted(self) -> ErrorClassification:
        return ErrorClassification(
            code="GLOBAL_CONCURRENCY_WAIT_EXHAUSTED",
            category="terminal",
            retryable=False,
        )

    def decide(
        self,
        classification: ErrorClassification,
        attempt_number: int,
        retry_after_seconds: int | None,
    ) -> RetryDecision:
        is_timeout = classification.code == "PROVIDER_TIMEOUT"
        if is_timeout or classification.category != "transient":
            return RetryDecision(should_retry=False, delay_seconds=0, next_attempt_number=attempt_number)

        if attempt_number > MAX_TRANSIENT_RETRIES:
            return RetryDecision(should_retry=False, delay_seconds=0, next_attempt_number=attempt_number)

        delay = retry_after_seconds if retry_after_seconds is not None else DEFAULT_RETRY_DELAY_SECONDS
        return RetryDecision(
            should_retry=True,
            delay_seconds=max(delay, 0),
            next_attempt_number=attempt_number + 1,
        )
