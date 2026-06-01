---
id: 001-flux-container-setup
unit: 001-tryoff-model-service
intent: 004-tryoff-garment-extraction
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 014-tryoff-model-service
implemented: false
---

# Story: 001-flux-container-setup

## User Story

**As a** platform engineer
**I want** a Dockerized service that loads FLUX.2-klein-base-9B + virtual-tryoff-lora on startup
**So that** the backend can send garment extraction requests to a stable local inference endpoint

## Acceptance Criteria

- [ ] **Given** the container is started, **When** it finishes booting, **Then** the FLUX.2-klein-base-9B model and the virtual-tryoff-lora LoRA weights are loaded into GPU memory and fused
- [ ] **Given** the container is running, **When** a request hits POST /tryoff, **Then** it is processed using the pre-loaded fused model (no per-request weight loading)
- [ ] **Given** GPU memory is unavailable, **When** the container starts, **Then** it exits with a clear error log and does not silently fail
- [ ] **Given** the container is built, **When** weights are not present on disk, **Then** the build step downloads them from HuggingFace at image build time (not at runtime)

## Technical Notes

- Base image: NVIDIA CUDA PyTorch image (same lineage as FASHN container)
- Install: `diffusers`, `torch`, `accelerate`, `transformers`, `huggingface_hub`
- Pipeline: `Flux2KleinPipeline.from_pretrained("black-forest-labs/FLUX.2-klein-base-9B", torch_dtype=torch.bfloat16)`
- LoRA: `pipeline.load_lora_weights("fal/virtual-tryoff-lora")` then `pipeline.fuse_lora(lora_scale=1.0)`
- GPU dtype: `torch.bfloat16`
- Container restart policy: `unless-stopped` (same as FASHN)

## Dependencies

### Requires
- None (foundation story)

### Enables
- 002-tryoff-inference-api (model must be loaded before endpoint is implemented)
- 003-container-health-monitoring

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| HuggingFace Hub unavailable at build time | Build fails with descriptive error |
| VRAM < 24 GB | Container logs OOM error and exits with code 1 |
| LoRA weights corrupted | Raises RuntimeError during fuse_lora; container exits |

## Out of Scope

- Inference endpoint implementation (story 002)
- Health check endpoint (story 003)
- Multi-GPU or model parallelism
