import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.tryoff_model_client import (
    TryoffModelClient,
    TryoffModelClientError,
)


class TestTryoffModelClient:
    @pytest.fixture
    def client(self):
        with patch("services.tryoff_model_client.settings") as mock_settings:
            mock_settings.TRYOFF_MODEL_URL = "http://tryoff-model:8000"
            mock_settings.TRYOFF_MODEL_TIMEOUT_SECONDS = 120
            return TryoffModelClient()

    @pytest.mark.asyncio
    async def test_should_extract_garment_successfully(self, client):
        source_image_url = "http://minio/source.jpg"
        garment_type = "upper"
        expected_output = b"PNG_OUTPUT_BYTES"

        with patch("services.tryoff_model_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # Mock image download
            mock_image_response = MagicMock()
            mock_image_response.status_code = 200
            mock_image_response.content = b"IMAGE_BYTES"
            mock_image_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_image_response)

            # Mock model service call
            mock_model_response = MagicMock()
            mock_model_response.status_code = 200
            mock_model_response.content = expected_output
            mock_client.post = AsyncMock(return_value=mock_model_response)

            result = await client.extract_garment(source_image_url, garment_type)

            assert result == expected_output
            mock_client.get.assert_called_once_with(source_image_url)
            mock_client.post.assert_called_once()

            # Verify the POST call arguments
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://tryoff-model:8000/tryoff"
            assert call_args[1]["data"]["garment_type"] == "upper"

    @pytest.mark.asyncio
    async def test_should_raise_error_on_model_service_503(self, client):
        source_image_url = "http://minio/source.jpg"

        with patch("services.tryoff_model_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # Mock image download
            mock_image_response = MagicMock()
            mock_image_response.status_code = 200
            mock_image_response.content = b"IMAGE_BYTES"
            mock_image_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_image_response)

            # Mock model service returns 503
            mock_model_response = MagicMock()
            mock_model_response.status_code = 503
            mock_model_response.text = "Model loading"
            mock_client.post = AsyncMock(return_value=mock_model_response)

            with pytest.raises(TryoffModelClientError, match="Model service unavailable"):
                await client.extract_garment(source_image_url, "upper")

    @pytest.mark.asyncio
    async def test_should_raise_error_on_model_service_504(self, client):
        source_image_url = "http://minio/source.jpg"

        with patch("services.tryoff_model_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_image_response = MagicMock()
            mock_image_response.status_code = 200
            mock_image_response.content = b"IMAGE_BYTES"
            mock_image_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_image_response)

            mock_model_response = MagicMock()
            mock_model_response.status_code = 504
            mock_model_response.text = "Timeout"
            mock_client.post = AsyncMock(return_value=mock_model_response)

            with pytest.raises(TryoffModelClientError, match="Model service timeout"):
                await client.extract_garment(source_image_url, "upper")

    @pytest.mark.asyncio
    async def test_should_raise_error_on_model_service_500(self, client):
        source_image_url = "http://minio/source.jpg"

        with patch("services.tryoff_model_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_image_response = MagicMock()
            mock_image_response.status_code = 200
            mock_image_response.content = b"IMAGE_BYTES"
            mock_image_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_image_response)

            mock_model_response = MagicMock()
            mock_model_response.status_code = 500
            mock_model_response.text = "Internal error"
            mock_client.post = AsyncMock(return_value=mock_model_response)

            with pytest.raises(TryoffModelClientError, match="Model service error 500"):
                await client.extract_garment(source_image_url, "upper")

    @pytest.mark.asyncio
    async def test_should_raise_error_on_http_timeout(self, client):
        source_image_url = "http://minio/source.jpg"

        with patch("services.tryoff_model_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # Mock timeout exception
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            with pytest.raises(TryoffModelClientError, match="Request timeout"):
                await client.extract_garment(source_image_url, "upper")

    @pytest.mark.asyncio
    async def test_should_raise_error_on_http_error(self, client):
        source_image_url = "http://minio/source.jpg"

        with patch("services.tryoff_model_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # Mock HTTP error
            mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))

            with pytest.raises(TryoffModelClientError, match="HTTP error"):
                await client.extract_garment(source_image_url, "upper")

    @pytest.mark.asyncio
    async def test_should_handle_all_garment_types(self, client):
        source_image_url = "http://minio/source.jpg"

        for garment_type in ["upper", "lower", "dress"]:
            with patch("services.tryoff_model_client.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                mock_image_response = MagicMock()
                mock_image_response.status_code = 200
                mock_image_response.content = b"IMAGE_BYTES"
                mock_image_response.raise_for_status = MagicMock()
                mock_client.get = AsyncMock(return_value=mock_image_response)

                mock_model_response = MagicMock()
                mock_model_response.status_code = 200
                mock_model_response.content = b"OUTPUT"
                mock_client.post = AsyncMock(return_value=mock_model_response)

                result = await client.extract_garment(source_image_url, garment_type)

                assert result == b"OUTPUT"
                call_args = mock_client.post.call_args
                assert call_args[1]["data"]["garment_type"] == garment_type
