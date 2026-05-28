import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.catalogo import Catalogo, CatalogoItem
from models.vton_job import VTONJob
from repositories.catalogo_repo import CatalogoItemRepo, CatalogoRepo
from repositories.vton_job_repo import VTONJobRepo
from services.catalogo_service import (
    CatalogoItemNotFoundError,
    CatalogoNotFoundError,
    CatalogoOwnershipError,
    CatalogoService,
    EmptyCatalogCannotPublishError,
    InvalidCatalogStatusError,
    ReorderValidationError,
    VTONJobNotCompletedError,
    VTONJobNotFoundError,
    VTONJobOwnershipError,
)


class TestCatalogoService:
    @pytest.fixture
    def mock_catalogo_repo(self):
        return AsyncMock(spec=CatalogoRepo)

    @pytest.fixture
    def mock_item_repo(self):
        return AsyncMock(spec=CatalogoItemRepo)

    @pytest.fixture
    def mock_vton_repo(self):
        return AsyncMock(spec=VTONJobRepo)

    @pytest.fixture
    def mock_minio(self):
        client = AsyncMock()
        client.get_presigned_url = AsyncMock(return_value="http://minio/presigned")
        return client

    @pytest.fixture
    def service(
        self, mock_catalogo_repo, mock_item_repo, mock_vton_repo, mock_minio
    ):
        return CatalogoService(
            mock_catalogo_repo, mock_item_repo, mock_vton_repo, mock_minio
        )

    # --- Story 001: Create Catalog ---

    @pytest.mark.asyncio
    async def test_should_create_catalog_with_valid_name(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        name = "Summer Collection 2026"

        created_catalogo = MagicMock(spec=Catalogo)
        created_catalogo.id = uuid.uuid4()
        created_catalogo.mayorista_id = mayorista_id
        created_catalogo.name = name
        created_catalogo.status = "draft"
        created_catalogo.item_count = 0
        created_catalogo.created_at = datetime.now(timezone.utc)

        mock_catalogo_repo.create = AsyncMock(return_value=created_catalogo)

        result = await service.create_catalog(mayorista_id, name)

        assert result.mayorista_id == mayorista_id
        assert result.name == name
        assert result.status == "draft"
        assert result.item_count == 0
        mock_catalogo_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_create_catalog_with_whitespace_trimmed(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        name = "  Winter Collection  "

        created_catalogo = MagicMock(spec=Catalogo)
        created_catalogo.id = uuid.uuid4()
        created_catalogo.mayorista_id = mayorista_id
        created_catalogo.name = name.strip()
        created_catalogo.status = "draft"
        created_catalogo.item_count = 0
        created_catalogo.created_at = datetime.now(timezone.utc)

        mock_catalogo_repo.create = AsyncMock(return_value=created_catalogo)

        result = await service.create_catalog(mayorista_id, name.strip())

        assert result.name == "Winter Collection"

    # --- Story 002: Add Catalog Item ---

    @pytest.mark.asyncio
    async def test_should_add_item_from_completed_vton_job(
        self, service, mock_catalogo_repo, mock_item_repo, mock_vton_repo, mock_minio
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()
        vton_job_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.id = catalog_id
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_vton_job = MagicMock(spec=VTONJob)
        mock_vton_job.id = vton_job_id
        mock_vton_job.mayorista_id = mayorista_id
        mock_vton_job.status = "completed"
        mock_vton_job.result_minio_key = "results/test.jpg"
        mock_vton_repo.get_by_id = AsyncMock(return_value=mock_vton_job)

        mock_item_repo.get_max_position = AsyncMock(return_value=0)

        created_item = MagicMock(spec=CatalogoItem)
        created_item.id = uuid.uuid4()
        created_item.catalog_id = catalog_id
        created_item.vton_job_id = vton_job_id
        created_item.garment_name = "Linen Blazer"
        created_item.price = Decimal("89.99")
        created_item.cloth_type = "upper_body"
        created_item.sku = "LBZ-001"
        created_item.image_key = "results/test.jpg"
        created_item.position = 1
        created_item.created_at = datetime.now(timezone.utc)
        mock_item_repo.create = AsyncMock(return_value=created_item)

        mock_catalogo_repo.increment_item_count = AsyncMock()

        item, image_url = await service.add_item(
            catalog_id=catalog_id,
            vton_job_id=vton_job_id,
            garment_name="Linen Blazer",
            price=Decimal("89.99"),
            cloth_type="upper_body",
            sku="LBZ-001",
            mayorista_id=mayorista_id,
        )

        assert item.garment_name == "Linen Blazer"
        assert item.position == 1
        assert image_url == "http://minio/presigned"
        mock_item_repo.create.assert_called_once()
        mock_catalogo_repo.increment_item_count.assert_called_once_with(catalog_id)

    @pytest.mark.asyncio
    async def test_should_reject_add_item_catalog_not_found(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(CatalogoNotFoundError, match="Catalog not found"):
            await service.add_item(
                catalog_id=catalog_id,
                vton_job_id=uuid.uuid4(),
                garment_name="Test",
                price=Decimal("10.00"),
                cloth_type="upper_body",
                sku="TEST-001",
                mayorista_id=mayorista_id,
            )

    @pytest.mark.asyncio
    async def test_should_reject_add_item_catalog_not_owned(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(
            CatalogoOwnershipError, match="You do not own this catalog"
        ):
            await service.add_item(
                catalog_id=catalog_id,
                vton_job_id=uuid.uuid4(),
                garment_name="Test",
                price=Decimal("10.00"),
                cloth_type="upper_body",
                sku="TEST-001",
                mayorista_id=mayorista_id,
            )

    @pytest.mark.asyncio
    async def test_should_reject_add_item_vton_job_not_found(
        self, service, mock_catalogo_repo, mock_vton_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_vton_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(VTONJobNotFoundError, match="VTON job not found"):
            await service.add_item(
                catalog_id=catalog_id,
                vton_job_id=uuid.uuid4(),
                garment_name="Test",
                price=Decimal("10.00"),
                cloth_type="upper_body",
                sku="TEST-001",
                mayorista_id=mayorista_id,
            )

    @pytest.mark.asyncio
    async def test_should_reject_add_item_vton_job_not_completed(
        self, service, mock_catalogo_repo, mock_vton_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()
        vton_job_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_vton_job = MagicMock(spec=VTONJob)
        mock_vton_job.id = vton_job_id
        mock_vton_job.mayorista_id = mayorista_id
        mock_vton_job.status = "processing"
        mock_vton_repo.get_by_id = AsyncMock(return_value=mock_vton_job)

        with pytest.raises(
            VTONJobNotCompletedError,
            match="Job must be completed before adding to catalog",
        ):
            await service.add_item(
                catalog_id=catalog_id,
                vton_job_id=vton_job_id,
                garment_name="Test",
                price=Decimal("10.00"),
                cloth_type="upper_body",
                sku="TEST-001",
                mayorista_id=mayorista_id,
            )

    @pytest.mark.asyncio
    async def test_should_reject_add_item_vton_job_not_owned(
        self, service, mock_catalogo_repo, mock_vton_repo
    ):
        mayorista_id = uuid.uuid4()
        other_mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()
        vton_job_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_vton_job = MagicMock(spec=VTONJob)
        mock_vton_job.id = vton_job_id
        mock_vton_job.mayorista_id = other_mayorista_id
        mock_vton_job.status = "completed"
        mock_vton_job.result_minio_key = "results/test.jpg"
        mock_vton_repo.get_by_id = AsyncMock(return_value=mock_vton_job)

        with pytest.raises(
            VTONJobOwnershipError, match="You do not own this VTON job"
        ):
            await service.add_item(
                catalog_id=catalog_id,
                vton_job_id=vton_job_id,
                garment_name="Test",
                price=Decimal("10.00"),
                cloth_type="upper_body",
                sku="TEST-001",
                mayorista_id=mayorista_id,
            )

    @pytest.mark.asyncio
    async def test_should_append_item_at_next_position(
        self, service, mock_catalogo_repo, mock_item_repo, mock_vton_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()
        vton_job_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_vton_job = MagicMock(spec=VTONJob)
        mock_vton_job.mayorista_id = mayorista_id
        mock_vton_job.status = "completed"
        mock_vton_job.result_minio_key = "results/test.jpg"
        mock_vton_repo.get_by_id = AsyncMock(return_value=mock_vton_job)

        mock_item_repo.get_max_position = AsyncMock(return_value=5)

        created_item = MagicMock(spec=CatalogoItem)
        created_item.position = 6
        created_item.image_key = "results/test.jpg"
        mock_item_repo.create = AsyncMock(return_value=created_item)

        mock_catalogo_repo.increment_item_count = AsyncMock()

        item, _ = await service.add_item(
            catalog_id=catalog_id,
            vton_job_id=vton_job_id,
            garment_name="Test",
            price=Decimal("10.00"),
            cloth_type="upper_body",
            sku="TEST-001",
            mayorista_id=mayorista_id,
        )

        assert item.position == 6

    # --- Story 003: Remove Catalog Item ---

    @pytest.mark.asyncio
    async def test_should_remove_item_from_owned_catalog(
        self, service, mock_catalogo_repo, mock_item_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()
        item_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_item_repo.delete = AsyncMock(return_value=True)
        mock_catalogo_repo.decrement_item_count = AsyncMock()

        await service.remove_item(catalog_id, item_id, mayorista_id)

        mock_item_repo.delete.assert_called_once_with(item_id, catalog_id)
        mock_catalogo_repo.decrement_item_count.assert_called_once_with(catalog_id)

    @pytest.mark.asyncio
    async def test_should_reject_remove_item_catalog_not_found(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(CatalogoNotFoundError, match="Catalog not found"):
            await service.remove_item(catalog_id, uuid.uuid4(), mayorista_id)

    @pytest.mark.asyncio
    async def test_should_reject_remove_item_catalog_not_owned(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(
            CatalogoOwnershipError, match="You do not own this catalog"
        ):
            await service.remove_item(catalog_id, uuid.uuid4(), mayorista_id)

    @pytest.mark.asyncio
    async def test_should_reject_remove_item_not_found(
        self, service, mock_catalogo_repo, mock_item_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()
        item_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_item_repo.delete = AsyncMock(return_value=False)

        with pytest.raises(
            CatalogoItemNotFoundError, match="Item not found in this catalog"
        ):
            await service.remove_item(catalog_id, item_id, mayorista_id)

    # --- Story 004: Reorder Catalog Items ---

    @pytest.mark.asyncio
    async def test_should_reorder_items_with_valid_bijection(
        self, service, mock_catalogo_repo, mock_item_repo, mock_minio
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()
        item1_id = uuid.uuid4()
        item2_id = uuid.uuid4()
        item3_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_item1 = MagicMock(spec=CatalogoItem)
        mock_item1.id = item1_id
        mock_item1.position = 1
        mock_item1.image_key = "results/1.jpg"
        mock_item1.garment_name = "Item 1"
        mock_item1.price = Decimal("10.00")
        mock_item1.cloth_type = "upper_body"
        mock_item1.sku = "SKU-1"

        mock_item2 = MagicMock(spec=CatalogoItem)
        mock_item2.id = item2_id
        mock_item2.position = 2
        mock_item2.image_key = "results/2.jpg"
        mock_item2.garment_name = "Item 2"
        mock_item2.price = Decimal("20.00")
        mock_item2.cloth_type = "lower_body"
        mock_item2.sku = "SKU-2"

        mock_item3 = MagicMock(spec=CatalogoItem)
        mock_item3.id = item3_id
        mock_item3.position = 3
        mock_item3.image_key = "results/3.jpg"
        mock_item3.garment_name = "Item 3"
        mock_item3.price = Decimal("30.00")
        mock_item3.cloth_type = "dress"
        mock_item3.sku = "SKU-3"

        mock_item_repo.get_all_by_catalog = AsyncMock(
            side_effect=[
                [mock_item1, mock_item2, mock_item3],
                [mock_item3, mock_item1, mock_item2],
            ]
        )

        mock_item_repo.update_positions = AsyncMock()

        result = await service.reorder_items(
            catalog_id=catalog_id,
            ordered_item_ids=[item3_id, item1_id, item2_id],
            mayorista_id=mayorista_id,
        )

        assert len(result) == 3
        mock_item_repo.update_positions.assert_called_once()
        call_args = mock_item_repo.update_positions.call_args[0][0]
        assert call_args[item3_id] == 1
        assert call_args[item1_id] == 2
        assert call_args[item2_id] == 3

    @pytest.mark.asyncio
    async def test_should_reject_reorder_with_missing_items(
        self, service, mock_catalogo_repo, mock_item_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()
        item1_id = uuid.uuid4()
        item2_id = uuid.uuid4()
        item3_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_item1 = MagicMock(spec=CatalogoItem)
        mock_item1.id = item1_id
        mock_item2 = MagicMock(spec=CatalogoItem)
        mock_item2.id = item2_id
        mock_item3 = MagicMock(spec=CatalogoItem)
        mock_item3.id = item3_id

        mock_item_repo.get_all_by_catalog = AsyncMock(
            return_value=[mock_item1, mock_item2, mock_item3]
        )

        with pytest.raises(
            ReorderValidationError,
            match="All catalog items must be included in the reorder request",
        ):
            await service.reorder_items(
                catalog_id=catalog_id,
                ordered_item_ids=[item1_id, item2_id],
                mayorista_id=mayorista_id,
            )

    @pytest.mark.asyncio
    async def test_should_reject_reorder_with_extra_items(
        self, service, mock_catalogo_repo, mock_item_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()
        item1_id = uuid.uuid4()
        item2_id = uuid.uuid4()
        extra_item_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_item1 = MagicMock(spec=CatalogoItem)
        mock_item1.id = item1_id
        mock_item2 = MagicMock(spec=CatalogoItem)
        mock_item2.id = item2_id

        mock_item_repo.get_all_by_catalog = AsyncMock(
            return_value=[mock_item1, mock_item2]
        )

        with pytest.raises(
            ReorderValidationError,
            match="All catalog items must be included in the reorder request",
        ):
            await service.reorder_items(
                catalog_id=catalog_id,
                ordered_item_ids=[item1_id, item2_id, extra_item_id],
                mayorista_id=mayorista_id,
            )

    @pytest.mark.asyncio
    async def test_should_reject_reorder_with_duplicate_ids(
        self, service, mock_catalogo_repo, mock_item_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()
        item1_id = uuid.uuid4()
        item2_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_item1 = MagicMock(spec=CatalogoItem)
        mock_item1.id = item1_id
        mock_item2 = MagicMock(spec=CatalogoItem)
        mock_item2.id = item2_id

        mock_item_repo.get_all_by_catalog = AsyncMock(
            return_value=[mock_item1, mock_item2]
        )

        with pytest.raises(
            ReorderValidationError, match="Duplicate IDs in reorder request"
        ):
            await service.reorder_items(
                catalog_id=catalog_id,
                ordered_item_ids=[item1_id, item1_id],
                mayorista_id=mayorista_id,
            )

    @pytest.mark.asyncio
    async def test_should_reject_reorder_catalog_not_found(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(CatalogoNotFoundError, match="Catalog not found"):
            await service.reorder_items(
                catalog_id=catalog_id,
                ordered_item_ids=[uuid.uuid4()],
                mayorista_id=mayorista_id,
            )

    @pytest.mark.asyncio
    async def test_should_reject_reorder_catalog_not_owned(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(
            CatalogoOwnershipError, match="You do not own this catalog"
        ):
            await service.reorder_items(
                catalog_id=catalog_id,
                ordered_item_ids=[uuid.uuid4()],
                mayorista_id=mayorista_id,
            )

    # --- Story 005: Rename Catalog ---

    @pytest.mark.asyncio
    async def test_should_rename_catalog_successfully(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.id = catalog_id
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo.name = "Old Name"
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        updated_catalogo = MagicMock(spec=Catalogo)
        updated_catalogo.id = catalog_id
        updated_catalogo.name = "New Name"
        mock_catalogo_repo.update_name = AsyncMock(return_value=updated_catalogo)

        result = await service.rename_catalog(
            catalog_id=catalog_id,
            mayorista_id=mayorista_id,
            new_name="New Name",
        )

        assert result.name == "New Name"
        mock_catalogo_repo.update_name.assert_called_once_with(
            catalog_id, "New Name"
        )

    @pytest.mark.asyncio
    async def test_should_reject_rename_catalog_not_found(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(CatalogoNotFoundError, match="Catalog not found"):
            await service.rename_catalog(
                catalog_id=catalog_id,
                mayorista_id=mayorista_id,
                new_name="New Name",
            )

    @pytest.mark.asyncio
    async def test_should_reject_rename_catalog_not_owned(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(
            CatalogoOwnershipError, match="You do not own this catalog"
        ):
            await service.rename_catalog(
                catalog_id=catalog_id,
                mayorista_id=mayorista_id,
                new_name="New Name",
            )

    # --- Story 006: Publish/Unpublish Catalog ---

    @pytest.mark.asyncio
    async def test_should_publish_catalog_with_items(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.id = catalog_id
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo.status = "draft"
        mock_catalogo.item_count = 5
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        updated_catalogo = MagicMock(spec=Catalogo)
        updated_catalogo.status = "published"
        mock_catalogo_repo.update_status = AsyncMock(
            return_value=updated_catalogo
        )

        result = await service.update_catalog_status(
            catalog_id=catalog_id,
            mayorista_id=mayorista_id,
            new_status="published",
        )

        assert result.status == "published"
        mock_catalogo_repo.update_status.assert_called_once_with(
            catalog_id, "published"
        )

    @pytest.mark.asyncio
    async def test_should_unpublish_published_catalog(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.id = catalog_id
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo.status = "published"
        mock_catalogo.item_count = 5
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        updated_catalogo = MagicMock(spec=Catalogo)
        updated_catalogo.status = "draft"
        mock_catalogo_repo.update_status = AsyncMock(
            return_value=updated_catalogo
        )

        result = await service.update_catalog_status(
            catalog_id=catalog_id,
            mayorista_id=mayorista_id,
            new_status="draft",
        )

        assert result.status == "draft"

    @pytest.mark.asyncio
    async def test_should_reject_publish_empty_catalog(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.id = catalog_id
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo.status = "draft"
        mock_catalogo.item_count = 0
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        with pytest.raises(
            EmptyCatalogCannotPublishError,
            match="Cannot publish an empty catalog",
        ):
            await service.update_catalog_status(
                catalog_id=catalog_id,
                mayorista_id=mayorista_id,
                new_status="published",
            )

    @pytest.mark.asyncio
    async def test_should_reject_invalid_status_value(
        self, service
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        with pytest.raises(
            InvalidCatalogStatusError,
            match="Status must be 'draft' or 'published'",
        ):
            await service.update_catalog_status(
                catalog_id=catalog_id,
                mayorista_id=mayorista_id,
                new_status="archived",
            )

    @pytest.mark.asyncio
    async def test_should_return_same_catalog_on_idempotent_publish(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.id = catalog_id
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo.status = "published"
        mock_catalogo.item_count = 5
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        result = await service.update_catalog_status(
            catalog_id=catalog_id,
            mayorista_id=mayorista_id,
            new_status="published",
        )

        assert result.status == "published"
        mock_catalogo_repo.update_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_reject_publish_catalog_not_found(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(CatalogoNotFoundError, match="Catalog not found"):
            await service.update_catalog_status(
                catalog_id=catalog_id,
                mayorista_id=mayorista_id,
                new_status="published",
            )

    @pytest.mark.asyncio
    async def test_should_reject_publish_catalog_not_owned(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(
            CatalogoOwnershipError, match="You do not own this catalog"
        ):
            await service.update_catalog_status(
                catalog_id=catalog_id,
                mayorista_id=mayorista_id,
                new_status="published",
            )

    # --- Story 007: Delete Catalog ---

    @pytest.mark.asyncio
    async def test_should_delete_catalog_and_items(
        self, service, mock_catalogo_repo, mock_item_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.id = catalog_id
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_item_repo.delete_all_by_catalog = AsyncMock(return_value=5)
        mock_catalogo_repo.delete = AsyncMock(return_value=True)

        await service.delete_catalog(
            catalog_id=catalog_id,
            mayorista_id=mayorista_id,
        )

        mock_item_repo.delete_all_by_catalog.assert_called_once_with(catalog_id)
        mock_catalogo_repo.delete.assert_called_once_with(catalog_id)

    @pytest.mark.asyncio
    async def test_should_reject_delete_catalog_not_found(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(CatalogoNotFoundError, match="Catalog not found"):
            await service.delete_catalog(
                catalog_id=catalog_id,
                mayorista_id=mayorista_id,
            )

    @pytest.mark.asyncio
    async def test_should_reject_delete_catalog_not_owned(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(
            CatalogoOwnershipError, match="You do not own this catalog"
        ):
            await service.delete_catalog(
                catalog_id=catalog_id,
                mayorista_id=mayorista_id,
            )

    # --- Story 008: List Catalogs ---

    @pytest.mark.asyncio
    async def test_should_list_catalogs_with_pagination(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()

        mock_catalogs = [MagicMock(spec=Catalogo) for _ in range(3)]
        mock_catalogo_repo.list_by_mayorista = AsyncMock(
            return_value=(mock_catalogs, 10)
        )

        catalogs, total = await service.list_catalogs(
            mayorista_id=mayorista_id,
            page=1,
            page_size=20,
        )

        assert len(catalogs) == 3
        assert total == 10
        mock_catalogo_repo.list_by_mayorista.assert_called_once_with(
            mayorista_id, 1, 20
        )

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_no_catalogs(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()

        mock_catalogo_repo.list_by_mayorista = AsyncMock(
            return_value=([], 0)
        )

        catalogs, total = await service.list_catalogs(
            mayorista_id=mayorista_id,
            page=1,
            page_size=20,
        )

        assert len(catalogs) == 0
        assert total == 0

    # --- Story 009: Get Catalog with Items ---

    @pytest.mark.asyncio
    async def test_should_get_catalog_with_items(
        self, service, mock_catalogo_repo, mock_item_repo, mock_minio
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.id = catalog_id
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo.name = "Test Catalog"
        mock_catalogo.status = "draft"
        mock_catalogo.item_count = 2
        mock_catalogo.created_at = datetime.now(timezone.utc)
        mock_catalogo.updated_at = datetime.now(timezone.utc)
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_item1 = MagicMock(spec=CatalogoItem)
        mock_item1.id = uuid.uuid4()
        mock_item1.catalog_id = catalog_id
        mock_item1.vton_job_id = uuid.uuid4()
        mock_item1.garment_name = "Blazer"
        mock_item1.price = Decimal("89.99")
        mock_item1.cloth_type = "upper_body"
        mock_item1.sku = "BLZ-001"
        mock_item1.image_key = "results/1.jpg"
        mock_item1.position = 1
        mock_item1.created_at = datetime.now(timezone.utc)

        mock_item2 = MagicMock(spec=CatalogoItem)
        mock_item2.id = uuid.uuid4()
        mock_item2.catalog_id = catalog_id
        mock_item2.vton_job_id = uuid.uuid4()
        mock_item2.garment_name = "Pants"
        mock_item2.price = Decimal("49.99")
        mock_item2.cloth_type = "lower_body"
        mock_item2.sku = "PNT-001"
        mock_item2.image_key = "results/2.jpg"
        mock_item2.position = 2
        mock_item2.created_at = datetime.now(timezone.utc)

        mock_item_repo.get_all_by_catalog = AsyncMock(
            return_value=[mock_item1, mock_item2]
        )

        catalogo, items_with_urls = await service.get_catalog_with_items(
            catalog_id=catalog_id,
            mayorista_id=mayorista_id,
        )

        assert catalogo.name == "Test Catalog"
        assert catalogo.item_count == 2
        assert len(items_with_urls) == 2
        assert items_with_urls[0][0].garment_name == "Blazer"
        assert items_with_urls[0][1] == "http://minio/presigned"
        assert items_with_urls[1][0].garment_name == "Pants"
        assert items_with_urls[1][1] == "http://minio/presigned"

    @pytest.mark.asyncio
    async def test_should_get_catalog_with_no_items(
        self, service, mock_catalogo_repo, mock_item_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo = MagicMock(spec=Catalogo)
        mock_catalogo.id = catalog_id
        mock_catalogo.mayorista_id = mayorista_id
        mock_catalogo.name = "Empty Catalog"
        mock_catalogo.status = "draft"
        mock_catalogo.item_count = 0
        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(
            return_value=mock_catalogo
        )

        mock_item_repo.get_all_by_catalog = AsyncMock(return_value=[])

        catalogo, items_with_urls = await service.get_catalog_with_items(
            catalog_id=catalog_id,
            mayorista_id=mayorista_id,
        )

        assert catalogo.name == "Empty Catalog"
        assert catalogo.item_count == 0
        assert items_with_urls == []

    @pytest.mark.asyncio
    async def test_should_reject_get_catalog_not_found(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(CatalogoNotFoundError, match="Catalog not found"):
            await service.get_catalog_with_items(
                catalog_id=catalog_id,
                mayorista_id=mayorista_id,
            )

    @pytest.mark.asyncio
    async def test_should_reject_get_catalog_not_owned(
        self, service, mock_catalogo_repo
    ):
        mayorista_id = uuid.uuid4()
        catalog_id = uuid.uuid4()

        mock_catalogo_repo.get_by_id_and_mayorista = AsyncMock(return_value=None)
        mock_catalogo_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(
            CatalogoOwnershipError, match="You do not own this catalog"
        ):
            await service.get_catalog_with_items(
                catalog_id=catalog_id,
                mayorista_id=mayorista_id,
            )
