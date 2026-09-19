---
id: 051-source-image-intake
unit: 002-source-image-intake
intent: 009-bfashion-generation-bridge
type: ddd-construction-bolt
status: planned
stories:
  - 001-source-image-presign
  - 002-source-image-confirm
  - 003-source-image-rejection
created: 2026-09-18T11:05:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts: [050-bridge-provisioning]
enables_bolts: [053-photoshoot-orchestration]
requires_units: [001-bridge-provisioning]
blocks: true

complexity:
  avg_complexity: 2
  avg_uncertainty: 2
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 051-source-image-intake

## Overview

Cierra G1, el hueco central del intent: hoy no existe ningún camino para que BFashion entregue bytes a Virtual Closet. Este bolt entrega el camino de subida servidor-a-servidor completo: presign, confirmación, y verificación fail-closed, sin que los bytes atraviesen ningún backend.

## Objective

Que un archivo subido directamente por el navegador del staff a MinIO/S3 quede registrado como media utilizable (`SourceImage` o `GarmentPhoto`, según `kind`), verificado contra el objeto real, y accesible como entrada de un photoshoot.

## Stories Included

- **001-source-image-presign**: Emitir la URL presignada de subida (Must)
- **002-source-image-confirm**: Confirmar y registrar la imagen de origen (Must)
- **003-source-image-rejection**: Rechazos fail-closed y discrepancias declarado/real (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. model**: Pending → `ddd-01-domain-model.md`
- [ ] **2. design**: Pending → `ddd-02-technical-design.md`
- [ ] **3. implement**: Pending → código en `backend/models`, `backend/repositories`, `backend/services`, `backend/api`
- [ ] **4. test**: Pending → `ddd-03-test-report.md`

## Dependencies

### Requires
- **050-bridge-provisioning** (Required): el presign se resuelve contra un `ProductLink` creable por API y un `staff_id` vigente

### Enables
- `053-photoshoot-orchestration` (el disparo exige un `source_image_id` en estado `ready`)

## Success Criteria

- [ ] `POST .../source-images:presign` firma un `PUT` de vida corta acotado a una clave, sin credenciales de almacenamiento en la respuesta
- [ ] `POST .../source-images/{id}:confirm` verifica el objeto real (existencia, tipo, tamaño) antes de registrar la media
- [ ] El registro delega en `tryoff_source_image_service` (`garment_on_model`) o `media_service` (`flat_garment`), sin un cuarto almacén paralelo
- [ ] Discrepancias declarado/real dejan la imagen en `rejected`, nunca en `ready`
- [ ] Vínculo ajeno, tenant ajeno o staff revocado: fail-closed en ambos endpoints
- [ ] Nuevo modelo `BridgeSourceImage` con revisión Alembic aplicada
- [ ] Todos los criterios de aceptación de las 3 historias cubiertos por pruebas
- [ ] Código revisado

## Notes

Verificar `MINIO_PUBLIC_ENDPOINT` y la política CORS del bucket **antes** de empezar la etapa de implementación: el navegador del staff tiene que alcanzar ese endpoint directamente. Si no lo alcanza, es un problema de despliegue por decisión explícita del dueño del producto, no un segundo camino de código.
