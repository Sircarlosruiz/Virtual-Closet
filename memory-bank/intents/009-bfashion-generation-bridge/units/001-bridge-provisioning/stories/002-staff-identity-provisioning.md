---
id: 002-staff-identity-provisioning
unit: 001-bridge-provisioning
intent: 009-bfashion-generation-bridge
status: complete
priority: must
created: 2026-09-18T10:12:00.000Z
assigned_bolt: 050-bridge-provisioning
implemented: true
---

# Story: 002-staff-identity-provisioning

## User Story

**As a** backend de BFashion ejecutando `manage.py link_staff_identity`
**I want** aprovisionar por API el `Mayorista` espejo que representa a un staff de BFashion y quedarme con su UUID
**So that** el `staff_id` que aserto en cada llamada del puente sea un actor que Virtual Closet reconoce, sin que nadie transcriba UUIDs a mano

## Acceptance Criteria

- [ ] **Given** un `ServiceClient` válido, **When** llamo a `POST /api/integration/v1/staff-identities` con un `external_staff_id` nuevo, `email`, `display_name` y `role`, **Then** recibo `201` con `staff_id` (UUID del `Mayorista` espejo), `external_staff_id`, `email`, `role`, `is_active: true` y `created: true`
- [ ] **Given** un `external_staff_id` ya aprovisionado, **When** repito la llamada, **Then** recibo `200` con **el mismo** `staff_id` y `created: false`, y no se crea un segundo `Mayorista` ni un segundo vínculo
- [ ] **Given** el `staff_id` devuelto, **When** lo uso como `staff_id` asertado en cualquier endpoint del puente, **Then** `integration_service._authorize_staff` lo acepta **sin que se haya modificado** `integration_service.py`
- [ ] **Given** un espejo recién creado, **When** inspecciono la fila `mayorista`, **Then** su `role` está en `{admin, owner, staff}` y su `tenant_id` es el del `ServiceClient` autenticado
- [ ] **Given** la respuesta del endpoint, **When** la leo, **Then** no contiene contraseña, hash, secreto ni ningún material de credencial
- [ ] **Given** cabeceras de servicio ausentes o inválidas, **When** llamo al endpoint, **Then** recibo `401` y no se aprovisiona nada
- [ ] **Given** un `email` que ya pertenece a un `Mayorista` real (no espejo) del mismo tenant, **When** intento aprovisionar, **Then** recibo `409` con motivo explícito y no se reutiliza esa cuenta como espejo

## Technical Notes

- Nuevo modelo `StaffIdentityLink` con unicidad `(system, external_staff_id)`, deliberadamente paralelo a `ProductLink`. La simetría es intencional: mismo patrón de unicidad, mismo `tenant_id`, mismo `is_active`.
- `external_staff_id` se almacena como texto: la PK de `django.contrib.auth.User` es entera, pero el contrato la transporta como string para no acoplarse al tipo de BFashion.
- El espejo es una fila `mayorista` sin credenciales usables: se genera un hash de contraseña aleatorio y no recuperable, y no se devuelve nada de eso.
- `system` y `tenant_id` se derivan del `ServiceClient`, nunca del cuerpo.
- Revisión Alembic obligatoria.
- Ver **OQ-5**: decidir si los espejos computan cuota mensual de mayorista. Propuesta: no.

## Dependencies

### Requires
- Ninguna (primera historia del intent)

### Enables
- `001-product-link-creation`
- `003-staff-identity-revocation`
- Todo el resto del contrato C

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Dos peticiones concurrentes con el mismo `external_staff_id` | Una crea, la otra devuelve el mismo `staff_id` con `created: false`. Nunca dos espejos |
| Reaprovisionar un `external_staff_id` previamente revocado | Devuelve el mismo `staff_id` y lo reactiva, con `created: false`. No crea un espejo nuevo |
| `role` fuera de `{admin, owner, staff}` | `422`: el espejo tiene que satisfacer `STAFF_ROLES` o no sirve para nada |
| `email` malformado | `422` de validación |
| Mismo `external_staff_id` en dos `system` distintos | Son dos vínculos distintos; la unicidad es por par |

## Out of Scope

- Login por cookie del espejo en Virtual Closet
- La tabla `StaffIntegrationIdentity` y el comando `manage.py link_staff_identity`, que construye BFashion
- Sincronización de cambios de perfil (nombre, email) desde BFashion
