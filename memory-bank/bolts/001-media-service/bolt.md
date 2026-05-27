---
id: 001-media-service
unit: 001-media-service
intent: 001-vton-generation-pipeline
type: ddd-construction-bolt
status: complete
stories:
  - 001-upload-garment-photo
  - 002-upload-own-model-photo
  - 003-curated-model-library
created: 2026-05-26T00:00:00.000Z
started: 2026-05-26T23:00:00.000Z
completed: "2026-05-27T05:38:47Z"
current_stage: null
stages_completed:
  - name: model
    completed: 2026-05-26T23:05:00.000Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-05-26T23:10:00.000Z
    artifact: ddd-02-technical-design.md
  - name: implement
    completed: 2026-05-26T23:20:00.000Z
    artifact: src/media/
  - name: test
    completed: 2026-05-26T23:25:00.000Z
    artifact: ddd-03-test-report.md
requires_bolts: []
enables_bolts:
  - 002-vton-job-service
  - 004-vton-pipeline-ui
requires_units: []
blocks: false
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 001-media-service

## Overview

Implements the media asset management layer for the VTON pipeline. Covers domain modeling for garment and model photos, MinIO integration, and REST API endpoints for upload and library access.

## Objective

Build a fully tested media service that allows mayoristas to upload garment photos, upload their own model photos, and browse the curated model library — all backed by MinIO storage and PostgreSQL metadata.

## Stories Included

- **001-upload-garment-photo**: Upload garment photo to MinIO (Must)
- **002-upload-own-model-photo**: Upload own model photo to MinIO (Must)
- **003-curated-model-library**: Browse curated model library (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- ✅ **1. Domain Model**: Complete → `ddd-01-domain-model.md`
- ✅ **2. Technical Design**: Complete → `ddd-02-technical-design.md`
- ✅ **3. Implement**: Complete → `models/media.py`, `repositories/media_repo.py`, `services/media_service.py`, `services/model_library_service.py`, `api/routers/media.py`, `api/schemas/media.py`, `core/minio_client.py`, Alembic migration
- ⏳ **4. Test**: In Progress → `ddd-03-test-report.md` ← current

## Dependencies

### Requires
- None (foundational bolt — first to execute)

### Enables
- 002-vton-job-service (needs garment/model photo IDs)
- 004-vton-pipeline-ui (needs upload and library endpoints)

## Success Criteria

- [ ] All 3 stories implemented with acceptance criteria met
- [ ] File type and size validation enforced
- [ ] Mayorista namespace isolation verified (access control tests pass)
- [ ] Curated library returns correct items with presigned URLs
- [ ] Integration tests passing against real PostgreSQL + MinIO
