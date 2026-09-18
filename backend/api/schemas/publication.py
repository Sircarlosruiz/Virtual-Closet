"""API contract for manual publication selection and sync delivery."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PublicationDecisionRequest(BaseModel):
    product_link_id: UUID
    generation_job_id: UUID
    composition_version_id: UUID | None = None
    decision: Literal["selected", "discarded"]


class SyncDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    destination: str
    status: str
    retryable: bool
    last_error: str | None = None
    attempt_count: int
    external_ref: str | None = None
    durable_object_key: str | None = None


class PublicationResponse(BaseModel):
    id: UUID
    product_link_id: UUID
    generation_job_id: UUID
    composition_version_id: UUID | None
    decision: str
    deliveries: list[SyncDeliveryResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PublicationCandidateResponse(BaseModel):
    generation_job_id: UUID
    composition_version_id: UUID | None
    kind: Literal["generation_result", "composition_version"]
    durable_object_key: str
    preview_url: str | None = None
    decision: str | None = None
    publication_id: UUID | None = None
    eligible: bool = True
