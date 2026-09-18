import io
import uuid

import pytest
from PIL import Image
from sqlalchemy import select

import core.database as database
from api.schemas.composition import (
    CompositionRequest,
    OverlayAnchor,
    OverlayPlacement,
    OverlayStyle,
)
from models.composition_snapshot import CompositionSnapshot
from models.generation_job import GenerationJob
from models.image_template import ImageTemplate
from models.mayorista import Mayorista
from models.product_overlay import CompositionVersion
from repositories.composition_snapshot_repo import CompositionSnapshotRepository
from repositories.composition_version_repo import CompositionVersionRepository
from repositories.generation_job_repo import GenerationJobRepository
from repositories.product_overlay_repo import ProductOverlayRepository
from services.composition_spec import InvalidSkuError, normalize_sku
from services.sku_composition_service import (
    BaseImageUnavailableError,
    GenerationJobNotFoundError,
    OverlayDoesNotFitError,
    SkuCompositionService,
)
from tests.conftest import login_user, register_user


class FakeStorage:
    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects = dict(objects or {})
        self.uploaded: list[str] = []

    async def object_exists(self, key: str, bucket_override: str | None = None) -> bool:
        return key in self.objects

    async def get_object_bytes(
        self, key: str, bucket_override: str | None = None
    ) -> bytes:
        return self.objects[key]

    async def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "image/jpeg",
        bucket_override: str | None = None,
    ) -> None:
        self.objects[key] = data
        self.uploaded.append(key)


def make_base(width: int = 600, height: int = 800) -> bytes:
    image = Image.new("RGB", (width, height), (255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def spec(sku: str, **style_overrides) -> CompositionRequest:
    style = {"color": "#000000", "font_size": 48}
    style.update(style_overrides)
    return CompositionRequest(
        sku=sku,
        placement=OverlayPlacement(
            anchor=OverlayAnchor.bottom_right, offset_x=24, offset_y=24
        ),
        style=OverlayStyle(**style),
    )


async def _owner_id(email: str = "test@mayorista.com") -> uuid.UUID:
    async with database.async_session() as session:
        user = (
            await session.execute(select(Mayorista).where(Mayorista.email == email.lower()))
        ).scalar_one()
        return user.id


async def _create_job(owner_id, result_key: str | None = "generated/base.png") -> GenerationJob:
    async with database.async_session() as session:
        job = GenerationJob(
            owner_id=owner_id,
            mode="text",
            provider="openai",
            status="completed",
            input_data={"mode": "text", "prompt": "a red jacket"},
            result_key=result_key,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


def _service(db, storage: FakeStorage) -> SkuCompositionService:
    return SkuCompositionService(
        ProductOverlayRepository(db),
        CompositionVersionRepository(db),
        GenerationJobRepository(db),
        CompositionSnapshotRepository(db),
        storage=storage,
    )


def test_normalize_sku_collapses_whitespace_and_drops_controls():
    assert normalize_sku("  REF:\x00  CAM-001  ") == "REF: CAM-001"


def test_normalize_sku_rejects_invisible_only():
    with pytest.raises(InvalidSkuError):
        normalize_sku("\x00\x01\t")


@pytest.mark.asyncio
async def test_compose_renders_valid_version_and_writes_output(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _owner_id()
    job = await _create_job(owner_id)
    base = make_base()
    storage = FakeStorage({job.result_key: base})

    async with database.async_session() as db:
        result = await _service(db, storage).compose(owner_id, job.id, spec("REF: CAM-001"))

    assert result.created is True
    assert result.version.status == "valid"
    assert result.version.sku_normalized == "REF: CAM-001"
    assert result.version.rendered_key == (
        f"compositions/{job.id}/{result.overlay.id}/v1.png"
    )
    assert result.version.rendered_checksum.startswith("sha256:")
    assert result.version.rendered_key in storage.uploaded

    output = Image.open(io.BytesIO(storage.objects[result.version.rendered_key]))
    assert output.size == Image.open(io.BytesIO(base)).size


@pytest.mark.asyncio
async def test_compose_is_idempotent_for_identical_spec(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _owner_id()
    job = await _create_job(owner_id)
    storage = FakeStorage({job.result_key: make_base()})

    async with database.async_session() as db:
        first = await _service(db, storage).compose(owner_id, job.id, spec("REF: CAM-001"))
    async with database.async_session() as db:
        second = await _service(db, storage).compose(owner_id, job.id, spec("REF: CAM-001"))

    assert second.created is False
    assert second.version.id == first.version.id
    async with database.async_session() as db:
        rows = (
            await db.execute(
                select(CompositionVersion).where(
                    CompositionVersion.overlay_id == first.overlay.id
                )
            )
        ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_recompose_appends_version_without_mutating_base_or_prior(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _owner_id()
    job = await _create_job(owner_id)
    base = make_base()
    storage = FakeStorage({job.result_key: base})

    async with database.async_session() as db:
        first = await _service(db, storage).compose(owner_id, job.id, spec("REF: CAM-001"))
    base_after_first = storage.objects[job.result_key]

    async with database.async_session() as db:
        second = await _service(db, storage).compose(owner_id, job.id, spec("REF: CAM-002"))

    assert second.created is True
    assert second.version.version == 2
    assert second.version.id != first.version.id
    assert storage.objects[job.result_key] == base_after_first

    async with database.async_session() as db:
        prior = await CompositionVersionRepository(db).get_by_id(first.version.id)
        refreshed_job = await GenerationJobRepository(db).get_by_id(job.id)
    assert prior.status == "valid"
    assert prior.rendered_key == first.version.rendered_key
    assert refreshed_job.result_key == job.result_key


@pytest.mark.asyncio
async def test_style_change_recomposes_into_new_version(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _owner_id()
    job = await _create_job(owner_id)
    storage = FakeStorage({job.result_key: make_base()})

    async with database.async_session() as db:
        first = await _service(db, storage).compose(owner_id, job.id, spec("REF: CAM-001"))
    async with database.async_session() as db:
        second = await _service(db, storage).compose(
            owner_id, job.id, spec("REF: CAM-001", font_size=64)
        )

    assert second.created is True
    assert second.version.version == 2
    assert second.version.spec_hash != first.version.spec_hash
    assert second.version.rendered_checksum != first.version.rendered_checksum


@pytest.mark.asyncio
async def test_overlay_that_does_not_fit_is_blocked_and_not_uploaded(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _owner_id()
    job = await _create_job(owner_id)
    storage = FakeStorage({job.result_key: make_base()})
    request = CompositionRequest(
        sku="REF: THIS-SKU-IS-FAR-TOO-LONG-TO-FIT",
        placement=OverlayPlacement(max_width=10, max_height=10),
        style=OverlayStyle(color="#000000", font_size=200),
    )

    async with database.async_session() as db:
        with pytest.raises(OverlayDoesNotFitError) as error:
            await _service(db, storage).compose(owner_id, job.id, request)

    assert error.value.version_id is not None
    assert storage.uploaded == []

    async with database.async_session() as db:
        blocked = await CompositionVersionRepository(db).get_by_id(error.value.version_id)
    assert blocked.status == "blocked"
    assert blocked.rendered_key is None
    assert blocked.rendered_checksum is None
    assert blocked.fit_result["fits"] is False


@pytest.mark.asyncio
async def test_compose_requires_a_completed_base_image(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _owner_id()
    job = await _create_job(owner_id, result_key=None)
    storage = FakeStorage()

    async with database.async_session() as db:
        with pytest.raises(BaseImageUnavailableError):
            await _service(db, storage).compose(owner_id, job.id, spec("REF: CAM-001"))


@pytest.mark.asyncio
async def test_compose_rejects_jobs_owned_by_another_account(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _owner_id()
    job = await _create_job(owner_id)
    storage = FakeStorage({job.result_key: make_base()})

    async with database.async_session() as db:
        with pytest.raises(GenerationJobNotFoundError):
            await _service(db, storage).compose(uuid.uuid4(), job.id, spec("REF: CAM-001"))


@pytest.mark.asyncio
async def test_compose_attaches_snapshot_when_present(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _owner_id()
    job = await _create_job(owner_id)
    storage = FakeStorage({job.result_key: make_base()})

    async with database.async_session() as db:
        template = ImageTemplate(
            scope="common",
            version=1,
            status="active",
            name="Studio look",
            created_by=owner_id,
        )
        db.add(template)
        await db.commit()
        await db.refresh(template)
        snapshot = CompositionSnapshot(
            generation_job_id=job.id,
            template_id=template.id,
            template_version=1,
            effective_configuration={"provider": "openai", "reference_keys": []},
        )
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)
        snapshot_id = snapshot.id

    async with database.async_session() as db:
        result = await _service(db, storage).compose(owner_id, job.id, spec("REF: CAM-001"))

    assert result.overlay.composition_snapshot_id == snapshot_id
