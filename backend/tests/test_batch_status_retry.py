import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from api.schemas.batches import BatchItemResponse
from models.batch_job import (
    BatchItem,
    BatchJob,
)
from repositories.batch_repo import BatchJobRepo
from services.batch_completion_handler import (
    BatchCompletionHandler,
    compute_batch_status,
)
from services.batch_retry_service import (
    BatchRetryService,
    ItemNotFailedError,
    MayoristaOwnershipError,
    RetryEnqueueError,
)


# --- Unit Tests: compute_batch_status ---


class TestComputeBatchStatus:
    def test_should_return_in_progress_when_not_all_terminal(self):
        assert compute_batch_status(5, 3, 10) == "in-progress"

    def test_should_return_complete_when_all_succeed(self):
        assert compute_batch_status(10, 0, 10) == "complete"

    def test_should_return_failed_when_all_fail(self):
        assert compute_batch_status(0, 10, 10) == "failed"

    def test_should_return_partial_when_mixed(self):
        assert compute_batch_status(7, 3, 10) == "partial"

    def test_should_return_in_progress_when_zero_done(self):
        assert compute_batch_status(0, 0, 5) == "in-progress"


# --- Unit Tests: BatchCompletionHandler ---


class TestBatchCompletionHandler:
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def handler(self, mock_db):
        return BatchCompletionHandler(mock_db)

    @pytest.mark.asyncio
    async def test_should_update_item_and_increment_completed_count(
        self, handler, mock_db
    ):
        vton_job_id = uuid.uuid4()
        batch_id = uuid.uuid4()

        # Mock BatchItem lookup
        mock_item = MagicMock()
        mock_item.id = uuid.uuid4()
        mock_item.batch_id = batch_id
        mock_item.vton_job_id = vton_job_id

        mock_db.execute = AsyncMock(side_effect=[
            # First call: select BatchItem
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_item)),
            # Second call: update counter
            MagicMock(first=MagicMock(return_value=MagicMock(
                completed_count=6, failed_count=2, total_items=10, status="in-progress"
            ))),
            # Third call: status update (no change, so not executed)
        ])

        await handler.on_vton_job_complete(vton_job_id, "results/key.jpg")

        assert mock_item.status == "complete"
        assert mock_item.completed_at is not None

    @pytest.mark.asyncio
    async def test_should_skip_if_no_batch_item(self, handler, mock_db):
        vton_job_id = uuid.uuid4()

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        await handler.on_vton_job_complete(vton_job_id, "results/key.jpg")

        # Only one execute call (the select)
        assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_should_update_item_and_increment_failed_count(
        self, handler, mock_db
    ):
        vton_job_id = uuid.uuid4()
        batch_id = uuid.uuid4()

        mock_item = MagicMock()
        mock_item.id = uuid.uuid4()
        mock_item.batch_id = batch_id
        mock_item.vton_job_id = vton_job_id

        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_item)),
            MagicMock(first=MagicMock(return_value=MagicMock(
                completed_count=5, failed_count=5, total_items=10, status="in-progress"
            ))),
            MagicMock(),  # status update
        ])

        await handler.on_vton_job_failed(vton_job_id, "Connection timeout")

        assert mock_item.status == "failed"
        assert mock_item.error_message == "Connection timeout"

    @pytest.mark.asyncio
    async def test_should_compute_partial_status(self, handler, mock_db):
        vton_job_id = uuid.uuid4()
        batch_id = uuid.uuid4()

        mock_item = MagicMock()
        mock_item.id = uuid.uuid4()
        mock_item.batch_id = batch_id

        # Simulate last item failing, resulting in partial status
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_item)),
            MagicMock(first=MagicMock(return_value=MagicMock(
                completed_count=7, failed_count=3, total_items=10, status="in-progress"
            ))),
            MagicMock(),  # status update (in-progress → partial)
        ])

        await handler.on_vton_job_failed(vton_job_id, "GPU OOM")

        # Verify status update was called (3 execute calls)
        assert mock_db.execute.call_count == 3


# --- Unit Tests: BatchRetryService ---


class TestBatchRetryService:
    @pytest.fixture
    def mock_batch_repo(self):
        return AsyncMock(spec=BatchJobRepo)

    @pytest.fixture
    def mock_vton_service(self):
        return AsyncMock()

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_batch_repo, mock_vton_service, mock_db):
        return BatchRetryService(mock_batch_repo, mock_vton_service, mock_db)

    @pytest.mark.asyncio
    async def test_should_retry_failed_item(
        self, service, mock_batch_repo, mock_vton_service, mock_db
    ):
        batch_id = uuid.uuid4()
        item_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        # Mock batch ownership
        mock_batch = MagicMock()
        mock_batch.mayorista_id = mayorista_id
        mock_batch_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_batch)

        # Mock failed item
        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.status = "failed"
        mock_item.garment_id = uuid.uuid4()
        mock_item.model_id = uuid.uuid4()
        mock_item.cloth_type = "upper_body"
        mock_item.retry_count = 0
        mock_batch_repo.get_item_by_id = AsyncMock(return_value=mock_item)

        # Mock VtonJob creation
        mock_vton_job = MagicMock()
        mock_vton_job.id = uuid.uuid4()
        mock_vton_service.submit_job = AsyncMock(return_value=(mock_vton_job, "http://presigned"))

        # Mock counter update
        mock_db.execute = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=MagicMock(
            completed_count=5, failed_count=4, total_items=10, status="partial"
        ))))

        result = await service.retry_item(batch_id, item_id, mayorista_id)

        assert result.status == "pending"
        assert result.vton_job_id == mock_vton_job.id
        assert result.error_message is None
        mock_vton_service.submit_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_reject_retry_on_non_failed_item(
        self, service, mock_batch_repo
    ):
        batch_id = uuid.uuid4()
        item_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        mock_batch = MagicMock()
        mock_batch.mayorista_id = mayorista_id
        mock_batch_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_batch)

        mock_item = MagicMock()
        mock_item.status = "complete"  # Not failed
        mock_batch_repo.get_item_by_id = AsyncMock(return_value=mock_item)

        with pytest.raises(ItemNotFailedError, match="Can only retry failed"):
            await service.retry_item(batch_id, item_id, mayorista_id)

    @pytest.mark.asyncio
    async def test_should_reject_retry_on_processing_item(
        self, service, mock_batch_repo
    ):
        batch_id = uuid.uuid4()
        item_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        mock_batch = MagicMock()
        mock_batch_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_batch)

        mock_item = MagicMock()
        mock_item.status = "processing"
        mock_batch_repo.get_item_by_id = AsyncMock(return_value=mock_item)

        with pytest.raises(ItemNotFailedError, match="processing"):
            await service.retry_item(batch_id, item_id, mayorista_id)

    @pytest.mark.asyncio
    async def test_should_reject_retry_for_wrong_mayorista(
        self, service, mock_batch_repo
    ):
        batch_id = uuid.uuid4()
        item_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        # Batch belongs to different mayorista
        mock_batch_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_batch_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(MayoristaOwnershipError, match="do not own"):
            await service.retry_item(batch_id, item_id, mayorista_id)

    @pytest.mark.asyncio
    async def test_should_raise_retry_enqueue_error_on_vton_failure(
        self, service, mock_batch_repo, mock_vton_service
    ):
        batch_id = uuid.uuid4()
        item_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        mock_batch = MagicMock()
        mock_batch_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_batch)

        mock_item = MagicMock()
        mock_item.status = "failed"
        mock_batch_repo.get_item_by_id = AsyncMock(return_value=mock_item)

        mock_vton_service.submit_job = AsyncMock(side_effect=Exception("Celery down"))

        with pytest.raises(RetryEnqueueError, match="Celery down"):
            await service.retry_item(batch_id, item_id, mayorista_id)


# --- Unit Tests: Pydantic Schema (retry_count) ---


class TestBatchItemResponseSchema:
    def test_should_include_retry_count(self):
        response = BatchItemResponse(
            id=uuid.uuid4(),
            garment_id=uuid.uuid4(),
            model_id=uuid.uuid4(),
            cloth_type="upper_body",
            status="failed",
            retry_count=2,
            created_at=datetime.now(timezone.utc),
        )

        assert response.retry_count == 2

    def test_should_default_retry_count_to_zero(self):
        response = BatchItemResponse(
            id=uuid.uuid4(),
            garment_id=uuid.uuid4(),
            model_id=uuid.uuid4(),
            cloth_type="dress",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )

        assert response.retry_count == 0
