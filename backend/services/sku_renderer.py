"""Deterministic Pillow-based SKU overlay rendering and fit validation.

Fit validation and rendering share the same measurement/placement helpers so
the dimensions that pass validation are exactly the dimensions that get drawn
(NFR-3). The renderer is a pure function of `(base_bytes, spec, font_version)`:
no clocks, randomness, or provider state reach the pixels (ADR-053/054).
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from services.composition_spec import UnsupportedFontError

if TYPE_CHECKING:
    from api.schemas.composition import OverlayPlacement, OverlayStyle

SUPPORTED_FONTS = frozenset({"default"})

# Bump when the render pipeline changes how pixels are produced. It is folded
# into `font_version`, so an upgrade appends a new version instead of quietly
# changing the meaning of an existing spec hash (ADR-054).
RENDER_PIPELINE_VERSION = "v1"


def font_version(font_family: str) -> str:
    if font_family not in SUPPORTED_FONTS:
        raise UnsupportedFontError(f"Font family '{font_family}' is not supported")
    return f"pillow-{Image.__version__}:{font_family}:{RENDER_PIPELINE_VERSION}"


def load_font(font_family: str, size: int) -> ImageFont.FreeTypeFont:
    if font_family not in SUPPORTED_FONTS:
        raise UnsupportedFontError(f"Font family '{font_family}' is not supported")
    return ImageFont.load_default(size=size)


def measure_text(font: ImageFont.FreeTypeFont, text: str) -> tuple[int, int, int, int]:
    """Returns `(left, top, width, height)` of the text's bounding box."""
    left, top, right, bottom = font.getbbox(text)
    return left, top, max(0, right - left), max(0, bottom - top)


def _split_anchor(anchor: str) -> tuple[str, str]:
    horizontal = "center"
    vertical = "center"
    if "left" in anchor:
        horizontal = "left"
    elif "right" in anchor:
        horizontal = "right"
    if "top" in anchor:
        vertical = "top"
    elif "bottom" in anchor:
        vertical = "bottom"
    return horizontal, vertical


def resolve_frame(
    image_size: tuple[int, int],
    placement: "OverlayPlacement",
    text_width: int,
    text_height: int,
) -> tuple[int, int, int, int]:
    """Returns `(x, y, available_width, available_height)` for the overlay."""
    image_w, image_h = image_size
    offset_x = placement.offset_x
    offset_y = placement.offset_y

    available_width = placement.max_width or max(1, image_w - 2 * offset_x)
    available_height = placement.max_height or max(1, image_h - 2 * offset_y)

    horizontal, vertical = _split_anchor(placement.anchor.value)
    if horizontal == "left":
        x = offset_x
    elif horizontal == "right":
        x = image_w - offset_x - text_width
    else:
        x = (image_w - text_width) // 2

    if vertical == "top":
        y = offset_y
    elif vertical == "bottom":
        y = image_h - offset_y - text_height
    else:
        y = (image_h - text_height) // 2

    return max(0, x), max(0, y), available_width, available_height


def image_size_from_bytes(base_bytes: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(base_bytes)) as image:
        return image.size


def evaluate_fit(
    image_size: tuple[int, int],
    sku: str,
    placement: "OverlayPlacement",
    style: "OverlayStyle",
) -> dict:
    font = load_font(style.font_family, style.font_size)
    _, _, text_width, text_height = measure_text(font, sku)

    stroke = style.stroke_width if style.stroke_color else 0
    rendered_width = text_width + 2 * stroke
    rendered_height = text_height + 2 * stroke

    _, _, available_width, available_height = resolve_frame(
        image_size, placement, rendered_width, rendered_height
    )

    fits = rendered_width <= available_width and rendered_height <= available_height
    reason = None
    if not fits:
        reason = (
            f"SKU needs {rendered_width}x{rendered_height}px but only "
            f"{available_width}x{available_height}px are available"
        )
    return {
        "fits": fits,
        "rendered_width": rendered_width,
        "rendered_height": rendered_height,
        "available_width": available_width,
        "available_height": available_height,
        "reason": reason,
    }


def _rgba(color: str, opacity: float) -> tuple[int, int, int, int]:
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    alpha = int(round(255 * opacity))
    return red, green, blue, alpha


def render_composition(
    base_bytes: bytes,
    sku: str,
    placement: "OverlayPlacement",
    style: "OverlayStyle",
) -> bytes:
    """Renders the overlay deterministically and returns PNG bytes."""
    base = Image.open(io.BytesIO(base_bytes)).convert("RGB")
    canvas = Image.new("RGB", base.size)
    canvas.paste(base)  # rebuild without source metadata/EXIF

    font = load_font(style.font_family, style.font_size)
    text_left, text_top, text_width, text_height = measure_text(font, sku)
    stroke = style.stroke_width if style.stroke_color else 0
    x, y, _, _ = resolve_frame(
        base.size,
        placement,
        text_width + 2 * stroke,
        text_height + 2 * stroke,
    )
    draw_x = x + stroke
    draw_y = y + stroke

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    if style.background_color:
        draw.rectangle(
            [draw_x, draw_y, draw_x + text_width, draw_y + text_height],
            fill=_rgba(style.background_color, style.opacity),
        )
    draw.text(
        (draw_x - text_left, draw_y - text_top),
        sku,
        font=font,
        fill=_rgba(style.color, style.opacity),
        stroke_width=stroke,
        stroke_fill=(
            _rgba(style.stroke_color, style.opacity)
            if stroke and style.stroke_color
            else None
        ),
    )

    composed = Image.alpha_composite(canvas.convert("RGBA"), layer).convert("RGB")
    buffer = io.BytesIO()
    composed.save(buffer, format="PNG", compress_level=6, optimize=False)
    return buffer.getvalue()
