---
id: 053-photoshoot-orchestration
unit: 003-photoshoot-orchestration
intent: 009-bfashion-generation-bridge
type: ddd-construction-bolt
status: complete
stories:
  - 001-photoshoot-submission
  - 002-stage-pipeline-execution
  - 003-generation-job-materialization
created: 2026-09-18T11:15:00.000Z
started: 2026-09-19T15:52:00.000Z
completed: "2026-09-19T16:36:03Z"
current_stage: null
stages_completed:
  - name: model
    completed: 2026-09-19T15:55:00.000Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-09-19T15:57:00.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-09-19T15:58:00.000Z
    artifact: adr-067-vton-stage-is-a-gate.md, adr-068-photoshoot-tick-reschedule.md, adr-069-contract-c-pose-types.md, adr-070-photoshoot-owned-result-key.md
  - name: implement
    completed: 2026-09-19T16:18:00.000Z
    artifact: photoshoot models/services/router/task
  - name: test
    completed: 2026-09-19T16:35:11.000Z
    artifact: ddd-03-test-report.md
requires_bolts:
  - 050-bridge-provisioning
  - 051-source-image-intake
  - 052-replicate-execution-reliability
enables_bolts:
  - 054-photoshoot-orchestration
requires_units:
  - 001-bridge-provisioning
  - 002-source-image-intake
  - 004-replicate-execution-reliability
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

- [x] **1. model**: Complete → `ddd-01-domain-model.md`
- [x] **2. design**: Complete → `ddd-02-technical-design.md`
- [x] **3. adr-analysis**: Complete → ADR-067, ADR-068, ADR-069, ADR-070
- [x] **4. implement**: Complete → commit-then-enqueue, tryoff en la txn del tick
- [x] **5. test**: Complete → `ddd-03-test-report.md` (61 passed; pending bolt-close)

## Dependencies

### Requires
- **050-bridge-provisioning** (Required): vínculo y staff vigentes
- **051-source-image-intake** (Required): `source_image_id` en `ready`
- **052-replicate-execution-reliability** (Required): proveedor, credencial, concurrencia y timeouts operativos

### Enables
- `054-photoshoot-orchestration` (estado agregado, idempotencia y asiento de variantes sobre esta base)

## Success Criteria

- [x] `expected_results` se calcula en el momento del disparo, antes de que exista ningún resultado
- [x] `garment_on_model` ejecuta las 4 etapas; `flat_garment` marca `tryoff` como `skipped`, no `failed`
- [x] El fallo de una rama no cancela las demás
- [x] N×M resultados se materializan como N×M `GenerationJob` completados con `result_key` durable
- [x] Cada resultado aparece en `GET .../generation-jobs/{job_id}/publication-candidates` sin modificar `publication_service.py`
- [x] Verificado por ejecución que `PoseSet` + `BatchJob` cubren la expansión a N poses sin cambios de contrato interno
- [x] Todos los criterios de aceptación de las 3 historias cubiertos por pruebas
- [ ] Código revisado

## Notes

Riesgo principal: verificar en la etapa de modelo, antes de implementar, que `PoseSet` y `BatchJob` realmente cubren la expansión a N poses tal como el unit-brief lo supone. Si no, este bolt necesita una etapa de diseño técnico más profunda de lo estimado.
