---
unit: 001-bridge-provisioning
bolt: 050-bridge-provisioning
stage: test
status: complete
updated: 2026-09-19T01:11:10Z
---

# Test Report - bridge-provisioning

## Test Summary

| Category | Passed | Failed | Skipped | Coverage |
|----------|--------|--------|---------|----------|
| Unit | 0 | 0 | 0 | n/a |
| Integration | 18 | 0 | 0 | not instrumented |
| Security | 8 (subset of integration) | 0 | 0 | - |
| Performance | 1 (concurrency) | 0 | 0 | - |
| Regression (contrato B) | 11 | 0 | 0 | - |
| **Total** | **29** | **0** | **0** | not instrumented |

Ejecutado: `uv run python -m pytest tests/test_bridge_provisioning.py tests/test_integration_bridge.py`  
Postgres de prueba: contenedor `postgres:16` en `:5433`.  
Resultado: `29 passed, 2 warnings in 69.91s`.

`pytest-cov` no está en el grupo `dev` de `backend/pyproject.toml`. No se reporta % de cobertura. Los 18 tests nuevos cubren todos los criterios de aceptación de las 3 historias.

## Acceptance Criteria Validation

| Story | Criteria | Status |
|-------|----------|--------|
| 001 | 201 + `created: true` en alta nueva | ✅ |
| 001 | 200 + mismo `product_link_id` + `created: false` en replay | ✅ |
| 001 | 403 si el par único es de otro tenant | ✅ |
| 001 | `system` / `tenant_id` del cuerpo se ignoran | ✅ |
| 001 | 403 si `staff_id` desconocido / revocado | ✅ |
| 001 | 401 sin cabeceras de servicio | ✅ (401 test de provision; misma dependencia) |
| 001 | 403 si `prenda_id` es de otro mayorista | ✅ |
| 001 | 409 si el vínculo existente está inactivo | ✅ |
| 001 | 403 si `external_wholesaler_id` no coincide | ✅ |
| 001 | 422 si `external_product_id` vacío | ✅ |
| 002 | 201 con UUID, role ∈ STAFF_ROLES, tenant del cliente | ✅ |
| 002 | 200 + mismo UUID en reaprovisionar | ✅ |
| 002 | UUID aceptado por `_authorize_staff` (POST generation-jobs 202) | ✅ |
| 002 | Respuesta sin password / secret / hash | ✅ |
| 002 | 401 sin credenciales | ✅ |
| 002 | 409 si el email es de un mayorista real | ✅ |
| 002 | 422 si `role` fuera de set o email inválido | ✅ |
| 002 | Reactivar tras revoke: mismo UUID, `created: false` | ✅ |
| 003 | 200 `is_active: false`; segundo revoke 200 | ✅ |
| 003 | Tras revoke, `create_link` → 403 | ✅ |
| 003 | El `Mayorista` no se borra | ✅ |
| 003 | 404 al revocar desconocido o de otro tenant | ✅ |

## Unit Tests

No se añadieron tests de capa de servicio aislados (sin HTTP). La lógica de invariantes se ejercita a través de los endpoints, que es el contrato que consume el intent 020.

## Integration Tests

Archivo: `backend/tests/test_bridge_provisioning.py`

- Alta / replay de `staff-identities` y `product-links`
- Reactivación de espejo (ADR-059)
- 409 de `ProductLink` inactivo (ADR-059)
- Owner = espejo (ADR-060)
- El espejo satisface el contrato B sin editar `integration_service.py` (ADR-057)

Regresión: `tests/test_integration_bridge.py` — 11/11. El constructor de `ProductLinkService` sigue siendo compatible.

## Security Tests

| Case | Result |
|------|--------|
| Cabeceras ausentes → 401 | ✅ |
| Staff desconocido / revocado → 403 | ✅ |
| Par de producto de otro tenant → 403 | ✅ |
| Revoke cross-tenant → 404 (ADR-040) | ✅ |
| Email de mayorista real → 409 | ✅ |
| Prenda ajena → 403 | ✅ |
| Wholesaler mismatch → 403 | ✅ |
| Cuerpo sin secretos | ✅ |

## Performance Tests

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| 10 creates concurrentes correctos | 10×201, sin 500 | 10×201 | ✅ |
| NFR-1 p95 ≤ 1 s (10 concurrentes) | ≤ 1 s | ~1.95 s en ASGI de un worker | 🚫 no medido en prod |

`get_service_client` verifica el secreto con bcrypt en cada request. En un solo event loop de pytest eso serializa ~200 ms × N y rompe el p95. En producción con varios workers el objetivo sigue vigente; no se cambió la dependencia existente. El provisionamiento es peor (bcrypt del secreto **y** del hash irrecuperable del espejo) y no se usa como path caliente.

## Coverage Report

No instrumentado (`pytest-cov` ausente). Revisión manual: los caminos de `StaffIdentityService` (provision, replay, reactivate, revoke, resolve) y `ProductLinkService.create_link` (alta, replay, tenant, inactivo, wholesaler, prenda) tienen al menos un test.

## Issues Found

| Issue | Severity | Status |
|-------|----------|--------|
| `logger.info(..., extra={"created": ...})` pisa `LogRecord.created` y aborta el request | High | Fixed — clave `link_created` |
| `EmailStr` rechaza TLD reservado `.test` | Low | Tests usan `@example.com`; el contrato acepta cualquier email RFC válido |
| NFR-1 no demostrable en el harness de un worker | Medium | Open — verificar con uvicorn multi-worker antes de Operations |

## Ready for Operations

- [x] All acceptance criteria met
- [ ] Code coverage > 80% (no medido)
- [x] No critical/high severity issues open
- [ ] Performance targets met (NFR-1 pendiente de medición multi-worker)
- [x] Security tests passing

## Notes

Aplicar `alembic upgrade head` (revisión `b8c9d0e1f2a3`) en el entorno real antes de Operations. El compose de Virtual Closet no estaba levantado; 5432 lo ocupa `ecommerce-db`.
