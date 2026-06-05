import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.batch_media_save_service import BatchMediaSaveService


class TestBatchMediaSaveService:
    @pytest.fixture
    def mock_batch_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_media_service(self):
        return AsyncMock()

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_batch_repo, mock_media_service, mock_db):
        return BatchMediaSaveService(
            mock_batch_repo, mock_media_service, mock_db
        )

    @pytest.mark.asyncio
    async def test_should_skip_if_media_already_saved(
        self, service, mock_batch_repo, mock_media_service
    ):
        batch_id = uuid.uuid4()
        item_id = uuid.uuid4()
        existing_media_id = uuid.uuid4()

        mock_item = MagicMock()
        mock_item.result_media_id = existing_media_id
        mock_batch_repo.get_item_by_id = AsyncMock(return_value=mock_item)

        result = await service.save_result(
            batch_id, item_id, uuid.uuid4(), "results/key.jpg"
        )

        assert result == existing_media_id
        mock_media_service.save_vton_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_save_media_with_batch_metadata(
        self, service, mock_batch_repo, mock_media_service, mock_db
    ):
        batch_id = uuid.uuid4()
        item_id = uuid.uuid4()
        vton_job_id = uuid.uuid4()

        mock_item = MagicMock()
        mock_item.result_media_id = None
        mock_item.garment_id = uuid.uuid4()
        mock_item.model_id = uuid.uuid4()
        mock_batch_repo.get_item_by_id = AsyncMock(return_value=mock_item)

        mock_batch = MagicMock()
        mock_batch.mayorista_id = uuid.uuid4()
        mock_batch.name = "Test Batch"
        mock_batch_repo.get_by_id = AsyncMock(return_value=mock_batch)

        mock_media_item = MagicMock()
        mock_media_item.id = uuid.uuid4()
        mock_media_service.save_vton_result = AsyncMock(return_value=mock_media_item)

        result = await service.save_result(
            batch_id, item_id, vton_job_id, "results/key.jpg"
        )

        assert result == mock_media_item.id
        mock_media_service.save_vton_result.assert_called_once()
        call_kwargs = mock_media_service.save_vton_result.call_args[1]
        assert call_kwargs["batch_id"] == batch_id
        assert call_kwargs["batch_name"] == "Test Batch"
        assert call_kwargs["vton_job_id"] == vton_job_id

    @pytest.mark.asyncio
    async def test_should_handle_duplicate_constraint_error(
        self, service, mock_batch_repo, mock_media_service
    ):
        batch_id = uuid.uuid4()
        item_id = uuid.uuid4()

        mock_item = MagicMock()
        mock_item.result_media_id = None
        mock_batch_repo.get_item_by_id = AsyncMock(return_value=mock_item)

        mock_batch = MagicMock()
        mock_batch.mayorista_id = uuid.uuid4()
        mock_batch.name = "Test Batch"
        mock_batch_repo.get_by_id = AsyncMock(return_value=mock_batch)

        mock_media_service.save_vton_result = AsyncMock(
            side_effect=Exception("duplicate key value violates unique constraint")
        )

        result = await service.save_result(
            batch_id, item_id, uuid.uuid4(), "results/key.jpg"
        )

        assert result is None  # Graceful degradation

    @pytest.mark.asyncio
    async def test_should_flag_error_on_media_save_failure(
        self, service, mock_batch_repo, mock_media_service, mock_db
    ):
        batch_id = uuid.uuid4()
        item_id = uuid.uuid4()

        mock_item = MagicMock()
        mock_item.result_media_id = None
        mock_batch_repo.get_item_by_id = AsyncMock(return_value=mock_item)

        mock_batch = MagicMock()
        mock_batch.mayorista_id = uuid.uuid4()
        mock_batch.name = "Test Batch"
        mock_batch_repo.get_by_id = AsyncMock(return_value=mock_batch)

        mock_media_service.save_vton_result = AsyncMock(
            side_effect=Exception("MinIO connection refused")
        )

        result = await service.save_result(
            batch_id, item_id, uuid.uuid4(), "results/key.jpg"
        )

        assert result is None
        mock_batch_repo.set_media_save_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_return_none_if_item_not_found(
        self, service, mock_batch_repo
    ):
        batch_id = uuid.uuid4()
        item_id = uuid.uuid4()

        mock_batch_repo.get_item_by_id = AsyncMock(return_value=None)

        result = await service.save_result(
            batch_id, item_id, uuid.uuid4(), "results/key.jpg"
        )

        assert result is None
