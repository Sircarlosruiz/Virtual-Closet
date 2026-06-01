---
id: 014-tryoff-model-service
unit: 001-tryoff-model-service
intent: 004-tryoff-garment-extraction
type: ddd-construction-bolt
status: complete
stories:
  - 001-flux-container-setup
  - 002-tryoff-inference-api
created: 2026-05-31T00:00:00.000Z
started: 2026-05-31T12:00:00.000Z
completed: "2026-06-01T01:27:23Z"
current_stage: null
stages_completed:
  - name: domain-model
    completed: 2026-05-31T12:15:00.000Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-05-31T12:30:00.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-05-31T12:45:00.000Z
    artifact: adr-003-build-time-weight-download.md
  - name: implement
    completed: 2026-05-31T13:00:00.000Z
    artifact: source-code
requires_bolts: []
enables_bolts:
  - 015-tryoff-model-service
  - 016-tryoff-job-service
requires_units: []
blocks: false
complexity:
  avg_complexity: 3
  avg_uncertainty: 2
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 014-tryoff-model-service

## Overview

Build and validate the self-hosted FLUX.2-klein-base-9B + virtual-tryoff-lora Docker container. Establishes the inference endpoint that the entire TryOff pipeline depends on.

## Objective

Deliver a containerized inference service that accepts a source image and garment type, runs FLUX extraction, and returns a clean white-background garment PNG — with the LoRA fused at startup for zero per-request overhead.

## Stories Included

- **001-flux-container-setup**: FLUX.2-klein container with LoRA weights loaded and fused (Must)
- **002-tryoff-inference-api**: POST /tryoff inference endpoint returning garment PNG (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Define InferenceRequest / InferenceResult entities; map garment_type → prompt
- [ ] **2. Technical Design**: Dockerfile, model loading strategy, endpoint contract, GPU memory plan
- [ ] **3. Implementation**: Container + FastAPI endpoint + LoRA fuse-on-startup
- [ ] **4. Test**: Integration test against running container; validate no human visible in output

## Dependencies

### Requires
- None (foundation bolt for this intent)

### Enables
- 015-tryoff-model-service (health monitoring)
- 016-tryoff-job-service (job service calls this container)

## Success Criteria

- [ ] Container builds successfully with FLUX.2-klein weights + virtual-tryoff-lora
- [ ] POST /tryoff returns valid PNG with no visible human body parts
- [ ] Output dimensions ≥ 768×1024 px
- [ ] Inference time p95 < 60s in local test

## Notes

- 🚫 **BLOCKED**: Do NOT start this bolt until the HuggingFace commercial license for `black-forest-labs/FLUX.2-klein-base-9B` is confirmed. Check [https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) license terms. If not commercially usable, evaluate alternatives (fal.ai cloud API, or a permissive-license FLUX variant).
- Runs on dedicated separate GPU node (not shared with FASHN)
- Follow FASHN container pattern exactly for Docker management commands
- GPU requirement: ~24 GB VRAM (document in deployment notes)
