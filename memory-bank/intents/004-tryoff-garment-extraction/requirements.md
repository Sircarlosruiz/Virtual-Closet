---
intent: 004-tryoff-garment-extraction
phase: inception
status: draft
created: 2026-05-31T00:00:00Z
updated: 2026-05-31T00:00:00Z
---

# Requirements: TryOff Garment Extraction

## Intent Overview

End-to-end pipeline for extracting individual garments from lifestyle or product photos using the FLUX.2-klein Virtual Try-Off LoRA (`fal/virtual-tryoff-lora`), self-hosted like FASHN. A mayorista uploads a source image (editorial photo or existing product shot) of a model wearing clothing, selects which garments to extract (e.g., top and pants separately), and receives clean product-photography-style images of each garment on a white background. Extracted garments are saved to the media library and can be fed directly into the existing VTON pipeline (001-vton-generation-pipeline) to apply them to a different model.

This closes the loop:
```
Lifestyle/product photo of model wearing garment
  → TryOff extraction → clean garment image (media library)
  → VTON pipeline → garment applied to a different model
```

## Business Goals

| Goal | Success Metric | Priority |
|------|----------------|----------|
| Mayoristas can extract clean garment images from any photo they have | First successful extraction within 5 minutes of feature availability | Must |
| Multiple garments extracted independently from a single photo | Top and bottom extracted as separate media library items from one source image | Must |
| Extracted garments flow directly into VTON pipeline | Mayorista can go from extraction to VTON job in under 3 clicks | Must |
| Self-hosted model keeps costs predictable | No per-call cloud API fees; GPU cost is fixed infra | Should |

---

## Functional Requirements

### FR-1: Source Image Upload
- **Description**: Mayorista uploads a source image containing a model wearing clothing. Both lifestyle/editorial photos and existing product shots (flat-lay or mannequin) are supported input types.
- **Acceptance Criteria**: System accepts JPEG/PNG uploads; image is stored and associated with the TryOff job session.
- **Priority**: Must

### FR-2: Multi-Garment Selection
- **Description**: From a single source image, the user can initiate multiple extraction jobs — one per garment (e.g., extract the shirt, extract the pants). Each garment is specified via a garment-type selector (upper, lower, dress/full-body) that maps to the model's prompt internally.
- **Acceptance Criteria**: User can queue at least 2 extractions from the same image in a single session; each produces a separate output.
- **Priority**: Must

### FR-3: Async Extraction Processing
- **Description**: TryOff jobs are processed asynchronously via Celery/RabbitMQ, same infrastructure as VTON. User can poll for job status and retrieve output when complete.
- **Acceptance Criteria**: Job is queued on submission; status transitions through `pending → processing → complete/failed`; output image retrievable on completion.
- **Priority**: Must

### FR-4: Clean Garment Output
- **Description**: Output is a product-photography-style image of the extracted garment on a white background, with style, texture, color, and 3D form preserved (as if on an invisible mannequin).
- **Acceptance Criteria**: Output image contains no visible human; garment is recognizable and matches the source garment's design.
- **Priority**: Must

### FR-5: Media Library Integration
- **Description**: Each extracted garment image is saved to the mayorista's media library automatically upon job completion, tagged with source image reference and garment type.
- **Acceptance Criteria**: Extracted garment appears in media library; tagged with garment type and linked to source image; available for selection in VTON pipeline.
- **Priority**: Must

### FR-6: VTON Pipeline Handoff
- **Description**: After extraction completes, the user is offered a direct action to use the extracted garment as input to the VTON pipeline. Clicking it opens the VTON job submission flow with the garment pre-filled.
- **Acceptance Criteria**: One-click handoff pre-populates the garment field in VTON submission; user only needs to select a model and submit.
- **Priority**: Must

### FR-7: Retry on Failure
- **Description**: Failed TryOff jobs are automatically retried up to 2 times before being marked as failed, consistent with VTON pipeline behavior.
- **Acceptance Criteria**: Job retries automatically on failure; after max retries, status is `failed` with error message.
- **Priority**: Should

### FR-8: Job History
- **Description**: Mayoristas can view a history of past TryOff extractions, including source image, extracted garment output, garment type, and job status.
- **Acceptance Criteria**: History list shows last N jobs with thumbnails and status; clicking an item shows detail.
- **Priority**: Should

---

## Non-Functional Requirements

### Performance
| Requirement | Metric | Target |
|-------------|--------|--------|
| Extraction time | p95 job duration | < 90 seconds per garment |
| Queue wait | Time from submission to processing start | < 30 seconds under normal load |
| Output resolution | Minimum output image size | 768×1024 px |

### Scalability
| Requirement | Metric | Target |
|-------------|--------|--------|
| Concurrent jobs | Parallel TryOff jobs | 1 per GPU (same constraint as FASHN) |
| Queue depth | Max queued jobs | 50 (shared with VTON queue or separate) |

### Security
| Requirement | Standard | Notes |
|-------------|----------|-------|
| Authentication | JWT (existing) | Same auth as VTON pipeline |
| Authorization | Mayorista-scoped | Extracted garments private to uploading mayorista |
| Data Protection | Existing S3/MinIO policy | Source and output images stored per existing media policy |

### Reliability
| Requirement | Metric | Target |
|-------------|--------|--------|
| Availability | Uptime | 99.9% (follows platform SLA) |
| Auto-retry | Max retries on failure | 2 retries before marking failed |
| Model service health | Recovery on crash | Container auto-restart (same as FASHN) |

---

## Constraints

### Technical Constraints
- FLUX.2-klein-base-9B requires ~24 GB VRAM; runs on a **dedicated separate GPU node** (not shared with FASHN)
- Model weights loaded from `fal/virtual-tryoff-lora` + `black-forest-labs/FLUX.2-klein-base-9B` via HuggingFace
- 🚫 **BLOCKER**: HuggingFace commercial license for `black-forest-labs/FLUX.2-klein-base-9B` is **not confirmed**. Self-hosting for commercial use requires explicit license approval before construction begins on `001-tryoff-model-service`.
- Async job architecture must reuse existing Celery/RabbitMQ infrastructure with a **separate `tryoff` queue** (not shared with VTON queue)
- Extracted garment images must be compatible with VTON pipeline input format (JPEG, min 768×1024 px)

### Business Constraints
- Self-hosted deployment only (no fal.ai cloud API) to keep costs predictable
- Garment type selection must map to model prompts without exposing raw prompt to the user

---

## Assumptions

| Assumption | Risk if Invalid | Mitigation |
|------------|-----------------|------------|
| GPU node can support FLUX.2-klein (24 GB VRAM) alongside FASHN | Both models can't run simultaneously on shared GPU | Schedule on separate GPU or time-share with queue |
| FLUX.2-klein-base-9B HuggingFace weights are publicly accessible for self-hosting | License restriction blocks self-host | Verify HuggingFace license before implementation |
| TryOff produces usable garment images from both editorial and flat-lay inputs | Flat-lay photos (no human) may confuse the model | A/B test both input types during validation |
| Existing Celery/RabbitMQ queue can absorb TryOff jobs without impacting VTON throughput | Queue contention degrades both pipelines | Separate queues per job type or priority lanes |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should TryOff and FASHN/VTON share the same GPU node or run on separate nodes? | Infra | — | ✅ Resolved: Separate dedicated GPU node for TryOff |
| What is the FLUX.2-klein-base-9B HuggingFace license? Can we self-host commercially? | Carlos | ASAP | 🚫 BLOCKER — License not confirmed. Construction on 001-tryoff-model-service is blocked until resolved. |
| Should the TryOff job queue be separate from the VTON queue or share it with lower priority? | Arch | — | ✅ Resolved: Separate Celery queue named `tryoff` |
