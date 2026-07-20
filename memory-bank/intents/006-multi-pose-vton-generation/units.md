---
intent: 006-multi-pose-vton-generation
phase: inception
status: decomposed
updated: 2026-07-17T00:00:00Z
---

# Unit Decomposition: 006-multi-pose-vton-generation

## Requirement-to-Unit Mapping

- **FR-1** (Model Entity with Pose Photo Upload) → `001-model-pose-service` (API) + `003-multi-pose-vton-generation-ui` (UI)
- **FR-2** (List Model Poses) → `001-model-pose-service` (API) + `003-multi-pose-vton-generation-ui` (UI)
- **FR-3** (Pose-Aware Garment Submission with Deselection) → `002-pose-set-service` (API) + `003-multi-pose-vton-generation-ui` (UI)
- **FR-4** (Multi-Pose Batch Expansion) → `002-pose-set-service`
- **FR-5** (PoseSet Registration) → `002-pose-set-service`
- **FR-6** (Pose Set Result Retrieval) → `002-pose-set-service` (API) + `003-multi-pose-vton-generation-ui` (UI)
- **FR-7** (Backward Compatibility for Single-Pose Usage) → `001-model-pose-service` (legacy backfill); no changes required in existing `001-vton-generation-pipeline` / `005-batch-vton-generation` units

---

## Units

### Unit 1: `001-model-pose-service`

- **Purpose**: Backend domain for the `Model` identity and its pose photos
- **Responsibility**: `Model` aggregate owning 1..N `ModelPhoto` poses, pose type enum enforcement (`front`/`side`/`back`, no duplicates), pose CRUD API, and one-time backfill of legacy `ModelPhoto` rows into implicit single-pose `Model` wrappers
- **Assigned Requirements**: FR-1, FR-2, FR-7 (backfill)
- **Dependencies**: `001-media-service` (intent `001-vton-generation-pipeline`) — reuses file validation and MinIO upload conventions
- **Interface**: REST API consumed by `002-pose-set-service` and `003-multi-pose-vton-generation-ui`
- **Unit Type**: backend
- **Default Bolt Type**: `ddd-construction-bolt`

### Unit 2: `002-pose-set-service`

- **Purpose**: Backend domain coordinating multi-pose generation submissions
- **Responsibility**: `PoseSet` aggregate; expands a pose-aware submission (garment + model + selected poses) into a standard `BatchJob`/`BatchItem` set via the existing batch pipeline, atomically registers the `PoseSet`, and exposes grouped result retrieval
- **Assigned Requirements**: FR-3 (API), FR-4, FR-5, FR-6 (API)
- **Dependencies**: `001-model-pose-service` (reads a model's poses), `001-batch-job-service` (intent `005-batch-vton-generation`, reused unchanged for batch creation/status/retry)
- **Interface**: REST API consumed by `003-multi-pose-vton-generation-ui`
- **Unit Type**: backend
- **Default Bolt Type**: `ddd-construction-bolt`

### Unit 3: `003-multi-pose-vton-generation-ui`

- **Purpose**: React frontend for model/pose management and multi-pose generation
- **Responsibility**: All user-facing interactions — create model & upload poses, list poses, pose deselection at submission time, and the grouped pose set result view (with retry wired to the existing batch item retry endpoint)
- **Assigned Requirements**: FR-1 (UI), FR-2 (UI), FR-3 (UI), FR-6 (UI)
- **Dependencies**: `001-model-pose-service`, `002-pose-set-service`
- **Interface**: Consumes REST APIs from both backend units
- **Unit Type**: frontend
- **Default Bolt Type**: `simple-construction-bolt`

---

## Dependency Graph

```
001-model-pose-service ──► 002-pose-set-service ──► 003-multi-pose-vton-generation-ui
        │                           │
        ▼                           ▼
001-media-service           001-batch-job-service
(existing, intent 001)      (existing, intent 005 — reused, not modified)
```

---

## Stories Estimate

| Unit | Stories | Must | Should |
|------|---------|------|--------|
| 001-model-pose-service | 4 | 4 | 0 |
| 002-pose-set-service | 2 | 2 | 0 |
| 003-multi-pose-vton-generation-ui | 3 | 3 | 0 |
| **Total** | **9** | **9** | **0** |

---

## Bolt Estimate

| Unit | Bolts | Type |
|------|-------|------|
| 001-model-pose-service | 2 | ddd-construction-bolt |
| 002-pose-set-service | 1 | ddd-construction-bolt |
| 003-multi-pose-vton-generation-ui | 2 | simple-construction-bolt |
| **Total** | **5** | — |
