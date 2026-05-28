import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.customer import Customer


class CustomerRepo:
    """Data access for Customer entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, customer: Customer) -> Customer:
        self._db.add(customer)
        await self._db.commit()
        await self._db.refresh(customer)
        return customer

    async def get_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        result = await self._db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email_and_mayorista(
        self, email: str, mayorista_id: uuid.UUID
    ) -> Customer | None:
        result = await self._db.execute(
            select(Customer).where(
                Customer.email == email,
                Customer.mayorista_id == mayorista_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Customer | None:
        """Look up customer by email (no mayorista scope — for magic-link)."""
        result = await self._db.execute(
            select(Customer).where(Customer.email == email)
        )
        return result.scalar_one_or_none()

    async def update_token_hash(
        self, customer_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> None:
        await self._db.execute(
            update(Customer)
            .where(Customer.id == customer_id)
            .values(invitation_token_hash=token_hash, token_expires_at=expires_at)
        )
        await self._db.commit()

    async def activate(self, customer_id: uuid.UUID) -> None:
        await self._db.execute(
            update(Customer)
            .where(Customer.id == customer_id)
            .values(status="active")
        )
        await self._db.commit()

    async def list_by_mayorista(
        self, mayorista_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[Customer], int]:
        """List customers owned by mayorista with pagination."""
        offset = (page - 1) * page_size

        count_query = select(Customer).where(
            Customer.mayorista_id == mayorista_id
        )
        count_result = await self._db.execute(count_query)
        total = len(count_result.all())

        query = (
            select(Customer)
            .where(Customer.mayorista_id == mayorista_id)
            .order_by(Customer.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(query)
        customers = list(result.scalars().all())

        return customers, total
