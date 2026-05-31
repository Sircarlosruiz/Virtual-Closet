---
intent: 003-fashn-provider-upgrade
created: 2026-05-31T00:00:00Z
completed: 2026-05-31T00:00:00Z
status: complete
---

# Inception Log: 003-fashn-provider-upgrade

## Overview

**Intent**: Quality upgrade for FASHN v1.5 — fix hand/finger artifacts via post-gen compositing tuning and eliminate leg skin patches via conditional postprocess.py logic. Includes deployment reliability, A/B parameter evaluation, and multi-subject test suite.
**Type**: brown-field (enhancement to existing FASHN v1.5 integration on branch `fix/fashn_provider_upgrade`)
**Created**: 2026-05-31

## Artifacts Created

| Artifact | Status | File |
|----------|--------|------|
| Requirements | ✅ | requirements.md |
| System Context | ✅ | system-context.md |
| Units | ✅ | units.md |
| Unit 001 Brief | ✅ | units/001-fashn-postprocess/unit-brief.md |
| Unit 002 Brief | ✅ | units/002-fashn-validation/unit-brief.md |
| Stories (unit 001) | ✅ | units/001-fashn-postprocess/stories/ (4 stories) |
| Stories (unit 002) | ✅ | units/002-fashn-validation/stories/ (2 stories) |
| Bolt 011 | ✅ | memory-bank/bolts/011-fashn-postprocess/bolt.md |
| Bolt 012 | ✅ | memory-bank/bolts/012-fashn-postprocess/bolt.md |
| Bolt 013 | ✅ | memory-bank/bolts/013-fashn-validation/bolt.md |

## Summary

| Metric | Count |
|--------|-------|
| Functional Requirements | 6 |
| Units | 2 |
| Stories | 6 |
| Bolts Planned | 3 |

## Units Breakdown

| Unit | Stories | Bolts | Priority |
|------|---------|-------|----------|
| 001-fashn-postprocess | 4 (2 Must, 1 Should, 1 Could) | 2 (011, 012) | Must |
| 002-fashn-validation | 2 (2 Must) | 1 (013) | Must |

## Decision Log

| Date | Decision | Rationale | Approved |
|------|----------|-----------|----------|
| 2026-05-31 | Post-gen compositing for hands (not pre-gen masking) | FASHN v1.5 API does not accept hand mask input | Yes |
| 2026-05-31 | Conditional leg correction (not removal) | Backward compat — correction still needed when pant-block artifacts appear | Yes |
| 2026-05-31 | Multi-subject test suite (≥3 subjects) | María alone insufficient to validate across poses/body types | Yes |
| 2026-05-31 | Scope includes parameter audit + model variant selection | Broader upgrade, not just bug fixes | Yes |
| 2026-05-31 | Use simple-construction-bolt for both units | No domain modeling needed — ML service tuning + validation work | Yes |
| 2026-05-31 | 2 units: postprocess (code) + validation (ops+test) | Clean separation of code changes from deployment + testing concerns | Yes |
| 2026-05-31 | 3 bolts: 011 (Must fixes), 012 (A/B), 013 (ops+validation) | Natural grouping by dependency and phase | Yes |

## Scope Changes

| Date | Change | Reason | Impact |
|------|--------|--------|--------|
| 2026-05-31 | Removed "pre-gen hand masking" from FR-1 | FASHN v1.5 does not support mask input; post-gen compositing is the correct approach | FR-1 retitled to "Hand Compositing Tuning" |
| 2026-05-31 | Added FR-3 (deployment reliability) | Orphan process on :8002 was causing stale test results — must be fixed | +1 story in unit 002 |

## Ready for Construction

**Checklist**:
- [x] Requirements documented
- [x] System context defined
- [x] Units decomposed
- [x] Stories created for all units
- [x] Bolts planned
- [x] Human review complete

## Next Steps

1. Human review at Checkpoint 3
2. After approval → begin Construction Phase
3. Start with Bolt: `011-fashn-postprocess`
4. Execute: `/specsmd-construction-agent --unit="001-fashn-postprocess" --bolt-id="011-fashn-postprocess"`

## Dependencies

- Requires: FASHN v1.5 integration (already complete — git `feat(vton): integrate FASHN VTON v1.5`, branch `fix/fashn_provider_upgrade` at ab596d4)
- Execution order: 011 → 012 → 013
- 013 requires both 011 and 012 to be complete before running multi-subject test suite
