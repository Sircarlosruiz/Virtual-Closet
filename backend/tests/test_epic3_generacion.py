import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import register_user, login_user


@pytest.fixture(autouse=True)
def mock_storage():
    """Simulate uploaded objects at the storage boundary; keep DB/services real."""
    with (
        patch("services.prenda_service.ensure_minio_buckets", new_callable=AsyncMock),
        patch("services.storage_service.StorageService.object_exists", new_callable=AsyncMock, return_value=True),
        patch("services.storage_service.StorageService.generate_upload_url", new_callable=AsyncMock, return_value="http://storage/upload"),
        patch("services.storage_service.StorageService.generate_download_url", new_callable=AsyncMock, return_value="http://storage/image.jpg"),
    ):
        yield


@pytest.mark.asyncio
async def test_list_modelos_ia_returns_list(client_with_seeds):
    await register_user(client_with_seeds)
    await login_user(client_with_seeds)
    response = await client_with_seeds.get("/api/modelos-ia")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 6


@pytest.mark.asyncio
async def test_list_modelos_ia_includes_shared_models_from_all_plans(client_with_seeds):
    await register_user(client_with_seeds)
    await login_user(client_with_seeds)
    response = await client_with_seeds.get("/api/modelos-ia")
    data = response.json()
    base_models = [m for m in data if m["plan_minimo"] == "base"]
    assert len(base_models) == 4
    assert len([m for m in data if m["plan_minimo"] == "pro"]) == 2


@pytest.mark.asyncio
async def test_list_modelos_ia_requires_auth(client):
    response = await client.get("/api/modelos-ia")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_crear_generacion_success(client_with_seeds):
    await register_user(client_with_seeds)
    await login_user(client_with_seeds)

    upload_resp = await client_with_seeds.get("/api/prendas/upload-url?extension=jpg")
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()

    prenda_resp = await client_with_seeds.post(
        "/api/prendas",
        json={"prenda_id": upload_data["prenda_id"], "object_key": upload_data["object_key"], "nombre": "Test Prenda"},
    )
    assert prenda_resp.status_code == 201, prenda_resp.text
    prenda_id = prenda_resp.json()["id"]

    modelos_resp = await client_with_seeds.get("/api/modelos-ia")
    modelos = modelos_resp.json()
    modelo_id = next(m["id"] for m in modelos if m["plan_minimo"] == "base")

    gen_resp = await client_with_seeds.post(
        "/api/generaciones",
        json={"prenda_id": prenda_id, "modelo_ia_id": modelo_id},
    )
    assert gen_resp.status_code == 201, gen_resp.text
    gen_data = gen_resp.json()
    assert gen_data["estado"] == "procesando"
    assert gen_data["prenda_id"] == prenda_id
    assert gen_data["modelo_ia_id"] == modelo_id
    assert "id" in gen_data


@pytest.mark.asyncio
async def test_crear_generacion_invalid_prenda(client_with_seeds):
    await register_user(client_with_seeds)
    await login_user(client_with_seeds)

    response = await client_with_seeds.post(
        "/api/generaciones",
        json={"prenda_id": "00000000-0000-0000-0000-000000000000", "modelo_ia_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_crear_generacion_requires_auth(client):
    response = await client.post(
        "/api/generaciones",
        json={"prenda_id": "00000000-0000-0000-0000-000000000000", "modelo_ia_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_generacion(client_with_seeds):
    await register_user(client_with_seeds)
    await login_user(client_with_seeds)

    upload_resp = await client_with_seeds.get("/api/prendas/upload-url?extension=jpg")
    upload_data = upload_resp.json()
    prenda_resp = await client_with_seeds.post(
        "/api/prendas",
        json={"prenda_id": upload_data["prenda_id"], "object_key": upload_data["object_key"], "nombre": "Test Prenda"},
    )
    assert prenda_resp.status_code == 201, prenda_resp.text
    prenda_id = prenda_resp.json()["id"]

    modelos_resp = await client_with_seeds.get("/api/modelos-ia")
    modelos = modelos_resp.json()

    gen_resp = await client_with_seeds.post(
        "/api/generaciones",
        json={"prenda_id": prenda_id, "modelo_ia_id": next(m["id"] for m in modelos if m["plan_minimo"] == "base")},
    )
    assert gen_resp.status_code == 201, gen_resp.text
    generacion_id = gen_resp.json()["id"]

    get_resp = await client_with_seeds.get(f"/api/generaciones/{generacion_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == generacion_id


@pytest.mark.asyncio
async def test_list_generaciones_by_prenda(client_with_seeds):
    await register_user(client_with_seeds)
    await login_user(client_with_seeds)

    upload_resp = await client_with_seeds.get("/api/prendas/upload-url?extension=jpg")
    upload_data = upload_resp.json()
    prenda_resp = await client_with_seeds.post(
        "/api/prendas",
        json={"prenda_id": upload_data["prenda_id"], "object_key": upload_data["object_key"], "nombre": "Test Prenda"},
    )
    assert prenda_resp.status_code == 201, prenda_resp.text
    prenda_id = prenda_resp.json()["id"]

    modelos_resp = await client_with_seeds.get("/api/modelos-ia")
    modelos = modelos_resp.json()

    gen_resp = await client_with_seeds.post(
        "/api/generaciones",
        json={"prenda_id": prenda_id, "modelo_ia_id": next(m["id"] for m in modelos if m["plan_minimo"] == "base")},
    )
    assert gen_resp.status_code == 201, gen_resp.text

    list_resp = await client_with_seeds.get(f"/api/prendas/{prenda_id}/generaciones")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
