---
stage: plan
bolt: 047-product-generation-bridge
created: 2026-09-18T15:17:41Z
---

## Implementation Plan: 003-product-image-integration

### Objective

Define and implement the authenticated server-to-server (S2S) command/status bridge that lets BFashion staff initiate an image-generation job on a linked product while Virtual Closet remains the single generation authority. Ownership is resolved exclusively from an explicit, persisted product/wholesaler link; Virtual Closet never infers ownership from SKU and never exposes a direct OpenAI/provider path to the caller.

### Scope

**In scope**
- Service-to-service authentication for the BFashion integration caller.
- Explicit `ProductLink` persistence (external system ↔ external product/wholesaler ↔ Virtual Closet mayorista/tenant/entity).
- S2S generation-command endpoint that validates link + staff authorization and creates a Virtual Closet `GenerationJob` through the existing pipeline.
- S2S job-status endpoint scoped to the calling service/link.
- Fail-closed behavior for unknown, mismatched, inactive, or unauthorized links.
- Contract tests for accepted and rejected requests.

**Out of scope (bolt 048 / later)**
- Manual selection and publication of results to product galleries.
- Sync delivery/idempotent `ProductImage` writes to BFashion.
- Artifact/result download URLs (selection/publication concern).
- The BFashion-side client implementation (separate repo, `~/dev/bfashion/ecommerce`); this bolt fixes the contract it consumes.

### Deliverables

1. **Data model & migration**
   - `backend/models/product_link.py` — explicit link entity.
   - `backend/models/service_client.py` — S2S service identity (hashed secret, tenant/mayorista scope, active flag, rotation/audit fields).
   - Alembic migration following the repo's manual 12-hex sequential revision convention (down_revision = `d4e5f6a7b8c9`).
2. **Repositories**
   - `backend/repositories/product_link_repo.py`
   - `backend/repositories/service_client_repo.py`
3. **Services**
   - `backend/services/product_link_service.py` — link resolution + fail-closed validation.
   - `backend/services/integration_service.py` — S2S orchestration: authenticate → resolve link → authorize staff → delegate to `ImageGenerationService`.
4. **Auth dependency**
   - `get_service_client` in `backend/core/dependencies.py` (constant-time credential verification, active/scope checks).
5. **API surface**
   - `backend/api/schemas/integration.py` (Pydantic DTOs, v1 contract).
   - `backend/api/routers/integration.py` under `/api/integration/v1/`, registered in `backend/main.py`.
6. **Tests**
   - `backend/tests/test_integration_bridge.py` — contract tests (accepted + rejected).

### Dependencies

- **044-generation-reliability** (complete): idempotency fingerprinting, DB-backed `Idempotency-Key` uniqueness, retry/invocation history.
- **046-template-composition** (complete): snapshots/versions referenced by generated jobs.
- **Existing generation pipeline** (`ImageGenerationService.create_job`, `tasks.generate_image`, ADR-047 secret boundary, ADR-048 commit-before-enqueue) — reused unchanged; the bridge adds no second provider path.
- **Existing auth primitives** (`backend/core/security.py`, `backend/core/dependencies.py`) — extended, not replaced.
- **External**: BFashion Django REST (`~/dev/bfashion/ecommerce`, `Product`/`ProductImage` in `backend/catalog/models.py`) — consumes this contract; cross-repo, must be agreed.

### Technical Approach

- **Service identity**: add a DB-backed `ServiceClient` (secret stored hashed) verified by a new dependency using constant-time comparison. Do not add a shared static env key; DB-backed identity supports rotation, per-tenant scoping, and audit.
- **Fail-closed link resolution**: the request carries external identifiers (`system`, `external_product_id`, `external_wholesaler_id`) but the `owner_id`/tenant used for job creation is read from the persisted `ProductLink`, never from the request. Unknown/inactive/tenant-mismatched links → 403/404 with structured domain error and **no job created**.
- **Staff authorization**: caller asserts the staff actor; Virtual Closet validates that actor belongs to the link's mayorista/tenant with a staff role before delegating.
- **Job creation**: reuse `ImageGenerationService.create_job(mayorista_id, request, idempotency_key)` and propagate `Idempotency-Key`; replay returns the existing job, conflicting payload → 409.
- **Status**: owner-scoped `get_owned` lookup constrained to the link's mayorista; expose the existing status/attempt fields. Artifact retrieval is deferred to bolt 048.
- **Isolation**: `tenant_id`/`mayorista_id` on `ProductLink` and `ServiceClient`; cross-tenant access is rejected.

### Acceptance Criteria

- [ ] A valid authenticated S2S request with an explicit active product/wholesaler link creates a Virtual Closet generation job for the link's mayorista.
- [ ] Unknown, mismatched, inactive, cross-tenant, or unauthorized-staff requests fail closed (no job, no publication) with a structured error.
- [ ] A BFashion-originated job's status is retrievable only by the originating service/link scope.
- [ ] Idempotent replay returns the same job; changed payload with the same key returns 409.
- [ ] BFashion cannot invoke OpenAI directly: no provider credential or second generation path is exposed.
- [ ] Contract tests cover accepted and rejected request cases.
