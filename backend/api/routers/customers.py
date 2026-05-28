import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.customer import CustomerRegisterRequest, CustomerResponse
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.customer_repo import CustomerRepo
from services.customer_service import (
    CustomerAlreadyExistsError,
    CustomerService,
)
from services.token_service import TokenService

router = APIRouter(prefix="/api/customers", tags=["customers"])


def _get_customer_service(db: AsyncSession = Depends(get_db)) -> CustomerService:
    customer_repo = CustomerRepo(db)
    token_service = TokenService()
    return CustomerService(customer_repo, token_service)


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_customer(
    body: CustomerRegisterRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    customer_service: CustomerService = Depends(_get_customer_service),
):
    """Register a new customer and send invitation email."""
    try:
        customer, invitation_token = await customer_service.register_customer(
            mayorista_id=mayorista.id,
            name=body.name,
            email=body.email,
        )
    except CustomerAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    from services.email_service import send_invitation_email

    asyncio.create_task(
        send_invitation_email(
            customer_email=customer.email,
            customer_name=customer.name,
            mayorista_name=mayorista.nombre_negocio,
            invitation_token=invitation_token,
        )
    )

    return customer
