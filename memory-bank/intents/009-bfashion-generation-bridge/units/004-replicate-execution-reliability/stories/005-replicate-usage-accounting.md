---
id: 005-replicate-usage-accounting
unit: 004-replicate-execution-reliability
intent: 009-bfashion-generation-bridge
status: complete
priority: must
created: 2026-09-18T10:53:00.000Z
assigned_bolt: 055-replicate-execution-reliability
implemented: true
---

# Story: 005-replicate-usage-accounting

## User Story

**As a** plataforma que registra consumo de proveedores de IA
**I want** que `UsageAccountingService` reconozca la forma de telemetría que Replicate realmente reporta
**So that** el consumo de un despliegue Replicate-only no quede siempre como `unknown` por diseño

## Acceptance Criteria

- [ ] **Given** una invocación real contra Replicate, **When** se completa, **Then** al menos un `provider_invocation` queda con `usage_status: "reported"` y su `model` identificado
- [ ] **Given** la telemetría que Replicate expone (identificador de predicción, tiempo de predicción, métricas del modelo), **When** se normaliza, **Then** `UsageAccountingService.normalize` la reconoce sin necesitar los campos de tokens de OpenAI
- [ ] **Given** un campo de telemetría que Replicate no informa para una ejecución concreta, **When** se normaliza, **Then** se registra como `unknown`, nunca como `0`
- [ ] **Given** cualquier coste derivado de la telemetría de uso, **When** se expone, **Then** se identifica explícitamente como estimación
- [ ] **Given** un job de OpenAI, **When** se normaliza su uso, **Then** el comportamiento existente del intent 008 no cambia

## Technical Notes

- `_SAFE_USAGE_FIELDS` hoy es `{total_tokens, input_tokens, output_tokens, input_tokens_details, output_tokens_details}`. Se amplía con un conjunto equivalente para Replicate, no se reemplaza: la normalización debe distinguir por `provider`.
- El SDK `replicate` expone `prediction.metrics` (por ejemplo `predict_time`) y el identificador de la predicción; verificar contra una ejecución real cuál es la forma exacta antes de fijar el esquema, en lugar de asumirla.
- Esta historia se ejecuta después de la orquestación (`003-photoshoot-orchestration`) porque necesita invocaciones reales de Replicate contra las que verificar, no solo datos sintéticos.

## Dependencies

### Requires
- `001-replicate-provider-wiring`
- Photoshoots reales ejecutados (unidad `003`, para tener invocaciones que medir)

### Enables
- Ninguna (cierra junto con `006` en el bolt `055`)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Replicate cambia la forma de su respuesta de métricas entre versiones del SDK | Los campos no reconocidos se ignoran; no rompe la normalización, degrada a `unknown` para esos campos |
| Un job mixto (parte Replicate, parte composición local) | Solo la parte que llamó al proveedor tiene `usage_status`; la composición no consume cuota de proveedor |

## Out of Scope

- Facturación automática al mayorista
- Alertas o límites de gasto
