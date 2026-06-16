"""SMS OTP service.

Handles sending and verifying SMS one-time passwords via Twilio.
Uses Redis for rate limiting and OTP storage (ADR-023).
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt

from core.config import settings
from core.redis_client import get_redis

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

OTP_LENGTH = 6
OTP_TTL_SECONDS = 300  # 5 minutes
RATE_LIMIT_WINDOW_SECONDS = 600  # 10 minutes
RATE_LIMIT_MAX_SENDS = 3


class SmsRateLimitExceededError(Exception):
    """Raised when SMS OTP rate limit is exceeded."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded; try again in {retry_after} seconds")


class SmsDeliveryError(Exception):
    """Raised when SMS delivery fails via Twilio."""


class SmsOtpService:
    """Domain service for SMS OTP flows."""

    def __init__(self):
        self._twilio_client = None

    async def _get_twilio_client(self):
        """Lazy-initialize Twilio client."""
        if self._twilio_client is None:
            try:
                from twilio.rest import Client

                self._twilio_client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN,
                )
            except ImportError:
                logger.warning("twilio package not installed — SMS OTP will use console mode")
                self._twilio_client = None
        return self._twilio_client

    async def send_otp(self, mayorista_id: UUID, phone_number: str) -> bool:
        """Send a 6-digit OTP via SMS.

        Checks rate limit first. If within limits, generates OTP, stores
        hashed in Redis, and sends via Twilio.

        Raises:
            SmsRateLimitExceededError: If rate limit exceeded.
            SmsDeliveryError: If Twilio delivery fails.
        """
        redis = await get_redis()

        # Check rate limit
        rate_key = f"sms:rate:{mayorista_id}"
        if redis:
            current_count = await redis.get(rate_key)
            if current_count is not None and int(current_count) >= RATE_LIMIT_MAX_SENDS:
                ttl = await redis.ttl(rate_key)
                raise SmsRateLimitExceededError(retry_after=max(ttl, 0))

        # Generate OTP
        otp_code = f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}}"
        otp_hash = bcrypt.hashpw(
            otp_code.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        # Store in Redis with TTL
        otp_key = f"sms:otp:{mayorista_id}"
        if redis:
            await redis.setex(otp_key, OTP_TTL_SECONDS, otp_hash)

        # Send via Twilio
        twilio = await self._get_twilio_client()
        if twilio and hasattr(settings, "TWILIO_ACCOUNT_SID") and settings.TWILIO_ACCOUNT_SID:
            try:
                twilio.messages.create(
                    body=f"Your Virtual Closet verification code is: {otp_code}",
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=phone_number,
                )
            except Exception as e:
                logger.exception("Twilio SMS delivery failed for user %s", mayorista_id)
                raise SmsDeliveryError("SMS could not be sent. Please use a backup code.") from e
        else:
            # Console mode for development
            logger.info(
                "[SMS OTP CONSOLE] Phone: %s, Code: %s",
                phone_number,
                otp_code,
            )

        # Increment rate limit counter
        if redis:
            pipe = redis.pipeline()
            pipe.incr(rate_key)
            pipe.expire(rate_key, RATE_LIMIT_WINDOW_SECONDS)
            await pipe.execute()

        return True

    async def verify_otp(self, mayorista_id: UUID, otp_plaintext: str) -> bool:
        """Verify an SMS OTP code.

        Checks Redis for the stored hash and validates with bcrypt.
        Deletes the OTP on success (single-use).

        Returns True if valid, False otherwise.
        """
        redis = await get_redis()

        if redis is None:
            logger.warning("Redis unavailable — SMS OTP verification skipped")
            return False

        otp_key = f"sms:otp:{mayorista_id}"
        otp_hash = await redis.get(otp_key)

        if otp_hash is None:
            return False

        if bcrypt.checkpw(
            otp_plaintext.encode("utf-8"),
            otp_hash.encode("utf-8"),
        ):
            # Valid — delete (single-use)
            await redis.delete(otp_key)
            return True

        return False

    async def check_rate_limit(self, mayorista_id: UUID) -> dict:
        """Check if user is rate-limited for SMS sends.

        Returns {"allowed": True} or {"allowed": False, "retry_after": N}.
        """
        redis = await get_redis()

        if redis is None:
            return {"allowed": True}

        rate_key = f"sms:rate:{mayorista_id}"
        current_count = await redis.get(rate_key)

        if current_count is not None and int(current_count) >= RATE_LIMIT_MAX_SENDS:
            ttl = await redis.ttl(rate_key)
            return {"allowed": False, "retry_after": max(ttl, 0)}

        return {"allowed": True}
