import os
from urllib.parse import urlsplit, urlunsplit

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from unittest.mock import patch

from core.config import settings
import core.database as database
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
import models.generation_job  # noqa: F401 — ensure GenerationJob table is created

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/virtual_closet_test",
)

settings.COOKIE_SECURE = False
settings.EMAIL_BACKEND = "console"
settings.REDIS_URL = os.getenv(
    "TEST_REDIS_URL", urlunsplit(urlsplit(settings.REDIS_URL)._replace(path="/15"))
)
if not settings.TWO_FACTOR_ENCRYPTION_KEY:
    settings.TWO_FACTOR_ENCRYPTION_KEY = "M_QnGdvfW4CBKcdKSkRylQrRPSjENW3d5CEpXthzpbU="

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
async def client(monkeypatch):
    global _test_engine, _test_async_session
    import core.redis_client as redis_client

    # Async Redis connections belong to the event loop of this test.
    monkeypatch.setattr(redis_client, "_client", None)

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
    original_async_session = database.async_session
    database.async_session = _test_async_session

    async def _get_db():
        async with _test_async_session() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        # Drop the schema before releasing shared state so cleanup still has
        # the factory needed if HTTP teardown raises while releasing tasks.
        drop_error = None
        try:
            async with _test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        except BaseException as error:
            drop_error = error
        finally:
            if redis_client._client is not None:
                await redis_client._client.aclose()
                redis_client._client = None
            app.dependency_overrides.clear()
            database.async_session = original_async_session
            await _test_engine.dispose()
            _test_engine = None
            _test_async_session = None
        if drop_error is not None:
            raise drop_error


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


async def register_user(client, email="test@mayorista.com", password="Password1", nombre_negocio="Test Business"):
    return await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "business_name": nombre_negocio},
    )


async def request_login(client, email="test@mayorista.com", password="Password1"):
    """Call the credentials endpoint without completing verification or 2FA."""
    return await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


async def verify_user_email(client, email="test@mayorista.com"):
    """Verify an already registered user through the public endpoint."""
    from models.mayorista import Mayorista
    from models.email_verification_token import EmailVerificationToken
    async with database.async_session() as db:
        result = await db.execute(select(Mayorista).where(Mayorista.email == email.lower()))
        user = result.scalar_one()
        if user.email_verified:
            return user
        token_result = await db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.used.is_(False),
            )
        )
        token = token_result.scalar_one()
        response = await client.get("/api/auth/verify-email", params={"token": token.token})
        assert response.status_code == 200, response.text
        await db.refresh(user)
    return user


async def login_user(client, email="test@mayorista.com", password="Password1"):
    """Prepare an authenticated client for resource API tests.

    Runs email verification, credentials and TOTP setup/confirmation through
    HTTP, then seeds the legacy signed cookie consumed by
    get_current_mayorista. The challenge endpoint currently proves the final
    challenge consumed but does not issue a session cookie; sending the
    immediately issued TOTP again is expected to trigger replay protection.
    This helper is not an end-to-end session issuance test; use request_login
    for auth tests.
    """
    import pyotp
    from core.security import create_access_token, decrypt_value
    from models.two_factor import TwoFactorConfig

    user = await verify_user_email(client, email)
    response = await request_login(client, email, password)
    assert response.status_code == 200, response.text
    headers = {"Authorization": f"Bearer {response.json()['challenge_token']}"}
    if response.json()["requires_2fa_setup"]:
        setup = await client.post("/api/auth/2fa/setup", json={"method": "totp"}, headers=headers)
        assert setup.status_code == 200, setup.text
        secret = setup.json()["totp_secret"]
        confirmed = await client.post(
            "/api/auth/2fa/setup/confirm",
            json={"otp_code": pyotp.TOTP(secret).now()}, headers=headers,
        )
        assert confirmed.status_code == 200, confirmed.text
    else:
        async with database.async_session() as db:
            config = (await db.execute(
                select(TwoFactorConfig).where(TwoFactorConfig.mayorista_id == user.id)
            )).scalar_one()
            secret = decrypt_value(config.totp_secret_encrypted)
    client.cookies.clear()
    client.cookies.set("access_token", create_access_token(str(user.id)), domain="test.local", path="/")
    return client
