---
id: 003-global-concurrency-cap
unit: 004-replicate-execution-reliability
intent: 009-bfashion-generation-bridge
status: draft
priority: must
created: 2026-09-18T10:49:00Z
assigned_bolt: 052-replicate-execution-reliability
implemented: false
---

# Story: 003-global-concurrency-cap

## User Story

**As a** plataforma que paga por cada llamada a Replicate
**I want** un tope global configurable de llamadas simultáneas al proveedor
**So that** un photoshoot que expande a muchos resultados no dispare una ráfaga descontrolada de inferencias en paralelo

## Acceptance Criteria

- [ ] **Given** un tope configurado en 2, **When** un photoshoot expande a 12 resultados, **Then** el photoshoot completa con los 12 resultados, sin que en ningún instante medido haya más de 2 llamadas simultáneas al proveedor
- [ ] **Given** el excedente sobre el tope, **When** se mide, **Then** queda en cola y no falla: no hay descarte de trabajo por exceso de concurrencia
- [ ] **Given** el estado agregado de un photoshoot (`004-aggregate-status-and-candidates`), **When** lo consulto, **Then** el tiempo en cola se expone por separado del tiempo de ejecución
- [ ] **Given** el tope, **When** se configura, **Then** es un valor de despliegue, no un valor de código
- [ ] **Given** `ConcurrencyGuardService` (lease por job existente), **When** se introduce el tope global, **Then** ambos mecanismos coexisten sin que uno sustituya al otro: el lease sigue evitando duplicados de un mismo job, el tope global limita cuántas llamadas hay a la vez

## Technical Notes

- Nueva pieza, separada de `ConcurrencyGuardService`: ese servicio es un lease por job (anti-duplicado de entrega), no un contador de concurrencia global. No sobrecargar su responsabilidad.
- Implementación candidata: un semáforo respaldado por Redis (`REDIS_URL` ya está configurado para el denylist de sesión) o por una cola de prioridad en RabbitMQ con `worker_prefetch_multiplier` acotado. La decisión técnica final se toma en la etapa de diseño técnico del bolt.
- Propuesta de valor de partida: 2, heredado de NFR-1 del intent 008, pero marcado como ajustable (**OQ-3**) porque ese valor se fijó pensando en OpenAI.

## Dependencies

### Requires
- `002-provider-credential-gating`

### Enables
- `004-provider-timeout-policy`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| El worker se reinicia con trabajos en cola de concurrencia | Los trabajos en cola no se pierden; se retoman respetando el tope |
| Dos photoshoots distintos compiten por el mismo tope | El tope es global al despliegue, no por photoshoot ni por tenant |
| Tope configurado en 0 o negativo | Se rechaza en configuración, no en tiempo de ejecución |

## Out of Scope

- Prioridad entre photoshoots en cola
- Tope por tenant (solo hay un tenant en este intent)
- Autoescalado del número de workers
