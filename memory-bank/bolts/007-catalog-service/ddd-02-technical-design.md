---
stage: design
bolt: 007-catalog-service
created: 2026-05-28T15:00:00Z
---

# Technical Design: 007-catalog-service

## Architecture Overview

This bolt extends the existing catalog module created in bolt 006. No new modules or files are created — all changes are additions to existing files.

### Extension Points

1. **CatalogoRepo** (`repositories/catalogo_repo.py`): Add 4 new methods
2. **CatalogoItemRepo** (`repositories/catalogo_repo.py`): Add 1 new method
3. **CatalogoService** (`services/catalogo_service.py`): Add 4 new methods + 3 new exceptions
4. **Schemas** (`api/schemas/catalogo.py`): Add 3 new Pydantic models
5. **Router** (`api/routers/catalogo.py`): Add 3 new endpoints

## Data Model Changes

No schema changes. All operations use existing `catalogo` and `catalogo_item` tables from bolt 006.

### Existing Tables Used

- `catalogo`: `id, mayorista_id, name, status, item_count, created_at, updated_at`
- `catalogo_item`: `id, catalog_id, vton_job_id, garment_name, price, cloth_type, sku, image_key, position, created_at`

## Repository Layer

### CatalogoRepo Extensions

```python
async def update_name(self, catalog_id: UUID, new_name: str) -> Catalogo | None:
    """Update catalog name and updated_at timestamp.
    
    Returns updated catalog or None if not found.
    """
    stmt = (
        update(Catalogo)
        .where(Catalogo.id == catalog_id)
        .values(name=new_name, updated_at=func.now())
        .returning(Catalogo)
    )
    result = await self._db.execute(stmt)
    await self._db.commit()
    return result.scalar_one_or_none()

async def update_status(self, catalog_id: UUID, new_status: str) -> Catalogo | None:
    """Update catalog status and updated_at timestamp.
    
    Returns updated catalog or None if not found.
    """
    stmt = (
        update(Catalogo)
        .where(Catalogo.id == catalog_id)
        .values(status=new_status, updated_at=func.now())
        .returning(Catalogo)
    )
    result = await self._db.execute(stmt)
    await self._db.commit()
    return result.scalar_one_or_none()

async def delete(self, catalog_id: UUID) -> bool:
    """Delete catalog (items must be deleted first via CatalogoItemRepo).
    
    Returns True if deleted, False if not found.
    """
    stmt = delete(Catalogo).where(Catalogo.id == catalog_id)
    result = await self._db.execute(stmt)
    await self._db.commit()
    return result.rowcount > 0

async def list_by_mayorista(
    self, mayorista_id: UUID, page: int, page_size: int
) -> tuple[list[Catalogo], int]:
    """List catalogs owned by mayorista with pagination.
    
    Returns (catalogs, total_count).
    """
    offset = (page - 1) * page_size
    
    count_stmt = select(func.count(Catalogo.id)).where(
        Catalogo.mayorista_id == mayorista_id
    )
    total_result = await self._db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    list_stmt = (
        select(Catalogo)
        .where(Catalogo.mayorista_id == mayorista_id)
        .order_by(Catalogo.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await self._db.execute(list_stmt)
    catalogs = list(result.scalars().all())
    
    return catalogs, total
```

### CatalogoItemRepo Extensions

```python
async def delete_all_by_catalog(self, catalog_id: UUID) -> int:
    """Delete all items for a catalog.
    
    Returns count of deleted items.
    """
    stmt = delete(CatalogoItem).where(CatalogoItem.catalog_id == catalog_id)
    result = await self._db.execute(stmt)
    await self._db.commit()
    return result.rowcount
```

## Service Layer

### New Exceptions

```python
class EmptyCatalogCannotPublishError(Exception):
    """Raised when attempting to publish a catalog with 0 items."""

class InvalidCatalogStatusError(Exception):
    """Raised when status value is not 'draft' or 'published'."""
```

### CatalogoService Extensions

```python
async def rename_catalog(
    self, catalog_id: UUID, mayorista_id: UUID, new_name: str
) -> Catalogo:
    """Rename a catalog.
    
    Raises:
        CatalogoNotFoundError: If catalog doesn't exist
        CatalogoOwnershipError: If mayorista doesn't own the catalog
    """
    catalogo = await self._catalogo_repo.get_by_id_and_mayorista(
        catalog_id, mayorista_id
    )
    if catalogo is None:
        exists = await self._catalogo_repo.get_by_id(catalog_id)
        if exists is None:
            raise CatalogoNotFoundError("Catalog not found")
        raise CatalogoOwnershipError("You do not own this catalog")
    
    updated = await self._catalogo_repo.update_name(catalog_id, new_name)
    return updated

async def update_catalog_status(
    self, catalog_id: UUID, mayorista_id: UUID, new_status: str
) -> Catalogo:
    """Update catalog status (publish/unpublish).
    
    Raises:
        CatalogoNotFoundError: If catalog doesn't exist
        CatalogoOwnershipError: If mayorista doesn't own the catalog
        InvalidCatalogStatusError: If status is not 'draft' or 'published'
        EmptyCatalogCannotPublishError: If publishing empty catalog
    """
    if new_status not in ("draft", "published"):
        raise InvalidCatalogStatusError(
            "Status must be 'draft' or 'published'"
        )
    
    catalogo = await self._catalogo_repo.get_by_id_and_mayorista(
        catalog_id, mayorista_id
    )
    if catalogo is None:
        exists = await self._catalogo_repo.get_by_id(catalog_id)
        if exists is None:
            raise CatalogoNotFoundError("Catalog not found")
        raise CatalogoOwnershipError("You do not own this catalog")
    
    if new_status == "published" and catalogo.item_count == 0:
        raise EmptyCatalogCannotPublishError(
            "Cannot publish an empty catalog"
        )
    
    if catalogo.status == new_status:
        return catalogo
    
    updated = await self._catalogo_repo.update_status(catalog_id, new_status)
    return updated

async def delete_catalog(
    self, catalog_id: UUID, mayorista_id: UUID
) -> None:
    """Delete a catalog and all its items.
    
    Raises:
        CatalogoNotFoundError: If catalog doesn't exist
        CatalogoOwnershipError: If mayorista doesn't own the catalog
    """
    catalogo = await self._catalogo_repo.get_by_id_and_mayorista(
        catalog_id, mayorista_id
    )
    if catalogo is None:
        exists = await self._catalogo_repo.get_by_id(catalog_id)
        if exists is None:
            raise CatalogoNotFoundError("Catalog not found")
        raise CatalogoOwnershipError("You do not own this catalog")
    
    await self._item_repo.delete_all_by_catalog(catalog_id)
    await self._catalogo_repo.delete(catalog_id)

async def list_catalogs(
    self, mayorista_id: UUID, page: int, page_size: int
) -> tuple[list[Catalogo], int]:
    """List catalogs owned by mayorista with pagination.
    
    Returns (catalogs, total_count).
    """
    return await self._catalogo_repo.list_by_mayorista(
        mayorista_id, page, page_size
    )
```

## API Layer

### Pydantic Schemas

```python
class CatalogoUpdateRequest(BaseModel):
    """Request schema for PATCH /api/catalogos/{id}"""
    name: str | None = Field(None, min_length=1, max_length=100)
    status: CatalogStatus | None = None
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Catalog name cannot be empty or whitespace only")
        return stripped

class CatalogoListResponse(BaseModel):
    """Response schema for GET /api/catalogos"""
    catalogs: list[CatalogoResponse]
    total: int
    page: int
    page_size: int
```

### Router Endpoints

```python
@router.patch("/{catalog_id}", response_model=CatalogoResponse)
async def update_catalog(
    catalog_id: UUID,
    body: CatalogoUpdateRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    catalogo_service: CatalogoService = Depends(_get_catalogo_service),
):
    """Update catalog name and/or status."""
    try:
        catalogo = None
        
        if body.name is not None:
            catalogo = await catalogo_service.rename_catalog(
                catalog_id=catalog_id,
                mayorista_id=mayorista.id,
                new_name=body.name,
            )
        
        if body.status is not None:
            catalogo = await catalogo_service.update_catalog_status(
                catalog_id=catalog_id,
                mayorista_id=mayorista.id,
                new_status=body.status.value,
            )
        
        if catalogo is None:
            catalogo = await catalogo_service.get_catalog(
                catalog_id=catalog_id,
                mayorista_id=mayorista.id,
            )
        
        return catalogo
        
    except CatalogoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CatalogoOwnershipError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidCatalogStatusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmptyCatalogCannotPublishError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.delete("/{catalog_id}", status_code=204)
async def delete_catalog(
    catalog_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    catalogo_service: CatalogoService = Depends(_get_catalogo_service),
):
    """Delete a catalog and all its items."""
    try:
        await catalogo_service.delete_catalog(
            catalog_id=catalog_id,
            mayorista_id=mayorista.id,
        )
    except CatalogoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CatalogoOwnershipError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

@router.get("", response_model=CatalogoListResponse)
async def list_catalogs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mayorista: Mayorista = Depends(get_current_mayorista),
    catalogo_service: CatalogoService = Depends(_get_catalogo_service),
):
    """List catalogs owned by the authenticated mayorista."""
    catalogs, total = await catalogo_service.list_catalogs(
        mayorista_id=mayorista.id,
        page=page,
        page_size=page_size,
    )
    return CatalogoListResponse(
        catalogs=catalogs,
        total=total,
        page=page,
        page_size=page_size,
    )
```

## Error Handling

### Error Mapping

| Domain Exception | HTTP Status | Use Case |
|------------------|-------------|----------|
| CatalogoNotFoundError | 404 | Catalog doesn't exist |
| CatalogoOwnershipError | 403 | Mayorista doesn't own catalog |
| InvalidCatalogStatusError | 400 | Invalid status value |
| EmptyCatalogCannotPublishError | 422 | Publishing empty catalog |

### Validation Errors (Pydantic)

| Field | Validation | HTTP Status |
|-------|-----------|-------------|
| name | min_length=1, max_length=100, not whitespace | 422 |
| status | Must be 'draft' or 'published' | 422 |
| page | ge=1 | 422 |
| page_size | ge=1, le=100 | 422 |

## Testing Strategy

### Unit Tests (test_catalogo_service.py)

**Story 005 - Rename (4 tests)**:
- Rename catalog successfully
- Reject rename when catalog not found
- Reject rename when not owner
- Reject rename with invalid name

**Story 006 - Publish/Unpublish (6 tests)**:
- Publish catalog with items successfully
- Unpublish published catalog successfully
- Reject publish when catalog not found
- Reject publish when not owner
- Reject publish when catalog is empty
- Idempotent publish (already published)

**Story 007 - Delete (3 tests)**:
- Delete catalog and items successfully
- Reject delete when catalog not found
- Reject delete when not owner

**Story 008 - List (3 tests)**:
- List catalogs with pagination
- List returns empty when no catalogs
- List respects page_size limit

### Integration Tests (test_catalogo_api.py)

**Story 005 - Rename (3 tests)**:
- PATCH with name updates catalog
- PATCH with empty name returns 422
- PATCH on non-existent catalog returns 404

**Story 006 - Publish/Unpublish (4 tests)**:
- PATCH with status=published succeeds
- PATCH with status=draft succeeds
- PATCH publish empty catalog returns 422
- PATCH with invalid status returns 422

**Story 007 - Delete (2 tests)**:
- DELETE removes catalog and items
- DELETE non-existent catalog returns 404

**Story 008 - List (4 tests)**:
- GET returns paginated catalogs
- GET with no catalogs returns empty list
- GET with page_size > 100 clamps to 100
- GET without auth returns 401

## Performance Considerations

### Cascade Delete

- **Strategy**: Delete items first, then catalog
- **Transaction**: Both operations in same DB transaction
- **Performance**: O(n) where n = item_count
- **Optimization**: Single DELETE statement with WHERE clause (no SELECT needed)

### Pagination

- **Strategy**: Offset-based with COUNT query
- **Performance**: O(1) for count (indexed), O(page_size) for list
- **Index**: `idx_catalogo_mayorista_created` supports efficient pagination
- **Scaling**: Suitable for hundreds of catalogs per mayorista

### Status Update

- **Strategy**: Single UPDATE statement
- **Performance**: O(1)
- **Index**: Primary key lookup

## Security Considerations

### Ownership Validation

All operations validate `mayorista_id` before proceeding:
- `get_by_id_and_mayorista` ensures catalog belongs to authenticated user
- Prevents cross-tenant data access

### Input Validation

- Name: Stripped and validated for length/whitespace
- Status: Enum validation ensures only 'draft' or 'published'
- Pagination: Clamped to valid range (1-100)

## Migration Strategy

No database migration needed. This bolt only adds application logic to existing tables.

## Deployment Notes

- No new dependencies
- No configuration changes
- Backward compatible (existing endpoints unchanged)
- Can be deployed independently of bolt 006

## Summary

This technical design extends the catalog module with lifecycle operations:

- **3 new endpoints**: PATCH, DELETE, GET (list)
- **4 new service methods**: rename, update_status, delete, list
- **5 new repository methods**: update_name, update_status, delete, list_by_mayorista, delete_all_by_catalog
- **3 new exceptions**: EmptyCatalogCannotPublishError, InvalidCatalogStatusError
- **3 new schemas**: CatalogoUpdateRequest, CatalogoListResponse

All changes are additive and maintain backward compatibility with bolt 006.
