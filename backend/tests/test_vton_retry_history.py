import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.retry_policy import RetryPolicy, is_retriable_error
from services.vton_job_service import VTONJobService


# --- Unit Tests: RetryPolicy ---


class TestRetryPolicy:
    def test_should_calculate_exponential_backoff(self):
        policy = RetryPolicy(max_retries=3, base_delay=30, max_delay=600)

        assert policy.get_delay(0) == 30    # 30 * 2^0 = 30
        assert policy.get_delay(1) == 60    # 30 * 2^1 = 60
        assert policy.get_delay(2) == 120   # 30 * 2^2 = 120
        assert policy.get_delay(3) == 240   # 30 * 2^3 = 240

    def test_should_cap_delay_at_max(self):
        policy = RetryPolicy(max_retries=10, base_delay=30, max_delay=600)

        assert policy.get_delay(0) == 30
        assert policy.get_delay(4) == 480   # 30 * 2^4 = 480
        assert policy.get_delay(5) == 600   # 30 * 2^5 = 960 → capped at 600
        assert policy.get_delay(10) == 600  # still capped

    def test_should_allow_retry_when_under_limit(self):
        policy = RetryPolicy(max_retries=3)

        assert policy.should_retry(0) is True
        assert policy.should_retry(1) is True
        assert policy.should_retry(2) is True
        assert policy.should_retry(3) is False

    def test_should_use_defaults_from_settings(self):
        with patch("services.retry_policy.settings") as mock_settings:
            mock_settings.VTON_MAX_RETRIES = 5
            mock_settings.VTON_RETRY_BASE_DELAY_SECONDS = 60
            mock_settings.VTON_RETRY_MAX_DELAY_SECONDS = 1200

            policy = RetryPolicy()

            assert policy.max_retries == 5
            assert policy.base_delay == 60
            assert policy.max_delay == 1200


# --- Unit Tests: Error Classification ---


class TestIsRetriableError:
    def test_timeout_is_retriable(self):
        assert is_retriable_error(TimeoutError("connection timed out")) is True

    def test_connection_error_is_retriable(self):
        assert is_retriable_error(ConnectionError("connection refused")) is True

    def test_os_error_is_retriable(self):
        assert is_retriable_error(OSError("network unreachable")) is True

    def test_value_error_not_found_is_not_retriable(self):
        assert is_retriable_error(ValueError("Garment photo not found")) is False

    def test_value_error_invalid_is_not_retriable(self):
        assert is_retriable_error(ValueError("Invalid cloth type")) is False

    def test_value_error_unauthorized_is_not_retriable(self):
        assert is_retriable_error(ValueError("Unauthorized access")) is False

    def test_generic_value_error_is_retriable(self):
        assert is_retriable_error(ValueError("some unknown error")) is True

    def test_httpx_429_is_retriable(self):
        import httpx

        response = MagicMock()
        response.status_code = 429
        exc = httpx.HTTPStatusError("Rate limited", request=MagicMock(), response=response)
        assert is_retriable_error(exc) is True

    def test_httpx_500_is_retriable(self):
        import httpx

        response = MagicMock()
        response.status_code = 500
        exc = httpx.HTTPStatusError("Server error", request=MagicMock(), response=response)
        assert is_retriable_error(exc) is True

    def test_httpx_400_is_not_retriable(self):
        import httpx

        response = MagicMock()
        response.status_code = 400
        exc = httpx.HTTPStatusError("Bad request", request=MagicMock(), response=response)
        assert is_retriable_error(exc) is False

    def test_httpx_401_is_not_retriable(self):
        import httpx

        response = MagicMock()
        response.status_code = 401
        exc = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=response)
        assert is_retriable_error(exc) is False

    def test_httpx_403_is_not_retriable(self):
        import httpx

        response = MagicMock()
        response.status_code = 403
        exc = httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=response)
        assert is_retriable_error(exc) is False

    def test_httpx_404_is_not_retriable(self):
        import httpx

        response = MagicMock()
        response.status_code = 404
        exc = httpx.HTTPStatusError("Not found", request=MagicMock(), response=response)
        assert is_retriable_error(exc) is False


# --- Unit Tests: VTONJobService.list_jobs ---


class TestVTONJobServiceListJobs:
    @pytest.fixture
    def mock_vton_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_garment_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_model_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_minio(self):
        client = AsyncMock()
        client.get_presigned_url = AsyncMock(return_value="http://minio/presigned")
        return client

    @pytest.fixture
    def service(self, mock_vton_repo, mock_garment_repo, mock_model_repo, mock_minio):
        return VTONJobService(
            mock_vton_repo, mock_garment_repo, mock_model_repo, mock_minio
        )

    @pytest.mark.asyncio
    async def test_should_list_jobs_with_pagination(
        self, service, mock_vton_repo
    ):
        mayorista_id = uuid.uuid4()
        mock_jobs = [
            MagicMock(
                id=uuid.uuid4(),
                status="completed",
                cloth_type="upper_body",
                created_at=datetime.now(timezone.utc),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                result_minio_key="results/mayorista/job1.jpg",
                error_reason=None,
                retry_count=0,
            ),
            MagicMock(
                id=uuid.uuid4(),
                status="queued",
                cloth_type="dress",
                created_at=datetime.now(timezone.utc),
                started_at=None,
                completed_at=None,
                result_minio_key=None,
                error_reason=None,
                retry_count=0,
            ),
        ]
        mock_vton_repo.list_by_mayorista = AsyncMock(return_value=(mock_jobs, 15))

        items, total = await service.list_jobs(mayorista_id, page=1, page_size=2)

        assert len(items) == 2
        assert total == 15
        assert items[0]["status"] == "completed"
        assert items[0]["result_url"] == "http://minio/presigned"
        assert items[1]["status"] == "queued"
        assert items[1]["result_url"] is None

    @pytest.mark.asyncio
    async def test_should_list_failed_jobs_with_error_reason(
        self, service, mock_vton_repo
    ):
        mayorista_id = uuid.uuid4()
        mock_job = MagicMock(
            id=uuid.uuid4(),
            status="failed",
            cloth_type="lower_body",
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            result_minio_key=None,
            error_reason="Failed after 3 retries: Connection refused",
            retry_count=3,
        )
        mock_vton_repo.list_by_mayorista = AsyncMock()
        mock_vton_repo.list_by_mayorista.return_value = ([mock_job], 1)

        items, total = await service.list_jobs(mayorista_id)

        assert len(items) == 1
        assert items[0]["status"] == "failed"
        assert items[0]["error_reason"] == "Failed after 3 retries: Connection refused"
        assert items[0]["retry_count"] == 3
        assert items[0]["result_url"] is None
