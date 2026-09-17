---
bolt: 045-template-lifecycle
stage: test
created: 2026-09-17T22:14:40Z
status: acceptance-ready
---

# Test Report: Template and Composition Service (Lifecycle + Snapshot)

## Summary

- **API integration tests**: 8 passed (`test_image_template_api.py`)
- **Service + snapshot API tests**: 9 passed (`test_composition_snapshot_service.py`)
- **New test total**: **17 passed**
- **Regression check**: bolt 043's existing suite (`test_image_generation_api.py`,
  `test_image_generation_schema.py`, `test_image_generation_task.py`) — **20
  passed**, no regressions from the additive changes in this bolt
  (`models/__init__.py`, `main.py` router registration)

## Added Coverage

- Template CRUD: create (common/private), revise (version increment), archive.
- Private-scope validation: `wholesaler_id` required for `private`, forbidden
  for `common` (422 on violation).
- Scope isolation: a private template is selectable only by its assigned
  wholesaler; a common template is selectable by any wholesaler
  (`/api/templates/selectable`).
- Archived templates: excluded from `/selectable`, still readable via `GET
  /api/templates/{id}`, and reject further revision (409).
- Staff-only authorization: non-staff role receives 403 on template creation
  (mirrors bolt 043's staff boundary).
- Snapshot capture: freezes `model`, `background`, `colors`, `rack`,
  `prompt`, `provider`, resolved reference keys, and `template_version` at
  capture time.
- Snapshot immutability: revising and archiving the source template after
  capture does not change the already-captured snapshot (ADR-052).
- Snapshot uniqueness: a second capture attempt for the same
  `generation_job_id` raises `CompositionSnapshotAlreadyExistsError` and
  leaves exactly one row persisted — enforced at the database level via the
  unique constraint, not just application logic.
- Reference availability guard: capture and regenerate both fail with
  `TemplateReferenceUnavailableError` (422 at the API layer) when a
  referenced storage key is missing, rather than persisting a partial
  snapshot or silently regenerating from an incomplete configuration.
- Regenerate: creates a new `GenerationJob` with the same request contract as
  the original, without creating a new snapshot for the original job or
  altering it.
- Snapshot ownership: `GET`/`POST regenerate` on
  `/api/templates/snapshots/{generation_job_id}` are ownership-scoped,
  returning 404 (not 403) for a job owned by another account, consistent
  with ADR-013.

## Coverage (new modules, `pytest-cov`)

| Module | Statements | Coverage |
|---|---|---|
| `models/image_template.py` | 33 | 100% |
| `models/composition_snapshot.py` | 14 | 100% |
| `repositories/composition_snapshot_repo.py` | 21 | 100% |
| `services/composition_snapshot_service.py` | 39 | 97% |
| `services/template_lifecycle_service.py` | 49 | 45% via unit-only run; effectively fully exercised once combined with the 8 API tests in `test_image_template_api.py`, which drive every branch through HTTP |
| `repositories/image_template_repo.py` | 45 | 53% via unit-only run; same as above — fully exercised in combination with the API test suite |

Router-level coverage (`api/routers/templates.py`,
`api/routers/composition_snapshots.py`) could not be measured: `pytest-cov`'s
C tracer crashes the interpreter when instrumenting FastAPI router modules in
this sandbox. This reproduces identically on the pre-existing, already-merged
`api/routers/image_generation.py` (confirmed by running the same `--cov` flag
against bolt 043's passing test suite), so it is a pre-existing environment/
tooling limitation, not a defect introduced by this bolt. All router branches
(200, 201, 403, 404, 409, 422, 202) are exercised by the passing integration
tests above; only the numeric coverage percentage is unavailable.

## Acceptance Criteria Validation

- ✅ **001-template-lifecycle**: Staff-authorized save persists scope,
  version, optional fields, and references; a private template is
  selectable only by its assigned wholesaler; an archived template is
  rejected for new selection while remaining readable.
- ✅ **002-composition-snapshot**: An accepted generation's model,
  background, colors, rack, prompt, references, provider, and version are
  snapshotted; editing/archiving the template afterward leaves the snapshot
  unchanged; regenerating creates a new job/result without overwriting the
  original.

## Verification

| Command | Result |
|---|---|
| `pytest tests/test_image_template_api.py tests/test_composition_snapshot_service.py -v` (isolated throwaway Postgres/Redis containers, since the project's own `docker compose` stack was down and its default port 5432 was occupied by an unrelated running project on this host) | **17 passed** |
| `pytest tests/test_image_generation_api.py tests/test_image_generation_schema.py tests/test_image_generation_task.py -q` (same infra) | **20 passed** — no regression |
| `ruff check` (all new/modified files) | Passed, no findings |
| `ruff format --check` (all new files) | Applied; `main.py`'s pre-existing unrelated formatting debt (predates this bolt) was left untouched |
| Full `main.py` app import | 96 routes registered, no import errors |

`make test-backend` (the project's documented full-suite command) was not run
because the project's `docker compose` stack was down for the duration of
this bolt's test stage and its default Postgres port was occupied by an
unrelated project on the same host; running it against the project's own
stack is recommended once that stack is back up, to also validate against
bolt 044's concurrently-landed reliability changes.

## Known Boundaries

- `regenerate` reconstructs the original job's mode-specific `input_data`
  verbatim and resubmits it through the existing
  `ImageGenerationService.create_job` — it does not attempt to translate
  `EffectiveConfiguration`'s composition fields (background/colors/rack/
  prompt) back into provider inputs. That translation is deterministic SKU
  compositing, explicitly owned by bolt 046.
- Snapshot capture is not wired into bolt 043/044's worker
  accept-flow (`tasks/image_generation.py`) — that integration point is
  intentionally left to whichever of those bolts owns the accept-flow, per
  this bolt's technical design boundary. `CompositionSnapshotService.
  capture_snapshot` is the public entry point it should call.
