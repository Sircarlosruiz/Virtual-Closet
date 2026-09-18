---
stage: implement
bolt: 047-product-generation-bridge
created: 2026-09-18T15:18:43Z
---

## Implementation Walkthrough: 003-product-image-integration

### Summary

Added an authenticated server-to-server bridge that lets an external system (BFashion) request image generation for an explicitly linked product. Ownership, tenant scope, and the acting staff member are all re-validated inside Virtual Closet before the existing generation pipeline is invoked; the bridge therefore never becomes a second generation authority.

### Structure Overview

A new `integration` domain follows the standard backend layering: models (`ServiceClient`, `ProductLink`) → repositories → services (link resolution, orchestration) → API schema → router. Authentication is a new `core/dependencies.py` dependency, and the router reuses `ImageGenerationService`, the Celery task, and the existing idempotency mechanism.

### Completed Work

- [x] `backend/models/service_client.py` - DB-backed service identity; stores only a bcrypt secret hash, scoped to one tenant.
- [x] `backend/models/product_link.py` - explicit external product/wholesaler ↔ Virtual Closet owner mapping with tenant scope and unique external product constraint.
- [x] `backend/models/__init__.py` - exports the two new models.
- [x] `backend/repositories/service_client_repo.py` - lookup by id/name, audit `last_used_at`.
- [x] `backend/repositories/product_link_repo.py` - resolve link by external product, list by tenant.
- [x] `backend/services/product_link_service.py` - fail-closed link validation (missing/inactive/tenant/wholesaler mismatch).
- [x] `backend/services/integration_service.py` - orchestration: resolve link, authorize asserted staff actor, delegate job creation; owner-scoped status lookup.
- [x] `backend/core/dependencies.py` - `get_service_client` dependency verifying service headers and active tenant.
- [x] `backend/api/schemas/integration.py` - bridge request/response contracts reusing `ImageGenerationRequest`.
- [x] `backend/api/routers/integration.py` - `POST /products/generation-jobs` and `GET /products/{external_product_id}/generation-jobs/{job_id}`.
- [x] `backend/main.py` - registers the integration router.
- [x] `backend/alembic/versions/e5f6a7b8c9d0_create_integration_tables.py` - creates `service_clients` and `product_links`.
- [x] `backend/scripts/provision_service_client.py` - one-time service credential provisioning.
- [x] `backend/scripts/link_product.py` - explicit product link provisioning.
- [x] `backend/tests/test_integration_bridge.py` - accepted, rejected, isolation, and idempotency contract tests.
- [x] `backend/tests/conftest.py` - ensures the new tables are created in the test schema.

### Key Decisions

- **DB-backed service identity over a static env key**: enables rotation, per-tenant scope, activation, and audit. Requests present `X-Service-Id` and `X-Service-Secret`; the secret is verified against a bcrypt hash with the existing security primitives.
- **Ownership read only from `ProductLink`**: the external product identifier is used to find the link, never to infer the owner. This is the core fail-closed guarantee.
- **Asserted staff is re-validated**: BFashion asserts `staff_id`, but Virtual Closet checks the actor exists, has a staff role, and belongs to the link's tenant.
- **System derived from the authenticated service client**: the external system key is not request-controlled, preventing spoofing across systems.
- **Status scoped by link**: the status route is nested under the external product so it resolves the link and uses the owner-scoped repository lookup.
- **Reuse of the existing pipeline**: job creation, idempotency, commit-before-enqueue and worker secret boundary are unchanged, so BFashion cannot reach OpenAI.

### Deviations from Plan

- The status endpoint was implemented as a nested product route (`/products/{external_product_id}/generation-jobs/{job_id}`) rather than a flat job route, to make the explicit link part of the status contract and enforce owner scoping.
- Service client and product link provisioning scripts were added for operability; they were not itemized in the plan.
- Result/artifact download remains deferred to bolt 048 as planned.

### Dependencies Added

None. The implementation reuses existing bcrypt/FastAPI/SQLAlchemy dependencies.

### Developer Notes

- Tests require `TEST_DATABASE_URL` pointing at a PostgreSQL instance; the default is `postgresql+asyncpg://postgres:postgres@localhost:5432/virtual_closet_test`.
- A service client must be provisioned (or inserted) before the bridge can be called; `system` on the client must match `ProductLink.system`.
