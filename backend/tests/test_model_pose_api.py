import uuid
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import login_user, register_user

PRESIGNED_URL = "http://minio:9000/presigned"

PNG_BYTES = b"\x89PNG" + b"\x00" * 100
OVERSIZED_BYTES = b"\xff\xd8\xff" + b"\x00" * (10 * 1024 * 1024)
TEXT_BYTES = b"this is definitely not an image"


@pytest.fixture(autouse=True)
def mock_minio():
    """Mock MinIO at the client boundary — storage is not under test."""
    with patch(
        "core.minio_client.MinIOClient.upload_file", new=AsyncMock(return_value=None)
    ), patch(
        "core.minio_client.MinIOClient.get_presigned_url",
        new=AsyncMock(return_value=PRESIGNED_URL),
    ):
        yield


def _png_upload():
    return {"file": ("pose.png", PNG_BYTES, "image/png")}


async def _auth_cookies(client, email="pose@mayorista.com"):
    await register_user(client, email=email)
    response = await login_user(client, email=email)
    return response.cookies


async def _create_model(client, cookies, name="Test Model"):
    response = await client.post("/api/models", json={"name": name}, cookies=cookies)
    assert response.status_code == 201
    return response.json()


async def _upload_pose(client, cookies, model_id, pose):
    return await client.post(
        f"/api/models/{model_id}/poses",
        files=_png_upload(),
        data={"pose": pose},
        cookies=cookies,
    )


class TestCreateModel:
    @pytest.mark.asyncio
    async def test_should_create_model_when_authenticated(self, client):
        cookies = await _auth_cookies(client)

        response = await client.post(
            "/api/models", json={"name": "Valentina"}, cookies=cookies
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Valentina"
        assert uuid.UUID(data["id"])
        assert uuid.UUID(data["mayorista_id"])
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_should_trim_whitespace_in_name(self, client):
        cookies = await _auth_cookies(client)

        response = await client.post(
            "/api/models", json={"name": "  Valentina  "}, cookies=cookies
        )

        assert response.status_code == 201
        assert response.json()["name"] == "Valentina"

    @pytest.mark.asyncio
    async def test_should_reject_when_name_missing(self, client):
        cookies = await _auth_cookies(client)

        response = await client.post("/api/models", json={}, cookies=cookies)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_should_reject_when_name_blank(self, client):
        cookies = await _auth_cookies(client)

        response = await client.post(
            "/api/models", json={"name": "   "}, cookies=cookies
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_should_reject_when_name_exceeds_255_chars(self, client):
        cookies = await _auth_cookies(client)

        response = await client.post(
            "/api/models", json={"name": "x" * 256}, cookies=cookies
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_should_allow_duplicate_names_for_same_mayorista(self, client):
        cookies = await _auth_cookies(client)

        first = await client.post(
            "/api/models", json={"name": "Valentina"}, cookies=cookies
        )
        second = await client.post(
            "/api/models", json={"name": "Valentina"}, cookies=cookies
        )

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["id"] != second.json()["id"]

    @pytest.mark.asyncio
    async def test_should_return_401_when_not_authenticated(self, client):
        response = await client.post("/api/models", json={"name": "Valentina"})

        assert response.status_code == 401


class TestUploadPosePhoto:
    @pytest.mark.asyncio
    async def test_should_upload_pose_when_valid(self, client):
        cookies = await _auth_cookies(client)
        model = await _create_model(client, cookies)

        response = await _upload_pose(client, cookies, model["id"], "front")

        assert response.status_code == 201
        data = response.json()
        assert data["pose"] == "front"
        assert data["model_id"] == model["id"]
        assert data["presigned_url"] == PRESIGNED_URL
        assert "uploaded_at" in data

    @pytest.mark.asyncio
    async def test_should_accept_all_three_pose_types(self, client):
        cookies = await _auth_cookies(client)
        model = await _create_model(client, cookies)

        for pose in ("front", "side", "back"):
            response = await _upload_pose(client, cookies, model["id"], pose)
            assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_should_reject_duplicate_pose_type(self, client):
        cookies = await _auth_cookies(client)
        model = await _create_model(client, cookies)
        await _upload_pose(client, cookies, model["id"], "front")

        response = await _upload_pose(client, cookies, model["id"], "front")

        assert response.status_code == 400
        assert response.json()["detail"] == "Pose type already exists for this model"

    @pytest.mark.asyncio
    async def test_should_reject_duplicate_via_db_constraint_when_fast_path_raced(
        self, client
    ):
        """ADR-010: concurrent duplicate uploads — DB unique constraint is authoritative."""
        cookies = await _auth_cookies(client)
        model = await _create_model(client, cookies)
        await _upload_pose(client, cookies, model["id"], "front")

        # Simulate the race: fast-path check passes (stale read), DB rejects.
        with patch(
            "repositories.media_repo.ModelPhotoRepo.pose_exists",
            new=AsyncMock(return_value=False),
        ):
            response = await _upload_pose(client, cookies, model["id"], "front")

        assert response.status_code == 400
        assert response.json()["detail"] == "Pose type already exists for this model"

    @pytest.mark.asyncio
    async def test_should_reject_pose_outside_enum(self, client):
        cookies = await _auth_cookies(client)
        model = await _create_model(client, cookies)

        response = await _upload_pose(client, cookies, model["id"], "profile")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_should_reject_non_image_file(self, client):
        cookies = await _auth_cookies(client)
        model = await _create_model(client, cookies)

        response = await client.post(
            f"/api/models/{model['id']}/poses",
            files={"file": ("notes.txt", TEXT_BYTES, "text/plain")},
            data={"pose": "front"},
            cookies=cookies,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_should_reject_file_over_10mb(self, client):
        cookies = await _auth_cookies(client)
        model = await _create_model(client, cookies)

        response = await client.post(
            f"/api/models/{model['id']}/poses",
            files={"file": ("big.jpg", OVERSIZED_BYTES, "image/jpeg")},
            data={"pose": "front"},
            cookies=cookies,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_should_return_404_when_model_does_not_exist(self, client):
        cookies = await _auth_cookies(client)

        response = await _upload_pose(client, cookies, uuid.uuid4(), "front")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_should_return_404_when_model_owned_by_another_mayorista(self, client):
        owner_cookies = await _auth_cookies(client, email="owner@mayorista.com")
        model = await _create_model(client, owner_cookies)
        intruder_cookies = await _auth_cookies(client, email="intruder@mayorista.com")

        response = await _upload_pose(client, intruder_cookies, model["id"], "front")

        # ADR-013: 404, never 403 — do not leak existence.
        assert response.status_code == 404


class TestListModelPoses:
    @pytest.mark.asyncio
    async def test_should_list_poses_ordered_front_side_back(self, client):
        cookies = await _auth_cookies(client)
        model = await _create_model(client, cookies)
        # Upload in reverse order to prove ordering is not insertion-based.
        await _upload_pose(client, cookies, model["id"], "back")
        await _upload_pose(client, cookies, model["id"], "side")
        await _upload_pose(client, cookies, model["id"], "front")

        response = await client.get(f"/api/models/{model['id']}/poses", cookies=cookies)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert [item["pose"] for item in data["items"]] == ["front", "side", "back"]
        assert all(item["presigned_url"] == PRESIGNED_URL for item in data["items"])

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_model_has_no_poses(self, client):
        cookies = await _auth_cookies(client)
        model = await _create_model(client, cookies)

        response = await client.get(f"/api/models/{model['id']}/poses", cookies=cookies)

        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0}

    @pytest.mark.asyncio
    async def test_should_return_404_when_model_does_not_exist(self, client):
        cookies = await _auth_cookies(client)

        response = await client.get(f"/api/models/{uuid.uuid4()}/poses", cookies=cookies)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_should_return_404_when_model_owned_by_another_mayorista(self, client):
        owner_cookies = await _auth_cookies(client, email="owner@mayorista.com")
        model = await _create_model(client, owner_cookies)
        await _upload_pose(client, owner_cookies, model["id"], "front")
        intruder_cookies = await _auth_cookies(client, email="intruder@mayorista.com")

        response = await client.get(
            f"/api/models/{model['id']}/poses", cookies=intruder_cookies
        )

        # ADR-013: 404, never 403 — do not leak existence.
        assert response.status_code == 404
