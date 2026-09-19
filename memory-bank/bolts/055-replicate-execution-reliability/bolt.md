---
id: 055-replicate-execution-reliability
unit: 004-replicate-execution-reliability
intent: 009-bfashion-generation-bridge
type: ddd-construction-bolt
status: planned
stories:
  - 005-replicate-usage-accounting
  - 006-product-slug-overlay-fit
created: 2026-09-18T11:25:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts: [054-photoshoot-orchestration]
enables_bolts: []
requires_units: [003-photoshoot-orchestration]
blocks: true

complexity:
  avg_complexity: 2
  avg_uncertainty: 3
  max_dependencies: 1
  testing_scope: 3
---

# Bolt: 055-replicate-execution-reliability

## Overview

Último bolt del intent. Cierra la unidad `004` con las dos historias que necesitan datos reales para verificarse: la contabilidad de uso solo se puede comprobar contra invocaciones reales de Replicate, y el ajuste del overlay solo se puede comprobar contra slugs reales de BFashion sobre imágenes generadas de verdad. Por eso se ejecuta después de `053`/`054`, no en paralelo con `052`.

## Objective

Que al menos una invocación real de Replicate quede con consumo `reported` y modelo identificado, y que el compositor de overlay se comporte de forma predecible y verificada frente a slugs largos reales, sin cambiar su semántica determinista.

## Stories Included

- **005-replicate-usage-accounting**: Normalización de uso con forma de Replicate (Must)
- **006-product-slug-overlay-fit**: Overlay predecible con texto largo (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. model**: Pending → `ddd-01-domain-model.md`
- [ ] **2. design**: Pending → `ddd-02-technical-design.md`
- [ ] **3. implement**: Pending → ampliación de `UsageAccountingService`; verificación de `sku_renderer`/`composition_spec` contra slugs reales
- [ ] **4. test**: Pending → `ddd-03-test-report.md`

## Dependencies

### Requires
- **054-photoshoot-orchestration** (Required): necesita photoshoots reales completados contra Replicate, con y sin overlay, para verificar ambas historias

### Enables
- Ninguna. Cierra el intent.

## Success Criteria

- [ ] Al menos un `provider_invocation` real queda con `usage_status: "reported"` y modelo identificado
- [ ] Lo que Replicate no informa queda `unknown`, nunca `0`
- [ ] Un slug de más de 30 caracteres produce texto completo dentro de la imagen, o una `CompositionVersion` `blocked` con motivo medido
- [ ] Un overlay `blocked` no impide que el resultado base siga siendo candidato publicable
- [ ] Si la mayoría de slugs reales queda `blocked` con la configuración por defecto, queda documentado como escalamiento a **OQ-1**, no resuelto dentro del bolt
- [ ] Todos los criterios de aceptación de las 2 historias cubiertos por pruebas
- [ ] Código revisado

## Notes

Este bolt cierra NFR-7 (verificabilidad visual) para todo el intent: la validación previa a entrega de al menos 4 photoshoots reales contra Replicate, incluyendo un slug de más de 30 caracteres, se documenta aquí como evidencia final antes de dar el intent por completo.
