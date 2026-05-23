import io

import pytest
from PIL import Image

from services.vton.lmstudio_provider import LMStudioProvider, _DEFAULT_PLACEMENT


def _jpeg_bytes(color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (100, 100), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_composite_returns_jpeg():
    provider = LMStudioProvider()
    result = provider._composite_legacy(
        _jpeg_bytes((255, 0, 0)),
        _jpeg_bytes((0, 128, 255)),
        _DEFAULT_PLACEMENT,
    )
    out = Image.open(io.BytesIO(result))
    assert out.format == "JPEG"
    assert out.size == (100, 100)


def test_parse_placement_defaults_on_invalid_json():
    provider = LMStudioProvider()
    placement = provider._parse_placement("no json here")
    assert placement == _DEFAULT_PLACEMENT


def test_parse_placement_clamps_values():
    provider = LMStudioProvider()
    placement = provider._parse_placement(
        '{"scale": 9, "y_anchor": -1, "x_anchor": 2}'
    )
    assert placement["scale"] == 0.65
    assert placement["y_anchor"] == 0.25
    assert placement["x_anchor"] == 0.8


def test_normalize_root_url():
    assert LMStudioProvider._normalize_root_url("http://host:1234/v1") == "http://host:1234"
    assert LMStudioProvider._normalize_root_url("http://host:1234/api/v1") == "http://host:1234"
    assert LMStudioProvider._normalize_root_url("http://100.102.213.128:1234") == "http://100.102.213.128:1234"


def test_extract_message_content():
    content = LMStudioProvider._extract_message_content(
        {
            "output": [
                {"type": "message", "content": '{"scale": 0.4, "y_anchor": 0.5, "x_anchor": 0.5}'},
            ]
        }
    )
    assert "scale" in content
