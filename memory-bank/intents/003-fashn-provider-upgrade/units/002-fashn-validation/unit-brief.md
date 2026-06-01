---
unit: 002-fashn-validation
intent: 003-fashn-provider-upgrade
phase: inception
status: complete
unit_type: backend
default_bolt_type: simple-construction-bolt
created: 2026-05-31T00:00:00.000Z
updated: 2026-05-31T00:00:00.000Z
---

# Unit Brief: fashn-validation

## Purpose

Ensure the FASHN inference container always serves the latest built code (no stale orphan process), and build a multi-subject test suite (≥3 real subjects) that validates the postprocess fixes across diverse poses, garment types, and body types.

## Scope

### In Scope
- Docker ops: identify and eliminate the orphan FASHN process on :8002 that survives rebuilds
- Verify `docker compose up --build fashn` always routes requests to the new container
- Document kill/restart procedure for ops runbook
- Add startup version log line to FASHN container for unambiguous code-version identification
- Source ≥2 additional test subject photos (beyond María)
- Run each subject through the full pipeline with ≥1 garment
- Document pass/fail per artifact type (hand boundary, leg quality) in a test-results file committed to the repo
- Update `story-index.md` with test coverage status

### Out of Scope
- Code changes to `postprocess.py` or `main.py` (→ unit 001)
- Changes to the Celery worker or job pipeline
- Changes to the web UI or API contract

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-3 | Deployment reliability: no stale container after rebuild; version logging | Must |
| FR-4 | Multi-subject test suite: ≥3 subjects, diverse poses/garments, documented results | Must |

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| Test subject | A real person photo used for VTON validation | Name, body type, pose description, hand position, leg coverage |
| Test garment | Garment image used in test run | cloth_type, garment_photo_type (flat-lay/model), name |
| Test run | One /predict call: subject × garment | Input MD5s, output MD5, FASHN_SEED, observed artifacts |
| Test result | Pass/fail per artifact type for a test run | hand_boundary: pass/fail, leg_quality: pass/fail, regressions: none |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| Container rebuild validation | Rebuild + verify new code served | `docker compose up --build fashn` | MD5 change confirmation |
| Subject onboarding | Add photo to test set | Real photo, licensing confirmed | File in test directory |
| Test run execution | Call /predict, save output | Subject + garment images, seed | Output JPEG + log line |
| Result documentation | Record pass/fail per artifact | Output JPEG, visual inspection | test-results.md entry |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 2 |
| Must Have | 2 |
| Should Have | 0 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-container-deployment-reliability | Fix stale container; add version logging | Must | Planned |
| 002-multi-subject-test-suite | Source ≥3 subjects; run and document test suite | Must | Planned |

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| 001-fashn-postprocess | Test suite results are only meaningful after hand + leg fixes are in place |

### Depended By
| Unit | Reason |
|------|--------|
| None | Final validation unit — enables production deployment |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| Docker Compose | Container rebuild and networking | Low |
| Test subject photos | Real licensed photos for test set | Medium — sourcing is owner decision |

---

## Technical Context

### Suggested Technology
- Docker Compose (`docker compose up --build fashn`)
- `curl` or direct HTTP for `/predict` validation calls
- Makefile target or shell script for reproducible test runs

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| FASHN container | HTTP | POST /predict, GET /health |
| docker-compose.yml | Config | Port mapping, volume mounts |

---

## Constraints

- Test subject photos must be owned or licensed — no scraped images
- Test results file must be committed to the repo (not local-only)
- Container fix must not require changes to `postprocess.py` or `main.py`

---

## Success Criteria

### Functional
- [ ] After `docker compose up --build fashn`, requests route to the new container (confirmed by version log or MD5 change)
- [ ] No process outside compose network binds :8002
- [ ] ≥3 distinct subjects with photos in repo, each tested against ≥1 garment
- [ ] test-results.md committed with pass/fail per artifact type per subject
- [ ] All subjects pass FR-1 and FR-2 checks from unit 001

### Non-Functional
- [ ] Kill/restart procedure documented in ops runbook
- [ ] Test suite reproducible via Makefile or shell script (not ad-hoc curl)

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 013-fashn-validation | simple-construction-bolt | 001, 002 | Deployment fix + test suite (after 011 completes) |

---

## Notes

- The orphan process on :8002 was identified when v3 output appeared after rebuilding to v4 — the stale process was binding the port before the new container started
- Determinism (`FASHN_SEED=42`) means identical inputs produce identical outputs — MD5 comparison is reliable for confirming code version change
