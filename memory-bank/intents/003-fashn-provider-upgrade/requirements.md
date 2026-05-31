---
intent: 003-fashn-provider-upgrade
phase: inception
status: inception-complete
created: 2026-05-31T00:00:00Z
updated: 2026-05-31T00:00:00Z
---

# Requirements: FASHN Provider Upgrade

## Intent Overview

Quality validation and tuning for the FASHN v1.5 VTON integration on branch `fix/fashn_provider_upgrade` (commit ab596d4). The pipeline structure is in place — `postprocess.py` is committed and running — but two artifact types remain visible in evaluated output and two code paths (hand compositing, long-pants leg repair) need tuning and cross-subject validation. The scope also covers deployment reliability (orphan process on :8002), building a multi-subject test suite (≥3 real subjects), and a focused A/B on `segmentation_free` for one-pieces.

**Current baseline**: María + producto_1 (flat-lay lavender dress) — fashn_v4_maria.jpg (md5: c3d395d6) produced by postprocess v4.

## Business Goals

| Goal | Success Metric | Priority |
|------|----------------|----------|
| Clean hand/finger boundary in try-on output | No finger-into-fabric bleed or original-dress color under hands in test set | Must |
| Long-pants → dress conversion produces correct legs | fix_one_piece_legs passes on ≥1 long-pants subject without flat-color patches | Must |
| Correct container always serves /predict | Zero stale responses after rebuild; determinism log confirms code version | Must |
| Test suite covers diverse subjects and garment types | ≥3 real subjects × representative garments with documented before/after | Must |
| segmentation_free=False confirmed as optimal for one-pieces | A/B result documented; flag set to best value in env config | Should |

---

## Functional Requirements

### FR-1: Hand Compositing — Artifact Elimination
- **Description**: `preserve_hands_and_arms()` in `postprocess.py` restores original hands over FASHN output using a parser-derived, skin-gated mask. Current v4 output still shows (a) blurry finger edges and (b) color bleed from the original red dress under the hand region. The mask must exclude garment pixels more aggressively and the blend boundary must be tighter.
- **Acceptance Criteria**: In test output, no visible red/original-dress color under or around hands; finger edges are distinct from dress fabric; `_limb_mask_from_original()` garment exclusion covers all garment label IDs (`dress`, `skirt`, `pants`, `top`); `FASHN_PRESERVE_LIMBS=false` available as escape hatch for cases where compositing degrades output.
- **Priority**: Must

### FR-2: Long-Pants Branch — Validation and Threshold Tuning
- **Description**: `fix_one_piece_legs()` runs when `_original_wearing_long_pants()` returns True. This path has never been exercised on a real subject — thresholds (`_PANTS_AREA_RATIO=0.025`, `lum < 130`, `dist > 28`, blur kernel sizes) are empirical and unvalidated. Must be tested on a subject wearing substantial lower-body pants coverage.
- **Acceptance Criteria**: `fix_one_piece_legs()` runs on ≥1 committed long-pants test image; dark pant-block artifacts are eliminated in output; no flat-color skin patches introduced; `_PANTS_AREA_RATIO`, `lum`, and `dist` thresholds adjusted if needed and values documented with rationale in code.
- **Priority**: Must

### FR-3: Deployment Reliability — No Stale Container
- **Description**: An orphan FASHN process on port 8002 served v3 postprocess code after rebuilds, causing stale output. The deployment must guarantee the current container code always handles requests after a rebuild. Seed + code-version logging must make it unambiguous which code version produced a given output.
- **Acceptance Criteria**: After `docker compose up --build fashn`, requests to `/predict` are served by the newly built container (confirmed by MD5 change on identical inputs with a new seed, or by version log line at startup); no FASHN process outside the compose network binds :8002; documented kill/restart procedure in ops runbook.
- **Priority**: Must

### FR-4: Multi-Subject Test Suite
- **Description**: Only María has been tested. A structured test set of ≥3 real subjects must be sourced and run through the full pipeline, covering the key failure modes: (a) hands resting on/near dress area, (b) bare legs with one-piece, (c) long pants with one-piece, (d) upper-body garment. Results documented with before/after images and MD5 or visual checklist.
- **Acceptance Criteria**: ≥3 distinct subjects (different body types, skin tones, poses) with photos stored under `docs/imgs/` or a designated test directory; each subject run against ≥1 garment; output images and pass/fail per artifact type documented in a test-results file; all subjects pass FR-1 and FR-2 checks.
- **Priority**: Must

### FR-5: segmentation_free A/B for one-pieces
- **Description**: `_segmentation_free_for("overall")` currently returns `False` (garment segmentation on). This was set heuristically. An A/B test across ≥2 subjects with `segmentation_free=True` vs `False` for one-pieces must confirm which produces fewer artifacts (leg boundary, dress shape, color fidelity).
- **Acceptance Criteria**: Both values tested on ≥2 subjects; results compared on at least: dress silhouette accuracy, leg boundary, hand region; preferred value documented in env config with A/B rationale; `docker-compose.yml` or `.env.example` updated to reflect the chosen default.
- **Priority**: Should

### FR-6: Full-Resolution Model Image Evaluation
- **Description**: The Celery worker currently passes a thumbnail (`thumbnail_key`, ~400×600) to the FASHN container. Full-resolution input may improve hand and leg detail in FASHN output (more pixel-level signal for the diffusion model). This needs a controlled A/B on María.
- **Acceptance Criteria**: One test run with thumbnail vs. one with full-res on same garment; hand and leg quality compared visually and by MD5; decision documented — if full-res meaningfully improves quality, the worker is updated to use the full-res key.
- **Priority**: Could

---

## Non-Functional Requirements

### Quality
| Requirement | Metric | Target |
|-------------|--------|--------|
| Hand artifact rate | Finger-into-fabric bleed per subject | 0 in final test set |
| Leg patch artifact rate | Flat-color patches introduced by postprocess | 0 when bare legs detected |
| Long-pants repair rate | Dark artifacts remaining after fix_one_piece_legs | 0 in long-pants test |
| Regression rate | Previously passing cases broken by tuning | 0 |

### Performance
| Requirement | Metric | Target |
|-------------|--------|--------|
| Postprocess overhead (hand + conditional) | Added wall time per /predict call | < 3s |
| End-to-end job time (local GPU) | Celery task completion | < 90s |

### Maintainability
| Requirement | Standard | Notes |
|-------------|----------|-------|
| Threshold values | Named constants with inline rationale | Not magic numbers scattered in logic |
| Feature flags | FASHN_PRESERVE_LIMBS, FASHN_LEG_POSTPROCESS toggleable | Disable individual steps without code change |
| Test results | Before/after images + checklist committed | Reproducible baseline for future changes |

---

## Constraints

### Technical Constraints
- FASHN v1.5 `TryOnPipeline.__call__` does not accept a hand/limb preservation mask — post-gen compositing is the only viable approach without forking FASHN internals
- `postprocess.py` must remain backward-compatible with `cloth_type=upper` and `cloth_type=lower` (those paths return early, no leg postprocess)
- Human parser (`fashn_human_parser.FashnHumanParser`) must cover `hands`, `dress`, `skirt`, `pants`, `top`, `face`, `arms`, `torso`, `feet` label IDs — verify `FASHN_LABELS_TO_IDS` contains all of these

### Business Constraints
- Test subject photos must be owned or licensed — no scraped images
- No changes to the `/predict` or `/classify` API contract (caller interface stable)

---

## Assumptions

| Assumption | Risk if Invalid | Mitigation |
|------------|-----------------|------------|
| `FASHN_LABELS_TO_IDS` includes all label IDs used in postprocess.py | KeyError crash in production | Add guard at startup; verify label list against parser output |
| FASHN v4 output (c3d395d6) is the correct baseline for regression testing | Comparing against a stale baseline | Re-run María + producto_1 on clean container to establish canonical baseline |
| Orphan process on :8002 is gone after the container fix | Stale code still served after rebuild | Validate by checking MD5 changes after rebuild |
| Long-pants artifacts are visually similar to the dark blocks seen in earlier versions | Thresholds tuned for different artifact type | Run at least one long-pants case before finalizing thresholds |

---

## Out of Scope

- Adding a new VTON provider (Replicate, IDM-VTON, CatVTON)
- Face or hair restoration
- Background removal or studio backdrop generation
- Batch generation or multi-garment jobs
- Any changes to the Celery job pipeline or API contract (`/api/vton/generate`)
- Pre-generation hand masking (FASHN v1.5 does not support it)

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Does FashnHumanParser.predict() label map include `hands` as a distinct class (not merged with `arms`)? | Carlos | TBD | Pending |
| What's the source for the 2+ additional test subjects — existing user uploads or sourced externally? | Carlos | TBD | Pending |
| Is there a docker-compose override or makefile target to kill the orphan :8002 process? | Carlos | TBD | Pending |
