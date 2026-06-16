"""JWKS manager for RS256 key pair handling.

Manages RSA key pair generation, loading from environment, and
JWKS endpoint response formatting.
"""

import logging
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

from core.config import settings

logger = logging.getLogger(__name__)

# Module-level cache for loaded keys
_private_key = None
_public_key = None
_key_id = None


def _load_key_pair():
    """Load or generate the RSA key pair.

    If JWT_PRIVATE_KEY is set in environment, loads it.
    Otherwise, generates a new RSA 2048-bit key pair (for development only).

    Returns (private_key, public_key, kid).
    """
    global _private_key, _public_key, _key_id

    if _private_key is not None:
        return _private_key, _public_key, _key_id

    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
    from cryptography.hazmat.backends import default_backend

    if settings.JWT_PRIVATE_KEY:
        # Load from environment
        try:
            _private_key = serialization.load_pem_private_key(
                settings.JWT_PRIVATE_KEY.encode("utf-8"),
                password=None,
                backend=default_backend(),
            )
        except Exception:
            logger.error("Failed to load JWT_PRIVATE_KEY — generating temporary key")
            _private_key, _public_key, _key_id = _generate_key_pair()
            return _private_key, _public_key, _key_id
    else:
        # Generate temporary key (development only)
        logger.warning(
            "JWT_PRIVATE_KEY not set — using auto-generated key. "
            "This key will change on restart. Set JWT_PRIVATE_KEY for production."
        )
        return _generate_key_pair()

    # Derive public key from private key
    _public_key = _private_key.public_key()
    _key_id = "key-1"  # Static kid for now; rotate by changing key

    return _private_key, _public_key, _key_id


def _generate_key_pair():
    """Generate a new RSA 2048-bit key pair.

    Returns (private_key, public_key, kid).
    """
    from cryptography.hazmat.primitives.asymmetric import rsa
    import hashlib

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()

    # Generate kid from public key fingerprint
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    fingerprint = hashlib.sha256(pub_pem).hexdigest()[:16]
    kid = f"key-{fingerprint}"

    global _private_key, _public_key, _key_id
    _private_key = private_key
    _public_key = public_key
    _key_id = kid

    return private_key, public_key, kid


def get_private_key():
    """Get the active RS256 private key for signing."""
    private_key, _, _ = _load_key_pair()
    return private_key


def get_public_key():
    """Get the active RS256 public key for verification."""
    _, public_key, _ = _load_key_pair()
    return public_key


def get_jwks_response() -> dict:
    """Generate the JWKS response for /.well-known/jwks.json.

    Returns a dict with the 'keys' array containing the public key
    in JWK format.
    """
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
    import base64

    _, public_key, kid = _load_key_pair()

    # Extract RSA numbers
    public_numbers = public_key.public_numbers()

    # Base64url encode without padding
    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    n_bytes = public_numbers.n.to_bytes(
        (public_numbers.n.bit_length() + 7) // 8, byteorder="big"
    )
    e_bytes = public_numbers.e.to_bytes(
        (public_numbers.e.bit_length() + 7) // 8, byteorder="big"
    )

    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": b64url(n_bytes),
                "e": b64url(e_bytes),
            }
        ]
    }
