---
stage: model
bolt: 045-template-lifecycle
created: 2026-09-17T18:31:01Z
---

# Domain Model: Template and Composition Service (Lifecycle + Snapshot)

## Aggregates

### ImageTemplate (Aggregate Root)

A staff-managed, reusable composition configuration. Owns its own references
and version history metadata. Templates are never read live by historical
results — see `CompositionSnapshot`.

### CompositionSnapshot (Aggregate Root)

An immutable record of the exact configuration used to produce one generation
result. Independent lifecycle from `ImageTemplate`: created once, at accept
time, and never mutated afterward.

## Entities

### ImageTemplate

| Field | Meaning |
|---|---|
| `id` | Durable UUID |
| `scope` | `TemplateScope` value object: `common` or `private` |
| `wholesaler_id` | Present only when `scope = private`; `null` for `common` |
| `version` | Monotonic integer, starts at 1, incremented on every revision |
| `status` | `draft`, `active`, or `archived` |
| `name` | Staff-facing label |
| `model`, `background`, `colors`, `rack`, `prompt` | Optional composition fields |
| `references` | 0..n `TemplateReference` child entities |
| `created_by` | Staff account that owns administration (V1: Virtual Closet staff only) |
| `created_at`, `updated_at` | Lifecycle timestamps |

### TemplateReference (child entity of `ImageTemplate`)

| Field | Meaning |
|---|---|
| `id` | Durable UUID |
| `storage_key` | Durable object-storage key for the reference image (never a temporary URL) |
| `label` | Optional descriptive label |

### CompositionSnapshot

| Field | Meaning |
|---|---|
| `id` | Durable UUID |
| `generation_job_id` | FK to the `GenerationJob` (bolt 043) whose result this snapshot explains |
| `template_id` | Template selected at generation time (identity only, not a live reference) |
| `template_version` | Template `version` value copied at capture time |
| `effective_configuration` | Frozen `EffectiveConfiguration` value object |
| `created_at` | Capture timestamp |

## Value Objects

- **`TemplateScope`**: `common`, or `private` carrying a required `wholesaler_id`. Equality by value; a `common` scope with a `wholesaler_id` is invalid.
- **`TemplateStatus`**: finite set `draft | active | archived`. Only `draft` and `active` are selectable for new jobs.
- **`EffectiveConfiguration`**: immutable bag captured at snapshot time — `model`, `background`, `colors`, `rack`, `prompt`, `provider`, `reference_keys` (durable storage keys, copied — not linked), `template_version`. Equality by value; never recomputed from the live template after capture.

## Domain Events

- **`TemplateCreated`**: Trigger: staff saves a new template. Payload: `template_id`, `scope`, `version=1`.
- **`TemplateRevised`**: Trigger: staff edits a `draft`/`active` template's fields or references. Payload: `template_id`, `old_version`, `new_version`.
- **`TemplateArchived`**: Trigger: staff archives a template. Payload: `template_id`, `version_at_archival`. Existing `CompositionSnapshot`s are unaffected.
- **`CompositionSnapshotCaptured`**: Trigger: a `GenerationJob` result is accepted. Payload: `snapshot_id`, `generation_job_id`, `template_id`, `template_version`.

## Domain Services

- **`TemplateLifecycleService`**
  - Operations: `create_template`, `revise_template` (bumps `version`), `archive_template`, `list_selectable` (scope + wholesaler visibility, excludes `archived`).
  - Dependencies: `ImageTemplateRepository`.
- **`CompositionSnapshotService`**
  - Operations: `capture_snapshot(generation_job, template)` — builds `EffectiveConfiguration` by copying current template field values and resolving each `TemplateReference.storage_key` at capture time; fails with an actionable error if a referenced key is missing rather than silently omitting it. `regenerate(snapshot)` — builds a new generation request from the frozen snapshot without mutating the original snapshot or its result.
  - Dependencies: `CompositionSnapshotRepository`, `ImageTemplateRepository` (read-only, at capture time only).

## Repository Interfaces

- **`ImageTemplateRepository`**: Entity: `ImageTemplate` — Methods: `save`, `get_by_id` (scope-aware: common is globally visible, private is visible only to the assigned wholesaler and staff), `list_selectable(scope, wholesaler_id)`, `archive(id)`.
- **`CompositionSnapshotRepository`**: Entity: `CompositionSnapshot` — Methods: `save`, `get_by_generation_job_id`.

## Invariants

1. A `private` template always carries a `wholesaler_id`; a `common` template never does.
2. Only staff accounts may create, revise, or archive templates (mirrors the staff-only boundary established for `GenerationJob` creation in bolt 043).
3. A private template is selectable only for the assigned wholesaler's products; a common template is selectable by any wholesaler's products.
4. An `archived` template cannot be selected for a new job; it remains fully resolvable for reading and regenerating existing historical snapshots.
5. Revising a template increments `version` and never retroactively alters any existing `CompositionSnapshot`.
6. Exactly one `CompositionSnapshot` is captured per accepted generation result; snapshots are never overwritten. Regeneration always creates a new job/result (and, once accepted, a new snapshot) rather than mutating the original.
7. `CompositionSnapshot.effective_configuration.reference_keys` must be durable object-storage keys, never temporary/pre-signed URLs.
8. If a template's reference is deleted before a pending selection is captured, capture is blocked with an actionable error; already-captured snapshots are unaffected (see edge case: reference deleted).

## Boundaries

- `TemplateLifecycleService` + `ImageTemplateRepository` own template CRUD, versioning, and archival. They never read or write `CompositionSnapshot`.
- `CompositionSnapshotService` + `CompositionSnapshotRepository` own frozen-configuration capture and regeneration. They read `ImageTemplate` only at capture time and never hold a live reference afterward.
- `CompositionSnapshot` links to `GenerationJob` (bolt 043) by ID only; it does not extend or modify that aggregate.
- Deterministic SKU rendering and `ProductOverlay` are explicitly out of scope for this bolt — owned by bolt 046 (`046-template-composition`), which will read `CompositionSnapshot`/`EffectiveConfiguration` as an input.
- API schemas expose template `id`, `scope`, `version`, `status`, and configuration fields; `storage_key` values are internal identifiers, never raw or pre-signed URLs (per coding-standards logging rules).

## Ubiquitous Language

- **ImageTemplate**: A staff-managed, reusable composition configuration (model, background, colors, rack, prompt, references).
- **Common template**: A template selectable by any wholesaler's products.
- **Private template**: A template selectable only by its assigned wholesaler's products.
- **Version**: A monotonic counter incremented every time a template's fields or references are revised.
- **Archived**: A terminal template status that blocks new selection while preserving historical readability.
- **CompositionSnapshot**: The immutable, frozen configuration attached to one accepted generation result.
- **EffectiveConfiguration**: The value object holding the exact field values and reference keys captured into a snapshot.
- **Regenerate**: Creating a new generation job/result from a snapshot's frozen configuration, without altering the original.

## Stories Covered

- **001-template-lifecycle**: `ImageTemplate`, `TemplateReference`, `TemplateScope`, `TemplateStatus`, `TemplateLifecycleService`, invariants 1-4, 8.
- **002-composition-snapshot**: `CompositionSnapshot`, `EffectiveConfiguration`, `CompositionSnapshotService`, invariants 5-8.
