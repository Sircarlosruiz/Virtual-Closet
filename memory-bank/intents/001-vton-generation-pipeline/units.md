---
intent: 001-vton-generation-pipeline
phase: inception
status: draft
updated: 2026-05-26T00:00:00Z
---

# Units: 001-vton-generation-pipeline

## Unit Decomposition

Project type: `full-stack-web` — backend units use DDD decomposition; one frontend unit uses feature-based decomposition.

## Requirement-to-Unit Mapping

| FR | Requirement | Unit |
|----|-------------|------|
| FR-1 | Garment photo upload | `001-media-service` |
| FR-2 | Model photo management (own + curated library) | `001-media-service` |
| FR-3 | Cloth type selection (validated at job submission) | `002-vton-job-service` |
| FR-4 | Job submission | `002-vton-job-service` |
| FR-5 | Async processing via Celery | `002-vton-job-service` |
| FR-6 | Job status polling | `002-vton-job-service` |
| FR-7 | Automatic retry on failure | `002-vton-job-service` |
| FR-8 | Job history | `002-vton-job-service` |
| All user-facing FRs | Upload UI, model selection, job submission, status polling, result display | `003-vton-pipeline-ui` |

## Units

### Unit 1: `001-media-service` (Backend)

- **Purpose**: Manages garment and model photo uploads to MinIO. Provides both mayorista-owned uploads and a curated model library.
- **Assigned Requirements**: FR-1, FR-2
- **Bolt Type**: `ddd-construction-bolt`
- **Dependencies**: None (foundational)
- **Depended by**: `002-vton-job-service`, `003-vton-pipeline-ui`
- **Estimated Stories**: 3

### Unit 2: `002-vton-job-service` (Backend)

- **Purpose**: Full VTON job lifecycle — submission, async Celery processing, status tracking, retry logic, result storage, and job history.
- **Assigned Requirements**: FR-3, FR-4, FR-5, FR-6, FR-7, FR-8
- **Bolt Type**: `ddd-construction-bolt`
- **Dependencies**: `001-media-service` (needs garment/model MinIO URLs)
- **Depended by**: `003-vton-pipeline-ui`
- **Estimated Stories**: 5

### Unit 3: `003-vton-pipeline-ui` (Frontend)

- **Purpose**: All user-facing interactions for the VTON pipeline — upload forms, model selection, cloth type selector, job submission, status polling, result display, and job history.
- **Assigned Requirements**: All user-facing FRs (FR-1 through FR-8 from the UI perspective)
- **Bolt Type**: `simple-construction-bolt`
- **Dependencies**: `001-media-service`, `002-vton-job-service`
- **Depended by**: None
- **Estimated Stories**: 6

## Dependency Graph

```
001-media-service ──────────────────────────────► 003-vton-pipeline-ui
                                                         ▲
002-vton-job-service (depends on 001-media-service) ─────┘
```

Execution order:
1. `001-media-service` (no dependencies)
2. `002-vton-job-service` (requires 001-media-service)
3. `003-vton-pipeline-ui` (requires 001 + 002)
