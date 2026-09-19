---
unit: 005-photoshoot-catalog
bolt: 056-photoshoot-catalog
stage: test
status: complete
updated: 2026-09-19T01:54:00Z
---

# Test Report - photoshoot-catalog

## Test Summary

| Category | Passed | Failed | Skipped | Coverage |
|----------|--------|--------|---------|----------|
| Unit | 2 | 0 | 0 | n/a |
| Integration | 13 | 0 | 0 | not instrumented |
| Security | 6 (subset of integration) | 0 | 0 | - |
| Performance | 1 (concurrency) | 0 | 0 | - |
| Regression (`test_model_pose_api`) | 20 | 0 | 0 | - |
| **Total (this bolt)** | **15** | **0** | **0** | not instrumented |

Ejecutado:

```text
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/virtual_closet_test
TEST_REDIS_URL=redis://127.0.0.1:6380/15
uv run pytest tests/test_photoshoot_catalog.py -v
```

Postgres de prueba: contenedor `vc-test-pg` (`postgres:16` en `:5433`).  
Resultado bolt: `15 passed, 2 warnings in 35.01s`.

Regresión del cambio en `ModelPhotoRepo.list_by_model`: `tests/test_model_pose_api.py` + este archivo → `35 passed`.

`pytest-cov` no está en el grupo `dev` de `backend/pyproject.toml`. No se reporta % de cobertura. Los 15 tests cubren todos los criterios de aceptación de las 2 historias.

## Acceptance Criteria Validation

| Story | Criteria | Status |
|-------|----------|--------|
| 001 | 200 con `templates[]`, `models[]`, `cloth_types[]`, sugerencias, `max_pose_count`, `catalog_version` | ✅ |
| 001 | `draft` / `archived` no aparecen | ✅ |
| 001 | Plantilla `common` siempre aparece | ✅ |
| 001 | `private` de otro mayorista no aparece | ✅ |
| 001 | `available_poses` son las fotos reales, orden `front/side/back` | ✅ |
| 001 | `cloth_types` = `{upper_body, lower_body, dress}` | ✅ |
| 001 | `max_pose_count` = 3 | ✅ |
| 001 | Sugerencias distintas de plantillas activas; `colors=null` no rompe | ✅ |
| 001 | Mayorista sin propias: `200`, `models[]` vacío, solo `common` | ✅ |
| 001 | Modelo con 0 poses: aparece con `available_poses: []` y `preview_url` null | ✅ |
| 002 | Cliente de otro tenant → 404 `PRODUCT_LINK_NOT_FOUND` sin cuerpo de catálogo | ✅ |
| 002 | Vínculo inactivo → 404 idéntico | ✅ |
| 002 | `If-None-Match` coincidente → 304 sin cuerpo y sin presign (ADR-064) | ✅ |
| 002 | Archivar plantilla activa o alta de modelo cambia `catalog_version` / ETag | ✅ |
| 002 | Cabeceras ausentes → 401; no hay `templates` en la respuesta | ✅ |
| 002 | `If-None-Match` desconocido → 200 | ✅ |
| 002 | Wholesaler mismatch → 404 | ✅ |

## Unit Tests

Archivo: `backend/tests/test_photoshoot_catalog.py`

- Hash estable ante el mismo conjunto
- Hash distinto si se retira una plantilla visible (ADR-063)
- Hash distinto si se añade una pose

## Integration Tests

Mismo archivo, contra ASGI + Postgres:

- Agregación completa, ETag débil, `Cache-Control: private, no-cache`
- Aislamiento de privadas y modelos ajenos
- Catálogo vacío de propias
- 304 / ETag stale tras archivo
- Lectura sigue disponible tras revocar staff (sin `staff_id`)
- 10 lecturas concurrentes con la misma `catalog_version`

## Security Tests

| Case | Result |
|------|--------|
| Cabeceras ausentes → 401 | ✅ |
| Vínculo ausente / inactivo / otro tenant / wholesaler mismatch → 404 idéntico | ✅ |
| Sin `minio_key`, `prompt`, secretos ni API keys en el JSON | ✅ |
| Privadas y modelos de otro mayorista omitidos | ✅ |
| Presign no se llama en 401/404/304 | ✅ |
| Staff revocado no bloquea este GET | ✅ |

## Performance Tests

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| 10 lecturas concurrentes (ASGI local) | p95 ≤ 1 s (NFR-1 prod) | max < 5 s en test local; misma versión | ✅ corrección, no p95 de prod |

La aserción cubre que el hot path no se serializa mal ni diverge el hash. No es una medición de latencia de producción.

## Coverage Report

No instrumentado. Superficie ejercida:

- `services/photoshoot_catalog_service.py` — resolve, filtro `active`, hash, sugerencias, `with_preview_urls`
- `api/routers/integration.py` — GET, `If-None-Match`, 304
- `repositories/media_repo.py` — `list_by_model_ids`

## Issues Found

| Issue | Severity | Status |
|-------|----------|--------|
| Ninguno en el contrato de este bolt | — | — |

Una corrida conjunta con 051/050 sobre la misma `virtual_closet_test` produjo `CREATE TABLE` concurrente (`pg_type_typname_nsp_index`). Es contención del fixture `create_all`, no un defecto de este código. En aislamiento, 15/15.

## Ready for Operations

- [x] All acceptance criteria met
- [ ] Code coverage > 80% (no medido; `pytest-cov` ausente)
- [x] No critical/high severity issues open
- [x] Performance targets met at the level of local correctness
- [x] Security tests passing
