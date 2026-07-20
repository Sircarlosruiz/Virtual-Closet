import uuid

from pydantic import BaseModel, Field, field_validator


class PoseSetCreateRequest(BaseModel):
    garment_id: uuid.UUID
    model_id: uuid.UUID
    cloth_type: str
    pose_ids: list[uuid.UUID] = Field(min_length=1)

    @field_validator("cloth_type")
    @classmethod
    def validate_cloth_type(cls, value: str) -> str:
        if value not in {"upper_body", "lower_body", "dress"}:
            raise ValueError("cloth_type must be upper_body, lower_body, or dress")
        return value


class PoseSetCreateResponse(BaseModel):
    pose_set_id: uuid.UUID
    batch_id: uuid.UUID
    total_items: int


class PoseSetItemResponse(BaseModel):
    pose_type: str | None
    batch_item_id: uuid.UUID
    media_id: uuid.UUID | None
    image_url: str | None
    status: str
    error_message: str | None


class PoseSetDetailResponse(BaseModel):
    pose_set_id: uuid.UUID
    batch_id: uuid.UUID
    garment_id: uuid.UUID
    model_id: uuid.UUID
    status: str
    items: list[PoseSetItemResponse]
