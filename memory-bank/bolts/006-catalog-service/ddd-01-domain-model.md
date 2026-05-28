---
unit: 001-catalog-service
bolt: 006-catalog-service
stage: model
status: complete
updated: 2026-05-28T10:00:00Z
---

# Static Model - 001-catalog-service

## Bounded Context

**Catalog Management** — encompasses the creation and curation of product catalogs by a mayorista. This context owns the lifecycle of catalogs (draft collections of VTON-generated garment images) and their items (individual garment entries with product metadata). It reads from the VTON Pipeline context (job completion status, result image keys, mayorista ownership) but does not modify it.

## Domain Entities

- **Catalog**: `id (UUID), mayorista_id (UUID), name (string), status (CatalogStatus), item_count (int), created_at (datetime), updated_at (datetime)` — A named collection of garment images owned by a mayorista. Created in `draft` status. Only the owning mayorista may access or modify it. `item_count` is a denormalized counter reflecting the number of items.

- **CatalogItem**: `id (UUID), catalog_id (UUID), vton_job_id (UUID), garment_name (string), price (Decimal), cloth_type (ClothType), sku (string), image_key (string), position (int), created_at (datetime)` — A single garment entry within a catalog. References a completed VTON job. Stores the MinIO object key (not URL) for the result image. Position determines display order within the catalog.

## Value Objects

- **CatalogName**: `value (string)` — Constraints: 1-100 characters, must not be blank or whitespace-only. Immutable after construction (rename is a separate operation in a future bolt).

- **CatalogStatus**: `value (enum: draft | published)` — Constrains state transitions. Catalogs are created as `draft`. Publishing and unpublishing are handled in bolt 007.

- **Position**: `value (int)` — Constraints: positive integer (>= 1). Assigned automatically: `MAX(existing positions) + 1` on add, re-normalized to consecutive integers on reorder.

- **ItemMetadata**: `garment_name (string), price (Decimal), cloth_type (ClothType), sku (string)` — Constraints: `garment_name` non-empty, `price` >= 0 with precision (10,2), `cloth_type` in {upper_body, lower_body, dress}, `sku` non-empty string.

- **ClothType**: `value (enum: upper_body | lower_body | dress)` — Categorizes the garment for VTON model compatibility. Must match the VTON job's cloth type.

- **Price**: `amount (Decimal)` — Constraints: non-negative, precision (10,2). Accepts string or number input, normalized to Decimal on construction.

## Aggregates

- **Catalog** (Aggregate Root): Members: `CatalogItem` collection - Invariants:
  1. A Catalog always has a valid `CatalogName` (non-blank, <= 100 chars)
  2. A Catalog is always owned by exactly one `mayorista_id` — never orphaned
  3. `item_count` must equal the actual count of CatalogItems (eventual consistency acceptable within transaction boundary)
  4. All CatalogItems within a Catalog have unique `position` values (no duplicates)
  5. A CatalogItem's `vton_job_id` must reference a completed job owned by the same mayorista as the Catalog (cross-aggregate validation via domain service)
  6. Reorder operations must include exactly the full set of item IDs (bijection) — partial reorders are rejected
  7. Positions after reorder are consecutive integers starting from 1

## Domain Events

- **CatalogCreated**: Trigger: New catalog successfully persisted - Payload: `{ catalog_id, mayorista_id, name, status: draft, created_at }`

- **CatalogItemAdded**: Trigger: Item successfully added to catalog - Payload: `{ catalog_id, item_id, vton_job_id, position, item_count (updated) }`

- **CatalogItemRemoved**: Trigger: Item successfully deleted from catalog - Payload: `{ catalog_id, item_id, item_count (updated) }`

- **CatalogItemsReordered**: Trigger: Reorder transaction committed - Payload: `{ catalog_id, ordered_item_ids: [UUID], new_positions: {item_id: position} }`

## Domain Services

- **CatalogItemAdditionService**: Operations: `validate_and_add_item(catalog_id, vton_job_id, metadata, mayorista_id)` - Dependencies: `CatalogRepository`, `CatalogItemRepository`, `VTONJobRepository` (read-only cross-context). Validates: (1) catalog exists and belongs to mayorista, (2) VTON job exists, is completed, and belongs to the same mayorista, (3) metadata is valid. Creates the CatalogItem with next position and increments `item_count`.

- **CatalogReorderService**: Operations: `reorder_items(catalog_id, ordered_item_ids, mayorista_id)` - Dependencies: `CatalogRepository`, `CatalogItemRepository`. Validates: (1) catalog exists and belongs to mayorista, (2) `ordered_item_ids` is a bijection of current items. Atomically updates all positions within a single transaction.

## Repository Interfaces

- **CatalogRepo**: Entity: `Catalog` - Methods:
  - `create(catalog: Catalog) -> Catalog`
  - `get_by_id(catalog_id: UUID) -> Catalog | None`
  - `get_by_id_and_owner(catalog_id: UUID, mayorista_id: UUID) -> Catalog | None`
  - `update_item_count(catalog_id: UUID, delta: int) -> None`

- **CatalogItemRepo**: Entity: `CatalogItem` - Methods:
  - `create(item: CatalogItem) -> CatalogItem`
  - `get_by_id_and_catalog(item_id: UUID, catalog_id: UUID) -> CatalogItem | None`
  - `delete(item_id: UUID, catalog_id: UUID) -> None`
  - `get_all_by_catalog(catalog_id: UUID) -> list[CatalogItem]`
  - `get_max_position(catalog_id: UUID) -> int`
  - `update_positions(item_positions: dict[UUID, int]) -> None` (atomic batch update)

- **VTONJobRepo** (read-only, cross-context): Entity: `VTONJob` - Methods:
  - `get_by_id(job_id: UUID) -> VTONJob | None`
  - `verify_ownership(job_id: UUID, mayorista_id: UUID) -> bool`
  - `is_completed(job_id: UUID) -> bool`

## Ubiquitous Language

- **Catalog**: A named, ordered collection of garment images created by a mayorista for sharing with buyers
- **CatalogItem**: A single garment entry in a catalog, linking a VTON result image with product metadata
- **Mayorista**: A wholesaler user who creates catalogs and manages garment imagery
- **VTON Job**: A virtual try-on inference job that produces a result image stored in MinIO
- **image_key**: The MinIO object key for a VTON result image — stored in DB, not the URL
- **Pre-signed URL**: A time-limited MinIO URL generated on demand from an `image_key` for secure image access
- **Position**: An integer determining the display order of items within a catalog
- **Draft**: The initial status of a catalog; not yet visible to buyers
- **item_count**: Denormalized counter on the Catalog entity reflecting current number of items
- **Reorder**: An atomic operation that reassigns consecutive position values to all items in a catalog based on a user-specified ordering
- **Bijection**: The requirement that a reorder request must contain exactly the same set of item IDs as currently exist in the catalog
