import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from unittest.mock import AsyncMock, patch

from core.config import settings
from core.database import get_db
from core.limiter import limiter
from main import app
from models.mayorista import Base
import models.media  # noqa: F401 — ensure GarmentPhoto/ModelPhoto tables are created
import models.customer  # noqa: F401 — ensure Customer table is created
import models.email_verification_token  # noqa: F401 — ensure EmailVerificationToken table is created
import models.unlock_token  # noqa: F401 — ensure UnlockToken table is created
import models.tenant  # noqa: F401 — ensure Tenant table is created
import models.refresh_token  # noqa: F401 — ensure RefreshToken table is created
import models.two_factor  # noqa: F401 — ensure TwoFactorConfig/BackupCode tables are created
import models.oauth  # noqa: F401 — ensure OAuthLink/SmsOtpRecord tables are created
import models.password_reset_token  # noqa: F401 — ensure PasswordResetToken table is created

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/virtual_closet_test"

settings.COOKIE_SECURE = False

_test_engine = None
_test_async_session = None


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield


@pytest.fixture(autouse=True)
def mock_celery():
    """Mock Celery send_task to avoid RabbitMQ connection in tests."""
    with patch("api.routers.generaciones.celery_app.send_task") as mock_send:
        mock_send.return_value = None
        yield mock_send


@pytest_asyncio.fixture
async def client():
    global _test_engine, _test_async_session

    _test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _test_async_session = async_sessionmaker(
        _test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )

    async def _get_db():
        async with _test_async_session() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()
    _test_engine = None
    _test_async_session = None


@pytest_asyncio.fixture
async def client_with_seeds(client):
    """Client with 6 modelos IA seeded in the test database."""
    from models.modelo_ia import ModeloIA

    async with _test_async_session() as session:
        for i, (nombre, desc, plan) in enumerate([
            ("María", "Mujer latina, 25-30 años", "base"),
            ("Carlos", "Hombre latino, 30-35 años", "base"),
            ("Sofía", "Mujer latina, 20-25 años", "base"),
            ("Diego", "Hombre latino, 25-30 años, barba", "base"),
            ("Valentina Pro", "Mujer latina, premium", "pro"),
            ("Alejandro Pro", "Hombre latino, premium", "pro"),
        ], start=1):
            session.add(ModeloIA(
                nombre=nombre,
                descripcion=desc,
                thumbnail_key=f"{i:04d}.jpg",
                plan_minimo=plan,
            ))
        await session.commit()

    yield client


async def register_user(client, email="test@mayorista.com", password="password123", nombre_negocio="Test Business"):
    return await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "business_name": nombre_negocio},
    )


async def login_user(client, email="test@mayorista.com", password="password123"):
    return await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


async def verify_user_email(client, email="test@mayorista.com"):
    """Register + verify email for a test user. Returns the user object."""
    from models.mayorista import Mayorista
    from models.email_verification_token import EmailVerificationToken
    from sqlalchemy import select
    from core.database import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    await register_user(client, email=email, password=password, nombre_negocio="Test Business")

    db_gen = get_db()
    db: AsyncSession = await db_gen.__anext__()
    result = await db.execute(select(Mayorista).where(Mayorista.email == email))
    user = result.scalar_one_or_none()
    if user:
        token_result = await db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.used.is_(False),
            )
        )
        token = token_result.scalar_one_or_none()
        if token:
            await client.get(f"/api/auth/verify-email?token={token.token}")
    await db_gen.aclose()
    return user
