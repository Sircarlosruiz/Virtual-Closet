import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services.pose_set_service import (
    DuplicatePoseSelectionError,
    EmptyPoseSelectionError,
    InvalidPoseSelectionError,
    PoseSetResultService,
    PoseSetSubmissionService,
)


def _submission_service(photos=None):
    model_id = uuid.uuid4()
    mayorista_id = uuid.uuid4()
    garment_id = uuid.uuid4()
    model = SimpleNamespace(id=model_id, name="Model")
    garment = SimpleNamespace(id=garment_id)
    if photos is None:
        photos = [
            SimpleNamespace(id=uuid.uuid4(), model_id=model_id, pose="front")
        ]
    batch = SimpleNamespace(id=uuid.uuid4(), total_items=len(photos))
    pose_set = SimpleNamespace(id=uuid.uuid4(), batch_id=batch.id)

    model_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=model))
    garment_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=garment))
    photo_repo = SimpleNamespace(
        list_by_ids_for_model=AsyncMock(return_value=photos)
    )
    batch_service = SimpleNamespace(
        create_and_submit=AsyncMock(return_value=batch)
    )
    pose_set_repo = SimpleNamespace(create=AsyncMock(return_value=pose_set))
    db = SimpleNamespace()

    service = PoseSetSubmissionService(
        pose_set_repo,
        model_repo,
        photo_repo,
        garment_repo,
        SimpleNamespace(),
        batch_service,
        db,
    )
    return service, model_id, mayorista_id, garment_id, photos, batch, pose_set


@pytest.mark.asyncio
async def test_should_reject_empty_pose_selection():
    service, model_id, mayorista_id, garment_id, *_ = _submission_service()

    with pytest.raises(EmptyPoseSelectionError):
        await service.submit(
            mayorista_id,
            uuid.uuid4(),
            garment_id,
            model_id,
            "upper_body",
            [],
        )


@pytest.mark.asyncio
async def test_should_reject_duplicate_pose_ids():
    service, model_id, mayorista_id, garment_id, photos, *_ = _submission_service()

    with pytest.raises(DuplicatePoseSelectionError):
        await service.submit(
            mayorista_id,
            uuid.uuid4(),
            garment_id,
            model_id,
            "upper_body",
            [photos[0].id, photos[0].id],
        )


@pytest.mark.asyncio
async def test_should_reject_pose_not_in_model():
    service, model_id, mayorista_id, garment_id, *_ = _submission_service(
        photos=[]
    )

    with pytest.raises(InvalidPoseSelectionError):
        await service.submit(
            mayorista_id,
            uuid.uuid4(),
            garment_id,
            model_id,
            "upper_body",
            [uuid.uuid4()],
        )


@pytest.mark.asyncio
async def test_should_create_pose_set_through_existing_batch_service():
    service, model_id, mayorista_id, garment_id, photos, batch, pose_set = (
        _submission_service()
    )
    tenant_id = uuid.uuid4()

    created_pose_set, created_batch = await service.submit(
        mayorista_id,
        tenant_id,
        garment_id,
        model_id,
        "upper_body",
        [photos[0].id],
    )

    assert created_pose_set.batch_id == batch.id
    assert created_batch is batch
    service._batch_service.create_and_submit.assert_awaited_once()
    request = service._batch_service.create_and_submit.await_args.kwargs["request"]
    assert request.items[0].model_id == photos[0].id
    service._pose_set_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_should_project_partial_pose_results():
    pose_set_id = uuid.uuid4()
    model_id = uuid.uuid4()
    photo_id = uuid.uuid4()
    item = SimpleNamespace(
        id=uuid.uuid4(),
        model_id=photo_id,
        result_media_id=None,
        status="complete",
        error_message=None,
    )
    batch = SimpleNamespace(id=uuid.uuid4(), status="complete", items=[item])
    pose_set = SimpleNamespace(
        id=pose_set_id,
        batch_id=batch.id,
        model_id=model_id,
        garment_id=uuid.uuid4(),
    )
    repo = SimpleNamespace(
        get_by_id_and_mayorista=AsyncMock(return_value=pose_set)
    )
    batch_repo = SimpleNamespace(
        get_by_id_and_mayorista=AsyncMock(return_value=batch)
    )
    photo_repo = SimpleNamespace(
        list_by_ids_for_model=AsyncMock(
            return_value=[SimpleNamespace(id=photo_id, pose="front")]
        )
    )
    media_repo = SimpleNamespace(get_by_id=AsyncMock())
    media_service = SimpleNamespace(get_presigned_url=AsyncMock())
    service = PoseSetResultService(
        repo, batch_repo, photo_repo, media_repo, media_service
    )

    result = await service.get(uuid.uuid4(), pose_set_id)

    assert result["status"] == "complete"
    assert result["items"][0]["pose_type"] == "front"
    assert result["items"][0]["status"] == "complete"
