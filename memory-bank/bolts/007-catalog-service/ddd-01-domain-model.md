---
stage: model
bolt: 007-catalog-service
created: 2026-05-28T14:30:00Z
---

# Domain Model: 007-catalog-service

## Bounded Context

This bolt extends the **Catalog Management** bounded context established in bolt 006. It adds lifecycle operations (rename, publish/unpublish, delete) and query operations (list) to the existing Catalog aggregate.

## Entities

No new entities. This bolt operates on existing entities from bolt 006:

- **Catalog** (aggregate root): `id, mayorista_id, name, status, item_count, created_at, updated_at`
- **CatalogItem**: `id, catalog_id, vton_job_id, garment_name, price, cloth_type, sku, image_key, position, created_at`

## Value Objects

No new value objects. This bolt uses existing value objects:

- **CatalogStatus**: enum with values `draft` and `published`

## Aggregates

No changes to aggregate boundaries. The Catalog aggregate root continues to manage its CatalogItem collection.

### New Invariants

1. **Publish Guard**: A catalog with `item_count == 0` cannot transition to `published` status
2. **Idempotent Status Transitions**: Publishing an already-published catalog or unpublishing an already-draft catalog is a no-op (returns 200, no state change)
3. **Cascade Delete Invariant**: When a Catalog is deleted, all its CatalogItems must be deleted in the same transaction

## Domain Events

### New Events

- **CatalogRenamed**: Triggered when catalog name is updated
  - Payload: `{ catalog_id, mayorista_id, old_name, new_name, updated_at }`

- **CatalogPublished**: Triggered when catalog status changes from draft to published
  - Payload: `{ catalog_id, mayorista_id, item_count, published_at }`

- **CatalogUnpublished**: Triggered when catalog status changes from published to draft
  - Payload: `{ catalog_id, mayorista_id, unpublished_at }`

- **CatalogDeleted**: Triggered when catalog is permanently deleted
  - Payload: `{ catalog_id, mayorista_id, item_count, deleted_at }`

## Domain Services

### CatalogLifecycleService

Extends the existing CatalogService with lifecycle operations:

**Operations**:

1. **rename_catalog(catalog_id, mayorista_id, new_name) -> Catalog**
   - Validates ownership
   - Validates name (non-empty, max 100 chars, not whitespace-only)
   - Updates `name` field
   - Updates `updated_at` timestamp
   - Emits CatalogRenamed event
   - Returns updated catalog

2. **update_status(catalog_id, mayorista_id, new_status) -> Catalog**
   - Validates ownership
   - Validates status value (must be 'draft' or 'published')
   - If transitioning to 'published':
     - Check `item_count > 0`, else raise EmptyCatalogCannotPublishError
   - If status unchanged (idempotent): return catalog without update
   - Updates `status` field
   - Updates `updated_at` timestamp
   - Emits CatalogPublished or CatalogUnpublished event
   - Returns updated catalog

3. **delete_catalog(catalog_id, mayorista_id) -> None**
   - Validates ownership
   - Deletes all CatalogItems for this catalog (cascade)
   - Deletes the Catalog
   - Emits CatalogDeleted event

4. **list_catalogs(mayorista_id, page, page_size) -> (list[Catalog], total_count)**
   - Queries catalogs owned by mayorista_id
   - Orders by `created_at DESC`
   - Applies pagination (offset-based)
   - Returns list and total count

### Error Conditions

- **CatalogNotFoundError**: Catalog does not exist
- **CatalogOwnershipError**: Mayorista does not own the catalog
- **EmptyCatalogCannotPublishError**: Attempted to publish catalog with `item_count == 0`
- **InvalidCatalogStatusError**: Status value is not 'draft' or 'published'

## Repository Interfaces

### CatalogRepository (Extended)

New methods added to existing repository:

```python
async def update_name(self, catalog_id: UUID, new_name: str) -> Catalog | None:
    """Update catalog name and updated_at timestamp."""

async def update_status(self, catalog_id: UUID, new_status: str) -> Catalog | None:
    """Update catalog status and updated_at timestamp."""

async def delete(self, catalog_id: UUID) -> bool:
    """Delete catalog and all its items (cascade)."""

async def list_by_mayorista(
    self, mayorista_id: UUID, page: int, page_size: int
) -> tuple[list[Catalog], int]:
    """List catalogs owned by mayorista with pagination."""
```

### CatalogItemRepository (Extended)

New method added to existing repository:

```python
async def delete_all_by_catalog(self, catalog_id: UUID) -> int:
    """Delete all items for a catalog. Returns count of deleted items."""
```

## Business Rules

### Rename Rules

1. Name must be non-empty after stripping whitespace
2. Name must not exceed 100 characters
3. Name can be the same as current value (no-op, returns 200)
4. Rename does not affect `status` or `item_count`
5. Rename updates `updated_at` timestamp

### Publish/Unpublish Rules

1. **Publish Guard**: Cannot publish if `item_count == 0` (raises 422)
2. **Idempotent Publish**: Publishing already-published catalog returns 200 with no state change
3. **Idempotent Unpublish**: Unpublishing already-draft catalog returns 200 with no state change
4. **Instant Effect**: Published catalogs are immediately visible to buyers
5. **Instant Hide**: Unpublished catalogs immediately return 404 to buyers
6. Status transitions are synchronous (no background jobs)

### Delete Rules

1. Delete is permanent and irreversible
2. Cascade delete: all CatalogItems deleted in same transaction
3. VTON job records are NOT deleted (they belong to VTON pipeline domain)
4. Deleted published catalogs immediately return 404 to buyers
5. Delete returns 204 No Content on success

### List Rules

1. Only catalogs owned by the authenticated mayorista are returned
2. Default pagination: `page=1, page_size=20`
3. Maximum `page_size` is 100 (clamp larger values)
4. Minimum `page_size` is 1 (400 error if < 1)
5. Default ordering: `created_at DESC` (newest first)
6. Empty result returns `{ catalogs: [], total: 0, page: 1 }`
7. Page beyond total pages returns empty list with correct total

## API Contract (Preview)

### PATCH /api/catalogs/{catalog_id}

**Request Body** (one or both fields):
```json
{
  "name": "Winter 2026",
  "status": "published"
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "mayorista_id": "uuid",
  "name": "Winter 2026",
  "status": "published",
  "item_count": 5,
  "created_at": "2026-05-28T10:00:00Z",
  "updated_at": "2026-05-28T14:00:00Z"
}
```

**Error Responses**:
- 400: Invalid name or status value
- 403: Not the owner
- 404: Catalog not found
- 422: Cannot publish empty catalog

### DELETE /api/catalogs/{catalog_id}

**Response**: 204 No Content

**Error Responses**:
- 403: Not the owner
- 404: Catalog not found

### GET /api/catalogs

**Query Parameters**:
- `page` (int, default 1, min 1)
- `page_size` (int, default 20, min 1, max 100)

**Response** (200 OK):
```json
{
  "catalogs": [
    {
      "id": "uuid",
      "mayorista_id": "uuid",
      "name": "Summer 2026",
      "status": "published",
      "item_count": 10,
      "created_at": "2026-05-28T10:00:00Z",
      "updated_at": "2026-05-28T12:00:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 20
}
```

**Error Responses**:
- 400: Invalid pagination parameters
- 401: Not authenticated

## Integration Points

### Existing Integrations (from bolt 006)

- **MinIO**: No new MinIO operations in this bolt
- **VTON Jobs**: No new VTON job interactions

### New Integration Considerations

- **Buyer Portal (future bolt 008)**: Published catalogs will be queryable by buyer portal service
- **UI Layer (future bolt 009)**: List API will be consumed by catalog management UI

## Design Decisions

### PATCH Endpoint Design

**Decision**: Use single PATCH endpoint for both rename and status update

**Rationale**:
- Both operations update catalog metadata
- Field presence determines action (if `name` present, update name; if `status` present, update status)
- Both fields can be updated in single request
- Simpler API surface than separate endpoints

**Alternative Considered**: Separate endpoints (`PATCH /rename`, `PATCH /status`)
- Rejected: More endpoints, less RESTful

### Cascade Delete Strategy

**Decision**: Delete all CatalogItems in same transaction as Catalog

**Rationale**:
- Maintains referential integrity
- Single transaction ensures atomicity
- Items have no meaning without parent catalog

**Alternative Considered**: Soft delete with `deleted_at` timestamp
- Rejected: Out of scope for MVP, adds complexity

### Pagination Strategy

**Decision**: Offset-based pagination with `page` and `page_size`

**Rationale**:
- Consistent with existing VTON job list API
- Simple to implement and understand
- Suitable for moderate dataset sizes (hundreds of catalogs per mayorista)

**Alternative Considered**: Cursor-based pagination
- Rejected: More complex, not needed for this use case

## Ubiquitous Language

### New Terms

- **Publish**: Make a catalog visible to buyers in the portal
- **Unpublish**: Hide a catalog from buyers in the portal
- **Rename**: Update the display name of a catalog
- **Cascade Delete**: Delete operation that removes parent and all children in one transaction
- **Empty Catalog**: A catalog with `item_count == 0`
- **Publish Guard**: Business rule preventing publication of empty catalogs

### Existing Terms (from bolt 006)

- Catalog, CatalogItem, Mayorista, Draft, Published, Item Count

## Summary

This bolt extends the Catalog aggregate with lifecycle operations:

- **Rename**: Update catalog name with validation
- **Publish/Unpublish**: Toggle visibility with empty-catalog guard
- **Delete**: Permanent removal with cascade
- **List**: Paginated query for catalog management

All operations respect ownership (mayorista_id) and maintain aggregate invariants.
