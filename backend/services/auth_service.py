from datetime import timedelta

from core.security import create_access_token, hash_password, verify_password
from models.mayorista import Mayorista
from repositories.mayorista_repo import MayoristaRepository


class EmailAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AuthService:
    def __init__(self, repo: MayoristaRepository):
        self.repo = repo

    async def register(self, email: str, password: str, nombre_negocio: str) -> Mayorista:
        existing = await self.repo.get_by_email(email)
        if existing:
            raise EmailAlreadyExistsError("Este email ya está registrado")

        mayorista = Mayorista(
            email=email,
            password_hash=hash_password(password),
            nombre_negocio=nombre_negocio,
        )
        return await self.repo.create(mayorista)

    async def login(self, email: str, password: str) -> tuple[Mayorista, str]:
        mayorista = await self.repo.get_by_email(email)
        if not mayorista or not verify_password(password, mayorista.password_hash):
            raise InvalidCredentialsError("Email o contraseña incorrectos")

        token = create_access_token(str(mayorista.id))
        return mayorista, token

    async def refresh_token(self, mayorista: Mayorista) -> str:
        expires_delta = timedelta(days=settings.JWT_EXPIRE_DAYS)
        return create_access_token(str(mayorista.id), expires_delta=expires_delta)


from core.config import settings  # noqa: E402
