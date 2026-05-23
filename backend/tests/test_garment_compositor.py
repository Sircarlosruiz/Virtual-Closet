import io

from PIL import Image

from services.vton.garment_compositor import (
    _crop_to_content,
    _garment_kind,
    composite_garment_on_model,
)


def _rgba(w: int, h: int, fill: tuple[int, int, int, int]) -> bytes:
    img = Image.new("RGBA", (w, h), fill)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _rgb(w: int, h: int, fill: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (w, h), fill)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_garment_kind_dress_vs_top():
    dress = Image.new("RGBA", (80, 140), (100, 100, 100, 255))
    top = Image.new("RGBA", (120, 90), (100, 100, 100, 255))
    assert _garment_kind(dress) == "dress"
    assert _garment_kind(top) == "top"


def test_crop_to_content_trims_transparent_border():
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    for x in range(30, 70):
        for y in range(20, 80):
            img.putpixel((x, y), (255, 0, 0, 255))
    cropped = _crop_to_content(img)
    assert cropped.size == (40, 60)


def test_composite_returns_jpeg():
    garment = _rgba(120, 200, (200, 50, 50, 255))
    model = _rgb(400, 800, (220, 200, 190))
    result = composite_garment_on_model(garment, model)
    out = Image.open(io.BytesIO(result))
    assert out.format == "JPEG"
    assert out.size == (400, 800)
