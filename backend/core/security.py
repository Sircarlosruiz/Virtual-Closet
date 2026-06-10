import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(mayorista_id: str, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)

    to_encode = {"sub": mayorista_id, "exp": expire}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        return None


def create_challenge_token(user_id: str) -> str:
    """Create a short-lived challenge token after successful credential validation.

    The challenge_token proves the user passed email+password validation.
    It must be presented to the 2FA endpoint to receive a full JWT session.
    TTL: 5 minutes.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    to_encode = {
        "sub": user_id,
        "step": "credentials_passed",
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_challenge_token(token: str) -> dict | None:
    """Decode and validate a challenge token.

    Returns the payload if valid, None otherwise.
    Validates that the 'step' claim is 'credentials_passed'.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("step") != "credentials_passed":
            return None
        return payload
    except Exception:
        return None


def generate_verification_token() -> str:
    """Generate a 32-byte random hex token for email verification."""
    return secrets.token_hex(32)


def generate_unlock_token() -> str:
    """Generate a 32-byte random hex token for account unlock."""
    return secrets.token_hex(32)
