---
unit: 002-template-composition-service
bolt: 046-template-composition
stage: model
status: complete
updated: 2026-09-17T22:30:28Z
---

# Static Model: Template and Composition Service (Deterministic SKU Composition)

## Bounded Context

Deterministic post-generation composition. OpenAI (or the configured provider)
produces a *base image* — a scene generated from a template's fields and
references. This bolt adds the fixed-position elements the model cannot be
trusted to draw exactly: the product reference / SKU and any other pinned
overlay elements. Composition is a pure, local, deterministic rendering step:
it never calls a provider, never mutates the base image, and always produces a
new derived object.

Inputs are the base image (owned by `GenerationJob`, bolt 043/044), the
`CompositionSnapshot`/`EffectiveConfiguration` frozen at accept time (bolt
045), and a `SkuOverlaySpec` (introduced here). Output is an immutable
`CompositionVersion` that is either valid (publishable pending explicit staff
selection) or rejected by fit validation.

Out of scope: OpenAI inference and job queues (bolt 043/044), template
lifecycle and snapshots (bolt 045), publication/selection and BFashion sync
(bolt 048), free-canvas editing, and QR/barcode rendering.

## Aggregates

### ProductOverlay (Aggregate Root)

The versioned SKU / fixed-element overlay definition attached to one accepted
generation result. It is the consistency boundary for overlay edits: a change
to the SKU or its style is applied by appending a new `CompositionVersion`, not
by mutating an existing one. Identified per generation result.

### CompositionVersion (child entity of `ProductOverlay`)

One deterministic rendering of a `SkuOverlaySpec` onto the immutable base
image. Created once, never mutated; prior versions stay readable so a published
version is never silently replaced. Carries its own validity outcome and the
durable storage key of the rendered output.

## Entities

### ProductOverlay

| Field | Meaning |
|---|---|
| `id` | Durable UUID |
| `generation_job_id` | The `GenerationJob` (bolt 043) whose base image this overlay decorates |
| `base_image_key` | Durable object-storage key of the provider-produced base image (read-only; never written by this bolt) |
| `composition_snapshot_id` | The bolt 045 snapshot whose `EffectiveConfiguration` seeded defaults (identity only) |
| `created_by` | Staff account that configured the overlay |
| `created_at`, `updated_at` | Lifecycle timestamps |

### CompositionVersion

| Field | Meaning |
|---|---|
| `id` | Durable UUID |
| `overlay_id` | Parent `ProductOverlay` |
| `version` | Monotonic integer, starts at 1, incremented on every SKU/style change |
| `spec` | Frozen `SkuOverlaySpec` used to render this version |
| `fit_result` | `OverlayFitResult` recorded at render time |
| `status` | `valid` or `blocked` (see `CompositionStatus`) |
| `rendered_key` | Durable object-storage key of the composed output; `null` when `blocked` |
| `rendered_checksum` | Hash of the rendered bytes — the determinism witness |
| `created_at` | Render timestamp |

## Value Objects

- **`SkuText`**: the normalized product reference to render (e.g. `REF: CAM-001`). Constraints: non-empty after normalization; unsupported control characters are rejected or normalized per the documented rule; length bounded by a configured maximum; case preserved as configured; rendering and storage always use the same normalized value.
- **`OverlayPlacement`**: `anchor` (corner/center), `offset_x`, `offset_y`, optional `max_width`/`max_height` bounding box. Constraints: the resolved box must lie within the base image bounds; placement is absolute, not generative.
- **`OverlayStyle`**: `font_family`, `font_size`, `color`, `opacity`, optional `stroke`/`background`. Constraints: all fields required when an SKU is included; values come from the template's SKU location/style fields or an explicit staff value.
- **`SkuOverlaySpec`**: immutable composition of `SkuText` + `OverlayPlacement` + `OverlayStyle`. Constraints: complete before composing (if SKU is included, its settings must be filled first per FR-4); equality by value — two identical specs against the same base image must yield the same version.
- **`OverlayFitResult`**: `fits` (bool), `rendered_width`, `rendered_height`, `available_width`, `available_height`, optional `reason`. Constraints: purely a function of the spec, the base image dimensions, and the font metrics/version; never random and never dependent on provider state.
- **`RenderedComposition`**: `storage_key` (durable), `width`, `height`, `checksum`, `font_version`. Constraints: never a temporary/pre-signed URL.
- **`CompositionStatus`**: finite set `valid | blocked`. `valid` means the exact complete text was rendered and the candidate is eligible for staff selection; `blocked` means fit validation failed and the candidate is not publishable.

## Domain Events

- **`OverlayConfigured`**: Trigger: staff sets or changes the SKU/style for a result. Payload: `overlay_id`, `generation_job_id`, `sku_normalized`.
- **`CompositionComposed`**: Trigger: a `SkuOverlaySpec` is successfully rendered onto the base image. Payload: `overlay_id`, `version`, `rendered_key`, `rendered_checksum`.
- **`OverlayFitRejected`**: Trigger: the complete SKU text does not fit the configured placement. Payload: `overlay_id`, `rendered_width`, `available_width`, `reason`. Blocks publication of that candidate.
- **`CompositionVersionSuperseded`**: Trigger: a new version is appended after a SKU/style change. Payload: `overlay_id`, `previous_version`, `new_version`. The superseded version remains readable.

## Domain Services

- **`SkuCompositionService`**
  - Operations: `compose(base_image, spec)` → `CompositionVersion` (valid), `recompose(overlay, spec)` → new `CompositionVersion`. Resolves all spec fields, delegates fit validation, renders deterministically, persists an append-only version. Never calls a provider.
  - Dependencies: `OverlayFitValidator`, `ProductOverlayRepository`, `CompositionVersionRepository`, object storage, a font-metrics provider (deterministic, version-pinned).
- **`OverlayFitValidator`**
  - Operations: `validate(spec, image_dimensions, font_metrics)` → `OverlayFitResult`. Pure function: measures the *complete* text at the configured font/size and checks it against the placement bounding box.
  - Dependencies: font metrics only.
- **`SkuTextNormalizer`**
  - Operations: `normalize(raw)` → `SkuText`. Trims, rejects or normalizes unsupported control characters per the documented rule, enforces max length.
  - Dependencies: none.

## Repository Interfaces

- **`ProductOverlayRepository`**: Entity: `ProductOverlay` — Methods: `save`, `get_by_id`, `get_by_generation_job_id`, `list_versions`.
- **`CompositionVersionRepository`**: Entity: `CompositionVersion` — Methods: `append(version)` (insert-only; no update), `get_by_id`, `get_latest_by_overlay`, `list_by_overlay`, `find_by_spec_hash(overlay_id, spec_hash)`.
- **Read-only dependencies** (not owned here): `CompositionSnapshotRepository` (bolt 045) for `EffectiveConfiguration`; the generation result accessor (bolt 043/044) for `base_image_key`.

## Invariants

1. The base image is immutable: composition never overwrites, edits, or replaces the provider-produced `base_image_key`; every composition writes a **new** derived object.
2. Composition performs **no** provider/OpenAI call. It is a local, deterministic rendering step (FR-4, story criterion 2).
3. Determinism: identical base image bytes + identical `SkuOverlaySpec` + identical `font_version` produce byte-identical output and the same `rendered_checksum`; recomposing an unchanged spec reuses the existing version instead of appending a duplicate.
4. Any change to `SkuText` or `OverlayStyle` appends a new `CompositionVersion` and increments `version`; no prior version is ever mutated or deleted.
5. If an SKU is included, its full configuration (text, placement, style, font, size, color) must be complete before composing; incomplete specs are rejected before rendering.
6. Fit validation operates on the **complete** text: if the rendered text does not fit the placement bounds, composition is rejected with `OverlayDoesNotFitError`, no `valid` version is produced, and the candidate cannot be published (story criterion 3).
7. Only `valid` versions are eligible for publication. Marking a candidate as published/selected is owned by bolt 048; this bolt records validity only and never sets a published flag.
8. `SkuText` rendering and `SkuText` storage use the same normalized value; unsupported control characters are rejected or normalized per the documented rule, never silently dropped from the image but kept in storage (or vice versa).
9. `RenderedComposition.storage_key` and every persisted reference are durable object-storage keys — never temporary or pre-signed URLs (mirrors bolt 045 invariant 7).

## Boundaries

- `ProductOverlay` + `CompositionVersion` own SKU overlay configuration and rendering output. They read the base image key and the bolt 045 snapshot by ID only; they never write `GenerationJob`, `CompositionSnapshot`, or `ImageTemplate` rows.
- `SkuCompositionService` owns rendering and versioning; `OverlayFitValidator` owns fit decisions; `SkuTextNormalizer` owns text normalization. No provider adapter is involved.
- Publication/selection (FR-12) and BFashion sync remain owned by bolt 048 (`003-product-image-integration`); this bolt exposes version identity and validity through the integration contract only.
- Template SKU location/style defaults live in the template (FR-3) and are consumed through `EffectiveConfiguration`/`SkuOverlaySpec`; this bolt does not mutate the template schema.
- QR/barcode rendering is explicitly out of scope (per story).

## Ubiquitous Language

| Term | Definition |
|------|------------|
| Base Image | The provider-generated scene before any overlay; immutable input to composition. |
| SKU / Product Reference | The exact product code rendered as visible text (e.g. `REF: CAM-001`), taken from the product or entered explicitly and stored with the job. |
| Overlay | A fixed-position element added after generation; the SKU is the primary overlay in V1. |
| ProductOverlay | The versioned SKU/fixed-element definition attached to one generation result (aggregate root). |
| SkuOverlaySpec | The immutable value object holding the SKU text, placement, and style used to render one version. |
| Placement | The absolute anchor/offset/bounding box where the overlay is rendered. |
| Composition Version | One deterministic rendering of a spec onto the base image; append-only. |
| Fit Validation | The deterministic check that the complete text fits within the placement bounds. |
| Recompose | Creating a new composition version after a SKU/style change, without another provider call. |
| Publishable | A `valid` composition version eligible for explicit staff selection (selection itself is bolt 048). |
| Rendered Composition | The durable composed output and its checksum. |
| Font Version | The pinned font/metrics version that, together with base + spec, defines determinism. |

## Stories Covered

- **003-deterministic-sku-composition**: `ProductOverlay`, `CompositionVersion`, `SkuText`, `OverlayPlacement`, `OverlayStyle`, `SkuOverlaySpec`, `OverlayFitResult`, `RenderedComposition`, `SkuCompositionService`, `OverlayFitValidator`, `SkuTextNormalizer`, invariants 1–9.
