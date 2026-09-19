---
unit: 002-source-image-intake
bolt: 051-source-image-intake
stage: test
status: complete
updated: 2026-09-19T02:15:00Z
---

# Test Report - source-image-intake

## Test Summary

| Category | Passed | Failed | Skipped | Coverage |
|----------|--------|--------|---------|----------|
| Unit | 0 | 0 | 0 | n/a |
| Integration | 21 | 0 | 0 | not instrumented |
| Security | 7 (subset of integration) | 0 | 0 | - |
| Performance | 1 (concurrency) | 0 | 0 | - |
| Regression (050 + contrato B) | 29 | 0 | 0 | - |
| **Total** | **50** | **0** | **0** | not instrumented |

Ejecutado: `python -m pytest tests/test_source_image_intake.py tests/test_bridge_provisioning.py tests/test_integration_bridge.py -q --tb=short`  
Postgres de prueba: contenedor `vc-test-pg` (`postgres:16`) en `:5433`. Redis: `vc-test-redis` en `:6380`.  
Resultado: `50 passed, 2 warnings in 119.15s`.

`pytest-cov` no está en el grupo `dev` de `backend/pyproject.toml`. No se reporta % de cobertura. Los 21 tests nuevos cubren los criterios de aceptación de las 3 historias que este bolt puede demostrar sin el disparo de photoshoot (053).

## Acceptance Criteria Validation

| Story | Criteria | Status |
|-------|----------|--------|
| 001 | 201 + `source_image_id`, `upload_url`, `method: PUT`, `headers`, `expires_in`, `storage_key` | ✅ |
| 001 | El `PUT` usa la URL firmada; los bytes no pasan por el backend | ✅ (URL firmada; bytes mockeados — no hay segundo camino HTTP) |
| 001 | `content_type` fuera de jpeg/png → 422 y no se firma | ✅ |
| 001 | `size_bytes` por encima del límite → 422 y no se firma | ✅ |
| 001 | `kind` distinto de `garment_on_model` / `flat_garment` → 422 | ✅ |
| 001 | Fila creada en `pending`, ligada al `product_link` y no usable para generar | ✅ |
| 001 | URL acotada a una clave y a `PUT` | ✅ (firma de `StorageService` sobre esa clave; MinIO real es despliegue) |
| 001 | Vínculo inexistente / inactivo / otro tenant → 404 y no se firma | ✅ |
| 001 | Respuesta sin credenciales de almacenamiento ni de IA | ✅ |
| 002 | Confirmación de objeto subido → 200 `ready` + `kind` + tipo + tamaño + `preview_url` | ✅ |
| 002 | `garment_on_model` registra `SourceImage` (tryoff) | ✅ |
| 002 | `flat_garment` registra `GarmentPhoto` (media) | ✅ |
| 002 | Replay de `ready` → 200 mismo id, una sola media | ✅ |
| 002 | Objeto ausente → 409, permanece `pending` | ✅ |
| 002 | Imagen `ready` aceptada por photoshoot | ⏸ diferido a `053-photoshoot-orchestration` |
| 002 | `pending` / `rejected` rechazados al disparar | ⏸ diferido a `053-photoshoot-orchestration` |
| 002 | Checksum que no coincide → `rejected`, sin media | ✅ |
| 003 | Imagen de otro `product_link` → 403 opaco (igual que inexistente) | ✅ ADR-061 |
| 003 | Cliente de otro tenant → 404, no se firma | ✅ |
| 003 | Staff revocado → 403 en presign y confirm | ✅ |
| 003 | Tipo real ≠ declarado → `rejected`, no `ready` | ✅ |
| 003 | Tamaño real > límite → `rejected` con tamaño medido | ✅ |
| 003 | Bytes no decodificables → `rejected`, sin media | ✅ |
| 003 | Confirmación de `rejected` → 409 terminal | ✅ |
| 003 | Motivo concreto, sin rutas internas ni secretos | ✅ |

## Unit Tests

No se añadieron tests de capa de servicio aislados (sin HTTP). Los invariantes de propiedad, transición y fail-closed se ejercitan por los endpoints, que es el contrato que consume el intent 020.

## Integration Tests

Archivo: `backend/tests/test_source_image_intake.py` (21)

- Presign PUT (TTL 900, clave `bridge/source-images/{product_link_id}/{source_image_id}`)
- Rechazo de declaración inválida antes de firmar (tipo, tamaño, kind)
- Confirmación `garment_on_model` → `SourceImage` y `flat_garment` → `GarmentPhoto` sobre la misma `storage_key`
- Replay de `ready` y confirmación concurrente (una media)
- Objeto ausente permanece `pending`; vacío / ilegible / tipo / checksum / oversized → `rejected`
- ADR-061: missing y foreign `source_image_id` responden el mismo 403

Regresión: `tests/test_bridge_provisioning.py` (18) + `tests/test_integration_bridge.py` (11) — 29/29.

## Security Tests

| Case | Result |
|------|--------|
| Cabeceras ausentes → 401 | ✅ |
| Staff revocado → 403 en presign y confirm | ✅ |
| Producto de otro tenant → 404 `PRODUCT_LINK_NOT_FOUND` | ✅ |
| Vínculo inactivo / inexistente → 404 | ✅ |
| `source_image_id` ausente y ajeno → mismo 403 | ✅ ADR-061 |
| `filename` con `..` no entra en la clave | ✅ |
| Cuerpo sin secretos / claves / `minioadmin` | ✅ |

## Performance Tests

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Dos confirmaciones concurrentes | 2×200, una media | 2×200, 1 `SourceImage` | ✅ |
| NFR-1 p95 ≤ 1 s | ≤ 1 s | no medido en este bolt | 🚫 igual que 050 |

`get_service_client` verifica el secreto con bcrypt en cada request. En un solo event loop de pytest eso serializa ~200 ms × N. El camino caliente de subida es el `PUT` directo a almacenamiento, no estos endpoints.

## Coverage Report

No instrumentado (`pytest-cov` ausente). Revisión manual: `SourceImageIntakeService.presign` / `confirm`, `BridgeSourceImageRepository` (add, lock, transiciones) y los dos registros `register_existing` / `register_existing_garment` tienen al menos un test.

## Issues Found

| Issue | Severity | Status |
|-------|----------|--------|
| Confirm concurrente: `get_owned` + `lock_owned` en la misma sesión dejaba `status` stale en el identity map y el segundo registro chocaba con `tryoff_source_images_minio_key_key` | High | Fixed — confirm solo hace `SELECT FOR UPDATE` y `refresh` al adquirir el lock |
| Suite combinada contra schema sucio (`pg_type_typname_nsp_index`, `mayorista` ausente) | Medium | Mitigado — `DROP SCHEMA public CASCADE` en `vc-test-pg` antes del run formal |
| NFR-1 no demostrable en el harness de un worker | Medium | Open — mismo caveat que 050 |
| AC de photoshoot (`ready` / `pending` / `rejected` al disparar) | Low | Open — pertenece a 053 |

## Ready for Operations

- [x] All acceptance criteria met (salvo photoshoot, fuera de este bolt)
- [ ] Code coverage > 80% (no medido)
- [x] No critical/high severity issues open
- [ ] Performance targets met (NFR-1 pendiente de medición multi-worker)
- [x] Security tests passing

## Notes

Aplicar `alembic upgrade head` (revisión `c9d0e1f2a3b4`) en el entorno real antes de Operations. CORS / `MINIO_PUBLIC_ENDPOINT` siguen siendo despliegue, no un segundo camino de código. El compose de Virtual Closet no se usó; 5432 lo ocupa `ecommerce-db`.
