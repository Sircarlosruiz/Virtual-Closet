---
stage: implement
bolt: 013-fashn-validation
created: 2026-05-31T14:30:00Z
---

## Implementation Walkthrough: fashn-validation

### Summary

Implemented container reliability fixes and multi-subject test suite infrastructure for FASHN VTON v1.5. Added version logging to container startup, Makefile targets for clean restart and test execution, ops runbook documentation, and automated test suite script. Test execution deferred to GPU environment with owner-sourced test subjects.

### Structure Overview

Changes span three areas: (1) container reliability in `docker/fashn/main.py` and `Makefile`, (2) ops documentation in `docs/ops/`, and (3) test infrastructure in `docker/fashn/run_test_suite.py` and `docs/imgs/test-subjects/`. No changes to postprocess logic — this bolt is purely operational and validation-focused.

### Completed Work

- [x] `docker/fashn/main.py` - Added `FASHN_BUILD_TAG` version logging in lifespan startup
- [x] `Makefile` - Added `fashn-restart` target (kills orphan process on :8002, rebuilds container, verifies health)
- [x] `Makefile` - Added `fashn-test` target (mounts test subjects, runs test suite in container)
- [x] `docker/fashn/run_test_suite.py` - Automated test suite script: discovers subjects, runs /predict, saves outputs with MD5 logging
- [x] `docs/ops/fashn-container.md` - Ops runbook: restart procedure, version identification, determinism check, troubleshooting
- [x] `docs/imgs/test-subjects/test-results.md` - Test results template with evaluation criteria and sign-off
- [x] `docs/imgs/test-subjects/README.md` - Test subject requirements, directory structure, metadata format

### Key Decisions

- **`lsof -ti:8002 | xargs kill -9`**: Simplest reliable way to eliminate orphan process before rebuild. Works on Linux/macOS.
- **`FASHN_BUILD_TAG` env var**: Flexible version identification — can be git SHA, semantic version, or arbitrary tag. Defaults to `dev`.
- **Test suite as standalone script**: `run_test_suite.py` runs inside the container, calls `/predict` via HTTP, saves outputs locally. No external test framework dependency.
- **metadata.json per subject**: Structured subject metadata (cloth_type, hand_position, leg_coverage) enables automated test matrix validation.
- **Test results template**: Pre-structured markdown with evaluation criteria ensures consistent documentation across testers.

### Deviations from Plan

None. Implementation followed the plan exactly.

### Dependencies Added

- [x] `requests` - HTTP client for test suite script (already available in FASHN container)

### Developer Notes

- **Test subjects required**: Owner must source ≥3 licensed subject photos before running test suite
- **GPU environment required**: Test suite requires FASHN container with GPU access
- **Long-pants subject**: Critical for validating `fix_one_piece_legs` path — must be sourced
- **Determinism**: All tests use `FASHN_SEED=42` for reproducibility
- **Output naming**: `{subject}_{cloth_type}_{seed}.jpg` convention for easy identification
