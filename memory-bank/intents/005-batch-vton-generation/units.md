---
intent: 005-batch-vton-generation
phase: inception
status: decomposed
updated: 2026-06-04T00:00:00Z
---

# Unit Decomposition: 005-batch-vton-generation

## Requirement-to-Unit Mapping

- **FR-1** (Batch Creation UI) → `002-batch-vton-generation-ui`
- **FR-2** (Batch Submission) → `001-batch-job-service`
- **FR-3** (Batch Progress View) → `001-batch-job-service` (API) + `002-batch-vton-generation-ui` (UI)
- **FR-4** (Partial Failure Isolation) → `001-batch-job-service`
- **FR-5** (Retry Failed Items) → `001-batch-job-service` (API) + `002-batch-vton-generation-ui` (UI)
- **FR-6** (Automatic Media Library Save) → `001-batch-job-service`
- **FR-7** (Batch History) → `001-batch-job-service` (API) + `002-batch-vton-generation-ui` (UI)

---

## Units

### Unit 1: `001-batch-job-service`

- **Purpose**: Backend domain for batch VTON job management
- **Responsibility**: `BatchJob` and `BatchItem` entities, submission API, status tracking, partial failure isolation, individual item retry, and auto-save to media library
- **Assigned Requirements**: FR-2, FR-4, FR-5 (API), FR-6, FR-7 (API)
- **Dependencies**: `001-vton-generation-pipeline` (existing VTON job service for per-item execution)
- **Interface**: REST API consumed by `002-batch-vton-generation-ui`
- **Unit Type**: backend
- **Default Bolt Type**: `ddd-construction-bolt`

### Unit 2: `002-batch-vton-generation-ui`

- **Purpose**: React frontend for batch creation, progress monitoring, retry, and history
- **Responsibility**: All user-facing interactions — batch creation flow, progress page, retry controls, batch history page
- **Assigned Requirements**: FR-1, FR-3 (UI), FR-5 (UI), FR-7 (UI)
- **Dependencies**: `001-batch-job-service`
- **Interface**: Consumes `001-batch-job-service` REST API
- **Unit Type**: frontend
- **Default Bolt Type**: `simple-construction-bolt`

---

## Dependency Graph

```
001-batch-job-service ──► 002-batch-vton-generation-ui
        │
        ▼
001-vton-generation-pipeline (existing — reused, not modified)
```

---

## Stories Estimate

| Unit | Stories | Must | Should |
|------|---------|------|--------|
| 001-batch-job-service | 7 | 6 | 1 |
| 002-batch-vton-generation-ui | 4 | 3 | 1 |
| **Total** | **11** | **9** | **2** |

---

## Bolt Estimate

| Unit | Bolts | Type |
|------|-------|------|
| 001-batch-job-service | 3 | ddd-construction-bolt |
| 002-batch-vton-generation-ui | 2 | simple-construction-bolt |
| **Total** | **5** | — |
