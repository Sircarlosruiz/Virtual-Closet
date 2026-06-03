---
intent: 004-tryoff-garment-extraction
created: 2026-05-31T00:00:00Z
completed: null
status: in-progress
---

# Inception Log: 004-tryoff-garment-extraction

## Overview

**Intent**: TryOff garment extraction pipeline — extract individual garments from model photos using FLUX.2-klein Virtual Try-Off LoRA (self-hosted), save to media library, and hand off to VTON pipeline.
**Type**: green-field (new feature integrating with existing VTON pipeline)
**Created**: 2026-05-31

## Artifacts Created

| Artifact | Status | File |
|----------|--------|------|
| Requirements | ✅ | requirements.md |
| System Context | ✅ | system-context.md |
| Units | ✅ | units.md |
| Unit Brief (model-service) | ✅ | units/001-tryoff-model-service/unit-brief.md |
| Unit Brief (job-service) | ✅ | units/002-tryoff-job-service/unit-brief.md |
| Unit Brief (pipeline-ui) | ✅ | units/003-tryoff-pipeline-ui/unit-brief.md |
| Stories (001-tryoff-model-service) | ✅ | units/001-tryoff-model-service/stories/ (3 stories) |
| Stories (002-tryoff-job-service) | ✅ | units/002-tryoff-job-service/stories/ (7 stories) |
| Stories (003-tryoff-pipeline-ui) | ✅ | units/003-tryoff-pipeline-ui/stories/ (6 stories) |
| Bolt Plan | ✅ | memory-bank/bolts/014–020 (7 bolts) |

## Summary

| Metric | Count |
|--------|-------|
| Functional Requirements | 9 |
| Non-Functional Requirements | 8 (performance, scalability, security, reliability) |
| Units | 3 |
| Stories | 16 |
| Bolts Planned | 7 |

## Decision Log

| Date | Decision | Rationale | Approved |
|------|----------|-----------|----------|
| 2026-05-31 | Self-host FLUX.2-klein (no fal.ai cloud API) | Cost predictability; consistent with FASHN hosting model | Yes |
| 2026-05-31 | Extract top and bottom as separate jobs from same source image | Garments must be independent media library items for VTON compatibility | Yes |
| 2026-05-31 | Reuse Celery/RabbitMQ for async job processing | Infrastructure already exists from VTON pipeline | Yes |
| 2026-05-31 | Save extracted garments directly to media library | Seamless handoff to VTON pipeline; garments usable immediately | Yes |
| 2026-05-31 | TryOff model on dedicated separate GPU node (not shared with FASHN) | Avoids GPU memory contention; FLUX.2-klein needs ~24 GB VRAM | Yes |
| 2026-05-31 | Separate Celery queue `tryoff` (not shared with VTON queue) | Prevents queue starvation between pipelines | Yes |
| 2026-05-31 | 🚫 BLOCKER: FLUX.2-klein-base-9B commercial license NOT confirmed | HuggingFace license terms for black-forest-labs/FLUX.2-klein-base-9B must be verified before bolt 014 starts. Fallback: evaluate fal.ai cloud API or permissive-license FLUX variant. | Blocked |

## Scope Changes

| Date | Change | Reason | Impact |
|------|--------|--------|--------|
| 2026-06-03 | Added FR-9 and Story 006: extraction result full-size preview on flat background | User identified gap: status page only showed a thumbnail; no full-size preview before VTON handoff | +1 story in 003-tryoff-pipeline-ui; UI-only, no new backend endpoints |

## Units Breakdown

| Unit | Stories | Bolts | Priority |
|------|---------|-------|----------|
| 001-tryoff-model-service | 3 | 2 (014, 015) | Must |
| 002-tryoff-job-service | 7 | 3 (016, 017, 018) | Must |
| 003-tryoff-pipeline-ui | 6 | 2 (019, 020) | Must |

## Ready for Construction

**Checklist**:
- [x] Requirements documented
- [x] System context defined
- [x] Units decomposed
- [x] Stories created for all units
- [x] Bolts planned
- [x] Human review complete

**⚠️ Pre-construction action required**: Confirm `black-forest-labs/FLUX.2-klein-base-9B` commercial license on HuggingFace before starting bolt 014-tryoff-model-service. Bolt is marked `blocks: true` until resolved.

## Dependencies

- **Depends on**: `001-vton-generation-pipeline` — media library and VTON job submission must exist for handoff
- **Depends on**: FASHN container pattern — TryOff container follows same Docker/management pattern as FASHN

## Next Steps

1. Define system context and boundaries
2. Decompose into units
3. Create stories per unit
4. Plan bolts
