from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
)
from core.config import settings
from core.database import get_db
from core.dependencies import get_current_mayorista
from core.limiter import limiter
from core.security import create_access_token
from models.mayorista import Mayorista
from repositories.mayorista_repo import MayoristaRepository
from repositories.prenda_repo import PrendaRepository
from services.auth_service import AuthService, EmailAlreadyExistsError, InvalidCredentialsError
from services.email_service import send_welcome_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Este email ya está registrado"},
        422: {"description": "Validation error"},
    },
)
async def register(
    request: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    repo = MayoristaRepository(db)
    auth_service = AuthService(repo)

    try:
        mayorista = await auth_service.register(
            email=request.email,
            password=request.password,
            nombre_negocio=request.nombre_negocio,
        )
    except EmailAlreadyExistsError:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este email ya está registrado",
        )

    import asyncio

    asyncio.create_task(send_welcome_email(mayorista.email, mayorista.nombre_negocio))

    token = create_access_token(str(mayorista.id))
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=604800,  # 7 days
    )

    return RegisterResponse(
        id=mayorista.id,
        email=mayorista.email,
        nombre_negocio=mayorista.nombre_negocio,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"description": "Email o contraseña incorrectos"},
        429: {"description": "Demasiados intentos"},
    },
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    repo = MayoristaRepository(db)
    auth_service = AuthService(repo)

    try:
        mayorista, token = await auth_service.login(
            email=login_data.email,
            password=login_data.password,
        )
    except InvalidCredentialsError:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=604800,  # 7 days
    )

    return LoginResponse()


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    return {}


@router.get("/me", response_model=MeResponse)
async def me(
    mayorista: Mayorista = Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
):
    repo = PrendaRepository(db)
    count = await repo.count_by_mayorista(mayorista.id)
    return MeResponse(
        id=mayorista.id,
        email=mayorista.email,
        nombre_negocio=mayorista.nombre_negocio,
        plan=mayorista.plan,
        trial_activo=mayorista.trial_activo,
        trial_expira_en=mayorista.trial_expira_en,
        prendas_count=count,
    )
