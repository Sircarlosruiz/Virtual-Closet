import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from api.schemas.batches import BatchCreateRequest, BatchItemCreateRequest
from models.batch_job import (
    BATCH_ITEM_CAP,
    BatchItem,
    BatchJob,
    BatchJobStatus,
    BatchItemStatus,
)
from repositories.batch_repo import BatchJobRepo
from services.batch_submission_service import (
    BatchSubmissionService,
    BatchSizeExceededError,
    EmptyBatchError,
    MayoristaOwnershipError,
    BatchSubmissionError,
)


# --- Unit Tests: BatchSubmissionService ---


class TestBatchSubmissionService:
    @pytest.fixture
    def mock_batch_repo(self):
        return AsyncMock(spec=BatchJobRepo)

    @pytest.fixture
    def mock_garment_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_model_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_vton_service(self):
        return AsyncMock()

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_batch_repo,
        mock_garment_repo,
        mock_model_repo,
        mock_vton_service,
    ):
        return BatchSubmissionService(
            mock_batch_repo, mock_garment_repo, mock_model_repo, mock_vton_service
        )

    @pytest.mark.asyncio
    async def test_should_create_batch_with_single_item(
        self, service, mock_batch_repo, mock_garment_repo, mock_model_repo, mock_vton_service, mock_db
    ):
        mayorista_id = uuid.uuid4()
        garment_id = uuid.uuid4()
        model_id = uuid.uuid4()

        # Mock garment owned by mayorista
        mock_garment = MagicMock()
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_garment)
        mock_garment_repo.get_by_id = AsyncMock(return_value=mock_garment)

        # Mock model (curated, no ownership check)
        mock_model = MagicMock()
        mock_model.is_curated = True
        mock_model_repo.get_by_id = AsyncMock(return_value=mock_model)

        # Mock batch creation
        mock_batch = MagicMock()
        mock_batch.id = uuid.uuid4()
        mock_batch_repo.create_with_items = AsyncMock(return_value=mock_batch)

        # Mock VtonJob creation
        mock_vton_job = MagicMock()
        mock_vton_job.id = uuid.uuid4()
        mock_vton_service.submit_job = AsyncMock(return_value=mock_vton_job)

        request = BatchCreateRequest(
            name="Test Batch",
            items=[
                BatchItemCreateRequest(
                    garment_id=garment_id,
                    model_id=model_id,
                    cloth_type="upper_body",
                )
            ],
        )

        batch = await service.create_and_submit(mayorista_id, request, mock_db)

        mock_batch_repo.create_with_items.assert_called_once()
        mock_vton_service.submit_job.assert_called_once()
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_should_create_batch_with_100_items(
        self, service, mock_batch_repo, mock_garment_repo, mock_model_repo, mock_vton_service, mock_db
    ):
        mayorista_id = uuid.uuid4()

        mock_garment = MagicMock()
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_garment)
        mock_garment_repo.get_by_id = AsyncMock(return_value=mock_garment)

        mock_model = MagicMock()
        mock_model.is_curated = True
        mock_model_repo.get_by_id = AsyncMock(return_value=mock_model)

        mock_batch = MagicMock()
        mock_batch_repo.create_with_items = AsyncMock(return_value=mock_batch)

        mock_vton_job = MagicMock()
        mock_vton_job.id = uuid.uuid4()
        mock_vton_service.submit_job = AsyncMock(return_value=mock_vton_job)

        items = [
            BatchItemCreateRequest(
                garment_id=uuid.uuid4(),
                model_id=uuid.uuid4(),
                cloth_type="upper_body",
            )
            for _ in range(100)
        ]
        request = BatchCreateRequest(name="Large Batch", items=items)

        batch = await service.create_and_submit(mayorista_id, request, mock_db)

        assert mock_vton_service.submit_job.call_count == 100

    @pytest.mark.asyncio
    async def test_should_reject_empty_batch(self, service, mock_db):
        mayorista_id = uuid.uuid4()
        # Pydantic validates before service, so ValidationError is raised
        with pytest.raises(ValidationError, match="at least 1 item"):
            BatchCreateRequest(name="Empty", items=[])

    @pytest.mark.asyncio
    async def test_should_reject_batch_over_100_items(self, service, mock_db):
        mayorista_id = uuid.uuid4()
        items = [
            BatchItemCreateRequest(
                garment_id=uuid.uuid4(),
                model_id=uuid.uuid4(),
                cloth_type="upper_body",
            )
            for _ in range(101)
        ]
        # Pydantic validates before service, so ValidationError is raised
        with pytest.raises(ValidationError, match="exceeds maximum"):
            BatchCreateRequest(name="Too Large", items=items)

    @pytest.mark.asyncio
    async def test_should_reject_garment_not_owned(
        self, service, mock_garment_repo, mock_db
    ):
        mayorista_id = uuid.uuid4()
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_garment_repo.get_by_id = AsyncMock(return_value=MagicMock())  # exists but not owned

        request = BatchCreateRequest(
            items=[
                BatchItemCreateRequest(
                    garment_id=uuid.uuid4(),
                    model_id=uuid.uuid4(),
                    cloth_type="upper_body",
                )
            ],
        )

        with pytest.raises(MayoristaOwnershipError, match="does not belong"):
            await service.create_and_submit(mayorista_id, request, mock_db)

    @pytest.mark.asyncio
    async def test_should_reject_garment_not_found(
        self, service, mock_garment_repo, mock_db
    ):
        mayorista_id = uuid.uuid4()
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_garment_repo.get_by_id = AsyncMock(return_value=None)

        request = BatchCreateRequest(
            items=[
                BatchItemCreateRequest(
                    garment_id=uuid.uuid4(),
                    model_id=uuid.uuid4(),
                    cloth_type="upper_body",
                )
            ],
        )

        with pytest.raises(MayoristaOwnershipError, match="not found"):
            await service.create_and_submit(mayorista_id, request, mock_db)

    @pytest.mark.asyncio
    async def test_should_reject_model_not_found(
        self, service, mock_garment_repo, mock_model_repo, mock_db
    ):
        mayorista_id = uuid.uuid4()
        mock_garment = MagicMock()
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_garment)
        mock_garment_repo.get_by_id = AsyncMock(return_value=mock_garment)
        mock_model_repo.get_by_id = AsyncMock(return_value=None)

        request = BatchCreateRequest(
            items=[
                BatchItemCreateRequest(
                    garment_id=uuid.uuid4(),
                    model_id=uuid.uuid4(),
                    cloth_type="upper_body",
                )
            ],
        )

        with pytest.raises(MayoristaOwnershipError, match="not found"):
            await service.create_and_submit(mayorista_id, request, mock_db)

    @pytest.mark.asyncio
    async def test_should_reject_model_not_owned(
        self, service, mock_garment_repo, mock_model_repo, mock_db
    ):
        mayorista_id = uuid.uuid4()
        mock_garment = MagicMock()
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_garment)
        mock_garment_repo.get_by_id = AsyncMock(return_value=mock_garment)

        mock_model = MagicMock()
        mock_model.is_curated = False
        mock_model.mayorista_id = uuid.uuid4()  # different mayorista
        mock_model_repo.get_by_id = AsyncMock(return_value=mock_model)

        request = BatchCreateRequest(
            items=[
                BatchItemCreateRequest(
                    garment_id=uuid.uuid4(),
                    model_id=uuid.uuid4(),
                    cloth_type="upper_body",
                )
            ],
        )

        with pytest.raises(MayoristaOwnershipError, match="does not belong"):
            await service.create_and_submit(mayorista_id, request, mock_db)

    @pytest.mark.asyncio
    async def test_should_raise_submission_error_on_enqueue_failure(
        self, service, mock_batch_repo, mock_garment_repo, mock_model_repo, mock_vton_service, mock_db
    ):
        mayorista_id = uuid.uuid4()
        mock_garment = MagicMock()
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_garment)
        mock_garment_repo.get_by_id = AsyncMock(return_value=mock_garment)

        mock_model = MagicMock()
        mock_model.is_curated = True
        mock_model_repo.get_by_id = AsyncMock(return_value=mock_model)

        mock_batch = MagicMock()
        mock_batch_repo.create_with_items = AsyncMock(return_value=mock_batch)

        mock_vton_service.submit_job = AsyncMock(side_effect=Exception("Celery down"))

        request = BatchCreateRequest(
            items=[
                BatchItemCreateRequest(
                    garment_id=uuid.uuid4(),
                    model_id=uuid.uuid4(),
                    cloth_type="upper_body",
                )
            ],
        )

        with pytest.raises(BatchSubmissionError, match="Celery down"):
            await service.create_and_submit(mayorista_id, request, mock_db)

    @pytest.mark.asyncio
    async def test_should_set_batch_name_from_date_when_omitted(
        self, service, mock_batch_repo, mock_garment_repo, mock_model_repo, mock_vton_service, mock_db
    ):
        mayorista_id = uuid.uuid4()
        mock_garment = MagicMock()
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_garment)
        mock_garment_repo.get_by_id = AsyncMock(return_value=mock_garment)

        mock_model = MagicMock()
        mock_model.is_curated = True
        mock_model_repo.get_by_id = AsyncMock(return_value=mock_model)

        mock_batch = MagicMock()
        mock_batch_repo.create_with_items = AsyncMock(return_value=mock_batch)

        mock_vton_job = MagicMock()
        mock_vton_job.id = uuid.uuid4()
        mock_vton_service.submit_job = AsyncMock(return_value=mock_vton_job)

        request = BatchCreateRequest(
            name=None,  # omitted
            items=[
                BatchItemCreateRequest(
                    garment_id=uuid.uuid4(),
                    model_id=uuid.uuid4(),
                    cloth_type="upper_body",
                )
            ],
        )

        await service.create_and_submit(mayorista_id, request, mock_db)

        # Verify BatchJob was created with auto-generated name
        call_args = mock_batch_repo.create_with_items.call_args
        batch_arg = call_args[0][0]
        assert batch_arg.name.startswith("Batch ")


# --- Unit Tests: BatchJob Model ---


class TestBatchJobModel:
    def test_should_create_batch_job_with_defaults(self):
        batch = BatchJob(
            mayorista_id=uuid.uuid4(),
            name="Test Batch",
            total_items=5,
            completed_count=0,
            failed_count=0,
        )

        assert batch.total_items == 5
        assert batch.completed_count == 0
        assert batch.failed_count == 0

    def test_should_create_batch_item_with_defaults(self):
        item = BatchItem(
            batch_id=uuid.uuid4(),
            garment_id=uuid.uuid4(),
            model_id=uuid.uuid4(),
            cloth_type="dress",
        )

        assert item.vton_job_id is None
        assert item.error_message is None


# --- Unit Tests: Pydantic Schemas ---


class TestBatchSchemas:
    def test_should_validate_valid_batch_request(self):
        request = BatchCreateRequest(
            name="Valid Batch",
            items=[
                BatchItemCreateRequest(
                    garment_id=uuid.uuid4(),
                    model_id=uuid.uuid4(),
                    cloth_type="upper_body",
                )
            ],
        )

        assert request.name == "Valid Batch"
        assert len(request.items) == 1

    def test_should_validate_cloth_type(self):
        with pytest.raises(ValueError, match="cloth_type must be one of"):
            BatchItemCreateRequest(
                garment_id=uuid.uuid4(),
                model_id=uuid.uuid4(),
                cloth_type="invalid_type",
            )

    def test_should_reject_empty_items(self):
        with pytest.raises(ValueError, match="at least 1 item"):
            BatchCreateRequest(name="Empty", items=[])

    def test_should_reject_over_100_items(self):
        items = [
            BatchItemCreateRequest(
                garment_id=uuid.uuid4(),
                model_id=uuid.uuid4(),
                cloth_type="upper_body",
            )
            for _ in range(101)
        ]
        with pytest.raises(ValueError, match="exceeds maximum"):
            BatchCreateRequest(name="Too Large", items=items)

    def test_should_default_name_to_none(self):
        request = BatchCreateRequest(
            items=[
                BatchItemCreateRequest(
                    garment_id=uuid.uuid4(),
                    model_id=uuid.uuid4(),
                    cloth_type="upper_body",
                )
            ],
        )
        assert request.name is None
