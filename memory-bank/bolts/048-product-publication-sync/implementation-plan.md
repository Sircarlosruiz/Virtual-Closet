---
stage: plan
bolt: 048-product-publication-sync
created: 2026-09-18T15:40:11Z
---

## Implementation Plan: 003-product-image-integration

### Objective

Keep generation completion separate from product publication. Staff explicitly preview, select, or discard completed results; only selected candidates are delivered to Virtual Closet and BFashion product galleries. Delivery is idempotent per destination, recovers partial failures without regenerating, and never silently replaces existing gallery images.

### Scope

**In scope**
- Staff publication decisions (`selected` / `discarded`) on a specific publication candidate.
- Candidate identity: completed `GenerationJob` result plus an optional `valid` `CompositionVersion` (ADR-055 / ADR-056).
- Preview URLs derived from durable MinIO keys (never the source of truth for transfer).
- Append-only Virtual Closet product-gallery records (image + frozen configuration).
- Outbound BFashion sync adapter that upserts `ProductImage` + configuration by idempotency key.
- Per-destination `SyncDelivery` status (`pending` / `synced` / `failed`) with isolated retry.
- Cookie-authenticated staff API (Virtual Closet) and S2S API (BFashion staff via bolt 047 identity).

**Out of scope (bolt 049 / later)**
- Staff-facing review/publication UI in Next.js or BFashion admin.
- Automatic publishing on job completion.
- Catalog `published` status, prices, or inventory.
- OpenAI/provider re-invocation on publication failure.
- Implementing BFashion's ingest endpoint in `~/dev/bfashion/ecommerce` (separate repo). This bolt owns the outbound contract and a mockable adapter.

### Deliverables

1. **Data model & migration**
   - `backend/models/publication.py` — `PublicationSelection`, `SyncDelivery`, `ProductImage` (Virtual Closet gallery).
   - Alembic revision `f6a7b8c9d0e1` following the 12-hex sequential convention (`down_revision = e5f6a7b8c9d0`).
2. **Repositories**
   - `backend/repositories/publication_selection_repo.py`
   - `backend/repositories/sync_delivery_repo.py`
   - `backend/repositories/product_image_repo.py`
3. **Services**
   - `backend/services/publication_service.py` — candidate validation, select/discard, re-selection on new composition version.
   - `backend/services/sync_delivery_service.py` — commit-before-outbound, per-destination isolation, retry.
   - `backend/services/bfashion_sync_adapter.py` — HTTP client behind a protocol; no OpenAI path.
4. **API surface**
   - Cookie-auth staff routes on `/api/publications/` (select, discard, retry, status, preview).
   - S2S routes on `/api/integration/v1/products/{external_product_id}/publications` extending the bolt 047 router.
   - Schemas in `backend/api/schemas/publication.py`; S2S DTOs added to `backend/api/schemas/integration.py`.
5. **Job status enrichment**
   - Preview `result_key` / composed `rendered_key` as short-lived presigned URLs on both cookie and S2S job-status responses (artifact retrieval deferred from bolt 047).
6. **Tests**
   - `backend/tests/test_publication_selection.py`
   - `backend/tests/test_sync_delivery.py`

### Dependencies

- **047-product-generation-bridge** (complete): `ProductLink`, `ServiceClient`, fail-closed link resolution, S2S staff assertion, existing generation pipeline.
- **046-template-composition** (complete): append-only `CompositionVersion`; only `status = valid` is eligible; a new version requires a new explicit selection (ADR-055, ADR-056).
- **045-template-lifecycle** (complete): immutable `CompositionSnapshot` copied onto the published gallery record (ADR-052).
- **044-generation-reliability** (complete): completed jobs persist `result_key`; publication recovers from that object, never from OpenAI (NFR-2).
- **Existing MinIO client** (`core/minio_client.py`) — durable keys + presigned preview URLs.
- **Existing staff auth** (`get_current_mayorista` + staff roles) and S2S `get_service_client`.
- **External**: BFashion Django `Product` / `ProductImage` (`backend/catalog/models.py` in the ecommerce repo). The ingest contract is defined here; the ecommerce implementation is out of this repo.

### Technical Approach

#### Publication candidate

A candidate is addressable and immutable:

- `generation_job_id` (required): job must be `completed` with a durable `result_key`.
- `composition_version_id` (optional): when present, must belong to that job, `status = valid`, and have `rendered_key`. `blocked` versions cannot be selected (ADR-056).
- When no composition exists, the candidate is the raw generation result.
- Changing SKU/style appends a new `CompositionVersion`. The previous selection still points at the old version and **does not** publish the new one. Publishing the new version requires a new explicit selection (ADR-055). Existing gallery rows are never updated in place.

Discarded results remain historical (`decision = discarded`) and cannot be delivered. A later explicit `selected` decision on the same candidate is allowed (staff changed their mind); it is still an explicit action, never automatic.

#### Aggregates (owned by this bolt)

`PublicationSelection`

- One row per `(product_link_id, generation_job_id, composition_version_id)` unique (NULL composition treated as a distinct candidate via a sentinel or `NULLS NOT DISTINCT`).
- Fields: `decision` (`selected` | `discarded`), `selected_by`, `tenant_id`, `mayorista_id`, timestamps.
- Selection is independent of job status after completion; completing a job never creates a selection.

`SyncDelivery`

- One row per `(publication_selection_id, destination)` unique.
- Destinations: `virtual_closet` | `bfashion`.
- `status`: `pending` | `synced` | `failed`.
- `retryable` boolean, `last_error`, `attempt_count`, `external_ref` (BFashion `ProductImage` id/key), `durable_object_key`.
- A destination is `synced` only after **both** image and configuration copy are confirmed (NFR-5).
- Failure on one destination never mutates the other.

`ProductImage` (Virtual Closet gallery)

- Append-only row linked to `product_link_id` (and `prenda_id` when the link has one).
- Stores `minio_key`, `publication_selection_id` (unique so retries cannot insert a second gallery row), copied `configuration` JSONB from the composition snapshot + version identity, `position` (max+1, never reordering existing rows).
- Not `CatalogoItem`: catalogs carry price/SKU/publish-guard concerns outside this unit.

#### Commit-before-outbound

Mirror ADR-048:

1. Validate candidate + staff + product link (fail closed, same rules as bolt 047).
2. Persist selection and `pending` deliveries (and the VC gallery insert when that destination can be completed locally).
3. Commit.
4. Attempt BFashion outbound from durable storage (object bytes or a freshly minted transfer URL generated from the key, never a previously issued preview URL).
5. Update only the BFashion `SyncDelivery` row.

Retry of a failed destination reuses the same `SyncDelivery` and the same `publication_selection_id` as the idempotency key. It must not create another `ProductImage`, another generation job, or another OpenAI call.

#### Transfer vs preview

- Preview: short-lived MinIO presigned GET on `result_key` / `rendered_key`.
- Transfer: read the object by durable key. If BFashion needs an HTTP URL, mint a dedicated transfer URL at send time or stream bytes in the ingest body. If a transfer URL expires, refresh from the key without regenerating (story 003 edge case).

#### BFashion adapter contract (outbound)

Configurable `BFASHION_BASE_URL` plus service credentials (settings; not a second OpenAI path).

```text
PUT {BFASHION_BASE_URL}/internal/v1/products/{external_product_id}/images
Idempotency-Key: {publication_selection_id}
```

Body includes durable storage key or image bytes, content type, copied configuration snapshot, composition version id, generation job id, and staff actor. HTTP 200/201 with the same `Idempotency-Key` returns the existing `ProductImage` (no duplicate). Transient errors → `failed` + `retryable=true`; 4xx (except 409 conflict-as-success) → `failed` + `retryable=false`.

The adapter is a protocol so tests never hit the ecommerce repo.

#### API (staff cookie)

- `POST /api/publications` — select or discard a candidate for a product link.
- `POST /api/publications/{id}/retry` — retry failed retryable destinations only.
- `GET /api/publications/{id}` — selection + per-destination status.
- `GET /api/generation-jobs/{job_id}/publication-candidates` — completed result + valid versions with preview URLs and current decision.

Staff role required. Owner is the product link's `mayorista_id` / tenant, not inferred from SKU.

#### API (S2S, BFashion)

- `POST /api/integration/v1/products/{external_product_id}/publications`
- `POST /api/integration/v1/products/{external_product_id}/publications/{id}/retry`
- `GET /api/integration/v1/products/{external_product_id}/publications/{id}`

Same `get_service_client` + `ProductLink` fail-closed resolution as bolt 047. Asserted `staff_id` re-validated. Unknown/mismatched links create neither selection nor delivery.

#### Isolation and fail-closed

- Cross-tenant staff or inactive/mismatched `ProductLink` → 403/404, no writes.
- Non-completed jobs, missing `result_key`, or `blocked` composition versions → 409/422, no selection.
- Discarded candidate → 409 on delivery/retry until an explicit select.

### Acceptance Criteria

- [ ] Completed results can be selected or discarded; only `selected` candidates become deliveries.
- [ ] Publishing appends a gallery image; existing Virtual Closet and BFashion images are not replaced.
- [ ] A new `valid` composition version is not published until a new explicit selection of that version.
- [ ] Successful delivery stores image + configuration snapshot on both destinations; each destination reports `pending` / `synced` / `failed` independently.
- [ ] Duplicate delivery or retry does not create a second `ProductImage`, a second generation job, or an OpenAI call.
- [ ] A failed destination stays retryable without marking the other destination failed or synced incorrectly.
- [ ] Expired preview/transfer URLs are recovered from the durable object key without regenerating.
- [ ] Unknown, mismatched, inactive, or unauthorized product links fail closed (no publication).
- [ ] Discarded results remain queryable historically and cannot be delivered while discarded.
