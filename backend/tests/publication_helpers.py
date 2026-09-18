"""Shared fixtures for publication selection and sync-delivery tests."""

import uuid
from unittest.mock import patch

import pytest

import core.database as database
from api.routers.publication import get_bfashion_adapter
from main import app
from models.generation_job import GenerationJob
from services.bfashion_sync_adapter import BFashionImageResult, BFashionSyncError
from services.storage_service import StorageService


class FakeBFashion:
    def __init__(self) -> None:
        self.calls: list = []
        self.fail = False
        self.retryable = True
        self.refs: dict[uuid.UUID, str] = {}

    async def upsert_product_image(self, payload) -> BFashionImageResult:
        self.calls.append(payload)
        if self.fail:
            raise BFashionSyncError("BFashion unavailable", retryable=self.retryable)
        ref = self.refs.setdefault(
            payload.publication_selection_id, f"bf-{len(self.refs) + 1}"
        )
        return BFashionImageResult(external_ref=ref)


async def create_completed_job(
    owner_id: uuid.UUID, result_key: str = "generated/base.png"
) -> GenerationJob:
    async with database.async_session() as session:
        job = GenerationJob(
            owner_id=owner_id,
            mode="text",
            provider="openai",
            status="completed",
            input_data={"mode": "text", "prompt": "a red jacket"},
            result_key=result_key,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


@pytest.fixture
def fake_bfashion():
    adapter = FakeBFashion()
    app.dependency_overrides[get_bfashion_adapter] = lambda: adapter
    yield adapter
    app.dependency_overrides.pop(get_bfashion_adapter, None)


@pytest.fixture
def preview_urls():
    async def _url(self, key, ttl_seconds=900, bucket_override=None):
        return f"https://preview.test/{key}"

    with patch.object(StorageService, "generate_download_url", new=_url):
        yield
