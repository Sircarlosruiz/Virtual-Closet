---
id: 054-photoshoot-orchestration
unit: 003-photoshoot-orchestration
intent: 009-bfashion-generation-bridge
type: ddd-construction-bolt
status: complete
stories:
  - 004-aggregate-status-and-candidates
  - 005-photoshoot-idempotency-and-retry
  - 006-color-variant-forward-compat
created: 2026-09-18T11:20:00.000Z
started: 2026-09-19T16:45:00.000Z
completed: "2026-09-19T17:21:12Z"
current_stage: null
stages_completed:
  - name: model
    completed: 2026-09-19T16:48:00.000Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-09-19T17:00:00.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-09-19T17:02:00.000Z
    artifact: adr-071-photoshoot-idempotency-key-unique.md, adr-072-photoshoot-idempotency-service.md
  - name: implement
    completed: 2026-09-19T17:12:00.000Z
    artifact: source code
  - name: test
    completed: 2026-09-19T17:19:00.000Z
    artifact: ddd-03-test-report.md
requires_bolts:
  - 053-photoshoot-orchestration
enables_bolts:
  - 055-replicate-execution-reliability
requires_units:
  - 003-photoshoot-orchestration
blocks: true
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 054-photoshoot-orchestration

## Overview

Segundo bolt del agregado `Photoshoot`. Completa la superficie que BFashion consume por polling (estado agregado + candidatos en una sola consulta), cierra la garantía de idempotencia y reintento de principio a fin, y deja el asiento reservado para la segunda pasada de variantes de color sin obligar a una migración destructiva.

## Objective

Que `GET .../photoshoots/{id}` sea el único recurso que BFashion necesita sondear, que ningún reintento duplique trabajo ni imágenes, y que el modelo de datos ya admita `variant_key` para la futura generación por variante.

## Stories Included

- **004-aggregate-status-and-candidates**: Estado agregado y candidatos en una consulta (Must)
- **005-photoshoot-idempotency-and-retry**: Sin jobs ni imágenes duplicadas (Must)
- **006-color-variant-forward-compat**: Asiento reservado para la segunda pasada (Should)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [x] **1. model**: Complete → `ddd-01-domain-model.md`
- [x] **2. design**: Complete → `ddd-02-technical-design.md`
- [x] **3. adr-analysis**: Complete → ADR-071, ADR-072
- [x] **4. implement**: Complete → GET agregado, UNIQUE de idempotencia, `variant_key`
- [x] **5. test**: Complete → `ddd-03-test-report.md`

## Dependencies

### Requires
- **053-photoshoot-orchestration** (Required): el agregado y la materialización de candidatos ya deben existir

### Enables
- `055-replicate-execution-reliability` (necesita photoshoots reales completados para verificar consumo y overlay)

## Success Criteria

- [x] `GET .../photoshoots/{id}` devuelve estado agregado, etapas, contadores y candidatos en una sola llamada, sin disparar llamadas al proveedor
- [x] `candidates[]` es estructuralmente compatible con `PublicationCandidateResponse`
- [x] Misma `Idempotency-Key` + mismo contenido devuelve el mismo `photoshoot_id`; contenido distinto responde `409`
- [x] Un fallo de sincronización con BFashion no pierde ningún resultado ya generado
- [x] `variant_key` existe en `Photoshoot` y `PhotoshootResult`, nullable, `null` en todo disparo de V1
- [x] Todos los criterios de aceptación de las 3 historias cubiertos por pruebas
- [ ] Código revisado

## Notes

Este bolt cierra la unidad `003-photoshoot-orchestration` completa. Tras su cierre, el flujo end-to-end descrito en el objetivo de negocio del intent es ejecutable de punta a punta, salvo la verificación de consumo y overlay con datos reales que cubre `055`.
