---
id: 050-bridge-provisioning
unit: 001-bridge-provisioning
intent: 009-bfashion-generation-bridge
type: ddd-construction-bolt
status: complete
stories:
  - 001-product-link-creation
  - 002-staff-identity-provisioning
  - 003-staff-identity-revocation
created: 2026-09-18T11:00:00.000Z
started: 2026-09-19T00:36:16.000Z
completed: "2026-09-19T01:12:54Z"
current_stage: null
stages_completed:
  - name: model
    completed: 2026-09-19T00:37:52.000Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-09-19T00:39:01.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-09-19T00:40:02.000Z
    artifact: adr-057-c-contract-staff-resolution.md, adr-058-staff-identity-link-mirror-signal.md, adr-059-asymmetric-link-reactivation.md, adr-060-product-link-owner-is-mirror.md
  - name: implement
    completed: 2026-09-19T01:02:00.000Z
    artifact: backend/models/staff_identity_link.py
  - name: test
    completed: 2026-09-19T01:11:10Z
    artifact: ddd-03-test-report.md
requires_bolts: []
enables_bolts:
  - 051-source-image-intake
  - 053-photoshoot-orchestration
  - 056-photoshoot-catalog
requires_units: []
blocks: false
complexity:
  avg_complexity: 2
  avg_uncertainty: 2
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 050-bridge-provisioning

## Overview

Primer bolt del intent. Cierra el vacío de aprovisionamiento: hoy crear un `ProductLink` exige `scripts/link_product.py` a mano, y no existe ninguna forma de que BFashion aprovisione la identidad de staff espejo que `integration_service._authorize_staff` necesita.

## Objective

Que BFashion pueda, por API servidor-a-servidor: (1) crear el vínculo explícito de un producto borrador, de forma idempotente, y (2) aprovisionar y revocar el `Mayorista` espejo de cada staff, de forma idempotente y sin transcripción manual de UUIDs.

## Stories Included

- **001-product-link-creation**: Crear un vínculo de producto por el puente (Must)
- **002-staff-identity-provisioning**: Aprovisionar la identidad de staff espejo (Must)
- **003-staff-identity-revocation**: Revocar la identidad de staff espejo (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [x] **1. model**: Complete → `ddd-01-domain-model.md`
- [x] **2. design**: Complete → `ddd-02-technical-design.md`
- [x] **3. adr-analysis**: Complete → `adr-057` … `adr-060`
- [x] **4. implement**: Complete → código en `backend/models`, `backend/repositories`, `backend/services`, `backend/api`
- [x] **5. test**: Complete → `ddd-03-test-report.md`

## Dependencies

### Requires
- Ninguna. Es la unidad raíz del intent.

### Enables
- `051-source-image-intake` (el presign se resuelve contra un `ProductLink` creable por API)
- `053-photoshoot-orchestration` (el disparo exige vínculo y `staff_id` vigentes)
- `056-photoshoot-catalog` (la resolución de vínculo y el alcance por mayorista del catálogo dependen de lo mismo)

## Success Criteria

- [ ] Los tres endpoints nuevos existen y son fail-closed (`X-Service-Id`/`X-Service-Secret`)
- [ ] `POST /api/integration/v1/product-links` es idempotente por `(system, external_product_id)`
- [ ] `POST /api/integration/v1/staff-identities` es idempotente por `(system, external_staff_id)` y el UUID devuelto satisface `integration_service.STAFF_ROLES` sin modificar `integration_service.py`
- [ ] `POST /api/integration/v1/staff-identities/{external_staff_id}:revoke` desactiva sin borrar, y es idempotente
- [ ] Nuevo modelo `StaffIdentityLink` con revisión Alembic aplicada
- [ ] Todos los criterios de aceptación de las 3 historias cubiertos por pruebas
- [ ] Código revisado

## Notes

Riesgo de contrato, no técnico: los dos endpoints de `staff-identities` amplían la propuesta de partida del brief original (**OQ-2**). Confirmar la forma exacta con el intent hermano `020-ai-product-imagery-integration` antes de la etapa de diseño técnico, porque su comando `manage.py link_staff_identity` los va a consumir tal como se especifiquen aquí.
