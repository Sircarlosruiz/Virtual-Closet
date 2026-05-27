---
unit: 001-media-service
intent: 001-vton-generation-pipeline
phase: inception
status: complete
created: 2026-05-26T00:00:00.000Z
updated: 2026-05-26T00:00:00.000Z
---

# Unit Brief: 001-media-service

## Purpose

Manages all photo assets used in the VTON pipeline. Handles garment photo uploads from mayoristas, mayorista-owned model photo uploads, and a curated model photo library maintained by the platform. All files are stored in and served from MinIO.

## Scope

### In Scope
- Garment photo upload (JPG/PNG, max 10MB) stored under mayorista's namespace in MinIO
- Mayorista model photo upload stored under mayorista's namespace in MinIO
- Curated model library: read-only list of pre-approved model photos stored in a shared MinIO prefix
- File validation (type, size) before MinIO write
- Return of MinIO pre-signed URLs (15 min TTL) for access to uploaded files

### Out of Scope
- Image resizing or background removal (future enhancement)
- VTON job submission (handled by `002-vton-job-service`)
- Frontend upload UI (handled by `003-vton-pipeline-ui`)

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Garment photo upload to MinIO under mayorista namespace | Must |
| FR-2 | Model photo upload (own) + curated model library list | Must |

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| `GarmentPhoto` | A garment photo uploaded by a mayorista | id, mayorista_id, minio_key, filename, content_type, size_bytes, uploaded_at |
| `ModelPhoto` | A model photo (own upload or curated) | id, mayorista_id (null if curated), minio_key, label, is_curated, uploaded_at |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `upload_garment` | Validates and stores garment photo in MinIO | mayorista_id, file bytes, content_type | GarmentPhoto record + presigned URL |
| `upload_model_photo` | Validates and stores own model photo in MinIO | mayorista_id, file bytes, content_type | ModelPhoto record + presigned URL |
| `list_curated_models` | Returns read-only curated model photo library | (none) | List of ModelPhoto (is_curated=true) |
| `get_presigned_url` | Generates short-lived access URL for any stored file | minio_key | Pre-signed URL (15 min TTL) |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 3 |
| Must Have | 3 |
| Should Have | 0 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-upload-garment-photo | Upload Garment Photo | Must | Planned |
| 002-upload-own-model-photo | Upload Own Model Photo | Must | Planned |
| 003-curated-model-library | Browse Curated Model Library | Must | Planned |

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| Auth (pre-condition) | Mayorista must be authenticated; mayorista_id comes from JWT session |

### Depended By
| Unit | Reason |
|------|--------|
| `002-vton-job-service` | Needs garment and model photo MinIO keys to submit inference jobs |
| `003-vton-pipeline-ui` | Calls upload endpoints and model library list |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| MinIO | Primary file storage for all photos | Low |

---

## Technical Context

### Suggested Technology
- FastAPI router: `api/routers/media.py`
- Service: `services/media_service.py`
- Repository: `repositories/media_repo.py`
- Models: `models/media.py` (`GarmentPhoto`, `ModelPhoto` SQLAlchemy models)
- Schema: `api/schemas/media.py` (upload request/response Pydantic models)
- MinIO client: existing `core/` integration

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| MinIO | File storage | S3 API (boto3 / minio-py) |
| PostgreSQL | Metadata persistence | SQLAlchemy async |

### Data Storage

| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| GarmentPhoto metadata | PostgreSQL | Low (per upload) | Permanent |
| ModelPhoto metadata | PostgreSQL | Low | Permanent |
| Photo files | MinIO | Medium (MBs per file) | Permanent |

---

## Constraints

- File type validation: only JPG/PNG accepted
- Max file size: 10MB per upload
- Mayorista can only access their own uploads (not other mayoristas' namespaces)
- Curated model library is read-only for mayoristas (admin-managed)
- Pre-signed URLs must have a 15-minute TTL — never return permanent public URLs

---

## Success Criteria

### Functional
- [ ] Mayorista can upload a garment photo and receive a pre-signed URL
- [ ] Mayorista can upload their own model photo
- [ ] Mayorista can list all curated model photos
- [ ] Uploads are rejected if file type or size is invalid
- [ ] A mayorista cannot access another mayorista's uploads

### Non-Functional
- [ ] Upload endpoint responds within 500ms (excluding file transfer time)
- [ ] Pre-signed URLs expire after 15 minutes

### Quality
- [ ] Integration tests cover upload, validation, and access control
- [ ] All acceptance criteria met

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| `001-media-service` | ddd-construction-bolt | 001, 002, 003 | Domain model + API + MinIO integration |
