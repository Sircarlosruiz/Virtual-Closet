import uuid
from datetime import datetime, timezone

from models.customer import Customer
from repositories.customer_repo import CustomerRepo
from services.token_service import TokenService


class CustomerAlreadyExistsError(Exception):
    """Customer with this email already exists under this mayorista."""


class CustomerNotFoundError(Exception):
    """Customer not found."""


class InvalidTokenError(Exception):
    """Token is invalid, expired, or hash mismatch."""


class CustomerService:
    """Handles customer registration and authentication."""

    def __init__(
        self,
        customer_repo: CustomerRepo,
        token_service: TokenService,
    ) -> None:
        self._customer_repo = customer_repo
        self._token_service = token_service

    async def register_customer(
        self, mayorista_id: uuid.UUID, name: str, email: str
    ) -> tuple[Customer, str]:
        """Register a new customer and generate invitation token.

        Returns:
            tuple[Customer, str]: The created customer and plaintext invitation token.

        Raises:
            CustomerAlreadyExistsError: If email already registered under this mayorista.
        """
        existing = await self._customer_repo.get_by_email_and_mayorista(
            email, mayorista_id
        )
        if existing:
            raise CustomerAlreadyExistsError(
                f"Customer with email {email} already exists"
            )

        temp_customer_id = uuid.uuid4()
        invitation_token = self._token_service.create_invitation_token(
            temp_customer_id, mayorista_id
        )
        token_hash = self._token_service.hash_token(invitation_token)
        token_expires_at = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        from datetime import timedelta

        token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        customer = Customer(
            id=temp_customer_id,
            mayorista_id=mayorista_id,
            name=name,
            email=email,
            status="invited",
            invitation_token_hash=token_hash,
            token_expires_at=token_expires_at,
        )
        customer = await self._customer_repo.create(customer)

        return customer, invitation_token

    async def validate_token(self, token: str) -> Customer:
        """Validate invitation or magic-link token and activate customer.

        Returns:
            Customer: The authenticated customer.

        Raises:
            InvalidTokenError: If token is invalid, expired, or hash mismatch.
        """
        payload = self._token_service.decode_token(token)
        if payload is None:
            raise InvalidTokenError("Invalid or expired token")

        token_type = payload.get("type")
        if token_type not in ("invitation", "magic_link"):
            raise InvalidTokenError("Invalid token type")

        customer_id = payload.get("sub")
        if not customer_id:
            raise InvalidTokenError("Invalid token payload")

        customer = await self._customer_repo.get_by_id(uuid.UUID(customer_id))
        if not customer:
            raise InvalidTokenError("Customer not found")

        if not self._token_service.verify_token_hash(token, customer.invitation_token_hash):
            raise InvalidTokenError("Token hash mismatch")

        if customer.token_expires_at < datetime.now(timezone.utc):
            raise InvalidTokenError("Token expired")

        if customer.status == "invited":
            await self._customer_repo.activate(customer.id)
            customer.status = "active"

        return customer

    async def request_magic_link(self, email: str) -> str | None:
        """Request a magic-link for customer re-authentication.

        Returns:
            str | None: The magic-link token if customer exists, None otherwise.
        """
        customer = await self._customer_repo.get_by_email(email)
        if not customer:
            return None

        magic_link_token = self._token_service.create_magic_link_token(
            customer.id, customer.mayorista_id
        )
        token_hash = self._token_service.hash_token(magic_link_token)

        from datetime import timedelta

        token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        await self._customer_repo.update_token_hash(
            customer.id, token_hash, token_expires_at
        )

        return magic_link_token

    async def list_customers(
        self, mayorista_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[Customer], int]:
        """List customers owned by mayorista with pagination."""
        return await self._customer_repo.list_by_mayorista(
            mayorista_id, page, page_size
        )
