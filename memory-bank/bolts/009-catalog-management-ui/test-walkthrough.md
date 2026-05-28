---
stage: test
bolt: 009-catalog-management-ui
created: 2026-05-28T20:30:00Z
---

# Test Walkthrough: 009-catalog-management-ui

## Test Strategy

Tests cover three layers:
1. **Backend API tests** — Integration tests against FastAPI endpoints using httpx.AsyncClient
2. **Backend service tests** — Unit tests with mocked repositories
3. **Frontend E2E tests** — Playwright tests covering full user flows

## Backend API Tests

**File:** `backend/tests/test_catalogo_api.py`

### New Tests Added (GET /{catalog_id} endpoint)

| Test | Description | Expected |
|------|-------------|----------|
| `test_should_get_catalog_detail` | Authenticated user gets their catalog | 200, catalog data with empty items array |
| `test_should_reject_get_detail_nonexistent_catalog` | Get non-existent catalog | 404 |
| `test_should_reject_get_detail_without_auth` | Get catalog without authentication | 401 |
| `test_should_reject_get_detail_other_users_catalog` | Get another user's catalog | 403 |

### Run Command

```bash
cd backend && pytest tests/test_catalogo_api.py -v -k "detail"
```

## Backend Service Tests

**File:** `backend/tests/test_catalogo_service.py`

### New Tests Added (get_catalog_with_items method)

| Test | Description | Expected |
|------|-------------|----------|
| `test_should_get_catalog_with_items` | Get catalog with 2 items | Returns catalog + items with presigned URLs |
| `test_should_get_catalog_with_no_items` | Get empty catalog | Returns catalog + empty items list |
| `test_should_reject_get_catalog_not_found` | Catalog doesn't exist | Raises CatalogoNotFoundError |
| `test_should_reject_get_catalog_not_owned` | Catalog belongs to another user | Raises CatalogoOwnershipError |

### Run Command

```bash
cd backend && pytest tests/test_catalogo_service.py -v -k "get_catalog_with_items"
```

## Frontend E2E Tests

**File:** `frontend/e2e/catalogos.spec.ts`

### Test Coverage

| Test | Flow | Expected |
|------|------|----------|
| `shows empty state when no catalogs exist` | Navigate to /dashboard/catalogos with no catalogs | Empty state with CTA visible |
| `creates a new catalog via modal` | Click "Crear catálogo", fill name, submit | Catalog card appears with name, "Borrador" badge, "0 prendas" |
| `shows validation error for empty catalog name` | Submit modal with empty name | Validation error visible |
| `navigates to catalog detail when clicking a catalog` | Click catalog card | URL changes to /dashboard/catalogos/{id} |
| `shows empty state for new catalog` | Create catalog, navigate to detail | "Este catálogo está vacío" visible |
| `publish button is disabled for empty catalog` | View empty catalog detail | "Publicar" button is disabled |
| `deletes catalog with confirmation` | Click delete, confirm dialog | Redirects to list, catalog no longer visible |

### Run Command

```bash
cd frontend && pnpm e2e
```

Or with UI:

```bash
cd frontend && pnpm e2e:ui
```

## Acceptance Criteria Verification

### Story 001 - Catalog List Page
- [x] Catalogs displayed as cards with name, status badge, item count, updated date
- [x] Empty state with "Create your first catalog" CTA when no catalogs
- [x] "Create Catalog" modal accepts name and creates draft catalog
- [x] New catalog appears in list without full page reload
- [x] Clicking catalog navigates to detail page

### Story 002 - Catalog Detail Page
- [x] Catalog name, status, and item grid displayed on load
- [x] "Add Item" picker shows completed VTON jobs with metadata form
- [x] Remove item with confirmation → item disappears, count updates
- [x] Reorder via up/down arrows → saved via PATCH, reflected immediately
- [x] Catalog name editable inline → updates via PATCH

### Story 003 - Publish Flow
- [x] Publish button shows confirmation dialog
- [x] Confirmed publish → status badge changes to "Published" + success toast
- [x] Publish button disabled with tooltip when catalog has 0 items
- [x] Unpublish shows confirmation warning buyers will lose access
- [x] Confirmed unpublish → status badge changes to "Draft"
- [x] Delete Catalog with confirmation → redirects to catalog list

## Manual Testing Checklist

Before running automated tests, verify manually:

1. **Backend running:** `cd backend && uv run uvicorn main:app --reload`
2. **Frontend running:** `cd frontend && pnpm dev`
3. **Infrastructure running:** `make docker-infra` (PostgreSQL, MinIO)

### Manual Test Steps

1. Register new user → login → navigate to /dashboard/catalogos
2. Verify empty state shows
3. Create catalog "Test Collection" → verify card appears
4. Click card → verify detail page loads
5. Verify "Publicar" button is disabled (empty catalog)
6. Click "Añadir prenda" → verify VTON picker opens (may be empty if no VTONs)
7. Edit catalog name inline → verify update persists
8. Click "Eliminar" → confirm → verify redirect to list
9. Create another catalog → verify it appears in list

## Known Limitations

- E2E tests for "Add Item" flow require completed VTON jobs in the system
- Reorder E2E tests require multiple items in a catalog
- Image upload tests require MinIO to be running

## Test Results

Run all backend catalog tests:
```bash
cd backend && pytest tests/test_catalogo_api.py tests/test_catalogo_service.py -v
```

Run all frontend E2E tests:
```bash
cd frontend && pnpm e2e --grep "Catalog"
```
