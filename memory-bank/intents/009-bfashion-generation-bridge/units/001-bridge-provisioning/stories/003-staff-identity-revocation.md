---
id: 003-staff-identity-revocation
unit: 001-bridge-provisioning
intent: 009-bfashion-generation-bridge
status: complete
priority: must
created: 2026-09-18T10:14:00.000Z
assigned_bolt: 050-bridge-provisioning
implemented: true
---

# Story: 003-staff-identity-revocation

## User Story

**As a** backend de BFashion
**I want** revocar por API el espejo de un staff que ya no debe operar
**So that** ese actor deje de poder generar y publicar en Virtual Closet de inmediato, sin que se pierda el rastro de lo que hizo

## Acceptance Criteria

- [ ] **Given** un espejo activo, **When** llamo a `POST /api/integration/v1/staff-identities/{external_staff_id}:revoke`, **Then** recibo `200` con `staff_id`, `external_staff_id` e `is_active: false`
- [ ] **Given** un espejo revocado, **When** uso su `staff_id` en cualquier endpoint del contrato C, **Then** recibo `403` y no se crea, genera ni publica nada
- [ ] **Given** un espejo revocado, **When** consulto las filas históricas, **Then** `publication_selections.selected_by` y `product_links.created_by` conservan su referencia y el `Mayorista` **no** ha sido eliminado
- [ ] **Given** un espejo ya revocado, **When** vuelvo a revocarlo, **Then** recibo `200` con el mismo resultado: la operación es idempotente
- [ ] **Given** un `external_staff_id` desconocido, **When** intento revocarlo, **Then** recibo `404` sin filtrar información de otros tenants
- [ ] **Given** un espejo de otro tenant, **When** intento revocarlo con mi `ServiceClient`, **Then** recibo `403`/`404` y no se modifica nada
- [ ] **Given** un photoshoot en curso disparado por ese staff antes de la revocación, **When** se revoca, **Then** el photoshoot en curso no se cancela ni se pierden sus resultados; lo que se bloquea son las **nuevas** operaciones

## Technical Notes

- La revocación es lógica: `is_active = false` y `revoked_at`. Nunca un `DELETE` de `Mayorista`, porque hay claves foráneas históricas (`publication_selections.selected_by`, `product_links.created_by`) cuya semántica es de auditoría.
- La comprobación de vigencia debe aplicarse en el punto donde el puente resuelve el `staff_id`, para que ningún endpoint del contrato C se olvide de mirarla. Conviene centralizarla junto a la autorización de staff existente en lugar de repetirla en cada router.
- Decisión explícita: revocar no cancela trabajo en vuelo. Cancelar un photoshoot es una capacidad distinta y está fuera del alcance de este intent.

## Dependencies

### Requires
- `002-staff-identity-provisioning`

### Enables
- Ninguna (cierra la unidad)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Revocar mientras hay un photoshoot en `running` | El photoshoot continúa; las nuevas operaciones de ese staff se rechazan |
| Revocar el último staff activo del tenant | Permitido: Virtual Closet no impone una regla de «al menos un staff» |
| Reaprovisionar tras revocar | Reactiva el mismo espejo con el mismo UUID (ver `002`) |
| Consulta de estado de un photoshoot antiguo con `staff_id` revocado | La consulta se autoriza por `ServiceClient` y vínculo, no por el `staff_id` histórico del disparo |

## Out of Scope

- Cancelar photoshoots en curso
- Borrado físico de espejos o de su historia
- Notificar a BFashion que un espejo fue revocado desde el otro lado
