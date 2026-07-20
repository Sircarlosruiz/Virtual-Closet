import uuid
import importlib.util
from pathlib import Path

import pytest
import pytest_asyncio
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from models.media import ModelPhoto
from models.mayorista import Mayorista
from models.model import Model

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/virtual_closet_test"


@pytest_asyncio.fixture
async def backfill_db():
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    photo_ids = [uuid.uuid4() for _ in range(3)]
    mayorista_id = uuid.uuid4()

    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: (
                Mayorista.__table__.create(sync_connection, checkfirst=True),
                Model.__table__.create(sync_connection, checkfirst=True),
                ModelPhoto.__table__.create(sync_connection, checkfirst=True),
            )
        )

    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(
            Mayorista(
                id=mayorista_id,
                email=f"backfill-{mayorista_id}@example.com",
                password_hash="test",
                nombre_negocio="Backfill Test",
            )
        )
        session.add_all(
            [
                ModelPhoto(
                    id=photo_ids[0],
                    mayorista_id=mayorista_id,
                    minio_key=f"backfill/{photo_ids[0]}.jpg",
                    label="Legacy one",
                    is_curated=False,
                    content_type="image/jpeg",
                    size_bytes=100,
                ),
                ModelPhoto(
                    id=photo_ids[1],
                    mayorista_id=None,
                    minio_key=f"backfill/{photo_ids[1]}.jpg",
                    label="Orphan",
                    is_curated=False,
                    content_type="image/jpeg",
                    size_bytes=100,
                ),
                ModelPhoto(
                    id=photo_ids[2],
                    mayorista_id=None,
                    minio_key=f"backfill/{photo_ids[2]}.jpg",
                    label="Curated",
                    is_curated=True,
                    content_type="image/jpeg",
                    size_bytes=100,
                ),
            ]
        )
        await session.commit()

    yield engine, photo_ids

    async with AsyncSession(engine, expire_on_commit=False) as session:
        await session.execute(delete(ModelPhoto).where(ModelPhoto.id.in_(photo_ids)))
        await session.execute(delete(Model).where(Model.mayorista_id == mayorista_id))
        await session.execute(delete(Mayorista).where(Mayorista.id == mayorista_id))
        await session.commit()
    await engine.dispose()


def _run_migration(sync_connection):
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "b7c8d9e0f1a2_backfill_legacy_model_photos.py"
    )
    spec = importlib.util.spec_from_file_location("legacy_backfill", migration_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load legacy backfill migration")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    operations = Operations(MigrationContext.configure(sync_connection))
    with Operations.context(operations):
        migration.upgrade()


@pytest.mark.asyncio
async def test_should_backfill_legacy_rows_and_skip_curated_or_orphaned(backfill_db):
    engine, photo_ids = backfill_db

    async with engine.begin() as connection:
        await connection.run_sync(_run_migration)

    async with AsyncSession(engine) as session:
        rows = (
            await session.execute(
                select(ModelPhoto).where(ModelPhoto.id.in_(photo_ids))
            )
        ).scalars().all()
        by_id = {row.id: row for row in rows}

        assert by_id[photo_ids[0]].model_id is not None
        assert by_id[photo_ids[0]].pose == "front"
        assert by_id[photo_ids[1]].model_id is None
        assert by_id[photo_ids[1]].pose is None
        assert by_id[photo_ids[2]].model_id is None
        assert by_id[photo_ids[2]].pose is None

        wrapper = await session.get(Model, by_id[photo_ids[0]].model_id)
        assert wrapper is not None
        assert wrapper.mayorista_id == by_id[photo_ids[0]].mayorista_id


@pytest.mark.asyncio
async def test_should_be_idempotent_when_backfill_runs_twice(backfill_db):
    engine, photo_ids = backfill_db

    async with engine.begin() as connection:
        await connection.run_sync(_run_migration)

    async with AsyncSession(engine) as session:
        first = await session.get(ModelPhoto, photo_ids[0])
        first_model_id = first.model_id

    async with engine.begin() as connection:
        await connection.run_sync(_run_migration)

    async with AsyncSession(engine) as session:
        second = await session.get(ModelPhoto, photo_ids[0])
        wrappers = (
            await session.execute(
                select(Model).where(Model.mayorista_id == second.mayorista_id)
            )
        ).scalars().all()

        assert second.model_id == first_model_id
        assert len(wrappers) == 1
