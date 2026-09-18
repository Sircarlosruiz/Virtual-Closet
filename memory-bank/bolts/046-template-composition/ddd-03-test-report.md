---
stage: test
bolt: 046-template-composition
created: 2026-09-17T23:15:28Z
status: complete
---

# Test Report: Template and Composition Service (Deterministic SKU Composition)

## Summary

- **New unit tests**: 16/16 passed (`tests/test_sku_renderer.py`, `tests/test_sku_composition_service.py`)
- **New integration tests**: 8/8 passed (`tests/test_composition_api.py`)
- **Full backend suite**: 422/422 passed (0 failures, 7m06s)
- **New-code coverage**: 86% (target > 80%)
- **Security tests**: staff-only and ownership paths covered (403 / 404)
- **Performance**: render median **28 ms** at 1024x1024 and **110 ms** at 2048x2048 (target < 500 ms) — synchronous in-request composition (ADR-053) is comfortable.

### Coverage by new module

| Module | Stmts | Miss | Cover |
|---|---|---|---|
| `models/product_overlay.py` | 34 | 0 | 100% |
| `api/schemas/composition.py` | 75 | 2 | 97% |
| `services/sku_renderer.py` | 91 | 3 | 97% |
| `repositories/product_overlay_repo.py` | 21 | 1 | 95% |
| `services/composition_spec.py` | 25 | 2 | 92% |
| `repositories/composition_version_repo.py` | 30 | 4 | 87% |
| `services/sku_composition_service.py` | 109 | 25 | 77% |
| `api/routers/composition.py` | 66 | 25 | 62%* |
| **Total (new modules)** | **451** | **62** | **86%** |

\* The router figure is understated: the coverage tracer in this environment (coverage 7.15.2 / Python 3.13.5) recorded line numbers past the end of file (e.g. 2766 in a 164-line file) for `api/routers/composition.py`, a tooling artifact — the endpoint is exercised (integration tests create and read composed versions through HTTP). `pytest-cov` segfaults in this environment, so `coverage run` was used.

## Test Suite Breakdown

### Unit — deterministic rendering (`tests/test_sku_renderer.py`, 6 tests)

1. **Render is byte-for-byte deterministic** — two renders of the same spec produce identical bytes and SHA-256 (ADR-054).
2. **Font version is stable; unknown families rejected** — `font_version` is stable, non-`default` family raises `UnsupportedFontError`.
3. **Fit evaluation accepts/rejects by area** — valid spec fits; a 5x5px box rejects with a reason.
4. **Anchor placement** — `resolve_frame` honours top-left, bottom-right (with offsets) and centered anchors.
5. **Spec hash sensitivity** — changing font version or base image key yields a distinct hash.
6. **No provider import boundary** — the composition path never imports OpenAI/Replicate/VTON providers (invariant 2 / ADR-053).

### Unit — service (`tests/test_sku_composition_service.py`, 10 tests)

1. SKU normalization collapses whitespace and drops control characters.
2. Invisible-only SKU is rejected.
3. Compose renders a valid version and writes a `compositions/.../v1.png` output.
4. Identical spec is idempotent (one row, same version id).
5. New SKU appends version 2 without mutating the base image or prior version.
6. Style-only change appends a new version with a different hash and checksum.
7. Non-fitting overlay is persisted as `status=blocked` with no rendered key and no upload (ADR-056).
8. A job without a completed base image is rejected.
9. Jobs owned by another account are rejected.
10. The overlay links the bolt 045 `composition_snapshot_id` when a snapshot exists.

### Integration — API (`tests/test_composition_api.py`, 8 tests)

1. Non-staff receives **403**.
2. First compose returns **201**; identical re-request returns **200** with the same version.
3. Fit failure returns **422** with structured `OVERLAY_DOES_NOT_FIT` + `version_id`.
4. Read endpoints (`GET .../composition`, `.../versions`, `/api/composition-versions/{id}`) work and are ownership-scoped (**404** for another account).
5. Unknown job returns **404**.
6. Blank SKU and unknown font return **400**.
7. Missing base image returns **409**.
8. Reads without an overlay and unknown version return **404**.

## Acceptance Criteria Validation

- ✅ **003-deterministic-sku-composition** — *"the exact complete text is rendered at the configured position/style"*: the same measured dimensions drive both validation and rendering (`evaluate_fit` / `resolve_frame` / `render_composition`), and rendering is byte-deterministic. Verified structurally and by deterministic checksum; pixel-level OCR of the string is not performed.
- ✅ **003-deterministic-sku-composition** — *"an SKU/style change creates a new version without another OpenAI call or base mutation"*: tests 5, 6 and the no-provider-import boundary test.
- ✅ **003-deterministic-sku-composition** — *"an overlay that does not fit blocks publication with a validation error"*: blocked version persisted, HTTP 422 structured error, no output upload.
- ✅ **Edge case** — *unsupported control characters*: normalized away; invisible-only SKUs rejected.

### NFR traceability

- **NFR-3 (visual/composition quality)**: exact SKU validated before render; verifiable placement via deterministic frame math.
- **NFR-4 (privacy/access)**: staff-only 403 and ownership 404 enforced; composition never handles provider credentials.
- **NFR-5 (persistence/integrity)**: append-only versions, durable storage keys only, no pre-signed URLs, blocked attempts retained.

## Issues Found

1. **Coverage tracer mis-attributes router lines** (environment): line numbers beyond EOF recorded; `pytest-cov` segfaults. Worked around with `coverage run`; endpoint behaviour is verified by passing HTTP tests.
2. **`pillow` was only a transitive dependency** (via `rembg`). Added `pillow>=10.0.0` as a direct dependency since the renderer imports it.
3. **Design deviation**: `OverlayFitValidator` was folded into `services/sku_renderer.py` so validation and rendering share identical measurement code.
4. **V1 font support**: only Pillow's bundled scalable default font is supported; other families return HTTP 400. A bundled licensed font is a future follow-up if typography requirements grow.

## Recommendations

1. **Bolt 048 (`product-publication-sync`)**: filter publication candidates on `status == valid` and require a new explicit selection whenever the latest valid version changes (ADR-055).
2. **Font/renderer upgrades**: treat any change to `RENDER_PIPELINE_VERSION` or Pillow version as a new `font_version`; add a golden-image test before upgrading to confirm intentional pixel changes.
3. **Environments**: confirm the MinIO `generated` bucket exists and is writable in each environment (composition writes `compositions/…` there).
4. **Test infrastructure**: add a reusable composition storage stub to `tests/conftest.py` if more bolts touch composition, to avoid repeating the module-level `ApiFakeStorage` pattern.

## Verdict

All acceptance criteria for story 003 are met; full backend suite green (422 passed); coverage above target; no blocking issues. Bolt is ready for completion.
