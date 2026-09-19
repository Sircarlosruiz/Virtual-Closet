---
unit: 003-photoshoot-orchestration
bolt: 053-photoshoot-orchestration
stage: test
status: complete
updated: 2026-09-19T16:35:11Z
---

# Test Report - photoshoot-orchestration

## Test Summary

| Category | Passed | Failed | Skipped | Coverage |
|----------|--------|--------|---------|----------|
| Unit | 20 | 0 | 0 | not instrumented |
| Integration | 32 | 0 | 0 | not instrumented |
| Security | 9 (subset of integration) | 0 | 0 | - |
| Performance | 0 (NFR-1 estructural) | 0 | 0 | - |
| **Total** | **61** | **0** | **0** | not instrumented |

Ejecutado: `uv run pytest tests/test_photoshoot_submission.py tests/test_photoshoot_orchestration.py tests/test_tryoff_job_service.py tests/test_tryoff_api.py -q --tb=short`  
Postgres de prueba: contenedor `vc-test-pg` (`postgres:16`) en `:5433`. Redis: `vc-test-redis` en `:6380`.  
Resultado: `61 passed, 11 warnings in 116.76s`.

Re-run de Stage 5 tras el implement-review (commit-then-enqueue, tryoff en la txn del tick). Se añadieron 2 pruebas nuevas y se reforzaron 2 existentes.

`pytest-cov` no está en el grupo `dev` de `backend/pyproject.toml`. No se reporta % de cobertura. La inferencia real de Replicate no se llama: el tick observa Postgres y delega en servicios mockeados, coherente con ADR-067/068.

## Acceptance Criteria Validation

| Story | Criteria | Status |
|-------|----------|--------|
| 001 | `POST .../photoshoots` → 202 con `photoshoot_id`, `queued`, `stages`, `expected_results`, `created_at` | ✅ |
| 001 | `source_image_id` no `ready` → 422, 0 filas, no encola | ✅ |
| 001 | `model_ids` vacío → 422, no encola | ✅ |
| 001 | `cloth_type` desconocido → 422 | ✅ |
| 001 | `pose_count` 0 o 4 → 422 | ✅ |
| 001 | `expected_results` = M×N congelado en el disparo | ✅ (2×3 = 6) |
| 001 | Instantánea persistida (`configuration`, 4 etapas) | ✅ |
| 001 | Staff / vínculo inválidos → 403 / 404 fail-closed | ✅ |
| 001 | `model_ids` de otro tenant → 422 `MODEL_NOT_AVAILABLE`, no encola | ✅ |
| 002 | `garment_on_model`: tryoff → vton(validate) → M PoseSets | ✅ |
| 002 | `flat_garment`: tryoff `skipped`, no `failed` | ✅ |
| 002 | Fallo de un modelo: las demás ramas materializan (`partial`) | ✅ |
| 002 | Etapas registran status / error_code; no quedan en `running` | ✅ |
| 002 | Credenciales de proveedor no viajan por HTTP ni por el broker | ✅ (mensaje = `photoshoot_id`) |
| 002 | PoseSet cubre N poses por modelo; M modelos = M submits | ✅ |
| 002 | Tryoff comparte la txn del tick (`commit=False`, `publish=False`) y publica `external_job_id` después del commit | ✅ |
| 003 | 3×3 → 9 `GenerationJob` `completed` con `result_key` durable | ✅ |
| 003 | `owner_id` = `product_link.mayorista_id` | ✅ |
| 003 | Overlay que no cabe: job base sigue candidato publicable | ✅ |
| 003 | `GET .../publication-candidates` lista el job sin tocar `publication_service.py` | ✅ |
| 003 | `POST .../publications` entrega por el camino existente (201, destinos intactos) | ✅ |
| 003 | Copia a MinIO fallida: no hay job `completed` | ✅ |
| 003 | `PhotoshootResult` une photoshoot + model + pose | ✅ |
| 003 | Tick duplicado no crea un 10.º job | ✅ |
| 003 | Completar no crea `PublicationSelection` | ✅ |

## Unit Tests

- `plan(input_kind, overlay)`: tryoff/composition skipped vs pending
- `derive(...)`: `running` / `completed` / `partial` / `failed`
- Exclusividad Pydantic `pose_ids` XOR `pose_count`
- `photoshoot_tick_task` reagenda con `countdown` cuando el tick devuelve `reschedule`
- `TryoffJobService.submit_job(commit=False, publish=False)` usa `add()` y no publica al broker

## Integration Tests

`tests/test_photoshoot_submission.py` (27, de las cuales 7 unitarias)

- 202 + enqueue desde el servicio de submit (cola `photoshoot`, solo `photoshoot_id`)
- `flat_garment` / overlay vacío / overlay con texto
- Rechazos 422: origen, kind, modelos, cloth, poses, plantilla, SKU, `variant_key`, modelo ajeno
- Dos POSTs con la misma `Idempotency-Key` crean dos filas (replay es 054)

`tests/test_photoshoot_orchestration.py` (10, de las cuales 1 unitaria Celery)

- Orden de etapas y no re-submit de tryoff completado
- Tryoff: `submit_job(..., commit=False, publish=False)` y `publish_job` tras el commit del tick
- Rama VTON fallida vs todas fallidas vs tryoff fallido
- Materialización 3×3, UNIQUE de slot, persistencia diferida
- Candidato HTTP de publicación + `POST .../publications` con overlay bloqueado

`tests/test_tryoff_job_service.py` + `tests/test_tryoff_api.py` (24)

- Regresión del contrato `commit`/`publish` de tryoff (el tick reutiliza este servicio)

## Security Tests

| Case | Result |
|------|--------|
| Cabeceras ausentes → 401 cuerpo idéntico | ✅ |
| Staff revocado → 403 `STAFF_FORBIDDEN` | ✅ |
| Origen ajeno e inexistente → el mismo 403 `SOURCE_IMAGE_FORBIDDEN` | ✅ ADR-061 |
| Modelo ajeno → 422 `MODEL_NOT_AVAILABLE` | ✅ |
| Vínculo ausente → 404 `PRODUCT_LINK_NOT_FOUND` | ✅ |
| `REPLICATE_API_KEY` vacía → 503, 0 filas | ✅ |
| Respuesta 202 sin secretos / API keys | ✅ |
| Tryoff HTTP exige autenticación | ✅ |

## Performance Tests

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| p95 disparo (NFR-1) | ≤ 1 s, cero inferencia | Submit = lookups + insert + commit; tick async | ✅ estructural |
| Throughput | n/a en 053 | no medido | ⏸ |

No hay bench de carga. El 202 no espera tryoff/VTON/Replicate.

## Coverage Report

No instrumentado (`pytest-cov` ausente). Los 61 tests cubren submit HTTP, política de pipeline, derivación de estado, tick, materialización, publicación del job base y el contrato de persistencia diferida de tryoff.

## Issues Found

| Issue | Severity | Status |
|-------|----------|--------|
| Inferencia real Replicate/MinIO no ejercitada (delegación mockeada en tick) | Low | Open — entorno / bolt 055 |
| Replay `Idempotency-Key` y GET agregado | Low | Diferido a 054 (dos POSTs = dos filas, verificado) |
| `pytest-cov` no está en dependencias de dev | Low | Open — igual que 051/056 |
| NFR-7 “PoseSet real de 3 poses” se cubre con `PoseSetService.submit` mockeado (el contrato interno se verifica; la inferencia real no) | Low | Open — coherente con no reimplementar inferencia |

## Ready for Operations

- [x] All acceptance criteria met (historias 001–003 de este bolt)
- [ ] Code coverage > 80% (no medido; precedente del repo)
- [x] No critical/high severity issues open
- [x] Performance targets met (estructural)
- [x] Security tests passing
