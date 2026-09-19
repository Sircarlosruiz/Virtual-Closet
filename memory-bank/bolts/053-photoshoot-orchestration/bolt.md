---
id: 053-photoshoot-orchestration
unit: 003-photoshoot-orchestration
intent: 009-bfashion-generation-bridge
type: ddd-construction-bolt
status: planned
stories:
  - 001-photoshoot-submission
  - 002-stage-pipeline-execution
  - 003-generation-job-materialization
created: 2026-09-18T11:15:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts: [050-bridge-provisioning, 051-source-image-intake, 052-replicate-execution-reliability]
enables_bolts: [054-photoshoot-orchestration]
requires_units: [001-bridge-provisioning, 002-source-image-intake, 004-replicate-execution-reliability]
blocks: true

complexity:
  avg_complexity: 3
  avg_uncertainty: 2
  max_dependencies: 3
  testing_scope: 3
---

# Bolt: 053-photoshoot-orchestration

## Overview

Primer bolt del agregado `Photoshoot`, la pieza que cierra G2. Recibe el disparo de alto nivel, ejecuta el pipeline real por etapas según el tipo de entrada (`garment_on_model` o `flat_garment`), y materializa cada resultado como un `GenerationJob` completado — la forma exacta que el camino de publicación ya entregado (bolts 047/048) reconoce sin cambios, porque `product_overlays` y `publication_selections` solo aceptan candidatos anclados a `GenerationJob`.

## Objective

Que `POST .../photoshoots` dispare de verdad `tryoff → vton → poses → composición` sobre los servicios existentes, y que cada imagen producida termine siendo una fila `GenerationJob` completada, candidata a publicación sin tocar `publication_service.py` ni `sync_delivery_service.py`.

## Stories Included

- **001-photoshoot-submission**: Disparar un photoshoot desde BFashion (Must)
- **002-stage-pipeline-execution**: Ejecutar el pipeline por etapas según el tipo de entrada (Must)
- **003-generation-job-materialization**: Materializar cada resultado como candidato publicable (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. model**: Pending → `ddd-01-domain-model.md`
- [ ] **2. design**: Pending → `ddd-02-technical-design.md`
- [ ] **3. implement**: Pending → nuevos modelos `Photoshoot`, `PhotoshootStage`, `PhotoshootResult` + `PhotoshootOrchestrationService` + tasks Celery
- [ ] **4. test**: Pending → `ddd-03-test-report.md`

## Dependencies

### Requires
- **050-bridge-provisioning** (Required): vínculo y staff vigentes
- **051-source-image-intake** (Required): `source_image_id` en `ready`
- **052-replicate-execution-reliability** (Required): proveedor, credencial, concurrencia y timeouts operativos

### Enables
- `054-photoshoot-orchestration` (estado agregado, idempotencia y asiento de variantes sobre esta base)

## Success Criteria

- [ ] `expected_results` se calcula en el momento del disparo, antes de que exista ningún resultado
- [ ] `garment_on_model` ejecuta las 4 etapas; `flat_garment` marca `tryoff` como `skipped`, no `failed`
- [ ] El fallo de una rama no cancela las demás
- [ ] N×M resultados se materializan como N×M `GenerationJob` completados con `result_key` durable
- [ ] Cada resultado aparece en `GET .../generation-jobs/{job_id}/publication-candidates` sin modificar `publication_service.py`
- [ ] Verificado por ejecución que `PoseSet` + `BatchJob` cubren la expansión a N poses sin cambios de contrato interno
- [ ] Todos los criterios de aceptación de las 3 historias cubiertos por pruebas
- [ ] Código revisado

## Notes

Riesgo principal: verificar en la etapa de modelo, antes de implementar, que `PoseSet` y `BatchJob` realmente cubren la expansión a N poses tal como el unit-brief lo supone. Si no, este bolt necesita una etapa de diseño técnico más profunda de lo estimado.
