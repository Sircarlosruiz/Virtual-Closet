import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.tryoff_job import TryoffJob, GarmentType, TryoffJobStatus
from repositories.tryoff_job_repo import TryoffJobRepo, SourceImageRepo
from services.tryoff_job_service import (
    TryoffJobService,
    SourceImageNotFoundError,
    SourceImageOwnershipError,
)


class TestTryoffJobService:
    @pytest.fixture
    def mock_tryoff_repo(self):
        return AsyncMock(spec=TryoffJobRepo)

    @pytest.fixture
    def mock_source_image_repo(self):
        return AsyncMock(spec=SourceImageRepo)

    @pytest.fixture
    def mock_minio(self):
        client = AsyncMock()
        client.get_presigned_url = AsyncMock(return_value="http://minio/presigned")
        client.upload_file = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_tryoff_repo, mock_source_image_repo, mock_minio):
        return TryoffJobService(
            mock_tryoff_repo, mock_source_image_repo, mock_minio
        )

    @pytest.mark.asyncio
    async def test_should_submit_single_job(
        self, service, mock_tryoff_repo, mock_source_image_repo
    ):
        mayorista_id = uuid.uuid4()
        source_image_id = uuid.uuid4()

        # Mock source image owned by mayorista
        mock_source_image = MagicMock()
        mock_source_image.minio_key = "source_images/mayorista/photo.jpg"
        mock_source_image_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_source_image
        )

        # Mock job creation
        created_job = MagicMock()
        created_job.id = uuid.uuid4()
        created_job.status = "pending"
        created_job.garment_type = "upper"
        created_job.created_at = datetime.now(timezone.utc)
        mock_tryoff_repo.create = AsyncMock(return_value=created_job)

        with patch("services.tryoff_job_service.celery_app") as mock_celery:
            mock_celery.send_task = MagicMock()

            job = await service.submit_job(
                mayorista_id=mayorista_id,
                source_image_id=source_image_id,
                garment_type="upper",
            )

            assert job.status == "pending"
            assert job.garment_type == "upper"
            mock_tryoff_repo.create.assert_called_once()
            mock_celery.send_task.assert_called_once_with(
                "tasks.tryoff_task.process_tryoff_job",
                args=[str(job.id)],
                queue="tryoff",
            )

    @pytest.mark.asyncio
    async def test_should_submit_batch_jobs(
        self, service, mock_tryoff_repo, mock_source_image_repo
    ):
        mayorista_id = uuid.uuid4()
        source_image_id = uuid.uuid4()

        # Mock source image owned by mayorista
        mock_source_image = MagicMock()
        mock_source_image.minio_key = "source_images/mayorista/photo.jpg"
        mock_source_image_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_source_image
        )

        # Mock batch job creation
        job1 = MagicMock()
        job1.id = uuid.uuid4()
        job1.status = "pending"
        job1.garment_type = "upper"
        job1.created_at = datetime.now(timezone.utc)

        job2 = MagicMock()
        job2.id = uuid.uuid4()
        job2.status = "pending"
        job2.garment_type = "lower"
        job2.created_at = datetime.now(timezone.utc)

        mock_tryoff_repo.create_batch = AsyncMock(return_value=[job1, job2])

        with patch("services.tryoff_job_service.celery_app") as mock_celery:
            mock_celery.send_task = MagicMock()

            jobs = await service.submit_batch(
                mayorista_id=mayorista_id,
                source_image_id=source_image_id,
                garment_types=["upper", "lower"],
            )

            assert len(jobs) == 2
            assert jobs[0].garment_type == "upper"
            assert jobs[1].garment_type == "lower"
            mock_tryoff_repo.create_batch.assert_called_once()
            assert mock_celery.send_task.call_count == 2

    @pytest.mark.asyncio
    async def test_should_deduplicate_garment_types_in_batch(
        self, service, mock_tryoff_repo, mock_source_image_repo
    ):
        mayorista_id = uuid.uuid4()
        source_image_id = uuid.uuid4()

        mock_source_image = MagicMock()
        mock_source_image_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_source_image
        )

        job1 = MagicMock()
        job1.id = uuid.uuid4()
        job1.status = "pending"
        job1.garment_type = "upper"
        job1.created_at = datetime.now(timezone.utc)

        mock_tryoff_repo.create_batch = AsyncMock(return_value=[job1])

        with patch("services.tryoff_job_service.celery_app") as mock_celery:
            mock_celery.send_task = MagicMock()

            jobs = await service.submit_batch(
                mayorista_id=mayorista_id,
                source_image_id=source_image_id,
                garment_types=["upper", "upper", "upper"],  # Duplicates
            )

            assert len(jobs) == 1
            assert jobs[0].garment_type == "upper"
            # Verify only one task was sent
            assert mock_celery.send_task.call_count == 1

    @pytest.mark.asyncio
    async def test_should_reject_source_image_not_found(
        self, service, mock_source_image_repo
    ):
        mayorista_id = uuid.uuid4()
        source_image_id = uuid.uuid4()
        mock_source_image_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(SourceImageNotFoundError, match="Source image not found"):
            await service.submit_job(
                mayorista_id=mayorista_id,
                source_image_id=source_image_id,
                garment_type="upper",
            )

    @pytest.mark.asyncio
    async def test_should_reject_batch_source_image_not_found(
        self, service, mock_source_image_repo
    ):
        mayorista_id = uuid.uuid4()
        source_image_id = uuid.uuid4()
        mock_source_image_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(SourceImageNotFoundError, match="Source image not found"):
            await service.submit_batch(
                mayorista_id=mayorista_id,
                source_image_id=source_image_id,
                garment_types=["upper", "lower"],
            )

    @pytest.mark.asyncio
    async def test_should_get_job_status_with_result_url(
        self, service, mock_tryoff_repo, mock_minio
    ):
        mayorista_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = "complete"
        mock_job.garment_type = "upper"
        mock_job.created_at = datetime.now(timezone.utc)
        mock_job.started_at = datetime.now(timezone.utc)
        mock_job.completed_at = datetime.now(timezone.utc)
        mock_job.output_minio_key = "tryoff/mayorista/job.png"
        mock_job.error_reason = None
        mock_job.retry_count = 0

        mock_tryoff_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_job)
        mock_minio.get_presigned_url = AsyncMock(return_value="http://minio/result.png")

        result = await service.get_job_status(job_id, mayorista_id)

        assert result["status"] == "complete"
        assert result["result_url"] == "http://minio/result.png"

    @pytest.mark.asyncio
    async def test_should_get_job_status_pending_no_result_url(
        self, service, mock_tryoff_repo
    ):
        mayorista_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = "pending"
        mock_job.garment_type = "upper"
        mock_job.created_at = datetime.now(timezone.utc)
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.output_minio_key = None
        mock_job.error_reason = None
        mock_job.retry_count = 0

        mock_tryoff_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_job)

        result = await service.get_job_status(job_id, mayorista_id)

        assert result["status"] == "pending"
        assert result["result_url"] is None

    @pytest.mark.asyncio
    async def test_should_get_job_status_failed_with_error(
        self, service, mock_tryoff_repo
    ):
        mayorista_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = "failed"
        mock_job.garment_type = "upper"
        mock_job.created_at = datetime.now(timezone.utc)
        mock_job.started_at = datetime.now(timezone.utc)
        mock_job.completed_at = datetime.now(timezone.utc)
        mock_job.output_minio_key = None
        mock_job.error_reason = "Model service timeout"
        mock_job.retry_count = 2

        mock_tryoff_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_job)

        result = await service.get_job_status(job_id, mayorista_id)

        assert result["status"] == "failed"
        assert result["error_reason"] == "Model service timeout"
        assert result["retry_count"] == 2
        assert result["result_url"] is None

    @pytest.mark.asyncio
    async def test_should_reject_job_not_found(self, service, mock_tryoff_repo):
        mayorista_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_tryoff_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_tryoff_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(Exception, match="Job not found"):
            await service.get_job_status(job_id, mayorista_id)

    @pytest.mark.asyncio
    async def test_should_reject_job_not_owned(self, service, mock_tryoff_repo):
        mayorista_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_tryoff_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_tryoff_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(Exception, match="do not own"):
            await service.get_job_status(job_id, mayorista_id)

    @pytest.mark.asyncio
    async def test_should_list_jobs_with_pagination(
        self, service, mock_tryoff_repo, mock_minio
    ):
        mayorista_id = uuid.uuid4()

        job1 = MagicMock()
        job1.id = uuid.uuid4()
        job1.status = "complete"
        job1.garment_type = "upper"
        job1.created_at = datetime.now(timezone.utc)
        job1.started_at = datetime.now(timezone.utc)
        job1.completed_at = datetime.now(timezone.utc)
        job1.output_minio_key = "tryoff/mayorista/job1.png"
        job1.error_reason = None
        job1.retry_count = 0

        job2 = MagicMock()
        job2.id = uuid.uuid4()
        job2.status = "pending"
        job2.garment_type = "lower"
        job2.created_at = datetime.now(timezone.utc)
        job2.started_at = None
        job2.completed_at = None
        job2.output_minio_key = None
        job2.error_reason = None
        job2.retry_count = 0

        mock_tryoff_repo.list_by_mayorista = AsyncMock(return_value=([job1, job2], 2))
        mock_minio.get_presigned_url = AsyncMock(return_value="http://minio/result.png")

        results, total = await service.list_jobs(mayorista_id, page=1, page_size=20)

        assert total == 2
        assert len(results) == 2
        assert results[0]["status"] == "complete"
        assert results[0]["result_url"] == "http://minio/result.png"
        assert results[1]["status"] == "pending"
        assert results[1]["result_url"] is None
