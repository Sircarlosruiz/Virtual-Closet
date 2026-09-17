---
stage: design
bolt: 045-template-lifecycle
created: 2026-09-17T18:33:22Z
---

# Technical Design: Template and Composition Service (Lifecycle + Snapshot)

## Architecture Pattern

Same domain-driven layered pattern used by bolt 043
(`generation_job`): Model → Repository → Service → Schema → Router, with the
lifecycle side (`ImageTemplate`) and the snapshot side (`CompositionSnapshot`)
kept in separate modules per aggregate, matching their separate lifecycles
from the domain model.

## Layer Structure

```text
┌─────────────────────────────────────────────┐
│ Presentation   api/routers/templates.py      │  Staff-only template CRUD
│                api/routers/composition_       │  Snapshot read + regenerate
│                snapshots.py                  │
├─────────────────────────────────────────────┤
│ Application    services/template_lifecycle_  │  Create/revise/archive,
│                service.py                    │  selectable listing
│                services/composition_snapshot_ │  Capture at accept-time,
│                service.py                    │  regenerate
├─────────────────────────────────────────────┤
│ Domain         models/image_template.py      │  ImageTemplate,
│                                               │  TemplateReference
│                models/composition_snapshot.py │  CompositionSnapshot
├─────────────────────────────────────────────┤
│ Infrastructure repositories/image_template_   │  Scope-aware CRUD
│                repo.py                       │
│                repositories/composition_       │  Snapshot persistence
│                snapshot_repo.py              │
└─────────────────────────────────────────────┘
```

## Components

| Layer | Component | Responsibility |
|---|---|---|
| Model | `models/image_template.py` | SQLAlchemy: `ImageTemplate`, `TemplateReference` |
| Model | `models/composition_snapshot.py` | SQLAlchemy: `CompositionSnapshot` |
| Repository | `repositories/image_template_repo.py` | Scope-aware CRUD, `list_selectable`, `archive` |
| Repository | `repositories/composition_snapshot_repo.py` | Insert-only persistence, `get_by_generation_job_id` |
| Service | `services/template_lifecycle_service.py` | Validation, version bump, archival rules |
| Service | `services/composition_snapshot_service.py` | Capture at accept-time, regeneration |
| Schema | `api/schemas/template.py` | Pydantic request/response for templates |
| Schema | `api/schemas/composition_snapshot.py` | Pydantic response for snapshots |
| Router | `api/routers/templates.py` | Staff-only template endpoints |
| Router | `api/routers/composition_snapshots.py` | Snapshot read + regenerate endpoints |

## API

### Templates (staff-only)

`POST /api/templates`
- Body: `scope` (`common`\|`private`), `wholesaler_id` (required iff `private`), `name`, `model?`, `background?`, `colors?`, `rack?`, `prompt?`, `reference_storage_keys?: string[]`
- Response: HTTP 201 with `id`, `scope`, `wholesaler_id`, `version=1`, `status=draft`, timestamps

`GET /api/templates?scope=&wholesaler_id=&status=`
- Staff-only administrative listing; no visibility filtering applied for staff
- Response: paginated list of templates with all fields

`GET /api/templates/selectable?wholesaler_id=`
- Used by the product-generation flow (bolt 047) to list templates a given wholesaler may pick: `common` templates plus `private` templates where `wholesaler_id` matches, excluding `archived`
- Response: same shape, minus internal `created_by`

`PATCH /api/templates/{template_id}`
- Body: any subset of editable fields (`name`, `model`, `background`, `colors`, `rack`, `prompt`, `reference_storage_keys`)
- Rejects if `status = archived` (HTTP 409)
- On success: increments `version`, response includes new `version`

`POST /api/templates/{template_id}/archive`
- Sets `status = archived`; idempotent (already-archived returns 200 unchanged)
- Does not touch existing `composition_snapshots` rows

All template routes require `get_current_mayorista` plus a staff-role check,
reusing the pattern established for `image_generation` routes in bolt 043
(non-staff receives HTTP 403).

### Composition Snapshots

`GET /api/templates/snapshots/{generation_job_id}`
- Ownership-scoped to the job's owner (staff) per ADR-013 (404, not 403, for
  jobs owned by another account)
- Response: `id`, `generation_job_id`, `template_id`, `template_version`,
  `effective_configuration`, `created_at`
- Returns 404 if no snapshot exists yet (job not yet accepted) or job is
  unowned by the caller

`POST /api/templates/snapshots/{generation_job_id}/regenerate`
- Loads the frozen snapshot, builds a new `GenerationJob` creation request
  using `effective_configuration` (same contract as bolt 043's job creation),
  and returns the new `job_id` with HTTP 202
- Never mutates the original snapshot or its `generation_job_id`

Snapshot capture itself is **not** a public endpoint — it is invoked
internally by the generation-result-accept flow (owned by bolt 043/044), which
calls `CompositionSnapshotService.capture_snapshot(job, template)` once a
result is accepted.

## Data Persistence

### `image_templates`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `scope` | enum (`common`, `private`) | |
| `wholesaler_id` | UUID, nullable, FK `mayorista.id` | |
| `version` | integer, default 1 | Incremented by the service on each revision |
| `status` | enum (`draft`, `active`, `archived`) | |
| `name` | text | |
| `model`, `background`, `rack`, `prompt` | text, nullable | |
| `colors` | JSONB, nullable | |
| `created_by` | UUID, FK `mayorista.id` | Staff account |
| `created_at`, `updated_at` | timestamptz | |

Check constraint: `(scope = 'private' AND wholesaler_id IS NOT NULL) OR (scope = 'common' AND wholesaler_id IS NULL)`.

### `template_references`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `template_id` | UUID, FK `image_templates.id` (cascade delete not used — references are removed via revision, never hard-deleting a referenced-in-snapshot template) | |
| `storage_key` | text | Durable MinIO key, never a pre-signed URL |
| `label` | text, nullable | |
| `created_at` | timestamptz | |

### `composition_snapshots`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `generation_job_id` | UUID, FK `generation_jobs.id`, **unique** | Enforces exactly one snapshot per job (invariant 6) |
| `template_id` | UUID, FK `image_templates.id` | Identity reference only; row is never joined for live reads |
| `template_version` | integer | Copied at capture time |
| `effective_configuration` | JSONB | Frozen value object: `model`, `background`, `colors`, `rack`, `prompt`, `provider`, `reference_keys[]`, `template_version` |
| `created_at` | timestamptz | |

The `generation_job_id` uniqueness constraint is the durability mechanism for
invariant 6 — a second capture attempt for the same job fails at the database
level, not just in application logic.

## Security Design

- **Template administration**: staff-only, same dependency chain as bolt 043 (`get_current_mayorista` + staff-role check → 403 for non-staff).
- **Private scope isolation**: enforced primarily at the service layer — `list_selectable` and `get_by_id` (non-administrative path) always filter by `scope = common OR wholesaler_id = caller_wholesaler_id`, mirroring ADR-012's dependency-injection-first approach. No new ORM-level listener is introduced in this bolt; the existing tenant-scoping conventions from ADR-012/ADR-013 are reused rather than duplicated.
- **Snapshot ownership**: `GET`/`POST regenerate` on snapshots resolve the parent `GenerationJob` first and apply the same ownership check as bolt 043's job endpoints, returning 404 (not 403) for jobs owned by another account, per ADR-013.
- **No secrets in configuration**: `effective_configuration` never contains provider credentials — only the same sanitized reference-key style already established for `GenerationJob.input_data` in bolt 043.

## NFR Implementation

- **Immutability**: `composition_snapshots` rows are insert-only; the repository exposes no update method, only `save` (insert) and `get_by_generation_job_id`.
- **Reproducibility**: `regenerate` always derives a brand-new job creation request from `effective_configuration` and delegates to the existing bolt 043 job-creation path, so ADR-048 (commit-before-enqueue) is inherited automatically rather than re-implemented.
- **Consistency under concurrent edits**: `version` increment happens inside the same transaction as the field update, using a row-level lock (`SELECT ... FOR UPDATE`) on the template row to avoid lost updates from concurrent staff edits.
- **Referential safety**: capturing a snapshot resolves every `TemplateReference.storage_key` at that moment; if a referenced object is missing from storage, capture raises a domain error (`TemplateReferenceUnavailableError`) translated to HTTP 422, per invariant 8 — it never persists a partial snapshot.

## Integrations

- **Bolt 043 (`generation_jobs`)**: `composition_snapshots.generation_job_id` FK; `regenerate` calls the existing job-creation service function rather than duplicating validation.
- **Bolt 044 (generation reliability)**: the accept-flow that triggers `capture_snapshot` lives in that bolt's result-acceptance path; this bolt only provides the `CompositionSnapshotService.capture_snapshot` entry point it calls.
- **Bolt 046 (`046-template-composition`)**: will read `CompositionSnapshot.effective_configuration` as input to deterministic SKU compositing; no schema changes anticipated on this bolt's side.
- **Bolt 047 (product-generation-bridge)**: will call `GET /api/templates/selectable` when a wholesaler selects a template for a product generation job.

## Compatibility

No existing tables or endpoints are modified. `image_templates`,
`template_references`, and `composition_snapshots` are new tables added via a
single Alembic migration; no backfill is required since this is new
functionality.
