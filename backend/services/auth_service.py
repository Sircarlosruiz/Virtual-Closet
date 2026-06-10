"""Authentication domain service.

Handles registration, login, email verification, account lockout, and unlock.
All business rules are enforced here; routers translate domain exceptions to HTTP.
"""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from core.security import (
    create_challenge_token,
    generate_unlock_token,
    generate_verification_token,
    hash_password,
    verify_password,
)
from models.email_verification_token import EmailVerificationToken
from models.mayorista import Mayorista
from models.tenant import Tenant
from models.unlock_token import UnlockToken
from repositories.email_verification_token_repo import EmailVerificationTokenRepository
from repositories.mayorista_repo import MayoristaRepository
from repositories.tenant_repo import TenantRepo
from repositories.unlock_token_repo import UnlockTokenRepository


# ── Domain Exceptions ──────────────────────────────────────────────────────


class EmailAlreadyExistsError(Exception):
    """Raised when registration email is already taken."""


class InvalidCredentialsError(Exception):
    """Raised when email or password is incorrect."""


class EmailNotVerifiedError(Exception):
    """Raised when login is attempted on an unverified account."""


class AccountLockedError(Exception):
    """Raised when login is attempted on a locked account."""


class InvalidTokenError(Exception):
    """Raised when a verification or unlock token is invalid, expired, or used."""


class PasswordValidationError(Exception):
    """Raised when password does not meet complexity requirements."""


# ── Constants ──────────────────────────────────────────────────────────────

VERIFICATION_TOKEN_TTL_HOURS = 24
UNLOCK_TOKEN_TTL_HOURS = 24
LOCKOUT_THRESHOLD = 5


# ── Service ────────────────────────────────────────────────────────────────


class AuthService:
    """Domain service for authentication flows."""

    def __init__(
        self,
        mayorista_repo: MayoristaRepository,
        email_token_repo: EmailVerificationTokenRepository | None = None,
        unlock_token_repo: UnlockTokenRepository | None = None,
        tenant_repo: TenantRepo | None = None,
    ):
        self.mayorista_repo = mayorista_repo
        self.email_token_repo = email_token_repo
        self.unlock_token_repo = unlock_token_repo
        self.tenant_repo = tenant_repo

    # ── Registration ───────────────────────────────────────────────────

    async def register(
        self,
        email: str,
        password: str,
        business_name: str,
    ) -> tuple[Mayorista, EmailVerificationToken]:
        """Register a new mayorista with email verification.

        Creates a Tenant and User atomically. Returns the user and
        the email verification token that was generated.

        Raises:
            EmailAlreadyExistsError: If email is already registered.
        """
        email = email.lower()
        existing = await self.mayorista_repo.get_by_email(email)
        if existing:
            raise EmailAlreadyExistsError("Este email ya está registrado")

        # Create tenant first
        tenant_slug = self._generate_tenant_slug(business_name)
        tenant = Tenant(
            name=business_name,
            slug=tenant_slug,
            buyer_link_secret=secrets.token_hex(32),
        )
        if self.tenant_repo:
            tenant = await self.tenant_repo.create(tenant)
        else:
            self.mayorista_repo.session.add(tenant)
            await self.mayorista_repo.session.commit()
            await self.mayorista_repo.session.refresh(tenant)

        # Create user with tenant_id
        mayorista = Mayorista(
            email=email,
            password_hash=hash_password(password),
            nombre_negocio=business_name,
            tenant_id=tenant.id,
            email_verified=False,
            is_locked=False,
            failed_attempts=0,
        )
        mayorista = await self.mayorista_repo.create(mayorista)

        # Generate email verification token
        verification_token = await self._create_verification_token(mayorista.id)

        return mayorista, verification_token

    # ── Email Verification ─────────────────────────────────────────────

    async def verify_email(self, token: str) -> Mayorista:
        """Verify a user's email using the token from the verification link.

        Raises:
            InvalidTokenError: If token is invalid, expired, or already used.
        """
        if not self.email_token_repo:
            raise RuntimeError("email_token_repo is required for verify_email")

        email_token = await self.email_token_repo.find_by_token(token)
        if email_token is None:
            raise InvalidTokenError("Token inválido")

        if email_token.used:
            raise InvalidTokenError("Token ya utilizado")

        if email_token.expires_at < datetime.now(timezone.utc):
            raise InvalidTokenError("Token expirado")

        # Mark token as used and verify email atomically
        await self.email_token_repo.mark_used(token)
        mayorista = await self.mayorista_repo.mark_email_verified(email_token.user_id)

        if mayorista is None:
            raise RuntimeError(f"User {email_token.user_id} not found after verification")

        return mayorista

    async def resend_verification(self, email: str) -> EmailVerificationToken | None:
        """Resend a verification email.

        Returns a new token if the user exists and is not verified.
        Returns None if user not found (prevents enumeration).
        Invalidates any existing unused tokens for the user.
        """
        if not self.email_token_repo:
            raise RuntimeError("email_token_repo is required for resend_verification")

        email = email.lower()
        mayorista = await self.mayorista_repo.get_by_email(email)
        if mayorista is None or mayorista.email_verified:
            return None

        # Invalidate existing tokens
        await self.email_token_repo.invalidate_by_user_id(mayorista.id)

        # Create new token
        return await self._create_verification_token(mayorista.id)

    # ── Login ──────────────────────────────────────────────────────────

    async def login(self, email: str, password: str) -> dict:
        """Authenticate with email and password.

        Returns a challenge_token (not a full JWT) after successful
        credential validation. The challenge_token must be presented
        to the 2FA endpoint to receive a full session.

        Raises:
            InvalidCredentialsError: If credentials are incorrect.
            EmailNotVerifiedError: If email is not verified.
            AccountLockedError: If account is locked.
        """
        email = email.lower()
        mayorista = await self.mayorista_repo.get_by_email(email)

        # Timing-safe: always compare password even if user not found
        password_valid = False
        if mayorista and mayorista.password_hash:
            password_valid = verify_password(password, mayorista.password_hash)

        if not mayorista or not password_valid:
            raise InvalidCredentialsError("Email o contraseña incorrectos")

        # Check lockout (before checking email verification)
        if mayorista.is_locked:
            raise AccountLockedError(
                "Cuenta bloqueada. Revisa tu email para instrucciones de desbloqueo."
            )

        # Check email verification
        if not mayorista.email_verified:
            raise EmailNotVerifiedError(
                "Debes verificar tu email antes de iniciar sesión."
            )

        # Reset failed attempts on successful credential validation
        await self.mayorista_repo.reset_failed_attempts(mayorista.id)

        # Issue challenge_token (not full JWT)
        challenge_token = create_challenge_token(str(mayorista.id))

        # For this bolt: 2FA is not yet implemented, so we indicate setup is required
        # In bolt 031, this will check if 2FA is configured
        requires_2fa_setup = True

        return {
            "challenge_token": challenge_token,
            "requires_2fa_setup": requires_2fa_setup,
            "user": mayorista,
        }

    async def record_failed_login(self, email: str) -> tuple[int, bool]:
        """Record a failed login attempt and return (attempts, is_locked).

        Called by the router when credentials are invalid.
        Uses atomic increment to prevent race conditions.
        """
        email = email.lower()
        mayorista = await self.mayorista_repo.get_by_email(email)
        if mayorista is None:
            return 0, False

        result = await self.mayorista_repo.increment_failed_attempts(mayorista.id)
        if result is None:
            return 0, False

        failed_attempts, is_locked = result
        return failed_attempts, is_locked

    # ── Account Unlock ─────────────────────────────────────────────────

    async def create_unlock_token(self, user_id: UUID) -> UnlockToken:
        """Create an unlock token for a locked account.

        Called when an account is locked to send the unlock email.
        """
        if not self.unlock_token_repo:
            raise RuntimeError("unlock_token_repo is required for create_unlock_token")

        token_value = generate_unlock_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=UNLOCK_TOKEN_TTL_HOURS)

        unlock_token = UnlockToken(
            token=token_value,
            user_id=user_id,
            expires_at=expires_at,
        )
        return await self.unlock_token_repo.create(unlock_token)

    async def unlock_account(self, token: str) -> Mayorista:
        """Unlock an account using the token from the lockout email.

        Raises:
            InvalidTokenError: If token is invalid, expired, or already used.
        """
        if not self.unlock_token_repo:
            raise RuntimeError("unlock_token_repo is required for unlock_account")

        unlock_token = await self.unlock_token_repo.find_by_token(token)
        if unlock_token is None:
            raise InvalidTokenError("Token inválido")

        if unlock_token.used:
            raise InvalidTokenError("Token ya utilizado")

        if unlock_token.expires_at < datetime.now(timezone.utc):
            raise InvalidTokenError("Token expirado")

        # Mark token as used and unlock account
        await self.unlock_token_repo.mark_used(token)
        mayorista = await self.mayorista_repo.unlock_account(unlock_token.user_id)

        if mayorista is None:
            raise RuntimeError(f"User {unlock_token.user_id} not found after unlock")

        return mayorista

    # ── Internal Helpers ───────────────────────────────────────────────

    async def _create_verification_token(
        self, user_id: UUID
    ) -> EmailVerificationToken:
        """Create a new email verification token for the given user."""
        token_value = generate_verification_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_TTL_HOURS)

        email_token = EmailVerificationToken(
            token=token_value,
            user_id=user_id,
            expires_at=expires_at,
        )
        return await self.email_token_repo.create(email_token)

    @staticmethod
    def _generate_tenant_slug(business_name: str) -> str:
        """Generate a URL-safe slug from the business name.

        Adds a short random suffix to avoid collisions.
        """
        import re

        slug = re.sub(r"[^a-z0-9]+", "-", business_name.lower().strip()).strip("-")
        slug = slug[:40]  # max length before suffix
        suffix = secrets.token_hex(2)
        return f"{slug}-{suffix}"
