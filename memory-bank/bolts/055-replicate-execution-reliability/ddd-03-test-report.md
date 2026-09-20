---
unit: 004-replicate-execution-reliability
bolt: 055-replicate-execution-reliability
stage: test
status: complete
updated: 2026-09-20T18:12:00Z
---

# Test Report - replicate-execution-reliability (usage + overlay)

## Test Summary

| Category | Passed | Failed | Skipped | Coverage |
|----------|--------|--------|---------|----------|
| Unit | 60 | 0 | 0 | módulos del bolt ≥ 80 % (ver Coverage) |
| Integration | 57 | 0 | 0 | worker + photoshoot + composición contra Postgres aislado |
| Security | included above | 0 | 0 | whitelist, GET sin `usage_raw`/coste, owner-scope |
| Performance | N/A (NFR-4/NFR-7 de evidencia, no carga) | - | - | caracterización; live Replicate no adjunto |
| **Total** | **117** | **0** | **0** | **88 %** en módulos del bolt |

Suite ejecutada (`.venv` del backend, `TEST_DATABASE_URL` → `127.0.0.1:5433/virtual_closet_test`, `TEST_REDIS_URL` → `127.0.0.1:6380/15`):

```text
./.venv/bin/python -m pytest \
  tests/test_replicate_usage_accounting.py \
  tests/test_replicate_execution_reliability.py \
  tests/test_sku_renderer.py \
  tests/test_photoshoot_submission.py \
  tests/test_image_generation_reliability.py \
  tests/test_photoshoot_view.py \
  tests/test_sku_composition_service.py \
  --cov=services.usage_accounting_service \
  --cov=services.image_generation.replicate_tryon_adapter \
  --cov=services.vton.catvton_replicate_provider \
  --cov=tasks.image_generation \
  --cov-report=term-missing -q --tb=short
```

Resultado: **117 passed, 2 warnings in 190.98s**. Postgres: contenedor `vc-test-pg` (`postgres:16` en `:5433`). Redis: `vc-test-redis` en `:6380`.

CI no llama a Replicate. Los mocks **no** cierran NFR-4 / NFR-7 en vivo (ver Issues).

## Acceptance Criteria Validation

| Story | Criteria | Status |
|-------|----------|--------|
| 005-replicate-usage-accounting | Invocación real Replicate → `provider_invocation.usage_status=reported` y `model` identificado | ⏸ caracterización ✅ (`test_worker_replicate_job_records_reported_usage_from_sidecar`); live **no adjunto** |
| 005-replicate-usage-accounting | `normalize` reconoce telemetría Replicate sin tokens OpenAI | ✅ `test_should_report_replicate_usage_without_openai_tokens`, flatten `id`/`metrics` |
| 005-replicate-usage-accounting | Campo no informado → omitido / `unknown`, nunca `0` | ✅ `test_should_not_fabricate_zero_for_missing_replicate_fields` |
| 005-replicate-usage-accounting | Coste derivado, si existiera, se identifica como estimación; GET no expone coste | ✅ `test_get_job_exposes_attempt_history_and_usage` (`usage` = `{status, model, call_count}`; sin `cost` / `usage_raw`) |
| 005-replicate-usage-accounting | Job OpenAI: normalización del intent 008 no cambia | ✅ `test_should_keep_openai_token_normalization` + suite 008 |
| 006-product-slug-overlay-fit | Slug BFashion `len>30` se valida contra `SKU_MAX_LENGTH` en el disparo, no a mitad de pipeline | ✅ `test_should_accept_overlay_slug_longer_than_thirty`; `SKU_MAX_LENGTH+1` → 422 `OVERLAY_TEXT_TOO_LONG` |
| 006-product-slug-overlay-fit | Si no cabe → `CompositionVersion.status=blocked` con `fit_result` medido | ✅ `test_long_slug_blocked_reports_measured_dimensions`, `test_overlay_that_does_not_fit_is_blocked_and_not_uploaded` |
| 006-product-slug-overlay-fit | Overlay `blocked` no destruye el `GenerationJob` base como candidato | ✅ `test_should_not_count_blocked_overlay_as_failed_result` (054) |
| 006-product-slug-overlay-fit | Agregado distingue overlay bloqueado de generación fallida | ✅ `failed_results == 0` con `COMPOSITION_BLOCKED` |
| 006-product-slug-overlay-fit | Slug que cabe: medición y render compartidos (NFR-3 intent 008) | ✅ `test_evaluate_fit_and_render_share_measurement_for_long_slug` |
| 006-product-slug-overlay-fit | NFR-7: al menos un slug real `len>30` documentado (ajustado o `blocked`) | ⏸ caracterización ✅ (`blusa-manga-globo-estampada-verano`, `len=34`); live **no adjunto** |

OQ-1: no escalado. Un slug largo cabe con fuente modesta en lienzo grande y queda `blocked` con `max_width` estrecho. La semántica del compositor (ADR-054) no se cambió.

## Unit Tests

`tests/test_replicate_usage_accounting.py` (18)

- Whitelist Replicate vs OpenAI (ADR-074); flatten `prediction_id` / `metrics.predict_time`
- Sidecar del adaptador en `ProviderInvocationResult.usage` y `last_usage`
- Payload no-mapping / no-escalar → `unknown`, nunca JSON no serializable
- Hook CatVTON (`predictions.create` + `wait`) aislado del `__init__` de `services.vton` (OpenCV)
- Slug con guiones entra en `spec_hash` y cabe en `SKU_MAX_LENGTH`

`tests/test_sku_renderer.py` (8) — determinismo, fit/render del slug largo, `blocked` medido, sin importar proveedores

`tests/test_replicate_execution_reliability.py` (10 unitarios) — cableado 052, timeout, gate, cap en memoria

`tests/test_image_generation_reliability.py` (9 unitarios) — retry 008 + OpenAI `reported`/`unknown`

`tests/test_photoshoot_submission.py` / `test_photoshoot_view.py` / `test_sku_composition_service.py` — derive/plan, `COMPOSITION_BLOCKED`, `normalize_sku`

## Integration Tests

Worker `_process_job` contra Postgres `virtual_closet_test`:

- Job Replicate completa sin `OPENAI_API_KEY` (regresión 052; sidecar no-dict no rompe el flush)
- Sidecar `{prediction_id, predict_time}` → `usage_status=reported` en job e invocación
- OpenAI 008: usage, lease, 429, timeout, retry manual, GET attempts
- Photoshoot POST acepta slug `len=34`; rechaza `SKU_MAX_LENGTH+1` antes de encolar
- Composición `blocked` no sube `rendered_key`; GET no cuenta overlay bloqueado como fallo de generación

## Security Tests

| Case | Result |
|------|--------|
| Claves Replicate no reconocidas (`logs`, `input`) se descartan | ✅ |
| `raw_usage` que no es mapping (p. ej. mock) → `unknown`, no se persiste basura | ✅ |
| GET job: `usage` exacto `{status, model, call_count}`; sin `usage_raw` / `cost` / claves | ✅ |
| POST/GET photoshoot sin cabeceras S2S → 401 idéntico | ✅ |
| Staff revocado / vínculo ajeno: 403/404 opacos | ✅ |
| Gate de credencial Replicate vs OpenAI independiente | ✅ |

Logs de usage: `job_id` + `provider` + `model`; no se registra el dict crudo.

## Performance Tests

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| NFR-4 uso `reported` en invocación real | ≥ 1 `provider_invocation` live | solo worker mockeado | ⏸ |
| NFR-7 ≥ 4 photoshoots reales, un slug `len>30` | evidencia previa a entrega | caracterización local; live no adjunto | ⏸ |
| p95 HTTP | sin endpoint nuevo de escritura | GET aditivo 008 | N/A |

## Coverage Report

`pytest-cov` sobre los módulos tocados por este bolt (misma suite de 117):

| Module | Cover | Missing (aceptable) |
|--------|-------|---------------------|
| `usage_accounting_service.py` | 100 % | — |
| `replicate_tryon_adapter.py` | 90 % | lazy-import CatVTON; `ProviderTimeoutError`/`ProviderRequestError` re-raise; lectura MinIO por key |
| `catvton_replicate_provider.py` | 88 % | fallback `model_from_prediction`, `__init__` sin clave, `client.run`, variantes de URL |
| `tasks/image_generation.py` | 84 % | job ausente, Redis fail-closed, wait exhausted, sidecar `last_model`, Celery `apply_async` |
| **TOTAL** | **88 %** | > 80 % del criterio de stage |

El proveedor CatVTON se carga por ruta de archivo en el test del hook para no ejecutar `services.vton.__init__` (OpenCV/numpy en el mismo proceso).

## Issues Found

| Issue | Severity | Status |
|-------|----------|--------|
| Worker persistía `MagicMock` de `last_usage` en `usage_raw` (JSON) y rompía `test_worker_replicate_job_completes_without_openai_key` | Medium | Fixed — `normalize` exige `Mapping` + escalares JSON; sidecar solo si `dict` |
| Captura live Replicate (NFR-4 / NFR-7 / AC real de 005 y 006) | High (criterio de cierre del bolt) | Open — `nfr7-evidence.md`; CI no llama a Replicate |
| Postgres de Compose no publica `:5432`; `make test-backend` no es el camino de esta suite | Medium (entorno) | Open — tests usaron `vc-test-pg` en `:5433` |
| `pytest-cov` no está en el grupo `dev` de `backend/pyproject.toml` | Low | Open — medido con el paquete ya presente en `.venv` |

## Recommendations

- Adjuntar la muestra live de `nfr7-evidence.md` (mínimo: 1 invocación `reported` + 1 slug `len>30` valid/blocked) antes de considerar el intent cerrado en Operations.
- No cambiar política de overlay (OQ-1) salvo que esa muestra live quede mayoritariamente `blocked` con `ImageFont.load_default`.
- Añadir `pytest-cov` al grupo `dev` si se quiere cobertura en CI.

## Verification

| Command | Result |
|---------|--------|
| pytest 7 archivos 055 + regresiones 008/052/046/053/054 (Postgres `:5433`) | **117 passed** (190.98 s) |
| cobertura 4 módulos del bolt | **88 %** |

## Ready for Operations

- [x] Criterios de aceptación cubiertos en caracterización (historias 005–006)
- [ ] Criterio live NFR-4 / NFR-7 (invocación real Replicate) — abierto
- [x] Code coverage > 80%
- [x] No critical/high de código abiertos (el High restante es evidencia live, no un defecto)
- [x] Performance targets (estructurales) met
- [x] Security tests passing
