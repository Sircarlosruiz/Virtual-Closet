import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.conftest import register_user, login_user


class TestTryoffAPI:
    @pytest.mark.asyncio
    async def test_should_submit_single_job(self, client):
        # Register and login
        await register_user(client)
        login_response = await login_user(client)
        cookies = login_response.cookies

        # Create a source image first
        source_image_id = uuid.uuid4()
        
        with patch("repositories.tryoff_job_repo.SourceImageRepo.get_by_id_and_mayorista") as mock_get:
            mock_source_image = MagicMock()
            mock_source_image.id = source_image_id
            mock_get.return_value = mock_source_image

            with patch("repositories.tryoff_job_repo.TryoffJobRepo.create") as mock_create:
                mock_job = MagicMock()
                mock_job.id = uuid.uuid4()
                mock_job.status = "pending"
                mock_job.garment_type = "upper"
                mock_job.created_at = datetime.now(timezone.utc)
                mock_create.return_value = mock_job

                with patch("services.tryoff_job_service.celery_app.send_task") as mock_send:
                    mock_send.return_value = None

                    response = await client.post(
                        "/api/tryoff/jobs",
                        json={
                            "source_image_id": str(source_image_id),
                            "garment_type": "upper",
                        },
                        cookies=cookies,
                    )

                    assert response.status_code == 201
                    data = response.json()
                    assert data["status"] == "pending"
                    assert data["garment_type"] == "upper"
                    assert "job_id" in data
                    assert "created_at" in data

    @pytest.mark.asyncio
    async def test_should_submit_batch_jobs(self, client):
        await register_user(client)
        login_response = await login_user(client)
        cookies = login_response.cookies

        source_image_id = uuid.uuid4()

        with patch("repositories.tryoff_job_repo.SourceImageRepo.get_by_id_and_mayorista") as mock_get:
            mock_source_image = MagicMock()
            mock_source_image.id = source_image_id
            mock_get.return_value = mock_source_image

            with patch("repositories.tryoff_job_repo.TryoffJobRepo.create_batch") as mock_create:
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

                mock_create.return_value = [job1, job2]

                with patch("services.tryoff_job_service.celery_app.send_task") as mock_send:
                    mock_send.return_value = None

                    response = await client.post(
                        "/api/tryoff/jobs/batch",
                        json={
                            "source_image_id": str(source_image_id),
                            "garment_types": ["upper", "lower"],
                        },
                        cookies=cookies,
                    )

                    assert response.status_code == 201
                    data = response.json()
                    assert "jobs" in data
                    assert len(data["jobs"]) == 2
                    assert data["jobs"][0]["garment_type"] == "upper"
                    assert data["jobs"][1]["garment_type"] == "lower"

    @pytest.mark.asyncio
    async def test_should_reject_invalid_garment_type(self, client):
        await register_user(client)
        login_response = await login_user(client)
        cookies = login_response.cookies

        response = await client.post(
            "/api/tryoff/jobs",
            json={
                "source_image_id": str(uuid.uuid4()),
                "garment_type": "invalid_type",
            },
            cookies=cookies,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_should_reject_empty_garment_types_batch(self, client):
        await register_user(client)
        login_response = await login_user(client)
        cookies = login_response.cookies

        response = await client.post(
            "/api/tryoff/jobs/batch",
            json={
                "source_image_id": str(uuid.uuid4()),
                "garment_types": [],
            },
            cookies=cookies,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_should_reject_source_image_not_found(self, client):
        await register_user(client)
        login_response = await login_user(client)
        cookies = login_response.cookies

        with patch("repositories.tryoff_job_repo.SourceImageRepo.get_by_id_and_mayorista") as mock_get:
            mock_get.return_value = None

            response = await client.post(
                "/api/tryoff/jobs",
                json={
                    "source_image_id": str(uuid.uuid4()),
                    "garment_type": "upper",
                },
                cookies=cookies,
            )

            assert response.status_code == 404
            assert "Source image not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_should_get_job_status(self, client):
        await register_user(client)
        login_response = await login_user(client)
        cookies = login_response.cookies

        job_id = uuid.uuid4()

        with patch("repositories.tryoff_job_repo.TryoffJobRepo.get_by_id_and_mayorista") as mock_get:
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
            mock_get.return_value = mock_job

            with patch("core.minio_client.MinIOClient.get_presigned_url") as mock_presigned:
                mock_presigned.return_value = "http://minio/result.png"

                response = await client.get(
                    f"/api/tryoff/jobs/{job_id}",
                    cookies=cookies,
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "complete"
                assert data["result_url"] == "http://minio/result.png"
                assert data["garment_type"] == "upper"

    @pytest.mark.asyncio
    async def test_should_reject_job_not_found(self, client):
        await register_user(client)
        login_response = await login_user(client)
        cookies = login_response.cookies

        with patch("repositories.tryoff_job_repo.TryoffJobRepo.get_by_id_and_mayorista") as mock_get:
            mock_get.return_value = None

            with patch("repositories.tryoff_job_repo.TryoffJobRepo.get_by_id") as mock_get_any:
                mock_get_any.return_value = None

                response = await client.get(
                    f"/api/tryoff/jobs/{uuid.uuid4()}",
                    cookies=cookies,
                )

                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_should_reject_job_not_owned(self, client):
        await register_user(client)
        login_response = await login_user(client)
        cookies = login_response.cookies

        with patch("repositories.tryoff_job_repo.TryoffJobRepo.get_by_id_and_mayorista") as mock_get:
            mock_get.return_value = None

            with patch("repositories.tryoff_job_repo.TryoffJobRepo.get_by_id") as mock_get_any:
                mock_get_any.return_value = MagicMock()  # Job exists but not owned

                response = await client.get(
                    f"/api/tryoff/jobs/{uuid.uuid4()}",
                    cookies=cookies,
                )

                assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_should_list_jobs_with_pagination(self, client):
        await register_user(client)
        login_response = await login_user(client)
        cookies = login_response.cookies

        with patch("repositories.tryoff_job_repo.TryoffJobRepo.list_by_mayorista") as mock_list:
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

            mock_list.return_value = ([job1], 1)

            with patch("core.minio_client.MinIOClient.get_presigned_url") as mock_presigned:
                mock_presigned.return_value = "http://minio/result.png"

                response = await client.get(
                    "/api/tryoff/jobs?page=1&page_size=20",
                    cookies=cookies,
                )

                assert response.status_code == 200
                data = response.json()
                assert "items" in data
                assert "total" in data
                assert "page" in data
                assert "page_size" in data
                assert data["total"] == 1
                assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_should_require_authentication(self, client):
        # Try to submit job without authentication
        response = await client.post(
            "/api/tryoff/jobs",
            json={
                "source_image_id": str(uuid.uuid4()),
                "garment_type": "upper",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_should_require_authentication_for_status(self, client):
        response = await client.get(f"/api/tryoff/jobs/{uuid.uuid4()}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_should_require_authentication_for_list(self, client):
        response = await client.get("/api/tryoff/jobs")
        assert response.status_code == 401
