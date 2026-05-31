---
intent: 003-fashn-provider-upgrade
phase: inception
status: units-defined
updated: 2026-05-31T00:00:00Z
---

# Units: 003-fashn-provider-upgrade

## Unit Decomposition

This intent touches only the FASHN Docker service (`docker/fashn/`). There is no new frontend or API surface. Units are split by concern: code quality changes vs. deployment and validation.

| Unit | Purpose | FRs | Bolt Type | Stories |
|------|---------|-----|-----------|---------|
| 001-fashn-postprocess | Tune postprocess.py and main.py for hand compositing + leg repair | FR-1, FR-2, FR-5, FR-6 | simple-construction-bolt | 4 |
| 002-fashn-validation | Deployment reliability and multi-subject test suite | FR-3, FR-4 | simple-construction-bolt | 2 |

## Requirement-to-Unit Mapping

- **FR-1** Hand compositing artifact elimination → `001-fashn-postprocess`
- **FR-2** Long-pants branch validation and threshold tuning → `001-fashn-postprocess`
- **FR-3** Deployment reliability — no stale container → `002-fashn-validation`
- **FR-4** Multi-subject test suite → `002-fashn-validation`
- **FR-5** segmentation_free A/B for one-pieces → `001-fashn-postprocess`
- **FR-6** Full-resolution model image evaluation → `001-fashn-postprocess`

## Dependency Graph

```
001-fashn-postprocess ──► 012-fashn-postprocess (A/B bolt)
         │
         └──────────────► 013-fashn-validation
                              │
                          002-fashn-validation
```

Unit 002 (deployment + test suite) depends on unit 001 code fixes being in place before the multi-subject runs are meaningful.
