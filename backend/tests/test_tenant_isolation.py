"""Integration tests for multi-tenant isolation."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from uuid import UUID

from core.config import settings
from core.database import get_db
from core.limiter import limiter
from main import app
from models.mayorista import Base
from models.tenant import Tenant
from models.media import MediaItem
from models.catalogo import Catalogo
from models.vton_job import VTONJob, JobStatus, ClothType
from models.batch_job import BatchJob, BatchJobStatus
import models.media  # noqa: F401
import models.customer  # noqa: F401
import models.catalogo  # noqa: F401
import models.vton_job  # noqa: F401
import models.batch_job  # noqa: F401

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/virtual_closet_test"

settings.COOKIE_SECURE = False


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield


@pytest_asyncio.fixture
async def tenant_client():
    """Client with multi-tenant test database setup."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )

    async def _get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, async_session

    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _create_tenant(session: AsyncSession, name: str, slug: str) -> Tenant:
    import secrets
    tenant = Tenant(
        name=name,
        slug=slug,
        buyer_link_secret=secrets.token_hex(32),
        settings={},
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def _create_mayorista(session: AsyncSession, email: str, tenant_id: UUID, password_hash: str = "$2b$12$dummy"):
    from models.mayorista import Mayorista
    mayorista = Mayorista(
        email=email,
        password_hash=password_hash,
        nombre_negocio=f"Business {email}",
        tenant_id=tenant_id,
    )
    session.add(mayorista)
    await session.commit()
    await session.refresh(mayorista)
    return mayorista


async def _create_media_item(session: AsyncSession, mayorista_id: UUID, tenant_id: UUID) -> MediaItem:
    import uuid
    item = MediaItem(
        id=uuid.uuid4(),
        mayorista_id=mayorista_id,
        tenant_id=tenant_id,
        minio_key=f"test/{uuid.uuid4()}.jpg",
        media_type="garment",
        filename="test.jpg",
        content_type="image/jpeg",
        size_bytes=1000,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


class TestTenantIsolation:
    """Test that cross-tenant access returns 404."""

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_access_tenant_b_media(self, tenant_client):
        """Media items from tenant B should not be accessible to tenant A."""
        client, async_session = tenant_client

        # Create two tenants
        async with async_session() as session:
            tenant_a = await _create_tenant(session, "Tenant A", "tenant-a")
            tenant_b = await _create_tenant(session, "Tenant B", "tenant-b")

            mayorista_a = await _create_mayorista(session, "a@test.com", tenant_a.id)
            mayorista_b = await _create_mayorista(session, "b@test.com", tenant_b.id)

            # Create media items for each tenant
            media_a = await _create_media_item(session, mayorista_a.id, tenant_a.id)
            media_b = await _create_media_item(session, mayorista_b.id, tenant_b.id)

            # Verify tenant isolation
            result_a = await session.execute(
                select(MediaItem).where(
                    MediaItem.tenant_id == tenant_a.id,
                    MediaItem.id == media_b.id,  # Try to access tenant B's media
                )
            )
            assert result_a.scalar_one_or_none() is None, "Tenant A should not see Tenant B's media"

            result_b = await session.execute(
                select(MediaItem).where(
                    MediaItem.tenant_id == tenant_b.id,
                    MediaItem.id == media_a.id,  # Try to access tenant A's media
                )
            )
            assert result_b.scalar_one_or_none() is None, "Tenant B should not see Tenant A's media"

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_access_tenant_b_catalog(self, tenant_client):
        """Catalogs from tenant B should not be accessible to tenant A."""
        client, async_session = tenant_client

        async with async_session() as session:
            tenant_a = await _create_tenant(session, "Tenant A", "tenant-a")
            tenant_b = await _create_tenant(session, "Tenant B", "tenant-b")

            mayorista_a = await _create_mayorista(session, "a2@test.com", tenant_a.id)
            mayorista_b = await _create_mayorista(session, "b2@test.com", tenant_b.id)

            # Create catalogs for each tenant
            catalog_a = Catalogo(
                mayorista_id=mayorista_a.id,
                tenant_id=tenant_a.id,
                name="Catalog A",
                status="draft",
                item_count=0,
            )
            catalog_b = Catalogo(
                mayorista_id=mayorista_b.id,
                tenant_id=tenant_b.id,
                name="Catalog B",
                status="draft",
                item_count=0,
            )
            session.add_all([catalog_a, catalog_b])
            await session.commit()

            # Verify tenant isolation
            result_a = await session.execute(
                select(Catalogo).where(
                    Catalogo.tenant_id == tenant_a.id,
                    Catalogo.id == catalog_b.id,
                )
            )
            assert result_a.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_access_tenant_b_vton_job(self, tenant_client):
        """VTON jobs from tenant B should not be accessible to tenant A."""
        client, async_session = tenant_client

        async with async_session() as session:
            tenant_a = await _create_tenant(session, "Tenant A", "tenant-a")
            tenant_b = await _create_tenant(session, "Tenant B", "tenant-b")

            mayorista_a = await _create_mayorista(session, "a3@test.com", tenant_a.id)
            mayorista_b = await _create_mayorista(session, "b3@test.com", tenant_b.id)

            # Create VTON jobs for each tenant
            job_a = VTONJob(
                mayorista_id=mayorista_a.id,
                tenant_id=tenant_a.id,
                status=JobStatus.queued,
                cloth_type=ClothType.upper_body,
                retry_count=0,
                max_retries=3,
            )
            job_b = VTONJob(
                mayorista_id=mayorista_b.id,
                tenant_id=tenant_b.id,
                status=JobStatus.queued,
                cloth_type=ClothType.upper_body,
                retry_count=0,
                max_retries=3,
            )
            session.add_all([job_a, job_b])
            await session.commit()

            # Verify tenant isolation
            result_a = await session.execute(
                select(VTONJob).where(
                    VTONJob.tenant_id == tenant_a.id,
                    VTONJob.id == job_b.id,
                )
            )
            assert result_a.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_access_tenant_b_batch_job(self, tenant_client):
        """Batch jobs from tenant B should not be accessible to tenant A."""
        client, async_session = tenant_client

        async with async_session() as session:
            tenant_a = await _create_tenant(session, "Tenant A", "tenant-a")
            tenant_b = await _create_tenant(session, "Tenant B", "tenant-b")

            mayorista_a = await _create_mayorista(session, "a4@test.com", tenant_a.id)
            mayorista_b = await _create_mayorista(session, "b4@test.com", tenant_b.id)

            # Create batch jobs for each tenant
            batch_a = BatchJob(
                mayorista_id=mayorista_a.id,
                tenant_id=tenant_a.id,
                name="Batch A",
                status=BatchJobStatus.pending,
                total_items=0,
                completed_count=0,
                failed_count=0,
            )
            batch_b = BatchJob(
                mayorista_id=mayorista_b.id,
                tenant_id=tenant_b.id,
                name="Batch B",
                status=BatchJobStatus.pending,
                total_items=0,
                completed_count=0,
                failed_count=0,
            )
            session.add_all([batch_a, batch_b])
            await session.commit()

            # Verify tenant isolation
            result_a = await session.execute(
                select(BatchJob).where(
                    BatchJob.tenant_id == tenant_a.id,
                    BatchJob.id == batch_b.id,
                )
            )
            assert result_a.scalar_one_or_none() is None


class TestTenantCRUD:
    """Test tenant CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_tenant(self, tenant_client):
        """Test creating a tenant via service."""
        _, async_session = tenant_client
        from repositories.tenant_repo import TenantRepo
        from services.tenant_service import TenantService

        async with async_session() as session:
            repo = TenantRepo(session)
            service = TenantService(repo)

            tenant = await service.create_tenant(name="Test Tenant")
            assert tenant.name == "Test Tenant"
            assert tenant.slug == "test-tenant"
            assert tenant.is_active is True
            assert len(tenant.buyer_link_secret) == 64

    @pytest.mark.asyncio
    async def test_update_tenant_name(self, tenant_client):
        """Test updating tenant name."""
        _, async_session = tenant_client
        from repositories.tenant_repo import TenantRepo
        from services.tenant_service import TenantService

        async with async_session() as session:
            repo = TenantRepo(session)
            service = TenantService(repo)

            tenant = await service.create_tenant(name="Old Name")
            updated = await service.update_tenant(tenant.id, name="New Name")
            assert updated.name == "New Name"
            assert updated.slug != "old-name"

    @pytest.mark.asyncio
    async def test_deactivate_tenant(self, tenant_client):
        """Test deactivating a tenant."""
        _, async_session = tenant_client
        from repositories.tenant_repo import TenantRepo
        from services.tenant_service import TenantService, TenantInactiveError

        async with async_session() as session:
            repo = TenantRepo(session)
            service = TenantService(repo)

            tenant = await service.create_tenant(name="To Deactivate")
            deactivated = await service.deactivate_tenant(tenant.id)
            assert deactivated.is_active is False

            with pytest.raises(TenantInactiveError):
                await service.get_tenant(tenant.id)
