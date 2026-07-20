---
unit: 003-multi-pose-vton-generation-ui
intent: 006-multi-pose-vton-generation
phase: inception
status: complete
unit_type: frontend
default_bolt_type: simple-construction-bolt
created: 2026-07-17T00:00:00.000Z
updated: 2026-07-17T00:00:00.000Z
---

# Unit Brief: multi-pose-vton-generation-ui

## Purpose

React frontend for managing model poses and submitting multi-pose garment generation. Covers model/pose creation and listing, pose deselection at submission time, and a grouped pose set result view.

## Scope

### In Scope
- Model & pose management UI: create a `Model`, upload pose photos tagged front/side/back, view existing poses
- Pose-aware submission flow: select garment + model, see all of the model's poses pre-selected, allow deselection (min 1 required) before submitting
- Pose set result view: grouped display of all poses' outputs for one submission, per-pose status, retry action (calls existing batch item retry endpoint)
- Legacy single-pose models continue to render/submit through the same flow with no visible pose-selection step when only 1 pose exists

### Out of Scope
- Backend domain logic (handled by `001-model-pose-service` and `002-pose-set-service`)
- Catalog UI changes for displaying pose sets as catalog items (deferred — open question in requirements.md)
- Curated model library UI (unchanged, out of scope for this intent)

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Model creation + pose upload UI | Must |
| FR-2 | List model poses UI | Must |
| FR-3 | Pose deselection UI at submission time | Must |
| FR-6 | Pose set grouped result view UI (with retry action) | Must |

---

## Domain Concepts

### Key Entities
(Consumed via API, not owned by this unit)

| Entity | Description | Attributes |
|--------|-------------|------------|
| `Model` | Displayed in model picker and management page | `id`, `name`, poses list |
| `PoseSet` | Displayed as a grouped result card | `pose_set_id`, `status`, per-pose items |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| Model/pose management page | Create model, upload poses, view pose list | form input, file upload | calls `001-model-pose-service` API |
| Pose selection step | Render model's poses as checkboxes (pre-selected), enforce min 1 selected | model's pose list | `pose_ids[]` passed to submission |
| Submission action | Submit garment + model + cloth_type + selected poses | form state | calls `002-pose-set-service` `POST /api/pose-sets` |
| Pose set result view | Poll/display grouped per-pose status and images | `pose_set_id` | calls `002-pose-set-service` `GET /api/pose-sets/{id}`; retry calls existing `005` batch item retry endpoint |

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
| 001-model-pose-management-ui | Model & Pose Management UI | Must | Planned |
| 002-pose-selection-submission-ui | Pose Deselection & Submission UI | Must | Planned |
| 003-pose-set-result-view | Pose Set Grouped Result View | Must | Planned |

---

## Dependencies

### Depends On

| Unit | Reason |
|------|--------|
| `001-model-pose-service` | Model/pose CRUD endpoints |
| `002-pose-set-service` | Submission and grouped result endpoints |

### Depended By

None (top of the dependency chain for this intent).

### External Dependencies

| System | Purpose | Risk |
|--------|---------|------|
| Existing batch item retry endpoint (`005-batch-vton-generation`) | Retry a failed pose within a set | Low — reused as-is |

---

## Technical Context

### Suggested Technology
- React pages/components consistent with existing `003-vton-pipeline-ui` and `002-batch-vton-generation-ui` patterns
- Reuse existing polling pattern from batch progress UI (`005`) for the pose set result view

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| `001-model-pose-service` | REST API | JSON/HTTPS |
| `002-pose-set-service` | REST API | JSON/HTTPS |
| `001-batch-job-service` retry endpoint (existing) | REST API | JSON/HTTPS |

### Data Storage

None — stateless frontend, relies on backend APIs.

---

## Constraints

- Must not regress the existing single-pairing VTON/batch submission UI for mayoristas without multi-pose models
- Pose selection UI must default to all poses selected, with explicit deselection required to drop one
- Minimum 1 pose must remain selected before the submit action is enabled

---

## Success Criteria

### Functional
- [ ] Mayorista can create a model and upload up to 3 poses
- [ ] Mayorista can deselect poses before submitting, with submit disabled at 0 selected
- [ ] Pose set result view shows correct per-pose status and images as they complete
- [ ] Retry action on a failed pose works via the existing retry endpoint
- [ ] Single-pose (legacy) models submit exactly as they did before this intent

### Non-Functional
- [ ] UI reflects pose set status updates without requiring a full page reload (polling, consistent with existing batch UI)

### Quality
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 031-multi-pose-vton-generation-ui | simple-construction-bolt | 001, 002 | Model/pose management + pose-aware submission flow |
| 032-multi-pose-vton-generation-ui | simple-construction-bolt | 003 | Pose set grouped result view |
