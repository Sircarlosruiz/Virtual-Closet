"""Unit tests for TryOff main.py — no GPU required.

Tests validation logic, prompt templates, error handling, and health endpoint
by mocking the FLUX pipeline.

Usage:
    cd docker/flux && python -m pytest test_main.py -v
"""

import io
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))

import main


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state between tests."""
    main._models.clear()
    main._model_ready = False
    yield
    main._models.clear()
    main._model_ready = False


@pytest.fixture
def client():
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient
    return TestClient(main.app, raise_server_exceptions=False)


class TestPromptTemplates:
    """Test garment type → prompt mapping."""

    def test_upper_prompt(self):
        assert "upper garment" in main._PROMPT_TEMPLATES["upper"]
        assert "TRYOFF" in main._PROMPT_TEMPLATES["upper"]
        assert "NO HUMAN VISIBLE" in main._PROMPT_TEMPLATES["upper"]

    def test_lower_prompt(self):
        assert "lower garment" in main._PROMPT_TEMPLATES["lower"]

    def test_dress_prompt(self):
        assert "dress" in main._PROMPT_TEMPLATES["dress"]

    def test_all_garment_types_present(self):
        assert set(main._PROMPT_TEMPLATES.keys()) == {"upper", "lower", "dress"}


class TestImageValidation:
    """Test _validate_image function."""

    def _make_jpeg_bytes(self, width=100, height=100):
        img = Image.new("RGB", (width, height), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def _make_png_bytes(self, width=100, height=100):
        img = Image.new("RGB", (width, height), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_valid_jpeg(self):
        data = self._make_jpeg_bytes()
        img = main._validate_image(data)
        assert img.mode == "RGB"

    def test_valid_png(self):
        data = self._make_png_bytes()
        img = main._validate_image(data)
        assert img.mode == "RGB"

    def test_oversized_image_raises_413(self):
        from fastapi import HTTPException
        oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (11 * 1024 * 1024)
        with pytest.raises(HTTPException) as exc_info:
            main._validate_image(oversized)
        assert exc_info.value.status_code == 413

    def test_invalid_bytes_raises_400(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            main._validate_image(b"not an image")
        assert exc_info.value.status_code == 400

    def test_bmp_format_raises_400(self):
        from fastapi import HTTPException
        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="BMP")
        with pytest.raises(HTTPException) as exc_info:
            main._validate_image(buf.getvalue())
        assert exc_info.value.status_code == 400

    def test_grayscale_converted_to_rgb(self):
        img = Image.new("L", (100, 100), color=128)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        result = main._validate_image(buf.getvalue())
        assert result.mode == "RGB"


class TestHealthEndpoint:
    """Test GET /health endpoint."""

    def test_health_when_not_ready(self, client):
        main._model_ready = False
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "loading"
        assert data["model_loaded"] is False

    def test_health_when_ready(self, client):
        main._model_ready = True
        main._models["device"] = "cuda"
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True
        assert data["device"] == "cuda"


class TestTryoffEndpoint:
    """Test POST /tryoff endpoint (mocked pipeline)."""

    def _make_jpeg_bytes(self):
        img = Image.new("RGB", (200, 300), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_tryoff_when_model_not_ready(self, client):
        main._model_ready = False
        files = {"image": ("test.jpg", self._make_jpeg_bytes(), "image/jpeg")}
        data = {"garment_type": "upper"}
        response = client.post("/tryoff", files=files, data=data)
        assert response.status_code == 503

    def test_tryoff_invalid_garment_type(self, client):
        main._model_ready = True
        files = {"image": ("test.jpg", self._make_jpeg_bytes(), "image/jpeg")}
        data = {"garment_type": "shoes"}
        response = client.post("/tryoff", files=files, data=data)
        assert response.status_code == 422

    def test_tryoff_success(self, client):
        main._model_ready = True
        main._models["device"] = "cuda"

        output_img = Image.new("RGB", (768, 1024), color="white")
        mock_result = MagicMock()
        mock_result.images = [output_img]

        mock_pipe = MagicMock(return_value=mock_result)
        main._models["pipe"] = mock_pipe

        files = {"image": ("test.jpg", self._make_jpeg_bytes(), "image/jpeg")}
        data = {"garment_type": "upper"}
        response = client.post("/tryoff", files=files, data=data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        result_img = Image.open(io.BytesIO(response.content))
        assert result_img.format == "PNG"
        assert result_img.width == 768
        assert result_img.height == 1024

    def test_tryoff_all_garment_types(self, client):
        main._model_ready = True
        main._models["device"] = "cuda"

        output_img = Image.new("RGB", (768, 1024), color="white")
        mock_result = MagicMock()
        mock_result.images = [output_img]
        mock_pipe = MagicMock(return_value=mock_result)
        main._models["pipe"] = mock_pipe

        for garment_type in ["upper", "lower", "dress"]:
            files = {"image": ("test.jpg", self._make_jpeg_bytes(), "image/jpeg")}
            data = {"garment_type": garment_type}
            response = client.post("/tryoff", files=files, data=data)
            assert response.status_code == 200, f"Failed for garment_type={garment_type}"

    def test_tryoff_oversized_image(self, client):
        main._model_ready = True
        oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (11 * 1024 * 1024)
        files = {"image": ("huge.png", oversized, "image/png")}
        data = {"garment_type": "upper"}
        response = client.post("/tryoff", files=files, data=data)
        assert response.status_code == 413

    def test_tryoff_bmp_format(self, client):
        main._model_ready = True
        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="BMP")
        files = {"image": ("test.bmp", buf.getvalue(), "image/bmp")}
        data = {"garment_type": "upper"}
        response = client.post("/tryoff", files=files, data=data)
        assert response.status_code == 400
