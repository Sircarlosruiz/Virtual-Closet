---
unit: 002-template-composition-service
bolt: 046-template-composition
stage: design
status: complete
updated: 2026-09-17T22:31:28Z
---

# Technical Design: Template and Composition Service (Deterministic SKU Composition)

## Architecture Pattern

Same domain-driven layered pattern used by bolt 043 (`generation_job`) and bolt
045 (`image_template` / `composition_snapshot`): Model → Repository → Service →
Schema → Router. Composition is a **pure rendering pipeline**, not a provider
integration — it runs synchronously in the request path (deterministic, local,
sub-second for V1 image sizes) and never touches a queue or an inference
adapter. The append-only version store is the only source of truth for
composed outputs.

**Key decision**: V1 composes synchronously rather than via Celery. Composition
is a local byte operation with no network dependency; a synchronous call gives
the staff immediate fit-validation feedback (FR-4) and avoids a second job
state machine. The render function is isolated behind `SkuCompositionService`
so it can be moved to Celery later without changing the API or the model.
*(ADR-worthy — see Stage 3 candidate list.)*

## Layer Structure

```text
┌───────────────────────────────────────────────────────────┐
│ Presentation   api/routers/composition.py                  │  Staff-only compose/configure
│                                                            │  + read endpoints
├───────────────────────────────────────────────────────────┤
│ Application    services/sku_composition_service.py         │  Compose/recompose, versioning,
│                                                            │  idempotency, fit gating
│                services/overlay_fit_validator.py           │  Pure text-fit measurement
│                services/sku_text_normalizer.py             │  SKU normalization rules
├───────────────────────────────────────────────────────────┤
│ Domain         models/product_overlay.py                   │  ProductOverlay (root)
│                models/composition_version.py               │  CompositionVersion (child)
│                domain/composition_spec.py                  │  SkuOverlaySpec, SkuText,
│                                                            │  OverlayPlacement, OverlayStyle,
│                                                            │  OverlayFitResult, CompositionStatus
├───────────────────────────────────────────────────────────┤
│ Infrastructure repositories/product_overlay_repo.py        │  Overlay CRUD + row lock
│                repositories/composition_version_repo.py    │  Append-only persistence
│                infrastructure/rendering/sku_renderer.py    │  Pillow render + checksum
│                infrastructure/rendering/font_registry.py   │  Pinned font + font_version
└───────────────────────────────────────────────────────────┘
```

## Components

| Layer | Component | Responsibility |
|---|---|---|
| Model | `models/product_overlay.py` | SQLAlchemy: `ProductOverlay` |
| Model | `models/composition_version.py` | SQLAlchemy: `CompositionVersion` |
| Domain | `domain/composition_spec.py` | Value objects, normalization, spec hash |
| Repository | `repositories/product_overlay_repo.py` | `save`, `get_by_id`, `get_by_generation_job_id`, `lock_for_update` |
| Repository | `repositories/composition_version_repo.py` | `append`, `get_by_id`, `get_latest_by_overlay`, `list_by_overlay`, `find_by_spec_hash` |
| Service | `services/sku_text_normalizer.py` | `normalize(raw) → SkuText` |
| Service | `services/overlay_fit_validator.py` | `validate(spec, dims, metrics) → OverlayFitResult` (pure) |
| Service | `services/sku_composition_service.py` | Orchestrates normalize → fit → render → append; enforces idempotency |
| Infrastructure | `infrastructure/rendering/font_registry.py` | Loads a pinned, bundled font file; exposes `font_version` |
| Infrastructure | `infrastructure/rendering/sku_renderer.py` | Renders base + overlay deterministically, strips metadata, computes SHA-256 |
| Schema | `api/schemas/composition.py` | Pydantic request/response |
| Router | `api/routers/composition.py` | Staff-only composition endpoints |

## API

All routes require `get_current_mayorista` plus a staff-role check, reusing the
pattern from bolt 043/045 (non-staff → HTTP 403). The parent `GenerationJob` is
resolved first and ownership is checked per ADR-013 (unowned → HTTP 404).

### `POST /api/generation-jobs/{job_id}/composition`

Configure the SKU overlay and compose (idempotent). This is the primary
entrypoint; a spec change is an explicit recompose.

- Body:
  - `sku` (string, required unless derivable from the linked product)
  - `placement` (object: `anchor`, `offset_x`, `offset_y`, `max_width?`, `max_height?`)
  - `style` (object: `font_family`, `font_size`, `color`, `opacity?`, `stroke?`, `background?`)
- Behaviour:
  - Normalizes `sku`; rejects/normalizes unsupported control characters.
  - Rejects incomplete specs **before** rendering (`400` / `422`).
  - Computes `spec_hash = sha256(normalized_sku, placement, style, base_image_key, font_version)`.
  - If a version with the same `spec_hash` exists → returns it (`200`), no new version.
  - Otherwise runs fit validation, renders, and appends a version.
- Responses:
  - `201` with the new `CompositionVersion` (`status: valid`).
  - `200` with the existing version on idempotent re-request.
  - `422` structured error when the complete text does not fit; a `blocked`
    version is recorded (`rendered_key: null`) and its `id` is returned in the
    error context so the UI can surface the rejection.
  - `409` if the parent job is not yet in a composable state (no base image).

Response schema (valid version):

```json
{
  "id": "uuid",
  "overlay_id": "uuid",
  "generation_job_id": "uuid",
  "version": 2,
  "status": "valid",
  "sku": "REF: CAM-001",
  "placement": { "anchor": "bottom-right", "offset_x": 24, "offset_y": 24 },
  "style": { "font_family": "DejaVuSans-Bold", "font_size": 48, "color": "#FFFFFF" },
  "rendered_key": "generated/046/…/v2.png",
  "rendered_checksum": "sha256:…",
  "created_at": "2026-09-17T22:31:28Z"
}
```

### `GET /api/generation-jobs/{job_id}/composition`

- Returns the overlay plus the latest `CompositionVersion` (including a
  `blocked` latest version, if the last attempt failed).
- `404` if no overlay exists for the job (nothing composed yet) or the job is
  unowned.

### `GET /api/generation-jobs/{job_id}/composition/versions`

- Returns all versions for the job's overlay, newest first, ownership-scoped.
- Used by the review UI (bolt 049) and by publication integration (bolt 048) to
  require a **new explicit selection** after a SKU change.

### `GET /api/composition-versions/{version_id}`

- Returns one version by id, ownership-scoped (404 otherwise). Used by the
  integration layer to resolve a publication candidate's exact version.

**Not exposed**: rendering internals, font-file paths, raw storage keys as
pre-signed URLs. `rendered_key` is an internal identifier.

## Data Persistence

### `product_overlays`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `generation_job_id` | UUID, FK `generation_jobs.id`, **unique** | Exactly one overlay per generation result |
| `composition_snapshot_id` | UUID, FK `composition_snapshots.id`, nullable | Seeds defaults (bolt 045); identity only |
| `base_image_key` | text | Durable key copied from the job result; never written here |
| `created_by` | UUID, FK `mayorista.id` | Staff account |
| `created_at`, `updated_at` | timestamptz | |

### `composition_versions`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `overlay_id` | UUID, FK `product_overlays.id`, not null | |
| `version` | integer, not null | Monotonic per overlay, starts at 1 |
| `sku_normalized` | text, not null | The exact normalized value that was rendered |
| `placement` | JSONB, not null | Frozen spec |
| `style` | JSONB, not null | Frozen spec |
| `spec_hash` | text, not null | sha256 over spec + base key + font version |
| `font_version` | text, not null | Pinned font/metrics identity |
| `status` | enum (`valid`, `blocked`), not null | |
| `rendered_key` | text, nullable | Durable key; `null` when `blocked` |
| `rendered_checksum` | text, nullable | sha256 of rendered bytes |
| `fit_result` | JSONB, not null | `fits`, rendered/available dimensions, `reason` |
| `created_at` | timestamptz | |

Constraints:

- `UNIQUE (overlay_id, version)` — append-only version sequence.
- `UNIQUE (overlay_id, spec_hash)` — the database enforces determinism/idempotency: an identical spec can never produce a duplicate version, even under concurrent requests.

Single Alembic migration adds both tables; no existing tables are modified; no backfill required.

## Composition Pipeline (Determinism Contract)

```text
normalize(sku) ─► validate_complete(spec)
                      │
                      ├─ incomplete ─► 400/422 (no render)
                      ▼
              fit_validate(spec, image_dims, font_metrics)
                      │
                      ├─ does not fit ─► record blocked version ─► 422
                      ▼
              render(base_bytes, spec, font)  ── Pillow, pinned
                      │                          strip metadata, fixed encoder
                      ▼
              checksum = sha256(rendered_bytes)
                      ▼
              append CompositionVersion(valid)
```

Determinism rules:

1. Font is a **bundled, pinned file**; `font_version` is derived from the font
   identity + renderer version and is stored per version.
2. Output encoder parameters are fixed; all metadata/EXIF is stripped.
3. `spec_hash` includes `base_image_key` and `font_version`, so a font or
   renderer upgrade yields a **new** version rather than silently changing an
   existing version's bytes.
4. The renderer is a pure function of `(base_bytes, spec, font_version)`; no
   clocks, randomness, or provider state participate in pixel output.

## Security Design

- **Staff-only**: all composition routes use the 043/045 dependency chain — `get_current_mayorista` + staff-role check → 403 for non-staff.
- **Ownership**: parent `GenerationJob` is resolved first; jobs owned by another account return 404, not 403 (ADR-013 consistency).
- **No secret material**: no provider credentials exist in this bounded context at all (composition makes no provider call). `sku_normalized` and spec fields are non-secret.
- **Storage references**: only durable object-storage keys are persisted. Pre-signed/temporary URLs are never stored or logged (mirrors bolt 045 and coding-standards logging rules).
- **Input hardening**: SKU text normalization rejects unsupported control characters, preventing control-glyph rendering or log/display injection.

## NFR Implementation

- **Exactness (FR-4 / NFR-3)**: fit validation measures the **complete** text at the configured font/size/color before rendering; the same computed dimensions drive the final placement, so "validated" and "rendered" cannot diverge.
- **No re-generation**: composition is local; no provider client is imported into this module graph (enforced by an import-boundary test in Stage 5).
- **Immutability**: `CompositionVersionRepository.append` is the only write; no `update`/`delete` methods exist.
- **Version-on-change**: any change to `sku_normalized`, placement, or style changes `spec_hash` → new version; prior versions remain readable and the published selection (bolt 048) is never silently replaced.
- **Concurrency**: `ProductOverlayRepository.lock_for_update(overlay_id)` serializes version computation (`next_version = max(version) + 1`) inside the same transaction, mirroring bolt 045's row-lock approach for template version bumps. The `(overlay_id, spec_hash)` unique index is the race-safe backstop.
- **Performance**: render runs in-request; target < 500 ms for a 1024×1024 base at typical SKU sizes. If larger canvases or batch recomposition are required, the pipeline is already isolated behind the service and can be queued without API changes.
- **Failure transparency**: fit failure returns a structured domain error with dimensions, and records a `blocked` version, so the staff sees why publication is blocked.

### Domain Error Mapping

| Domain error | HTTP | Structured `detail.code` |
|---|---|---|
| `IncompleteOverlaySpecError` | 400 | `OVERLAY_SPEC_INCOMPLETE` |
| `OverlayDoesNotFitError` | 422 | `OVERLAY_DOES_NOT_FIT` |
| `BaseImageUnavailableError` | 409 | `BASE_IMAGE_UNAVAILABLE` |
| `CompositionNotFoundError` | 404 | `COMPOSITION_NOT_FOUND` |

Errors use the structured `{"detail": {"code", "message", "context"}}` form from `coding-standards.md`.

## Integrations

- **Bolt 043/044 (`generation_jobs`)**: read-only — the job's result key becomes `base_image_key`; a job without a stored result is not composable (`409`).
- **Bolt 045 (`composition_snapshots`)**: read-only — `EffectiveConfiguration` seeds SKU defaults; the snapshot is referenced by id. No schema change on 045's side.
- **Bolt 048 (`product-publication-sync`)**: consumes `GET /api/composition-versions/{id}` and the "new version requires new selection" rule; publication status is owned there, not here.
- **Bolt 049 (`openai-generation-ui`)**: uses the compose/read endpoints and surfaces `blocked` errors from the structured error context.

## Compatibility

New tables and new endpoints only. No existing table, endpoint, or contract is
modified. The renderer adds Pillow + a bundled font as backend dependencies;
dependency availability must be confirmed during the Implement stage (this
stage is design-only and did not inspect source).

## Open Items for Implementation

1. Confirm the image library already available in the backend (Pillow assumed) and the font file/license to bundle.
2. Confirm the structured-error helper used by existing routers so the new domain errors map consistently.
3. Confirm staff-role dependency name used by bolt 043/045 routes.
