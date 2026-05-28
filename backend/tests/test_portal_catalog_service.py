import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.catalogo import Catalogo, CatalogoItem
from repositories.catalogo_repo import CatalogoItemRepo, CatalogoRepo
from services.portal_catalog_service import (
    CatalogoNotFoundError,
    CatalogoOwnershipError,
    PortalCatalogService,
)


class TestPortalCatalogService:
    @pytest.fixture
    def mock_catalogo_repo(self):
        return AsyncMock(spec=CatalogoRepo)

    @pytest.fixture
    def mock_item_repo(self):
        return AsyncMock(spec=CatalogoItemRepo)

    @pytest.fixture
    def mock_minio(self):
        client = AsyncMock()
        client.get_presigned_url = AsyncMock(return_value="http://minio/presigned")
        return client

    @pytest.fixture
    def service(self, mock_catalogo_repo, mock_item_repo, mock_minio):
        return PortalCatalogService(mock_catalogo_repo, mock_item_repo, mock_minio)

    # --- Story 003: List Published Catalogs ---

    @pytest.mark.asyncio
    async def test_should_list_published_catalogs(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()

        catalog1 = MagicMock(spec=Catalogo)
        catalog1.id = uuid.uuid4()
        catalog1.name = "Summer Collection"
        catalog1.status = "published"
        catalog1.item_count = 5

        catalog2 = MagicMock(spec=Catalogo)
        catalog2.id = uuid.uuid4()
        catalog2.name = "Winter Collection"
        catalog2.status = "published"
        catalog2.item_count = 3

        mock_catalogo_repo.list_published_by_mayorista = AsyncMock(
            return_value=([catalog1, catalog2], 2)
        )

        catalogs, total = await service.list_published_catalogs(
            mayorista_id, page=1, page_size=20
        )

        assert len(catalogs) == 2
        assert total == 2
        assert catalogs[0].status == "published"
        assert catalogs[1].status == "published"
        mock_catalogo_repo.list_published_by_mayorista.assert_called_once_with(
            mayorista_id, 1, 20
        )

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_no_published_catalogs(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()

        mock_catalogo_repo.list_published_by_mayorista = AsyncMock(
            return_value=([], 0)
        )

        catalogs, total = await service.list_published_catalogs(
            mayorista_id, page=1, page_size=20
        )

        assert len(catalogs) == 0
        assert total == 0

    @pytest.mark.asyncio
    async def test_should_paginate_published_catalogs(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()

        catalog = MagicMock(spec=Catalogo)
        catalog.id = uuid.uuid4()
        catalog.status = "published"

        mock_catalogo_repo.list_published_by_mayorista = AsyncMock(
            return_value=([catalog], 5)
        )

        catalogs, total = await service.list_published_catalogs(
            mayorista_id, page=2, page_size=1
        )

        assert len(catalogs) == 1
        assert total == 5
        mock_catalogo_repo.list_published_by_mayorista.assert_called_once_with(
            mayorista_id, 2, 1
        )

    # --- Story 003: Get Published Catalog ---

    @pytest.mark.asyncio
    async def test_should_get_published_catalog_with_items(
        self, service, mock_catalogo_repo, mock_item_repo, mock_minio
    ):
        catalog_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        catalog = MagicMock(spec=Catalogo)
        catalog.id = catalog_id
        catalog.mayorista_id = mayorista_id
        catalog.name = "Summer Collection"
        catalog.status = "published"
        catalog.item_count = 2

        mock_catalogo_repo.get_by_id = AsyncMock(return_value=catalog)

        item1 = MagicMock(spec=CatalogoItem)
        item1.id = uuid.uuid4()
        item1.garment_name = "Linen Blazer"
        item1.price = Decimal("89.99")
        item1.cloth_type = "upper_body"
        item1.sku = "LBZ-001"
        item1.position = 1
        item1.image_key = "results/item1.jpg"

        item2 = MagicMock(spec=CatalogoItem)
        item2.id = uuid.uuid4()
        item2.garment_name = "Silk Dress"
        item2.price = Decimal("129.99")
        item2.cloth_type = "dress"
        item2.sku = "SLK-001"
        item2.position = 2
        item2.image_key = "results/item2.jpg"

        mock_item_repo.get_all_by_catalog = AsyncMock(return_value=[item1, item2])

        result_catalog, items_with_urls = await service.get_published_catalog(
            catalog_id, mayorista_id
        )

        assert result_catalog.id == catalog_id
        assert result_catalog.status == "published"
        assert len(items_with_urls) == 2
        assert items_with_urls[0][0].garment_name == "Linen Blazer"
        assert items_with_urls[0][1] == "http://minio/presigned"
        assert items_with_urls[1][0].garment_name == "Silk Dress"
        mock_minio.get_presigned_url.assert_called()

    @pytest.mark.asyncio
    async def test_should_reject_draft_catalog(
        self, service, mock_catalogo_repo
    ):
        catalog_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        catalog = MagicMock(spec=Catalogo)
        catalog.id = catalog_id
        catalog.mayorista_id = mayorista_id
        catalog.status = "draft"

        mock_catalogo_repo.get_by_id = AsyncMock(return_value=catalog)

        with pytest.raises(CatalogoNotFoundError, match="Catalog not found"):
            await service.get_published_catalog(catalog_id, mayorista_id)

    @pytest.mark.asyncio
    async def test_should_reject_nonexistent_catalog(
        self, service, mock_catalogo_repo
    ):
        catalog_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(CatalogoNotFoundError, match="Catalog not found"):
            await service.get_published_catalog(catalog_id, mayorista_id)

    @pytest.mark.asyncio
    async def test_should_reject_cross_mayorista_access(
        self, service, mock_catalogo_repo
    ):
        catalog_id = uuid.uuid4()
        owner_mayorista_id = uuid.uuid4()
        buyer_mayorista_id = uuid.uuid4()

        catalog = MagicMock(spec=Catalogo)
        catalog.id = catalog_id
        catalog.mayorista_id = owner_mayorista_id
        catalog.status = "published"

        mock_catalogo_repo.get_by_id = AsyncMock(return_value=catalog)

        with pytest.raises(CatalogoOwnershipError, match="Access denied"):
            await service.get_published_catalog(catalog_id, buyer_mayorista_id)

    @pytest.mark.asyncio
    async def test_should_return_empty_items_for_catalog_without_items(
        self, service, mock_catalogo_repo, mock_item_repo
    ):
        catalog_id = uuid.uuid4()
        mayorista_id = uuid.uuid4()

        catalog = MagicMock(spec=Catalogo)
        catalog.id = catalog_id
        catalog.mayorista_id = mayorista_id
        catalog.status = "published"
        catalog.item_count = 0

        mock_catalogo_repo.get_by_id = AsyncMock(return_value=catalog)
        mock_item_repo.get_all_by_catalog = AsyncMock(return_value=[])

        result_catalog, items_with_urls = await service.get_published_catalog(
            catalog_id, mayorista_id
        )

        assert result_catalog.id == catalog_id
        assert len(items_with_urls) == 0
