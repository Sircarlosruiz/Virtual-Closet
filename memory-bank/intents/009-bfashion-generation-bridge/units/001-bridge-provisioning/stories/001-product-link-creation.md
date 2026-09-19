---
id: 001-product-link-creation
unit: 001-bridge-provisioning
intent: 009-bfashion-generation-bridge
status: complete
priority: must
created: 2026-09-18T10:10:00.000Z
assigned_bolt: 050-bridge-provisioning
implemented: true
---

# Story: 001-product-link-creation

## User Story

**As a** backend de BFashion actuando en nombre de un staff
**I want** crear el vínculo explícito entre un producto borrador de BFashion y su propietario en Virtual Closet, por API servidor-a-servidor
**So that** el staff pueda crear el producto desde BFashion sin que un operador ejecute `scripts/link_product.py` a mano

## Acceptance Criteria

- [ ] **Given** un `ServiceClient` válido y un `staff_id` vigente, **When** llamo a `POST /api/integration/v1/product-links` con un `external_product_id` nuevo, **Then** recibo `201` con `product_link_id`, `mayorista_id`, `tenant_id`, `is_active: true` y `created: true`
- [ ] **Given** un vínculo ya existente para ese `(system, external_product_id)`, **When** repito la creación con el mismo contenido, **Then** recibo `200` con el **mismo** `product_link_id` y `created: false`, y no se produce un `500` por violación de `uq_product_links_system_external_product`
- [ ] **Given** un `external_product_id` que ya existe pero pertenece a otro tenant, **When** intento crearlo, **Then** recibo `403` y no se modifica ninguna fila
- [ ] **Given** un cuerpo de petición que incluye `system` o `tenant_id`, **When** se procesa, **Then** esos valores se ignoran y se toman del `ServiceClient` autenticado
- [ ] **Given** un `staff_id` desconocido, sin rol en `{admin, owner, staff}`, de otro tenant o revocado, **When** intento crear el vínculo, **Then** recibo `403` y no se crea nada
- [ ] **Given** cabeceras de servicio ausentes o inválidas, **When** llamo al endpoint, **Then** recibo `401` sin revelar si el producto existe
- [ ] **Given** un `prenda_id` que pertenece a otro mayorista, **When** lo envío, **Then** recibo `403` y no se crea el vínculo

## Technical Notes

- Extender `ProductLinkService` con una operación de creación idempotente. Hoy solo resuelve (`resolve_active_link`, `resolve_owned_link`).
- El `mayorista_id` se resuelve desde la identidad de staff espejo y el tenant del `ServiceClient`. Nunca se deduce de un SKU ni de ningún identificador externo: ese es el invariante que `models/product_link.py` documenta explícitamente.
- La idempotencia se apoya en la restricción única existente; capturar la colisión y devolver la fila existente en lugar de dejar escapar el error de integridad.
- `created_by` se rellena con el `staff_id` autorizado, para trazabilidad.
- No tocar `GET /api/product-links/lookup` ni `scripts/link_product.py`.

## Dependencies

### Requires
- `002-staff-identity-provisioning` (el `staff_id` asertado tiene que poder existir)

### Enables
- `001-source-image-presign`
- `001-photoshoot-submission`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Dos peticiones concurrentes con el mismo `external_product_id` | Una crea, la otra devuelve la existente con `created: false`. Ninguna produce `500` |
| Vínculo existente pero `is_active: false` | `409` con motivo explícito; reactivar es una operación distinta, no un efecto colateral de crear |
| `external_wholesaler_id` distinto del registrado en el vínculo existente | `403`, coherente con `ProductLinkService.resolve_active_link` |
| `external_product_id` vacío o de más de 255 caracteres | `422` de validación |

## Out of Scope

- Reactivar un vínculo desactivado
- Modificar o borrar vínculos existentes
- Listar vínculos por el puente
