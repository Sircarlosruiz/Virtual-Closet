import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.vton_job import VTONJob, ClothType, JobStatus
from repositories.vton_job_repo import VTONJobRepo
from services.vton_job_service import (
    VTONJobService,
    PhotoNotFoundError,
    PhotoOwnershipError,
)
from services.providers.vton_provider import VTONProvider


# --- Unit Tests: VTONJobService ---


class TestVTONJobService:
    @pytest.fixture
    def mock_vton_repo(self):
        return AsyncMock(spec=VTONJobRepo)

    @pytest.fixture
    def mock_garment_repo(self):
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_model_repo(self):
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_minio(self):
        client = AsyncMock()
        client.get_presigned_url = AsyncMock(return_value="http://minio/presigned")
        client.upload_file = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_vton_repo, mock_garment_repo, mock_model_repo, mock_minio):
        return VTONJobService(
            mock_vton_repo, mock_garment_repo, mock_model_repo, mock_minio
        )

    @pytest.mark.asyncio
    async def test_should_submit_job_with_own_garment_and_own_model(
        self, service, mock_vton_repo, mock_garment_repo, mock_model_repo
    ):
        mayorista_id = uuid.uuid4()
        garment_id = uuid.uuid4()
        model_id = uuid.uuid4()

        # Mock garment owned by mayorista
        mock_garment = MagicMock()
        mock_garment.minio_key = "garments/mayorista/photo.jpg"
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_garment)

        # Mock model owned by mayorista
        mock_model = MagicMock()
        mock_model.is_curated = False
        mock_model.mayorista_id = mayorista_id
        mock_model_repo.get_by_id = AsyncMock(return_value=mock_model)

        # Mock job creation
        created_job = MagicMock()
        created_job.id = uuid.uuid4()
        created_job.status = "queued"
        created_job.cloth_type = "upper_body"
        created_job.created_at = datetime.now(timezone.utc)
        mock_vton_repo.create = AsyncMock(return_value=created_job)

        with patch("services.vton_job_service.celery_app") as mock_celery:
            mock_celery.send_task = MagicMock()

            job, presigned_url = await service.submit_job(
                mayorista_id=mayorista_id,
                garment_photo_id=garment_id,
                model_photo_id=model_id,
                cloth_type="upper_body",
            )

            assert job.status == "queued"
            assert job.cloth_type == "upper_body"
            mock_vton_repo.create.assert_called_once()
            mock_celery.send_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_submit_job_with_curated_model(
        self, service, mock_vton_repo, mock_garment_repo, mock_model_repo
    ):
        mayorista_id = uuid.uuid4()
        garment_id = uuid.uuid4()
        model_id = uuid.uuid4()

        mock_garment = MagicMock()
        mock_garment.minio_key = "garments/mayorista/photo.jpg"
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_garment)

        # Curated model — no ownership check needed
        mock_model = MagicMock()
        mock_model.is_curated = True
        mock_model.mayorista_id = None
        mock_model_repo.get_by_id = AsyncMock(return_value=mock_model)

        created_job = MagicMock()
        created_job.id = uuid.uuid4()
        created_job.status = "queued"
        created_job.cloth_type = "dress"
        created_job.created_at = datetime.now(timezone.utc)
        mock_vton_repo.create = AsyncMock(return_value=created_job)

        with patch("services.vton_job_service.celery_app") as mock_celery:
            mock_celery.send_task = MagicMock()

            job, _ = await service.submit_job(
                mayorista_id=mayorista_id,
                garment_photo_id=garment_id,
                model_photo_id=model_id,
                cloth_type="dress",
            )

            assert job.status == "queued"
            assert job.cloth_type == "dress"

    @pytest.mark.asyncio
    async def test_should_reject_garment_not_found(
        self, service, mock_garment_repo
    ):
        mayorista_id = uuid.uuid4()
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_garment_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(PhotoNotFoundError, match="Garment photo not found"):
            await service.submit_job(
                mayorista_id=mayorista_id,
                garment_photo_id=uuid.uuid4(),
                model_photo_id=uuid.uuid4(),
                cloth_type="upper_body",
            )

    @pytest.mark.asyncio
    async def test_should_reject_garment_not_owned(
        self, service, mock_garment_repo
    ):
        mayorista_id = uuid.uuid4()
        # Not owned by mayorista but exists
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_garment_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(PhotoOwnershipError, match="do not own"):
            await service.submit_job(
                mayorista_id=mayorista_id,
                garment_photo_id=uuid.uuid4(),
                model_photo_id=uuid.uuid4(),
                cloth_type="upper_body",
            )

    @pytest.mark.asyncio
    async def test_should_reject_model_not_found(
        self, service, mock_garment_repo, mock_model_repo
    ):
        mayorista_id = uuid.uuid4()
        mock_garment = MagicMock()
        mock_garment.minio_key = "garments/mayorista/photo.jpg"
        mock_garment_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_garment)
        mock_model_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(PhotoNotFoundError, match="Model photo not found"):
            await service.submit_job(
                mayorista_id=mayorista_id,
                garment_photo_id=uuid.uuid4(),
                model_photo_id=uuid.uuid4(),
                cloth_type="upper_body",
            )

    @pytest.mark.asyncio
    async def test_should_get_job_status_with_result_url(
        self, service, mock_vton_repo, mock_minio
    ):
        mayorista_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = "completed"
        mock_job.created_at = datetime.now(timezone.utc)
        mock_job.started_at = datetime.now(timezone.utc)
        mock_job.completed_at = datetime.now(timezone.utc)
        mock_job.result_minio_key = "results/mayorista/job.jpg"
        mock_job.error_reason = None
        mock_job.retry_count = 0

        mock_vton_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_job)
        mock_minio.get_presigned_url = AsyncMock(return_value="http://minio/result.jpg")

        result = await service.get_job_status(job_id, mayorista_id)

        assert result["status"] == "completed"
        assert result["result_url"] == "http://minio/result.jpg"

    @pytest.mark.asyncio
    async def test_should_get_job_status_queued_no_result_url(
        self, service, mock_vton_repo
    ):
        mayorista_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = "queued"
        mock_job.created_at = datetime.now(timezone.utc)
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.result_minio_key = None
        mock_job.error_reason = None
        mock_job.retry_count = 0

        mock_vton_repo.get_by_id_and_mayorista = AsyncMock(return_value=mock_job)

        result = await service.get_job_status(job_id, mayorista_id)

        assert result["status"] == "queued"
        assert result["result_url"] is None

    @pytest.mark.asyncio
    async def test_should_reject_job_not_found(self, service, mock_vton_repo):
        mayorista_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_vton_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_vton_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(PhotoNotFoundError, match="Job not found"):
            await service.get_job_status(job_id, mayorista_id)

    @pytest.mark.asyncio
    async def test_should_reject_job_not_owned(self, service, mock_vton_repo):
        mayorista_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_vton_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_vton_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(PhotoOwnershipError, match="do not own"):
            await service.get_job_status(job_id, mayorista_id)


# --- Unit Tests: VTONProvider Factory ---


class TestVTONProviderFactory:
    def test_should_get_local_provider(self):
        from services.providers.vton_provider import get_vton_provider

        with patch("services.providers.vton_provider.settings") as mock_settings:
            mock_settings.VTON_PROVIDER = "local"
            with patch(
                "services.providers.local_gpu_provider.LocalGPUProvider"
            ) as mock_cls:
                mock_cls.return_value = MagicMock()
                provider = get_vton_provider()
                mock_cls.assert_called_once()

    def test_should_get_replicate_provider(self):
        from services.providers.vton_provider import get_vton_provider

        with patch("services.providers.vton_provider.settings") as mock_settings:
            mock_settings.VTON_PROVIDER = "replicate"
            with patch(
                "services.providers.replicate_provider.ReplicateProvider"
            ) as mock_cls:
                mock_cls.return_value = MagicMock()
                provider = get_vton_provider()
                mock_cls.assert_called_once()

    def test_should_reject_unknown_provider(self):
        from services.providers.vton_provider import get_vton_provider

        with patch("services.providers.vton_provider.settings") as mock_settings:
            mock_settings.VTON_PROVIDER = "unknown"
            with pytest.raises(ValueError, match="Unknown VTON_PROVIDER"):
                get_vton_provider()
