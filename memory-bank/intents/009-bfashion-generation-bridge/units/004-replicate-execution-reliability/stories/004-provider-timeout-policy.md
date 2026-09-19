---
id: 004-provider-timeout-policy
unit: 004-replicate-execution-reliability
intent: 009-bfashion-generation-bridge
status: draft
priority: must
created: 2026-09-18T10:51:00Z
assigned_bolt: 052-replicate-execution-reliability
implemented: false
---

# Story: 004-provider-timeout-policy

## User Story

**As a** llamada real a Replicate que puede tardar varios minutos
**I want** un timeout configurable por proveedor, no el `_REQUEST_TIMEOUT_SECONDS = 60` fijo actual
**So that** una generación legítima de 5-10 minutos no se corte a mitad de camino

## Acceptance Criteria

- [ ] **Given** una llamada a Replicate que tarda 10 minutos, **When** se ejecuta con la configuración de partida, **Then** no se corta por timeout
- [ ] **Given** el timeout, **When** se configura, **Then** es específico por proveedor: OpenAI conserva un valor corto, Replicate usa un valor de minutos (propuesta ≥ 900 s, con `TRYOFF_MODEL_TIMEOUT_SECONDS = 1800` como precedente del repositorio)
- [ ] **Given** un timeout vencido, **When** ocurre, **Then** el estado de fallo se refleja en ≤ 30 s
- [ ] **Given** un timeout con resultado desconocido, **When** se evalúa, **Then** no se reintenta automáticamente: requiere reintento explícito, coherente con `RetryPolicyService.classify_timeout`
- [ ] **Given** un `429` de Replicate, **When** se recibe, **Then** se reintenta como máximo 2 veces respetando `Retry-After`
- [ ] **Given** un error no transitorio de Replicate, **When** se recibe, **Then** no se reintenta automáticamente

## Technical Notes

- El cambio se concentra en `services/image_generation_providers.py` (o su equivalente para el adaptador de Replicate de `001-replicate-provider-wiring`): el timeout deja de ser una constante de módulo y pasa a resolverse por `provider`.
- Nueva variable de configuración en `core/config.py`, siguiendo el patrón de `TRYOFF_MODEL_TIMEOUT_SECONDS`.
- La política de reintentos (`RetryPolicyService`) ya existe y no se reescribe; solo se ajusta el timeout que la alimenta.

## Dependencies

### Requires
- `003-global-concurrency-cap`

### Enables
- `005-replicate-usage-accounting`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Replicate no responde nunca (conexión colgada) | Se corta al timeout configurado, no antes ni después |
| Timeout de OpenAI configurado accidentalmente igual al de Replicate | No rompe nada funcionalmente, pero deja de reflejar la intención de NFR-3; se valida con una prueba explícita de que ambos son independientes |

## Out of Scope

- Cambiar la política de clasificación de errores en `RetryPolicyService`
- Timeouts configurables por tenant o por job individual
