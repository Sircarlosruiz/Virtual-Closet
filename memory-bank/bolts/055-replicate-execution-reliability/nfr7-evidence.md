---
bolt: 055-replicate-execution-reliability
updated: 2026-09-20T18:12:00Z
---

# NFR-7 / NFR-4 evidence (bolt 055)

## Characterization (always-on tests)

Executed as part of Stage 4. These do **not** call Replicate.

| Check | Result | Where |
|-------|--------|--------|
| Replicate payload `{prediction_id, predict_time}` → `reported` + model | pass | `test_replicate_usage_accounting.py` |
| Nested `metrics.predict_time` + `id` alias | pass | same |
| OpenAI tokens on a Replicate job stay `unknown` | pass | same |
| Replicate metrics on an OpenAI job stay `unknown` | pass | same |
| OpenAI token whitelist unchanged | pass | same + `test_image_generation_reliability.py` |
| Missing Replicate fields omitted, never `0` | pass | same |
| Worker persists `provider_invocation.usage_status=reported` from sidecar | pass | `test_replicate_execution_reliability.py` |
| GET job usage is `{status, model, call_count}` — no cost / `usage_raw` | pass | `test_image_generation_reliability.py` |
| Slug `blusa-manga-globo-estampada-verano` (`len=34>30`) accepted at photoshoot POST | pass | `test_photoshoot_submission.py` |
| Same slug: `evaluate_fit` and render share canvas; blocked path reports measured dimensions | pass | `test_sku_renderer.py` |
| Overlay `blocked` does not increment `failed_results`; base remains a candidate | pass (054) | `test_photoshoot_view.py` |
| Blocked composition version has `rendered_key=null` + `fit_result` | pass (046) | `test_sku_composition_service.py` |
| `SKU_MAX_LENGTH+1` → 422 `OVERLAY_TEXT_TOO_LONG` | pass (053) | `test_photoshoot_submission.py` |

## Live Replicate (bolt-close criterion)

Requires `REPLICATE_API_KEY` and an explicit local run. CI skips this; mocks do **not** close NFR-4 / NFR-7.

Target sample (to fill when live is available):

| # | input_kind | cloth | slug | overlay | invocation usage |
|---|------------|-------|------|---------|------------------|
| 1 | garment_on_model | upper | (real BFashion, note length) | valid / blocked + reason | reported / unknown |
| 2 | garment_on_model | lower | | | |
| 3 | flat_garment | dress | | | |
| 4 | flat_garment | upper | **must include one slug with len>30** | | |

**Minimum to close the bolt:** ≥1 real `provider_invocation` with `usage_status=reported` and identified model; ≥1 slug `len>30` with `valid` complete text **or** `blocked` + measured `fit_result`.

Live capture: **not yet attached.** Stage 5 ran characterization only (117 passed, 88 % cov). Bolt-close still needs a live Replicate sample.

## OQ-1

Not escalated from characterization: long slugs can fit with a modest font on a large canvas and block with a tight `max_width`. Escalation happens only if the **majority of the live NFR-7 sample** is `blocked` with default placement/style/`ImageFont.load_default`. Compositor semantics were not changed in this bolt (ADR-054).
