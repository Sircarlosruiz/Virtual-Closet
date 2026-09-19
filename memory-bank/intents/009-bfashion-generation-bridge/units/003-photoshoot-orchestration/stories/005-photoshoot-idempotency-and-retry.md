---
id: 005-photoshoot-idempotency-and-retry
unit: 003-photoshoot-orchestration
intent: 009-bfashion-generation-bridge
status: draft
priority: must
created: 2026-09-18T10:38:00Z
assigned_bolt: 054-photoshoot-orchestration
implemented: false
---

# Story: 005-photoshoot-idempotency-and-retry

## User Story

**As a** backend de BFashion que puede reintentar una petición ante un timeout de red
**I want** que repetir el disparo de un photoshoot con la misma clave de idempotencia nunca duplique trabajo ni imágenes
**So that** un reintento seguro no le cueste al negocio una segunda llamada a Replicate ni una segunda imagen en la galería

## Acceptance Criteria

- [ ] **Given** un photoshoot ya creado con `Idempotency-Key: K`, **When** repito `POST .../photoshoots` con la misma `K` y el mismo contenido, **Then** recibo el **mismo** `photoshoot_id` y no se encola ni se crea nada nuevo
- [ ] **Given** un photoshoot creado con `Idempotency-Key: K`, **When** repito con la misma `K` pero contenido distinto, **Then** recibo `409`
- [ ] **Given** una entrega duplicada del mensaje Celery durante la ejecución de una etapa, **When** el worker la procesa dos veces, **Then** el lease de `ConcurrencyGuardService` impide una segunda llamada al proveedor para el mismo intento
- [ ] **Given** una selección de publicación ya sincronizada con BFashion, **When** se reintenta la entrega, **Then** se usa `Idempotency-Key = publication_selection_id` del contrato A y BFashion responde `409` (duplicado, no error) sin crear una segunda imagen
- [ ] **Given** un fallo de sincronización con BFashion tras un photoshoot completado, **When** se reintenta, **Then** el `GenerationJob` y su `result_key` ya persistidos se reutilizan, sin volver a llamar al proveedor
- [ ] **Given** dos fallos consecutivos de entrega a `bfashion` pero éxito en `virtual_closet`, **When** inspecciono los destinos, **Then** cada uno mantiene su estado independiente

## Technical Notes

- Reutilizar `IdempotencyService` y `compute_payload_fingerprint`, que ya implementan exactamente esta semántica para `GenerationJob`; aplicar el mismo patrón a `Photoshoot`.
- El lease por job de `ConcurrencyGuardService` se aplica a nivel de cada `GenerationJob` materializado, no al `Photoshoot` completo: cada llamada individual al proveedor tiene su propio lease.
- Esta historia es la que prueba explícitamente NFR-5 (durabilidad) y el contrato A sin modificarlo.

## Dependencies

### Requires
- `001-photoshoot-submission`
- `003-generation-job-materialization`

### Enables
- Ninguna (cierra junto con `004` y `006` la unidad, en el bolt `054`)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `Idempotency-Key` ausente | Se permite (no es obligatoria), pero entonces no hay protección de duplicado a nivel de disparo; se documenta como responsabilidad de BFashion enviarla |
| Reintento tras un `photoshoot` en `failed` | Con la misma clave e igual contenido, devuelve el mismo `photoshoot_id` en `failed`; no lo relanza automáticamente |
| Reintento de publicación tras que BFashion cambió de URL base | El `transfer_url` se remite fresco desde `storage_key`; no se reutiliza una URL caducada |

## Out of Scope

- Relanzar automáticamente un photoshoot fallido con nueva clave
- Deduplicación de contenido semánticamente idéntico con distinta `Idempotency-Key`
