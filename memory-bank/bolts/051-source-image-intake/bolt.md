---
id: 051-source-image-intake
unit: 002-source-image-intake
intent: 009-bfashion-generation-bridge
type: ddd-construction-bolt
status: complete
stories:
  - 001-source-image-presign
  - 002-source-image-confirm
  - 003-source-image-rejection
created: 2026-09-18T11:05:00.000Z
started: 2026-09-19T01:35:00.000Z
completed: "2026-09-19T02:03:37Z"
current_stage: null
stages_completed:
  - name: model
    completed: 2026-09-19T01:42:00.000Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-09-19T01:45:00.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-09-19T01:50:00.000Z
    artifact: adr-061-scoped-source-image-forbidden.md, adr-062-atomic-confirm-shared-session.md
  - name: implement
    completed: 2026-09-19T01:55:00.000Z
    artifact: backend/models/bridge_source_image.py
  - name: test
    completed: 2026-09-19T02:15:00Z
    artifact: ddd-03-test-report.md
requires_bolts:
  - 050-bridge-provisioning
enables_bolts:
  - 053-photoshoot-orchestration
requires_units:
  - 001-bridge-provisioning
blocks: false
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

- [x] **1. model**: Complete → `ddd-01-domain-model.md`
- [x] **2. design**: Complete → `ddd-02-technical-design.md`
- [x] **3. adr-analysis**: Complete → ADR-061, ADR-062
- [x] **4. implement**: Complete → `backend/models/bridge_source_image.py`
- [x] **5. test**: Complete → `ddd-03-test-report.md`

## Dependencies

### Requires
- **050-bridge-provisioning** (Required): el presign se resuelve contra un `ProductLink` creable por API y un `staff_id` vigente

### Enables
- `053-photoshoot-orchestration` (el disparo exige un `source_image_id` en estado `ready`)

## Success Criteria

- [x] `POST .../source-images:presign` firma un `PUT` de vida corta acotado a una clave, sin credenciales de almacenamiento en la respuesta
- [x] `POST .../source-images/{id}:confirm` verifica el objeto real (existencia, tipo, tamaño) antes de registrar la media
- [x] El registro delega en `tryoff_source_image_service` (`garment_on_model`) o `media_service` (`flat_garment`), sin un cuarto almacén paralelo
- [x] Discrepancias declarado/real dejan la imagen en `rejected`, nunca en `ready`
- [x] Vínculo ajeno, tenant ajeno o staff revocado: fail-closed en ambos endpoints
- [x] Nuevo modelo `BridgeSourceImage` con revisión Alembic aplicada
- [x] Todos los criterios de aceptación de las 3 historias cubiertos por pruebas
- [x] Código revisado

## Notes

Verificar `MINIO_PUBLIC_ENDPOINT` y la política CORS del bucket **antes** de empezar la etapa de implementación: el navegador del staff tiene que alcanzar ese endpoint directamente. Si no lo alcanza, es un problema de despliegue por decisión explícita del dueño del producto, no un segundo camino de código.
