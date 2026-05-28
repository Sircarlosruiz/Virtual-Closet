import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.customer import Customer
from repositories.customer_repo import CustomerRepo
from services.customer_service import (
    CustomerAlreadyExistsError,
    CustomerNotFoundError,
    CustomerService,
    InvalidTokenError,
)
from services.token_service import TokenService


class TestCustomerService:
    @pytest.fixture
    def mock_customer_repo(self):
        return AsyncMock(spec=CustomerRepo)

    @pytest.fixture
    def token_service(self):
        return TokenService()

    @pytest.fixture
    def service(self, mock_customer_repo, token_service):
        return CustomerService(mock_customer_repo, token_service)

    # --- Story 001: Register Customer ---

    @pytest.mark.asyncio
    async def test_should_register_customer_with_valid_data(
        self, service, mock_customer_repo
    ):
        mayorista_id = uuid.uuid4()
        name = "Ana López"
        email = "ana@buyer.com"

        mock_customer_repo.get_by_email_and_mayorista = AsyncMock(return_value=None)

        created_customer = MagicMock(spec=Customer)
        created_customer.id = uuid.uuid4()
        created_customer.mayorista_id = mayorista_id
        created_customer.name = name
        created_customer.email = email
        created_customer.status = "invited"
        created_customer.created_at = datetime.now(timezone.utc)

        mock_customer_repo.create = AsyncMock(return_value=created_customer)

        customer, token = await service.register_customer(mayorista_id, name, email)

        assert customer.mayorista_id == mayorista_id
        assert customer.name == name
        assert customer.email == email
        assert customer.status == "invited"
        assert token is not None
        mock_customer_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_reject_duplicate_email(
        self, service, mock_customer_repo
    ):
        mayorista_id = uuid.uuid4()
        email = "ana@buyer.com"

        existing_customer = MagicMock(spec=Customer)
        existing_customer.email = email
        mock_customer_repo.get_by_email_and_mayorista = AsyncMock(
            return_value=existing_customer
        )

        with pytest.raises(
            CustomerAlreadyExistsError,
            match=f"Customer with email {email} already exists",
        ):
            await service.register_customer(mayorista_id, "Ana", email)

        mock_customer_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_allow_same_email_for_different_mayoristas(
        self, service, mock_customer_repo
    ):
        mayorista_id_1 = uuid.uuid4()
        mayorista_id_2 = uuid.uuid4()
        email = "ana@buyer.com"

        mock_customer_repo.get_by_email_and_mayorista = AsyncMock(return_value=None)

        created_customer = MagicMock(spec=Customer)
        created_customer.id = uuid.uuid4()
        created_customer.mayorista_id = mayorista_id_2
        created_customer.email = email
        created_customer.status = "invited"
        created_customer.created_at = datetime.now(timezone.utc)

        mock_customer_repo.create = AsyncMock(return_value=created_customer)

        customer, token = await service.register_customer(
            mayorista_id_2, "Ana", email
        )

        assert customer.mayorista_id == mayorista_id_2
        mock_customer_repo.get_by_email_and_mayorista.assert_called_once_with(
            email, mayorista_id_2
        )

    # --- Story 002: Validate Token ---

    @pytest.mark.asyncio
    async def test_should_validate_invitation_token_and_activate_customer(
        self, service, mock_customer_repo, token_service
    ):
        customer_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        token = token_service.create_invitation_token(customer_id, mayorista_id)
        token_hash = token_service.hash_token(token)

        customer = MagicMock(spec=Customer)
        customer.id = customer_id
        customer.mayorista_id = mayorista_id
        customer.status = "invited"
        customer.invitation_token_hash = token_hash
        customer.token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        mock_customer_repo.get_by_id = AsyncMock(return_value=customer)
        mock_customer_repo.activate = AsyncMock()

        result = await service.validate_token(token)

        assert result.id == customer_id
        assert result.status == "active"
        mock_customer_repo.activate.assert_called_once_with(customer_id)

    @pytest.mark.asyncio
    async def test_should_validate_magic_link_token(
        self, service, mock_customer_repo, token_service
    ):
        customer_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        token = token_service.create_magic_link_token(customer_id, mayorista_id)
        token_hash = token_service.hash_token(token)

        customer = MagicMock(spec=Customer)
        customer.id = customer_id
        customer.mayorista_id = mayorista_id
        customer.status = "active"
        customer.invitation_token_hash = token_hash
        customer.token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        mock_customer_repo.get_by_id = AsyncMock(return_value=customer)
        mock_customer_repo.activate = AsyncMock()

        result = await service.validate_token(token)

        assert result.id == customer_id
        mock_customer_repo.activate.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_reject_expired_token(
        self, service, mock_customer_repo, token_service
    ):
        customer_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        token = token_service.create_invitation_token(customer_id, mayorista_id)
        token_hash = token_service.hash_token(token)

        customer = MagicMock(spec=Customer)
        customer.id = customer_id
        customer.invitation_token_hash = token_hash
        customer.token_expires_at = datetime.now(timezone.utc) - timedelta(days=1)

        mock_customer_repo.get_by_id = AsyncMock(return_value=customer)

        with pytest.raises(InvalidTokenError, match="Token expired"):
            await service.validate_token(token)

    @pytest.mark.asyncio
    async def test_should_reject_invalid_token_hash(
        self, service, mock_customer_repo, token_service
    ):
        customer_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        token = token_service.create_invitation_token(customer_id, mayorista_id)
        wrong_hash = token_service.hash_token("wrong_token")

        customer = MagicMock(spec=Customer)
        customer.id = customer_id
        customer.invitation_token_hash = wrong_hash
        customer.token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        mock_customer_repo.get_by_id = AsyncMock(return_value=customer)

        with pytest.raises(InvalidTokenError, match="Token hash mismatch"):
            await service.validate_token(token)

    @pytest.mark.asyncio
    async def test_should_reject_invalid_token_format(self, service):
        with pytest.raises(InvalidTokenError, match="Invalid or expired token"):
            await service.validate_token("invalid_token_string")

    @pytest.mark.asyncio
    async def test_should_reject_token_with_wrong_type(
        self, service, mock_customer_repo, token_service
    ):
        customer_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        token = token_service.create_buyer_session(customer_id, mayorista_id)
        token_hash = token_service.hash_token(token)

        customer = MagicMock(spec=Customer)
        customer.id = customer_id
        customer.invitation_token_hash = token_hash
        customer.token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        mock_customer_repo.get_by_id = AsyncMock(return_value=customer)

        with pytest.raises(InvalidTokenError, match="Invalid token type"):
            await service.validate_token(token)

    @pytest.mark.asyncio
    async def test_should_reject_token_for_nonexistent_customer(
        self, service, mock_customer_repo, token_service
    ):
        customer_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        token = token_service.create_invitation_token(customer_id, mayorista_id)

        mock_customer_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(InvalidTokenError, match="Customer not found"):
            await service.validate_token(token)

    # --- Story 002: Request Magic Link ---

    @pytest.mark.asyncio
    async def test_should_request_magic_link_for_existing_customer(
        self, service, mock_customer_repo
    ):
        customer_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()
        email = "ana@buyer.com"

        customer = MagicMock(spec=Customer)
        customer.id = customer_id
        customer.mayorista_id = mayorista_id
        customer.email = email

        mock_customer_repo.get_by_email = AsyncMock(return_value=customer)
        mock_customer_repo.update_token_hash = AsyncMock()

        token = await service.request_magic_link(email)

        assert token is not None
        mock_customer_repo.update_token_hash.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_return_none_for_nonexistent_customer(
        self, service, mock_customer_repo
    ):
        email = "nonexistent@buyer.com"

        mock_customer_repo.get_by_email = AsyncMock(return_value=None)

        token = await service.request_magic_link(email)

        assert token is None
        mock_customer_repo.update_token_hash.assert_not_called()

    # --- Story 004: List Customers ---

    @pytest.mark.asyncio
    async def test_should_list_customers_with_pagination(
        self, service, mock_customer_repo
    ):
        mayorista_id = uuid.uuid4()

        mock_customers = [MagicMock(spec=Customer) for _ in range(3)]
        mock_customer_repo.list_by_mayorista = AsyncMock(
            return_value=(mock_customers, 10)
        )

        customers, total = await service.list_customers(
            mayorista_id=mayorista_id,
            page=1,
            page_size=20,
        )

        assert len(customers) == 3
        assert total == 10
        mock_customer_repo.list_by_mayorista.assert_called_once_with(
            mayorista_id, 1, 20
        )

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_no_customers(
        self, service, mock_customer_repo
    ):
        mayorista_id = uuid.uuid4()

        mock_customer_repo.list_by_mayorista = AsyncMock(
            return_value=([], 0)
        )

        customers, total = await service.list_customers(
            mayorista_id=mayorista_id,
            page=1,
            page_size=20,
        )

        assert len(customers) == 0
        assert total == 0
