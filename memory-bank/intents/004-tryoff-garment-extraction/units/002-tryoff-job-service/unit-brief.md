---
unit: 002-tryoff-job-service
intent: 004-tryoff-garment-extraction
phase: inception
status: draft
created: 2026-05-31T00:00:00Z
updated: 2026-05-31T00:00:00Z
default_bolt_type: ddd-construction-bolt
---

# Unit Brief: tryoff-job-service

## Purpose

Async garment extraction job orchestration. Accepts source images and garment type selections from the UI, queues individual extraction jobs via Celery/RabbitMQ, calls the FLUX model container, persists extracted garment outputs to MinIO, saves results to the mayorista's media library, and provides job status and history APIs. Mirrors the structure of `002-vton-job-service` from intent 001.

## Scope

### In Scope
- Source image upload API (validation, MinIO storage)
- TryOff job creation: one job per garment type per source image
- Multi-garment queuing: multiple jobs from the same source image in one session
- Celery task: calls 001-tryoff-model-service POST /tryoff, handles response
- Output persistence: stores extracted garment PNG in MinIO, creates media library entry
- Auto-retry: up to 2 retries on job failure (Celery retry mechanism)
- Job status polling API
- Job history API (list past extractions with thumbnails)

### Out of Scope
- FLUX model inference (owned by 001-tryoff-model-service)
- UI rendering (owned by 003-tryoff-pipeline-ui)
- VTON job creation — handoff is a UI action that links to existing VTON submission form
- Auth and mayorista identity — reuses existing auth middleware

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Source image upload (both lifestyle and product photos) | Must |
| FR-2 | Multi-garment selection — queue top and pants as separate jobs | Must |
| FR-3 | Async extraction processing via Celery/RabbitMQ | Must |
| FR-4 | Output = clean white-background garment image | Must |
| FR-5 | Auto-save extracted garments to media library with tags | Must |
| FR-7 | Auto-retry on failure (max 2 retries) | Should |
| FR-8 | TryOff job history | Should |

---

## Domain Concepts

### Key Entities
| Entity | Description | Attributes |
|--------|-------------|------------|
| TryoffJob | A single garment extraction task | id, mayorista_id, source_image_id, garment_type (upper/lower/dress), status, output_media_id, created_at, completed_at, error |
| TryoffSession | Groups multiple jobs from the same source image | id, mayorista_id, source_image_id, jobs[], created_at |
| MediaItem (reused) | Existing media library entity | id, mayorista_id, url, type (extracted_garment), metadata (garment_type, source_job_id) |

### Key Operations
| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| POST /api/tryoff/jobs | Create extraction job(s) for a source image | source_image_id, garment_types[] | TryoffSession with job list |
| GET /api/tryoff/jobs/{id} | Poll job status | job_id | TryoffJob (with output_media_id when done) |
| GET /api/tryoff/jobs | List job history | mayorista_id, pagination | TryoffJob[] |
| process_tryoff_job (Celery task) | Execute extraction: call model → store output → update media library | TryoffJob | TryoffJob (updated status) |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 7 |
| Must Have | 5 |
| Should Have | 2 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-submit-tryoff-job | Submit a TryOff extraction job | Must | Planned |
| 002-process-job-celery | Process extraction job via Celery worker | Must | Planned |
| 003-multi-garment-queue | Queue multiple garments from one source image | Must | Planned |
| 004-poll-job-status | Poll job status and retrieve output | Must | Planned |
| 005-media-library-save | Auto-save extracted garment to media library | Must | Planned |
| 006-retry-on-failure | Auto-retry failed jobs | Should | Planned |
| 007-job-history | List past TryOff extraction jobs | Should | Planned |

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| 001-tryoff-model-service | Calls POST /tryoff for garment extraction inference |
| 001-vton-generation-pipeline (media-service) | Reuses media library data model and MinIO storage |

### Depended By
| Unit | Reason |
|------|--------|
| 003-tryoff-pipeline-ui | All API endpoints consumed by the frontend |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| RabbitMQ | Job queue broker (shared with VTON pipeline) | Medium |
| MinIO / S3 | Store source images + extracted garment outputs | Low |
| Celery | Async task execution | Low — existing infra |

---

## Technical Context

### Suggested Technology
- FastAPI (existing backend stack) for REST endpoints
- Celery with RabbitMQ broker (existing setup from VTON pipeline)
- SQLAlchemy + PostgreSQL for TryoffJob and TryoffSession entities
- MinIO SDK for object storage
- httpx for calling the model service container

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| 001-tryoff-model-service | Outbound API call | HTTP/REST (Docker internal network) |
| RabbitMQ | Message queue | AMQP |
| MinIO | Object storage | S3 API |
| Existing media library | DB write | SQLAlchemy |

### Data Storage
| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| TryoffJob records | PostgreSQL | ~100 rows/day/mayorista | 90 days |
| Source images | MinIO (raw bucket) | ~2 MB/image | 30 days |
| Extracted garments | MinIO (media bucket) | ~1 MB/image | Same as media library |

---

## Constraints

- Job queue must not starve VTON jobs — use separate Celery queue or priority lanes
- Extracted garment PNG must be minimum 768×1024 px for VTON compatibility
- TryOff model service must be reachable at a known internal URL (env var: `TRYOFF_MODEL_URL`)

---

## Success Criteria

### Functional
- [ ] Job created, queued, and processed end-to-end without manual intervention
- [ ] Multiple garment types queued from one source image produce separate media library items
- [ ] Failed job retries automatically; after 2 retries status becomes `failed`
- [ ] Extracted garment appears in mayorista's media library tagged with garment type

### Non-Functional
- [ ] Job creation API responds in < 500ms
- [ ] Celery task starts processing within 30 seconds of submission under normal load

### Quality
- [ ] Code coverage > 80%
- [ ] All acceptance criteria met

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 016-tryoff-job-service | ddd-construction-bolt | 001, 002, 003 | Core job submission + async processing |
| 017-tryoff-job-service | ddd-construction-bolt | 004, 005, 006 | Output handling, media library, retry |
| 018-tryoff-job-service | ddd-construction-bolt | 007 | Job history API |

---

## Notes

- The Celery task must handle `httpx.TimeoutException` from the model service and retry accordingly
- TryoffSession is a lightweight grouping concept (not a DB entity initially — can be inferred from shared source_image_id)
- Reuse the existing `MediaItem` model; add `garment_type` and `source_job_id` to metadata JSON field
