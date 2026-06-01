---
intent: 004-tryoff-garment-extraction
phase: inception
status: decomposed
updated: 2026-05-31T00:00:00Z
---

# Units: 004-tryoff-garment-extraction

## Decomposition Summary

| Unit | Name | Type | FRs | Priority | Dependencies |
|------|------|------|-----|----------|--------------|
| 001 | tryoff-model-service | backend (DDD) | FR-6 | Must | None |
| 002 | tryoff-job-service | backend (DDD) | FR-1, FR-2, FR-3, FR-4, FR-5, FR-7, FR-8 | Must | 001-tryoff-model-service |
| 003 | tryoff-pipeline-ui | frontend (simple) | FR-1, FR-2, FR-3, FR-4, FR-5 (UI), FR-6 handoff | Must | 002-tryoff-job-service |

## Requirement-to-Unit Mapping

- **FR-1** (Source image upload) → `002-tryoff-job-service` (upload API + validation) + `003-tryoff-pipeline-ui` (upload form)
- **FR-2** (Multi-garment selection) → `002-tryoff-job-service` (multi-job queuing) + `003-tryoff-pipeline-ui` (garment selector)
- **FR-3** (Async extraction processing) → `002-tryoff-job-service` (Celery task)
- **FR-4** (Clean garment output) → `001-tryoff-model-service` (FLUX inference) + `002-tryoff-job-service` (output handling)
- **FR-5** (Media library integration) → `002-tryoff-job-service` (auto-save + tagging)
- **FR-6** (VTON pipeline handoff) → `003-tryoff-pipeline-ui` (one-click action)
- **FR-7** (Auto-retry on failure) → `002-tryoff-job-service` (Celery retry config)
- **FR-8** (Job history) → `002-tryoff-job-service` (history API) + `003-tryoff-pipeline-ui` (history page)
- **Implied** (Self-hosted model container) → `001-tryoff-model-service` (FLUX container + inference endpoint)

## Dependency Graph

```text
001-tryoff-model-service
        │
        ▼
002-tryoff-job-service
        │
        ▼
003-tryoff-pipeline-ui
```

Also integrates with (external to this intent):
```text
001-vton-generation-pipeline (media library + VTON job API)
003-fashn-provider-upgrade (container management pattern reference)
```

## Unit Details

### 001-tryoff-model-service
- **Purpose**: Self-hosted FLUX.2-klein-base-9B + virtual-tryoff-lora container providing a single inference endpoint
- **Responsibility**: Model weight management, GPU memory management, inference API (POST /tryoff), health checks, container lifecycle
- **Default Bolt Type**: ddd-construction-bolt
- **Estimated Stories**: 3

### 002-tryoff-job-service
- **Purpose**: Async garment extraction job orchestration via Celery/RabbitMQ
- **Responsibility**: Job creation, multi-garment queuing, model service invocation, output storage, media library integration, retry logic, job history API
- **Default Bolt Type**: ddd-construction-bolt
- **Estimated Stories**: 7
- **Depends On**: 001-tryoff-model-service

### 003-tryoff-pipeline-ui
- **Purpose**: Frontend pages and components for the TryOff extraction flow
- **Responsibility**: Source image upload UI, garment type selector, job status display, extracted garment gallery, VTON handoff action
- **Default Bolt Type**: simple-construction-bolt
- **Estimated Stories**: 5
- **Depends On**: 002-tryoff-job-service
