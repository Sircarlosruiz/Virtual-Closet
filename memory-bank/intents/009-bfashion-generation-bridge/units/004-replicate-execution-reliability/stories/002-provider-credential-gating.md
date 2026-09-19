---
id: 002-provider-credential-gating
unit: 004-replicate-execution-reliability
intent: 009-bfashion-generation-bridge
status: complete
priority: must
created: 2026-09-18T10:47:00.000Z
assigned_bolt: 052-replicate-execution-reliability
implemented: true
---

# Story: 002-provider-credential-gating

## User Story

**As a** operador de un despliegue Replicate-only
**I want** que la comprobación de credencial del worker sea por proveedor, no una guarda global de `OPENAI_API_KEY`
**So that** un job de Replicate no falle por la ausencia de una credencial que ni siquiera necesita

## Acceptance Criteria

- [ ] **Given** `OPENAI_API_KEY` vacío y `REPLICATE_API_KEY` presente, **When** se ejecuta un `generate_image_task` para un job de Replicate, **Then** el job completa sin elevar `ValueError` por falta de credencial
- [ ] **Given** `OPENAI_API_KEY` vacío, **When** se ejecuta un job de OpenAI, **Then** falla de forma clasificada y no reintentable, con un código de error distinguible de un fallo del proveedor
- [ ] **Given** `REPLICATE_API_KEY` vacío, **When** se ejecuta un job de Replicate, **Then** falla igual de explícito y no reintentable
- [ ] **Given** ambas credenciales configuradas, **When** se ejecutan jobs de ambos proveedores, **Then** ninguno se ve afectado por la credencial del otro
- [ ] **Given** cualquier fallo de credencial, **When** inspecciono respuestas HTTP y registros, **Then** no aparece el valor de ninguna credencial
- [ ] **Given** la guarda de credencial, **When** se ejecuta, **Then** ocurre **antes** de tomar el lease de concurrencia y antes de cualquier llamada de red al proveedor

## Technical Notes

- Esta es la corrección del bloqueante identificado en el intent: `generate_image_task` hoy comprueba `settings.OPENAI_API_KEY` de forma incondicional, antes de mirar `job.provider`.
- La comprobación debe leer `job.provider` (ya persistido) y verificar solo la credencial correspondiente.
- Reutilizar la clasificación de error existente (`RetryPolicyService`) para marcar este fallo como no reintentable: una credencial ausente no se arregla reintentando.
- Esta historia toca código compartido con el intent 008; ejecutar su regresión antes de cerrar el bolt.

## Dependencies

### Requires
- `001-replicate-provider-wiring`

### Enables
- `003-global-concurrency-cap`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `provider` del job es un valor desconocido | Falla de forma clasificada, coherente con `001-replicate-provider-wiring` |
| Credencial presente pero inválida (rechazada por el proveedor en tiempo de ejecución) | No es responsabilidad de esta historia: eso lo cubre la clasificación de errores HTTP existente, no la guarda de arranque |

## Out of Scope

- Rotación o gestión de credenciales
- Validación de la credencial contra el proveedor en el arranque de la aplicación (solo se valida en el momento de uso)
