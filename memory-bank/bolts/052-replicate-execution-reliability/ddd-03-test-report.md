---
unit: 004-replicate-execution-reliability
bolt: 052-replicate-execution-reliability
stage: test
status: complete
updated: 2026-09-19T15:50:00Z
---

# Test Report - replicate-execution-reliability

## Test Summary

| Category | Passed | Failed | Skipped | Coverage |
|----------|--------|--------|---------|----------|
| Unit | 34 | 0 | 0 | módulos nuevos ≥ 80 % (ver Coverage) |
| Integration | 24 | 0 | 0 | worker + GET contra Postgres aislado |
| Security | included above | 0 | 0 | frontera de secretos + owner-scope |
| Performance | N/A (NFR de tope, no carga) | - | - | `in_flight ≤ 2` medido en test |
| **Total** | **58** | **0** | **0** | **86 %** en módulos del bolt |

Suite ejecutada (venv del backend, `TEST_DATABASE_URL` → `127.0.0.1:15432/virtual_closet_test`):

- `tests/test_replicate_execution_reliability.py` (16)
- `tests/test_image_generation_reliability.py` (21) — regresión intent 008
- `tests/test_image_generation_api.py` (6)
- `tests/test_image_generation_schema.py` (12)
- `tests/test_image_generation_task.py` (3)

## Acceptance Criteria Validation

| Story | Criteria | Status |
|-------|----------|--------|
| 001-replicate-provider-wiring | `_get_provider("replicate")` devuelve adaptador, no `ProviderRequestError` | ✅ `test_get_provider_wires_replicate_and_openai` |
| 001-replicate-provider-wiring | `generate` reutiliza CatVTON/Replicate existentes, sin cliente HTTP nuevo | ✅ `test_replicate_adapter_reuses_inner_provider_and_rejects_missing_keys` |
| 001-replicate-provider-wiring | `provider=openai` no cambia (intent 008) | ✅ `test_get_provider_wires_replicate_and_openai` + suite 008 |
| 001-replicate-provider-wiring | proveedor desconocido → `ProviderRequestError` clasificado | ✅ `test_get_provider_rejects_unknown` |
| 001-replicate-provider-wiring | `try_on` produce bytes persistibles (adaptador + worker, inner mockeado) | ✅ `test_worker_replicate_job_completes_without_openai_key` |
| 002-provider-credential-gating | Replicate completa con `OPENAI_API_KEY` vacío | ✅ `test_worker_replicate_job_completes_without_openai_key` |
| 002-provider-credential-gating | OpenAI sin clave → fallo no reintentable, código distinto de proveedor | ✅ `test_worker_openai_job_fails_without_openai_key`, `test_credential_missing_is_not_retryable` |
| 002-provider-credential-gating | Replicate sin clave → mismo fallo explícito | ✅ `test_worker_replicate_job_fails_without_replicate_key` |
| 002-provider-credential-gating | Cada job solo mira su credencial | ✅ `test_credential_gate_checks_only_job_provider` |
| 002-provider-credential-gating | HTTP/logs no filtran valores de clave | ✅ `_assert_no_secrets_leaked` en GET; gate no incluye el valor |
| 002-provider-credential-gating | Gate **antes** de lease y de red | ✅ orquestación en `_process_job` + tests de fallo de credencial (0 llamadas al adaptador) |
| 003-global-concurrency-cap | Tope 2: nunca más de 2 llamadas simultáneas | ✅ `test_worker_cap_two_never_exceeds_in_flight`, `test_memory_redis_cap_never_exceeds_limit` |
| 003-global-concurrency-cap | Excedente encola, no falla | ✅ `test_worker_reschedules_when_global_slot_denied` |
| 003-global-concurrency-cap | Espera vs ejecución visibles por separado | ✅ `test_get_job_exposes_queue_and_execution_durations` (GET job; agregado photoshoot = bolt 053) |
| 003-global-concurrency-cap | Tope es valor de despliegue (`Field(ge=1)`) | ✅ settings `IMAGE_GENERATION_GLOBAL_CONCURRENCY` |
| 003-global-concurrency-cap | Lease por job y tope global coexisten | ✅ lease skip + slot wait en suite 008/052 |
| 004-provider-timeout-policy | Partida Replicate 900 s (10 min no corta) | ✅ `test_timeout_policy_is_independent_per_provider` (default ≥ 900) |
| 004-provider-timeout-policy | OpenAI corto e independiente de Replicate | ✅ mismo test |
| 004-provider-timeout-policy | Timeout → `ProviderTimeoutError` y job `failed` sin auto-retry | ✅ `test_replicate_adapter_times_out_as_provider_timeout`, `test_timeout_is_never_auto_retried`, `test_worker_timeout_does_not_auto_retry` |
| 004-provider-timeout-policy | 429 ≤ 2 reintentos con `Retry-After` | ✅ regresión 008: `test_transient_error_retries_up_to_two_times_honoring_retry_after` |
| 004-provider-timeout-policy | Error no transitorio no auto-reintenta | ✅ `test_terminal_error_never_retries`, `test_worker_no_result_is_terminal` |

## Unit Tests

Resolución de proveedor, gate, política de timeout, clasificación `PROVIDER_CREDENTIAL_MISSING` / wait exhausted, adaptador (claves faltantes + `wait_for` → timeout), semáforo Redis en memoria (nunca supera el cap; fail-closed si `redis=None`), registro de la task Celery, y contratos de schema/API del intent 008.

`RetryPolicyService` y `UsageAccountingService` no se reescribieron; la suite 008 sigue cubriendo 429, timeout no retry, y usage unknown-vs-reported.

## Integration Tests

Worker `_process_job` contra Postgres aislado:

- Job Replicate `try_on` completa sin `OPENAI_API_KEY`.
- Job OpenAI / Replicate sin su clave → `failed` clasificado, adaptador no llamado.
- Sin hueco global → suelta lease, reagenda (`reschedule_slot_wait`), no incrementa `retry_count`.
- Cap=2 con varios jobs concurrentes: `max_in_flight ≤ 2`.
- GET job: `queue_wait_seconds` / `execution_seconds` aditivos.
- Regresión 008: idempotencia, lease, 429, timeout, retry manual, GET attempts/usage.

## Security Tests

- GET create/detail: key-set exacto; no `api_key` / `openai_api_key` / `replicate_api_key`; valores de settings no aparecen en el JSON.
- Owner-scope del GET sin cambio.
- `CredentialMissingError` no incluye el secreto; logs usan `job_id` + nombre de proveedor.

## Performance Tests

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Llamadas simultáneas al proveedor | ≤ `IMAGE_GENERATION_GLOBAL_CONCURRENCY` (partida 2) | `max_in_flight ≤ 2` en `test_worker_cap_two_never_exceeds_in_flight` | ✅ |
| Photoshoot de 12 resultados E2E | 053 | Fuera de este bolt (orquestación) | N/A |
| p95 HTTP | sin endpoint nuevo de escritura | GET aditivo | N/A |

## Coverage Report

`pytest-cov` sobre los módulos tocados por este bolt (misma suite de 58):

| Module | Cover | Missing (aceptable) |
|--------|-------|---------------------|
| `credential_gate_service.py` | 96 % | proveedor no cableado (rama de `ProviderRequestError`) |
| `provider_timeout_policy.py` | 93 % | fallback de proveedor desconocido |
| `retry_policy_service.py` | 97 % | rama residual |
| `tasks/image_generation.py` | 87 % | job ausente, Redis fail-closed en worker, wait exhausted post-deny, Celery `apply_async` |
| `global_concurrency_service.py` | 80 % | excepción Redis en acquire/release; `get_redis()` live |
| `replicate_tryon_adapter.py` | 76 % | lazy-import CatVTON, wrap de excepciones, base64, lectura MinIO por key |
| **TOTAL** | **86 %** | > 80 % del criterio de stage |

El adaptador queda por debajo del 80 % aislado porque las ramas de I/O real (MinIO / CatVTON) se mockean a propósito (no cliente HTTP nuevo, no red a Replicate).

## Issues Found

| Issue | Severity | Status |
|-------|----------|--------|
| Aserción de secretos del GET no incluía `queue_wait_seconds` / `execution_seconds` | Low | Fixed — `test_image_generation_api.py` |
| Postgres de Compose no publica `:5432` / red vacía; `make test-backend` no alcanza la DB | Medium (entorno) | Open — tests de este bolt usaron `vc-test-pg` en `:15432` |
| `pytest-cov` no estaba en el venv | Low | Instalado localmente para medir; no se añadió a `pyproject.toml` |

## Recommendations

- Cubrir en 053 el photoshoot de 12 resultados sobre el tope global (AC de 003 a nivel agregado).
- Añadir un test de adaptador para `garment_key` / base64 si 055 necesita esa ruta en serio.
- Reparar la red/puerto de Postgres en Compose para que `make test-backend` vuelva a ser el camino canónico.

## Verification

| Command | Result |
|---------|--------|
| pytest 5 archivos image-generation + reliability 052 (Postgres `:15432`) | **58 passed** (88.41 s) |
| misma suite + `--cov` de módulos del bolt | **58 passed**, **86 %** total |
| `ruff check` archivos nuevos/cambiados | Passed |

## Ready for Operations

- [x] All acceptance criteria met (historias 001–004; 005/006 siguen en bolt 055)
- [x] Code coverage > 80 % (86 % en módulos del bolt)
- [x] No critical/high severity issues open
- [x] Performance targets met (tope global; sin carga HTTP nueva)
- [x] Security tests passing
