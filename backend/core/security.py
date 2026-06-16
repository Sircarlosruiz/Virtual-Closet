import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from cryptography.fernet import Fernet
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


# ── Fernet Symmetric Encryption (ADR-022) ─────────────────────────────────


def _get_fernet() -> Fernet:
    """Get or create a Fernet instance from the encryption key.

    Raises:
        ValueError: If TWO_FACTOR_ENCRYPTION_KEY is not set.
    """
    if not settings.TWO_FACTOR_ENCRYPTION_KEY:
        raise ValueError(
            "TWO_FACTOR_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    return Fernet(settings.TWO_FACTOR_ENCRYPTION_KEY.encode())


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value using Fernet symmetric encryption.

    Returns the encrypted value as a base64-encoded string.
    """
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted string value.

    Returns the original plaintext string.
    """
    fernet = _get_fernet()
    return fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")


# ── RS256 JWT Signing (ADR-026) ──────────────────────────────────────────


def create_rs256_access_token(
    mayorista_id: str,
    tenant_id: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, str]:
    """Create an RS256-signed access token with full claims.

    Returns (access_token, jti).
    """
    from services.jwks_manager import get_private_key, _load_key_pair

    _, _, kid = _load_key_pair()
    private_key = get_private_key()

    jti = str(uuid.uuid4())

    if expires_delta is None:
        expires_delta = timedelta(minutes=15)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    to_encode = {
        "sub": mayorista_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": expire,
        "jti": jti,
    }

    # Use cryptography library directly for RS256 signing
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    import base64
    import json

    header = {"alg": "RS256", "typ": "JWT", "kid": kid}

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = b64url(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = private_key.sign(
        signing_input,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    signature_b64 = b64url(signature)
    token = f"{header_b64}.{payload_b64}.{signature_b64}"

    return token, jti


def decode_rs256_access_token(token: str) -> dict | None:
    """Decode and verify an RS256-signed access token.

    Returns the payload if valid, None otherwise.
    """
    from services.jwks_manager import get_public_key
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, utils
    import base64
    import json

    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        # Verify signature
        public_key = get_public_key()
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

        def b64url_decode(data: str) -> bytes:
            padding_needed = 4 - (len(data) % 4)
            if padding_needed != 4:
                data += "=" * padding_needed
            return base64.urlsafe_b64decode(data)

        signature = b64url_decode(signature_b64)

        public_key.verify(
            signature,
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        # Decode payload
        payload_bytes = b64url_decode(payload_b64)
        payload = json.loads(payload_bytes)

        # Check expiry
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            return None

        return payload

    except Exception:
        return None
