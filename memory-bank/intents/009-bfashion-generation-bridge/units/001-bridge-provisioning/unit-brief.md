---
unit: 001-bridge-provisioning
intent: 009-bfashion-generation-bridge
phase: inception
status: complete
unit_type: backend
default_bolt_type: ddd-construction-bolt
created: 2026-09-18T09:45:00.000Z
updated: 2026-09-18T09:45:00.000Z
---

# Unit Brief: bridge-provisioning

## Purpose

Permitir que BFashion dé de alta y de baja, por API servidor-a-servidor, las dos entidades que hoy solo se crean ejecutando scripts a mano: el **vínculo explícito de producto** (`ProductLink`) y la **identidad de staff espejo** (un `Mayorista` de Virtual Closet que representa a un `django.contrib.auth.User` de BFashion).

Sin esta unidad el flujo pedido es imposible: el staff crea el producto desde BFashion, así que el vínculo tiene que poder nacer por API, y `integration_service._authorize_staff` exige un UUID de `mayorista` que hoy nadie aprovisiona automáticamente.

## Scope

### In Scope
- `POST /api/integration/v1/product-links` — creación idempotente del vínculo
- `POST /api/integration/v1/staff-identities` — aprovisionamiento idempotente del espejo
- `POST /api/integration/v1/staff-identities/{external_staff_id}:revoke` — revocación
- Nuevo modelo `StaffIdentityLink` y su revisión Alembic
- Extensión de `ProductLinkService` con creación idempotente (hoy solo resuelve)
- Verificación fail-closed en los tres endpoints

### Out of Scope
- Autenticación por cookie del espejo en Virtual Closet: el espejo no es una cuenta usable
- La tabla `StaffIntegrationIdentity` y el comando `manage.py link_staff_identity`: los construye BFashion (intent 020)
- Borrado de `Mayorista`: la revocación desactiva, nunca elimina
- Cambios en `_authorize_staff`: el espejo se crea para satisfacer la regla existente, no al revés
- `GET /api/product-links/lookup` (cookie-auth) y `scripts/link_product.py`: siguen existiendo sin cambios

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Creación de vínculo de producto por el puente | Must |
| FR-2 | Aprovisionamiento y revocación de la identidad de staff espejo | Must |
| FR-15 | Fail-closed transversal en todo el puente | Must |

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| `ProductLink` (existente) | Mapeo autorizado producto externo → propietario en Virtual Closet | `system`, `external_product_id` (unique juntos), `external_wholesaler_id`, `mayorista_id`, `prenda_id`, `tenant_id`, `is_active`, `created_by` |
| `StaffIdentityLink` (**nuevo**) | Mapeo autorizado staff externo → `Mayorista` espejo | `system`, `external_staff_id` (unique juntos), `mayorista_id`, `tenant_id`, `is_active`, `created_at`, `revoked_at` |
| `Mayorista` (existente) | Actor de Virtual Closet. El espejo es una fila con rol en `{admin, owner, staff}` | `id`, `email`, `role`, `tenant_id` |
| `ServiceClient` (existente) | Identidad del backend llamante. Aporta `system` y `tenant_id` | `id`, `system`, `secret_hash`, `tenant_id`, `is_active` |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `create_link` | Crea o devuelve el vínculo de producto | `ServiceClient`, `external_product_id`, `external_wholesaler_id?`, `staff_id`, `prenda_id?` | `ProductLink`, `created: bool` |
| `provision_staff_identity` | Crea o devuelve el espejo del staff | `ServiceClient`, `external_staff_id`, `email`, `display_name`, `role` | `StaffIdentityLink`, `mayorista_id`, `created: bool` |
| `revoke_staff_identity` | Desactiva el espejo conservando historia | `ServiceClient`, `external_staff_id` | `StaffIdentityLink` con `is_active = false` |
| `resolve_staff_identity` | Valida que un `staff_id` asertado sigue vigente | `ServiceClient`, `staff_id` | `Mayorista` o error fail-closed |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 3 |
| Must Have | 3 |
| Should Have | 0 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| `001-product-link-creation` | Crear un vínculo de producto por el puente | Must | Planned |
| `002-staff-identity-provisioning` | Aprovisionar la identidad de staff espejo | Must | Planned |
| `003-staff-identity-revocation` | Revocar la identidad de staff espejo | Must | Planned |

---

## Dependencies

### Depends On

Ninguna. Es la unidad raíz del intent.

### Depended By

| Unit | Reason |
|------|--------|
| `002-source-image-intake` | El presign se resuelve contra un `ProductLink` que debe poder crearse por API |
| `003-photoshoot-orchestration` | El disparo exige vínculo y `staff_id` vigente |
| `005-photoshoot-catalog` | La resolución de vínculo y el alcance por mayorista del catálogo dependen de lo mismo |

### External Dependencies

| System | Purpose | Risk |
|--------|---------|------|
| BFashion (intent 020) | Consume ambos endpoints desde `manage.py link_staff_identity` y desde la creación del producto borrador | Alto — contrato nuevo, desarrollo paralelo |
| PostgreSQL | Persistencia de vínculos e identidades | Bajo |

---

## Technical Context

### Suggested Technology

FastAPI + SQLAlchemy async + Alembic, siguiendo `api/routers → services → repositories → models`. El nuevo `StaffIdentityLink` se modela de forma deliberadamente paralela a `ProductLink`: misma forma de unicidad `(system, external_*_id)`, mismo `tenant_id`, mismo `is_active`. Esa simetría es intencional y hace el código predecible.

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| `get_service_client` (`core/dependencies.py:149`) | Dependencia de autenticación | Cabeceras HTTP |
| `ProductLinkService` / `ProductLinkRepository` | Servicio y repositorio existentes | Interno |
| `MayoristaRepository` | Creación y consulta del espejo | Interno |
| `integration_service.STAFF_ROLES` | Contrato de autorización existente | Interno |

### Data Storage

| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| `product_links` | SQL | Una fila por producto de BFashion | Permanente |
| `staff_identity_links` | SQL | Una fila por staff de BFashion | Permanente; revocación lógica |

---

## Constraints

- `system` y `tenant_id` se derivan siempre del `ServiceClient`, jamás del cuerpo de la petición.
- La restricción única `uq_product_links_system_external_product` no puede producir un `500`: la creación repetida devuelve el vínculo existente.
- El espejo no puede convertirse en una cuenta usable: sin contraseña conocida por BFashion, sin secreto en la respuesta.
- Revocar no borra: `publication_selections.selected_by` y `product_links.created_by` conservan su referencia.
- Revisión Alembic obligatoria por el nuevo modelo.
- Ver **OQ-5**: decidir si los espejos computan cuota mensual de mayorista. Propuesta: no.

---

## Success Criteria

### Functional
- [ ] Crear dos veces el mismo `(system, external_product_id)` devuelve el mismo vínculo con `created: false`, nunca un `500`
- [ ] Un `external_product_id` de otro tenant responde `403` y no modifica nada
- [ ] Aprovisionar dos veces el mismo `external_staff_id` devuelve el **mismo** UUID con `created: false`
- [ ] El UUID devuelto es aceptado por `_authorize_staff` sin modificar `integration_service.py`
- [ ] Tras revocar, ese `staff_id` recibe `403` en el resto de endpoints del puente
- [ ] Revocar dos veces es idempotente y devuelve `200`

### Non-Functional
- [ ] p95 ≤ 1 s con 10 llamadas concurrentes (NFR-1)
- [ ] Ningún secreto en respuestas ni en registros (NFR-6)
- [ ] Credenciales de servicio inválidas o tenant inactivo: fail-closed en los tres endpoints (NFR-6)

### Quality
- [ ] Cobertura de código > 80 %
- [ ] Todos los criterios de aceptación cubiertos por pruebas
- [ ] Revisión de código aprobada

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| `050-bridge-provisioning` | ddd | 001, 002, 003 | Vínculos e identidades creables y revocables por API |

---

## Notes

El riesgo real de esta unidad no es técnico sino de contrato: los dos endpoints de `staff-identities` **no estaban** en la propuesta de contrato C del brief original. Su forma está fijada en FR-2 porque el comando `manage.py link_staff_identity` del intent 020 los va a consumir. Confirmar la forma exacta con el intent hermano antes de implementar (**OQ-2**).
