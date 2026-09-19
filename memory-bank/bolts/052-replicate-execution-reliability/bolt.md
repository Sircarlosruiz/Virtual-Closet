---
id: 052-replicate-execution-reliability
unit: 004-replicate-execution-reliability
intent: 009-bfashion-generation-bridge
type: ddd-construction-bolt
status: complete
stories:
  - 001-replicate-provider-wiring
  - 002-provider-credential-gating
  - 003-global-concurrency-cap
  - 004-provider-timeout-policy
created: 2026-09-18T11:10:00.000Z
started: 2026-09-19T01:35:10.000Z
completed: "2026-09-19T15:49:26Z"
current_stage: null
stages_completed:
  - name: model
    completed: 2026-09-19T01:37:20.000Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-09-19T01:40:55.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-09-19T01:47:09.000Z
    artifact: adr-065-redis-global-concurrency-reschedule.md
  - name: implement
    completed: 2026-09-19T15:23:42.000Z
    artifact: tasks/image_generation.py
  - name: test
    completed: 2026-09-19T15:50:00.000Z
    artifact: ddd-03-test-report.md
requires_bolts: []
enables_bolts:
  - 053-photoshoot-orchestration
requires_units: []
blocks: false
complexity:
  avg_complexity: 2
  avg_uncertainty: 2
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 052-replicate-execution-reliability

## Overview

Hace que el worker de generación sea realmente utilizable en un despliegue Replicate-only, que es la decisión de producción. Cubre el bloqueante de primera clase (`OPENAI_API_KEY` vacío tumba todo job, sin mirar el proveedor), el cableado del proveedor de Replicate, el tope global de concurrencia inexistente hoy, y los timeouts acordes a latencias de minutos.

Es independiente de `050` y `051`: es trabajo de worker y configuración, y puede desarrollarse en paralelo.

## Objective

Que un `GenerationJob` de Replicate complete de principio a fin sin `OPENAI_API_KEY` configurada, dentro de un tope global de concurrencia medible, y sin cortarse por un timeout pensado para OpenAI.

## Stories Included

- **001-replicate-provider-wiring**: Cablear el proveedor de Replicate al worker (Must)
- **002-provider-credential-gating**: Comprobar la credencial del proveedor del job (Must)
- **003-global-concurrency-cap**: Limitar las llamadas simultáneas al proveedor (Must)
- **004-provider-timeout-policy**: Tiempos de espera acordes a Replicate (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [x] **1. model**: Complete → `ddd-01-domain-model.md`
- [x] **2. design**: Complete → `ddd-02-technical-design.md`
- [x] **3. implement**: Complete → cambios en `backend/tasks/image_generation.py`, `backend/services`, `backend/core/config.py`
- [x] **4. test**: Complete → `ddd-03-test-report.md`

## Dependencies

### Requires
- Ninguna

### Enables
- `053-photoshoot-orchestration` (sin credencial por proveedor, tope y timeouts adecuados, el pipeline no completa contra Replicate)

## Success Criteria

- [x] `_get_provider` resuelve Replicate sin escribir un cliente HTTP nuevo
- [x] Con `OPENAI_API_KEY` vacío y `REPLICATE_API_KEY` presente, un job de Replicate completa
- [x] Tope global configurable de llamadas simultáneas; el excedente encola, no falla
- [x] Timeout por proveedor configurable, ≥ 900 s de partida para Replicate
- [x] Regresión de los jobs `text` del intent 008 pasa sin cambios de comportamiento
- [x] Todos los criterios de aceptación de las 4 historias cubiertos por pruebas
- [x] Código revisado

## Notes

Este bolt toca `_get_provider` y la guarda de credencial de `tasks/image_generation.py`, que son compartidos con el intent `008-openai-image-generation`. Ejecutar la regresión de ese intent antes de cerrar el bolt.
