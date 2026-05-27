import io
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from main import app
from models.media import GarmentPhoto, ModelPhoto
from models.mayorista import Mayorista
from repositories.media_repo import GarmentPhotoRepo, ModelPhotoRepo
from services.media_service import MediaUploadService
from services.model_library_service import ModelLibraryService
from core.minio_client import MinIOClient
from unittest.mock import AsyncMock, patch, MagicMock

# --- Fixtures ---


@pytest_asyncio.fixture
async def mayorista_with_session(client: AsyncClient):
    """Register and login a test user, return the Mayorista object."""
    from tests.conftest import register_user, login_user

    await register_user(client, email="media@test.com", password="testpass123")
    resp = await login_user(client, email="media@test.com", password="testpass123")

    async for session in app.dependency_overrides.get(get_db, get_db)():
        result = await session.execute(
            select(Mayorista).where(Mayorista.email == "media@test.com")
        )
        mayorista = result.scalar_one()
        yield mayorista
        break


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    """Minimal valid JPEG bytes (1x1 pixel red image)."""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e"
        b"\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7teletext7teletext(7teletext\x1c"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01"
        b"\x02\x03\x00\x04\x11\x05\x12!1A\x13Qa\x14q\x81\x91\xa1\x06#B\xb1\xc1\x15R\xd1\xf0$3br"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd4\xff\xd9"
    )


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Minimal valid PNG bytes (1x1 pixel)."""
    import struct
    import zlib

    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr = png_chunk(b"IHDR", ihdr_data)
    raw_data = b"\x00\xff\x00\x00"
    idat = png_chunk(b"IDAT", zlib.compress(raw_data))
    iend = png_chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


# --- Unit Tests: File Validation ---


class TestFileValidation:
    def test_should_accept_valid_jpeg(self, sample_jpeg_bytes):
        from services.media_service import _validate_file

        _validate_file(sample_jpeg_bytes, "image/jpeg")

    def test_should_accept_valid_png(self, sample_png_bytes):
        from services.media_service import _validate_file

        _validate_file(sample_png_bytes, "image/png")

    def test_should_reject_empty_file(self):
        from services.media_service import _validate_file, EmptyFileError

        with pytest.raises(EmptyFileError):
            _validate_file(b"", "image/jpeg")

    def test_should_reject_non_image_magic_bytes(self):
        """Should reject when magic bytes don't match JPEG or PNG, regardless of content_type."""
        from services.media_service import _validate_file, InvalidFileTypeError

        # PDF magic bytes: %PDF
        pdf_bytes = b"%PDF-1.4 fake pdf content here with enough data"

        with pytest.raises(InvalidFileTypeError):
            _validate_file(pdf_bytes, "application/pdf")

    def test_should_reject_oversized_file(self):
        from services.media_service import _validate_file, FileTooLargeError, MAX_FILE_SIZE

        with pytest.raises(FileTooLargeError):
            _validate_file(b"x" * (MAX_FILE_SIZE + 1), "image/jpeg")


# --- Unit Tests: MediaUploadService ---


class TestMediaUploadService:
    @pytest.fixture
    def mock_minio(self):
        client = AsyncMock(spec=MinIOClient)
        client.upload_file = AsyncMock()
        client.get_presigned_url = AsyncMock(return_value="http://minio:9000/presigned-url")
        return client

    @pytest.fixture
    def mock_repos(self):
        garment_repo = AsyncMock(spec=GarmentPhotoRepo)
        model_repo = AsyncMock(spec=ModelPhotoRepo)

        async def fake_create_garment(entity):
            entity.id = uuid.uuid4()
            return entity

        async def fake_create_model(entity):
            entity.id = uuid.uuid4()
            return entity

        garment_repo.create = fake_create_garment
        model_repo.create = fake_create_model
        return garment_repo, model_repo

    @pytest.mark.asyncio
    async def test_should_upload_garment_photo(self, sample_jpeg_bytes, mock_minio, mock_repos):
        garment_repo, model_repo = mock_repos
        service = MediaUploadService(garment_repo, model_repo, mock_minio)

        mayorista_id = uuid.uuid4()
        photo, presigned_url = await service.upload_garment(
            mayorista_id=mayorista_id,
            file_bytes=sample_jpeg_bytes,
            filename="shirt.jpg",
            content_type="image/jpeg",
        )

        assert photo.mayorista_id == mayorista_id
        assert photo.content_type == "image/jpeg"
        assert photo.size_bytes == len(sample_jpeg_bytes)
        assert photo.minio_key.startswith("garments/")
        assert presigned_url == "http://minio:9000/presigned-url"
        mock_minio.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_upload_model_photo(self, sample_png_bytes, mock_minio, mock_repos):
        garment_repo, model_repo = mock_repos
        service = MediaUploadService(garment_repo, model_repo, mock_minio)

        mayorista_id = uuid.uuid4()
        photo, presigned_url = await service.upload_model_photo(
            mayorista_id=mayorista_id,
            file_bytes=sample_png_bytes,
            filename="model.png",
            content_type="image/png",
            label="Test Model",
        )

        assert photo.mayorista_id == mayorista_id
        assert photo.content_type == "image/png"
        assert photo.is_curated is False
        assert photo.label == "Test Model"
        assert photo.minio_key.startswith("models/")
        mock_minio.upload_file.assert_called_once()


# --- Unit Tests: ModelLibraryService ---


class TestModelLibraryService:
    @pytest.fixture
    def mock_minio(self):
        client = AsyncMock(spec=MinIOClient)
        client.get_presigned_url = AsyncMock(return_value="http://minio:9000/presigned")
        return client

    @pytest.fixture
    def mock_model_repo(self):
        repo = AsyncMock(spec=ModelPhotoRepo)
        return repo

    @pytest.mark.asyncio
    async def test_should_list_curated_models(self, mock_minio, mock_model_repo):
        from models.media import ModelPhoto

        curated_models = [
            ModelPhoto(id=uuid.uuid4(), mayorista_id=None, minio_key="models/curated/1.jpg",
                       label="Model A", is_curated=True, content_type="image/jpeg", size_bytes=1000),
            ModelPhoto(id=uuid.uuid4(), mayorista_id=None, minio_key="models/curated/2.jpg",
                       label="Model B", is_curated=True, content_type="image/jpeg", size_bytes=1000),
        ]
        mock_model_repo.list_curated = AsyncMock(return_value=curated_models)

        service = ModelLibraryService(mock_model_repo, mock_minio)
        results = await service.list_curated_models()

        assert len(results) == 2
        assert results[0][0].is_curated is True
        mock_model_repo.list_curated.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_list_own_models(self, mock_minio, mock_model_repo):
        from models.media import ModelPhoto

        mayorista_id = uuid.uuid4()
        own_models = [
            ModelPhoto(id=uuid.uuid4(), mayorista_id=mayorista_id, minio_key="models/uuid/1.jpg",
                       label="My Model", is_curated=False, content_type="image/jpeg", size_bytes=1000),
        ]
        mock_model_repo.list_by_mayorista = AsyncMock(return_value=(own_models, 1))

        service = ModelLibraryService(mock_model_repo, mock_minio)
        results, total = await service.list_own_models(mayorista_id)

        assert len(results) == 1
        assert total == 1
        assert results[0][0].is_curated is False
