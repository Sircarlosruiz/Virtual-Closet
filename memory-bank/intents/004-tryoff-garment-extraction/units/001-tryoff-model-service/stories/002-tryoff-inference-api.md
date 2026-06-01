---
id: 002-tryoff-inference-api
unit: 001-tryoff-model-service
intent: 004-tryoff-garment-extraction
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 014-tryoff-model-service
implemented: false
---

# Story: 002-tryoff-inference-api

## User Story

**As a** Celery worker
**I want** to POST an image and a garment type to the TryOff model container
**So that** I receive a clean product-photography PNG of the extracted garment

## Acceptance Criteria

- [ ] **Given** a valid JPEG/PNG source image and garment_type (`upper`/`lower`/`dress`), **When** POST /tryoff is called, **Then** it returns a PNG with no visible human body parts and the garment centered on a white background
- [ ] **Given** a valid request, **When** inference completes, **Then** output image dimensions are ≥ 768×1024 px
- [ ] **Given** an invalid garment_type value, **When** POST /tryoff is called, **Then** it returns HTTP 422 with a descriptive validation error
- [ ] **Given** an unsupported image format (e.g., TIFF, BMP), **When** POST /tryoff is called, **Then** it returns HTTP 400
- [ ] **Given** inference is already running, **When** a second POST /tryoff arrives, **Then** it queues and processes after current inference completes (no parallel inference)

## Technical Notes

- Endpoint: `POST /tryoff` — accepts `multipart/form-data` with `image` (file) and `garment_type` (str)
- Garment type maps to prompt:
  - `upper` → `"TRYOFF extract the upper garment over a white background, product photography style. NO HUMAN VISIBLE."`
  - `lower` → `"TRYOFF extract the lower garment over a white background, product photography style. NO HUMAN VISIBLE."`
  - `dress` → `"TRYOFF extract the dress/full-body garment over a white background, product photography style. NO HUMAN VISIBLE."`
- Inference params: height=1024, width=768, num_inference_steps=28, guidance_scale=5.0
- Response: returns PNG bytes with `Content-Type: image/png`
- Use asyncio.Lock or threading.Lock to serialize requests (no concurrent inference)

## Dependencies

### Requires
- 001-flux-container-setup (model must be loaded)

### Enables
- 002-tryoff-job-service / 002-process-job-celery (calls this endpoint)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Source image > 10 MB | HTTP 413 with size limit message |
| Inference timeout (> 120s) | HTTP 504 with timeout error; Celery retries |
| GPU OOM during inference | HTTP 503; container recovers for next request |
| Grayscale image input | Converted to RGB before inference |

## Out of Scope

- Authentication on the endpoint (internal network only)
- Batch inference (one request at a time)
- Prompt customization by the caller (prompt is derived from garment_type)
