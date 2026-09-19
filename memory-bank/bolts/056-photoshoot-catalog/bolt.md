---
id: 056-photoshoot-catalog
unit: 005-photoshoot-catalog
intent: 009-bfashion-generation-bridge
type: ddd-construction-bolt
status: complete
stories:
  - 001-photoshoot-options-catalog
  - 002-catalog-isolation-and-freshness
created: 2026-09-18T11:55:00.000Z
started: 2026-09-19T01:35:20.000Z
completed: "2026-09-19T01:55:24Z"
current_stage: null
stages_completed:
  - name: model
    completed: 2026-09-19T01:36:51.000Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-09-19T01:41:17.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-09-19T01:45:00.000Z
    artifact: adr-063-catalog-version-content-hash.md, adr-064-weak-etag-deferred-presign.md
  - name: implement
    completed: 2026-09-19T01:50:00.000Z
    artifact: backend/services/photoshoot_catalog_service.py
  - name: test
    completed: 2026-09-19T01:55:24Z
    artifact: ddd-03-test-report.md
requires_bolts:
  - 050-bridge-provisioning
enables_bolts: []
requires_units:
  - 001-bridge-provisioning
blocks: true
complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 056-photoshoot-catalog

## Overview

Añadido tras una primera pasada de Checkpoint 3, al detectarse que `FR-5` (disparo del photoshoot) exige campos (`template_id`, `model_ids`, `pose_ids`/`pose_count`, `cloth_type`) que ninguna unidad exponía como descubribles por BFashion. Este bolt cierra ese hueco con un único endpoint de solo lectura.

**Nota de numeración**: este bolt recibe el número global `056`, posterior a `050`-`055`, porque los números reflejan orden de planeación, no de ejecución. Su ejecución real es **temprana**: justo después de `050`, en paralelo con `051` y `052` — ver "Execution Order" en `units.md`. La razón no es una dependencia técnica de `053` (no la tiene), sino que BFashion necesita este contrato para empezar a construir su formulario antes de que el staff tenga nada que enviar en el disparo.

## Objective

Que `GET /api/integration/v1/products/{external_product_id}/photoshoot-options` devuelva, en una sola respuesta fail-closed, las plantillas activas, los modelos con sus poses reales y el conjunto cerrado de `cloth_type`, con soporte de `ETag` para refrescos baratos.

## Stories Included

- **001-photoshoot-options-catalog**: Exponer plantillas, modelos, poses y `cloth_types` en un solo recurso (Must)
- **002-catalog-isolation-and-freshness**: Aislamiento fail-closed y versionado de caché (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [x] **1. model**: Complete → `ddd-01-domain-model.md` (sin modelo de datos nuevo ni Alembic)
- [x] **2. design**: Complete → `ddd-02-technical-design.md`
- [x] **3. adr-analysis**: Complete → ADR-063, ADR-064
- [x] **4. implement**: Complete → `backend/services/photoshoot_catalog_service.py`
- [x] **5. test**: Complete → `ddd-03-test-report.md`

## Dependencies

### Requires
- **050-bridge-provisioning** (Required): resolución de vínculo y alcance por mayorista

### Enables
- Ninguna unidad interna. Consumo externo directo por BFashion (intent 020), priorizado temprano por orden de entrega entre equipos.

## Success Criteria

- [ ] El catálogo agrega plantillas, modelos/poses y `cloth_types` en una sola llamada `200`
- [ ] Plantillas `draft`/`archived` nunca aparecen; `private` de otro mayorista nunca aparecen
- [ ] `background`/`colors` se presentan explícitamente como sugerencias, no como enum cerrado
- [ ] Vínculo ajeno o inactivo: `403`/`404` sin filtrar catálogo
- [ ] `ETag`/`If-None-Match` con `304` funcional cuando no hay cambios
- [ ] Todos los criterios de aceptación de las 2 historias cubiertos por pruebas
- [ ] Código revisado

## Notes

Bolt pequeño y de bajo riesgo técnico (solo lectura, sin modelo nuevo), pero de alta prioridad de entrega: es la pieza que el intent hermano necesita para dejar de tener su propia pregunta abierta (OQ-3 del lado de BFashion) sin resolver.
