import re
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

_HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _validate_hex_color(value: str) -> str:
    if not _HEX_COLOR.match(value):
        raise ValueError("color must be a hex value like #FFF or #FFFFFF")
    return value


class OverlayAnchor(str, Enum):
    top_left = "top-left"
    top_center = "top-center"
    top_right = "top-right"
    center_left = "center-left"
    center = "center"
    center_right = "center-right"
    bottom_left = "bottom-left"
    bottom_center = "bottom-center"
    bottom_right = "bottom-right"


class OverlayPlacement(BaseModel):
    """Absolute placement for a fixed-position overlay.

    `offset_x`/`offset_y` are insets from the anchored edge. `max_width`/
    `max_height` bound the available area; when omitted, the area is the image
    minus the offsets on that side.
    """

    anchor: OverlayAnchor = OverlayAnchor.bottom_right
    offset_x: int = Field(default=24, ge=0)
    offset_y: int = Field(default=24, ge=0)
    max_width: int | None = Field(default=None, gt=0)
    max_height: int | None = Field(default=None, gt=0)


class OverlayStyle(BaseModel):
    font_family: str = Field(default="default", min_length=1, max_length=80)
    font_size: int = Field(default=48, gt=0, le=2000)
    color: str = "#FFFFFF"
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    background_color: str | None = None
    stroke_color: str | None = None
    stroke_width: int = Field(default=0, ge=0, le=50)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        return _validate_hex_color(value)

    @field_validator("background_color", "stroke_color")
    @classmethod
    def validate_optional_color(cls, value: str | None) -> str | None:
        return _validate_hex_color(value) if value is not None else None


class CompositionRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=200)
    placement: OverlayPlacement = Field(default_factory=OverlayPlacement)
    style: OverlayStyle = Field(default_factory=OverlayStyle)


class FitResult(BaseModel):
    fits: bool
    rendered_width: int
    rendered_height: int
    available_width: int
    available_height: int
    reason: str | None = None


class CompositionVersionResponse(BaseModel):
    id: UUID
    overlay_id: UUID
    generation_job_id: UUID
    version: int
    status: str
    sku: str
    placement: OverlayPlacement
    style: OverlayStyle
    font_version: str
    rendered_key: str | None
    rendered_checksum: str | None
    fit_result: FitResult
    created_at: datetime

    @classmethod
    def from_model(cls, version, generation_job_id: UUID) -> "CompositionVersionResponse":
        return cls(
            id=version.id,
            overlay_id=version.overlay_id,
            generation_job_id=generation_job_id,
            version=version.version,
            status=version.status,
            sku=version.sku_normalized,
            placement=OverlayPlacement(**version.placement),
            style=OverlayStyle(**version.style),
            font_version=version.font_version,
            rendered_key=version.rendered_key,
            rendered_checksum=version.rendered_checksum,
            fit_result=FitResult(**version.fit_result),
            created_at=version.created_at,
        )


class CompositionSummaryResponse(BaseModel):
    overlay_id: UUID
    generation_job_id: UUID
    base_image_key: str
    latest_version: CompositionVersionResponse | None
