---
unit: 001-tryoff-model-service
intent: 004-tryoff-garment-extraction
phase: inception
status: complete
created: 2026-05-31T00:00:00.000Z
updated: 2026-05-31T00:00:00.000Z
default_bolt_type: ddd-construction-bolt
---

# Unit Brief: tryoff-model-service

## Purpose

Self-hosted containerized inference service for FLUX.2-klein-base-9B + virtual-tryoff-lora. Exposes a single HTTP endpoint that accepts a source image and garment type prompt, runs inference on GPU, and returns a clean product-photography garment image. Mirrors the FASHN container management pattern.

## Scope

### In Scope
- Docker container wrapping FLUX.2-klein-base-9B + `fal/virtual-tryoff-lora` weights
- Single inference endpoint: `POST /tryoff` (image + prompt → PNG)
- GPU memory management and model weight caching
- Health check endpoint for container liveness/readiness
- Container auto-restart on crash or OOM (same pattern as FASHN)
- HuggingFace weight download at build time

### Out of Scope
- Job queuing and orchestration (owned by 002-tryoff-job-service)
- Media library storage (owned by 002-tryoff-job-service)
- UI (owned by 003-tryoff-pipeline-ui)
- Multi-job parallelism (GPU is single-threaded; queue serialization handled by job service)

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| Implied | Self-hosted FLUX.2-klein-base-9B + virtual-tryoff-lora container providing clean inference API | Must |

*Note: FR-6 from requirements.md describes the constraint; this unit implements it.*

---

## Domain Concepts

### Key Entities
| Entity | Description | Attributes |
|--------|-------------|------------|
| InferenceRequest | Input to the FLUX model | image (bytes), prompt (str), width, height, num_steps, guidance_scale |
| InferenceResult | Output from FLUX model | image (bytes/PNG), inference_time_ms |

### Key Operations
| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| POST /tryoff | Run garment extraction inference | InferenceRequest | InferenceResult (PNG) |
| GET /health | Container liveness check | None | `{"status": "ok", "model_loaded": bool}` |

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
| 001-flux-container-setup | FLUX.2-klein container with LoRA weights | Must | Planned |
| 002-tryoff-inference-api | POST /tryoff inference endpoint | Must | Planned |
| 003-container-health-monitoring | Health check + auto-restart | Must | Planned |

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| None | Foundation unit for this intent |

### Depended By
| Unit | Reason |
|------|--------|
| 002-tryoff-job-service | Calls POST /tryoff for each garment extraction job |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| HuggingFace Hub | Download FLUX.2-klein-base-9B + virtual-tryoff-lora weights at build time | Medium — license must be verified |
| NVIDIA GPU (24 GB+ VRAM) | Model inference requires dedicated GPU memory | High — infra dependency |
| FASHN container (003) | Pattern reference for Docker management commands | Low — reference only |

---

## Technical Context

### Suggested Technology
- Base model: `black-forest-labs/FLUX.2-klein-base-9B` via HuggingFace `diffusers`
- LoRA adapter: `fal/virtual-tryoff-lora`
- Inference: Python + `diffusers` library (Flux2KleinPipeline)
- Container: Docker with NVIDIA CUDA base image (~same as FASHN)
- API: FastAPI (single endpoint, matches existing backend stack)
- GPU dtype: `torch.bfloat16`

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| 002-tryoff-job-service | Inbound API caller | HTTP/REST (internal Docker network) |
| HuggingFace Hub | Outbound (build time) | HTTPS |

### Data Storage
| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| Model weights | Filesystem (Docker volume) | ~18 GB | Persistent across restarts |
| Input/output images | In-memory only (not persisted here) | Per request | Request lifetime |

---

## Constraints

- FLUX.2-klein-base-9B requires ~24 GB VRAM; cannot share GPU with FASHN container simultaneously without scheduling
- Inference is synchronous inside the container (one request at a time); concurrency is managed by the job queue
- HuggingFace commercial license for FLUX.2-klein-base-9B must be confirmed before production deployment

---

## Success Criteria

### Functional
- [ ] Container starts, loads model, and is healthy within 60 seconds of boot
- [ ] POST /tryoff with a valid image returns a white-background garment PNG
- [ ] Output garment contains no visible human body parts
- [ ] Health endpoint returns `{"status": "ok"}` when model is loaded

### Non-Functional
- [ ] Inference time p95 < 60 seconds per garment
- [ ] Container auto-restarts on crash within 30 seconds (Docker restart policy)
- [ ] GPU OOM triggers graceful error response (HTTP 503) not container crash

### Quality
- [ ] Code coverage > 70% (integration tests against running container)
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 014-tryoff-model-service | ddd-construction-bolt | 001, 002 | Container setup + inference API |
| 015-tryoff-model-service | ddd-construction-bolt | 003 | Health monitoring + lifecycle management |

---

## Notes

- Follow the FASHN container management pattern exactly for Docker commands, restart policies, and GPU device mapping
- The LoRA must be fused before serving (`pipeline.fuse_lora(lora_scale=1.0)`) to avoid per-request overhead
- Default inference params: height=1024, width=768, num_inference_steps=28, guidance_scale=5.0
- Prompt template per garment type:
  - upper: `"TRYOFF extract the upper garment over a white background, product photography style. NO HUMAN VISIBLE."`
  - lower: `"TRYOFF extract the lower garment over a white background, product photography style. NO HUMAN VISIBLE."`
  - dress: `"TRYOFF extract the dress/full-body garment over a white background, product photography style. NO HUMAN VISIBLE."`
