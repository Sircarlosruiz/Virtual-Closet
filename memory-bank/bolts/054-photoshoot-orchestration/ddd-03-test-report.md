---
unit: 003-photoshoot-orchestration
bolt: 054-photoshoot-orchestration
stage: test
status: complete
updated: 2026-09-19T17:19:00Z
---

# Test Report - photoshoot-orchestration (vista, idempotencia, asiento)

## Test Summary

| Category | Passed | Failed | Skipped | Coverage |
|----------|--------|--------|---------|----------|
| Unit | 14 | 0 | 0 | not instrumented |
| Integration | 43 | 0 | 0 | not instrumented |
| Security | 8 (subset of integration) | 0 | 0 | - |
| Performance | 0 (NFR-1 estructural) | 0 | 0 | - |
| **Total** | **57** | **0** | **0** | not instrumented |

Ejecutado: `uv run pytest tests/test_photoshoot_view.py tests/test_photoshoot_submission.py tests/test_photoshoot_orchestration.py tests/test_sync_delivery.py -q --tb=short`  
Postgres de prueba: `127.0.0.1:5433` / `virtual_closet_test`. Redis: `127.0.0.1:6380`.  
Resultado: `57 passed, 2 warnings in 124.60s`.

`pytest-cov` no está en el grupo `dev` de `backend/pyproject.toml`. No se reporta % de cobertura. GET no llama al proveedor; el tick de 053 sigue mockeado. El adaptador HTTP de BFashion no se golpea de verdad: `FakeBFashion` cubre destinos independientes y reintento.

## Acceptance Criteria Validation

| Story | Criteria | Status |
|-------|----------|--------|
| 004 | GET `.../photoshoots/{id}` → `status`, `stages[]`, `expected_results`, `completed_results`, `failed_results`, `results[]`, `candidates[]` | ✅ |
| 004 | `status` derivado (`queued`/`running`/`partial`/`completed`/`failed`), no una columna mantenida a mano | ✅ |
| 004 | `candidates[]` valida como `PublicationCandidateResponse` y coincide con `GET .../publication-candidates` | ✅ |
| 004 | `completed` no crea `PublicationSelection` | ✅ |
| 004 | Photoshoot inexistente o de otro producto → 404 `PHOTOSHOOT_NOT_FOUND` idéntico; producto ausente → 404 `PRODUCT_LINK_NOT_FOUND` | ✅ |
| 004 | Polling GET no encola (`send_task` no se llama) | ✅ |
| 004 | `preview_url` regenerable (`https://preview.test/...`), nunca `minio_key` | ✅ |
| 005 | Misma `Idempotency-Key` + mismo payload → mismo `photoshoot_id`, `created: false`, no re-encola | ✅ |
| 005 | Misma clave + payload distinto → 409 `IDEMPOTENCY_CONFLICT` | ✅ |
| 005 | Tick duplicado no crea un 10.º job; lease por job (052 `test_worker_skips_when_lease_already_held`) | ✅ |
| 005 | Reintento de publicación reutiliza `GenerationJob.result_key`; destinos `virtual_closet`/`bfashion` independientes | ✅ |
| 005 | Contrato A: `Idempotency-Key = publication_selection_id`; HTTP 409 del ingest no crea segunda imagen (`HttpBFashionSyncAdapter` + `test_sync_delivery`) | ✅ |
| 005 | Sin cabecera: dos POSTs crean dos photoshoots | ✅ |
| 005 | Replay de un photoshoot `failed` no lo relanza | ✅ |
| 006 | `Photoshoot.variant_key` nullable; V1 sin clave → `null` | ✅ |
| 006 | `PhotoshootResult.variant_key` copia el del padre | ✅ |
| 006 | GET devuelve `variant_key` aunque sea `null` | ✅ |
| 006 | Dos `generation_job_id` del mismo vínculo publican sin chocar el UNIQUE de selecciones | ✅ |
| 006 | `variant_key` no vacía se persiste; V1 no filtra ni agrupa | ✅ |

## Unit Tests

`tests/test_photoshoot_view.py` (6)

- Huella estable ante el orden de claves JSON (`pose_ids` canónicos)
- `view_status`: `queued` / `running` / `partial` / `failed`
- Overlay `COMPOSITION_BLOCKED` no incrementa `failed_results`

`tests/test_photoshoot_submission.py` (7) — derivación `derive` y `plan` de 053, aún vigentes para GET

`tests/test_photoshoot_orchestration.py` (1) — reagenda Celery del tick

## Integration Tests

`tests/test_photoshoot_view.py` (9)

- GET `queued` con contadores, `variant_key: null` y sin candidatos
- GET `completed` con candidato tipado y preview firmada
- 404 opaco missing vs otro producto; 404 de vínculo ausente
- Replay 202 / 409 / no relanzar `failed`
- POST sin `Idempotency-Key` duplica filas
- Fallo BFashion no borra `result_key`; retry deja destinos independientes
- Dos jobs-variante → dos `PublicationSelection`

`tests/test_photoshoot_submission.py` (20)

- 202 + persistencia de `variant_key`
- Replay misma clave + mismo payload
- Rechazos 422/403/404/503 de 053 siguen verdes

`tests/test_photoshoot_orchestration.py` (9)

- Materialización, UNIQUE de slot, overlay bloqueado, tick duplicado

`tests/test_sync_delivery.py` (5)

- Destinos independientes, retry sin duplicar `ProductImage`/`GenerationJob`, preview desde clave durable

## Security Tests

| Case | Result |
|------|--------|
| GET sin cabeceras S2S → 401 cuerpo idéntico | ✅ |
| POST sin cabeceras S2S → 401 | ✅ |
| Photoshoot missing vs de otro producto → el mismo 404 `PHOTOSHOOT_NOT_FOUND` | ✅ ADR-061 |
| Producto ausente → 404 `PRODUCT_LINK_NOT_FOUND` | ✅ |
| Staff revocado → 403 `STAFF_FORBIDDEN` | ✅ |
| GET sin secretos / API keys / `minio_key` | ✅ |
| Preview nunca expone la clave de almacenamiento | ✅ |
| Contrato C: `X-Service-Id` / `X-Service-Secret` | ✅ |

## Performance Tests

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| p95 GET agregado (NFR-1) | ≤ 1 s, cero inferencia | Lectura Postgres + `preview_object_url` mockeada; `send_task` no se llama | ✅ estructural |
| Throughput | n/a en 054 | no medido | ⏸ |

No hay bench de carga. El GET no escribe y no dispara Replicate.

## Coverage Report

No instrumentado (`pytest-cov` ausente). Los 57 tests cubren GET agregado, UNIQUE/replay HTTP, `variant_key`, destinos de publicación y la regresión del pipeline 053.

Módulos de este bolt (no medidos numéricamente): `photoshoot_query_service`, `photoshoot_idempotency_service`, `photoshoot_status.view_status`/`counters`, índice UNIQUE en `models.photoshoot`, Alembic `f3a4b5c6d7e8`.

## Issues Found

| Issue | Severity | Status |
|-------|----------|--------|
| Inferencia real Replicate/MinIO no ejercitada | Low | Open — entorno / bolt 055 |
| `pytest-cov` no está en dependencias de dev | Low | Open — igual que 051/053/056 |
| HTTP 409 de BFashion se cubre en `HttpBFashionSyncAdapter`; `FakeBFashion` simula upsert, no el status code | Low | Open — contrato A ya mapea 409 a éxito |
| NFR-1 p95 no medido con carga | Low | Open — precedente estructural de 053 |

## Ready for Operations

- [x] All acceptance criteria met (historias 004–006 de este bolt)
- [ ] Code coverage > 80% (no medido; precedente del repo)
- [x] No critical/high severity issues open
- [x] Performance targets met (estructural)
- [x] Security tests passing
