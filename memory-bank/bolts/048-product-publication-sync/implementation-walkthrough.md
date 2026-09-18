---
stage: implement
bolt: 048-product-publication-sync
created: 2026-09-18T16:28:28Z
---

## Implementation Walkthrough: 003-product-image-integration

### Summary

Staff can now select or discard completed generation results without publishing automatically. Selected candidates are delivered independently to the Virtual Closet gallery and to BFashion, with durable per-destination status, idempotent retries, and preview URLs minted from storage keys rather than reused transfer links.

### Structure Overview

Publication is a new backend domain on the usual layers: models and migration, repositories, services (decision vs delivery vs outbound adapter), then cookie and S2S routers. Generation completion is unchanged; only an explicit decision creates deliveries. Virtual Closet writes are committed before the BFashion HTTP call so a partial failure can be retried without duplicating gallery rows or regenerating images.

### Completed Work

- [x] `backend/models/publication.py` - Selection, per-destination delivery, and append-only Virtual Closet gallery entities
- [x] `backend/models/__init__.py` - Exports the new publication models
- [x] `backend/alembic/versions/f6a7b8c9d0e1_create_publication_tables.py` - Schema for selections, deliveries, and gallery images
- [x] `backend/repositories/publication_selection_repo.py` - Lookup and persistence of staff decisions
- [x] `backend/repositories/sync_delivery_repo.py` - Lookup and persistence of destination status
- [x] `backend/repositories/product_image_repo.py` - Append-only gallery inserts and next position
- [x] `backend/services/publication_service.py` - Candidate validation, select/discard, preview helper
- [x] `backend/services/sync_delivery_service.py` - Commit-before-outbound sync and isolated retry
- [x] `backend/services/bfashion_sync_adapter.py` - Mockable outbound ingest client with fresh transfer URLs
- [x] `backend/services/product_link_service.py` - Fail-closed link resolution by id for cookie staff
- [x] `backend/services/integration_service.py` - Public link resolve and staff authorize for S2S publication
- [x] `backend/api/schemas/publication.py` - Cookie/S2S publication request and status contracts
- [x] `backend/api/schemas/integration.py` - S2S publication command and job preview field
- [x] `backend/api/schemas/image_generation.py` - Optional preview URL on job detail
- [x] `backend/api/routers/publication.py` - Cookie staff select, discard, retry, status, and candidates
- [x] `backend/api/routers/integration.py` - S2S publication, retry, status, candidates, and job preview
- [x] `backend/api/routers/image_generation.py` - Preview URL on staff job detail
- [x] `backend/main.py` - Registers publication routers
- [x] `backend/core/config.py` - BFashion outbound base URL and service credentials
- [x] `backend/.env.example` - Documents BFashion outbound settings
- [x] `backend/tests/conftest.py` - Creates publication tables in the test schema
- [x] `backend/tests/publication_helpers.py` - Shared fake BFashion adapter and preview URL stub
- [x] `backend/tests/test_publication_selection.py` - Selection, discard, re-selection, and fail-closed cases
- [x] `backend/tests/test_sync_delivery.py` - Dual delivery, partial failure, retry idempotency, S2S
- [x] `backend/tests/test_image_generation_api.py` - Allows preview URL on job detail payloads

### Key Decisions

- **Selection is a separate aggregate from generation and composition**: completing a job never publishes; a new valid composition version is a new candidate (ADR-055 / ADR-056).
- **Commit Virtual Closet delivery before calling BFashion**: matches the existing commit-before-outbound pattern so a failed destination stays retryable without duplicating gallery rows.
- **Gallery is append-only and keyed by selection**: retries reuse the same selection id as the idempotency key for both destinations.
- **Preview versus transfer**: short-lived URLs are minted from the durable MinIO key at read/send time; expired URLs are recovered without regenerating.
- **BFashion adapter is a protocol**: tests inject a fake client; the ecommerce ingest endpoint remains out of this repo.

### Deviations from Plan

- Retry also drains `pending` deliveries (not only `failed` + retryable) so a crash after commit and before the BFashion call can be recovered from the retry endpoint.
- An S2S candidates listing was added so BFashion can preview the same candidate set as Virtual Closet.
- Cookie GET/retry require the product link as a query parameter so status stays scoped to the explicit link.
- Tests were written in this stage so Stage 3 can execute them; they were not run here because local Postgres rejected the default test credentials and Docker was unavailable.

### Dependencies Added

None. The outbound adapter uses existing httpx and storage helpers. BFashion settings are optional environment values.

### Developer Notes

- Apply Alembic revision `f6a7b8c9d0e1` before using the new routes.
- Empty `BFASHION_BASE_URL` makes live outbound ingest fail as retryable; inject or configure the adapter in each environment.
- Tests expect `TEST_DATABASE_URL` against a reachable Postgres (default `postgres:postgres@localhost:5432/virtual_closet_test`).
