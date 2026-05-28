import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from core.config import settings


class TokenService:
    """JWT token generation/validation and bcrypt hashing for buyer portal."""

    def create_invitation_token(
        self, customer_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> str:
        """Create 7-day invitation JWT with type='invitation'."""
        payload = {
            "sub": str(customer_id),
            "mayorista_id": str(mayorista_id),
            "type": "invitation",
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        }
        return jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

    def create_magic_link_token(
        self, customer_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> str:
        """Create 15-minute magic-link JWT with type='magic_link'."""
        payload = {
            "sub": str(customer_id),
            "mayorista_id": str(mayorista_id),
            "type": "magic_link",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        }
        return jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

    def create_buyer_session(
        self, customer_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> str:
        """Create 7-day buyer session JWT with type='buyer_session'."""
        payload = {
            "sub": str(customer_id),
            "mayorista_id": str(mayorista_id),
            "type": "buyer_session",
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        }
        return jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

    def decode_token(self, token: str) -> dict | None:
        """Decode and validate JWT. Returns payload or None if invalid."""
        try:
            return jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
        except Exception:
            return None

    def hash_token(self, token: str) -> str:
        """Hash token with bcrypt.

        Since bcrypt has a 72-byte limit, we first hash the token with SHA-256
        to get a fixed-length hex string, then hash that with bcrypt.
        """
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return bcrypt.hashpw(token_hash.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_token_hash(self, token: str, hash: str) -> bool:
        """Verify token matches hash."""
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return bcrypt.checkpw(token_hash.encode("utf-8"), hash.encode("utf-8"))
