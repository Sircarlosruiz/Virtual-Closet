---
id: 001-replicate-provider-wiring
unit: 004-replicate-execution-reliability
intent: 009-bfashion-generation-bridge
status: complete
priority: must
created: 2026-09-18T10:45:00.000Z
assigned_bolt: 052-replicate-execution-reliability
implemented: true
---

# Story: 001-replicate-provider-wiring

## User Story

**As a** worker de generación de imágenes
**I want** resolver el proveedor de Replicate para los modos que el flujo del puente usa
**So that** un `GenerationJob` cuyo proveedor es Replicate no termine en `failed` por `ProviderRequestError`

## Acceptance Criteria

- [ ] **Given** un `GenerationJob` con `provider: "replicate"`, **When** `_get_provider` lo resuelve, **Then** devuelve un adaptador funcional en lugar de elevar `ProviderRequestError`
- [ ] **Given** ese adaptador, **When** se invoca `generate`, **Then** reutiliza la ruta Replicate existente (`services/vton/catvton_replicate_provider.py`, `services/providers/replicate_provider.py`) sin escribir un cliente HTTP nuevo
- [ ] **Given** un job cuyo `provider` sigue siendo `"openai"`, **When** se resuelve, **Then** el comportamiento existente del intent 008 no cambia
- [ ] **Given** un `provider` desconocido (ni `openai` ni `replicate`), **When** se resuelve, **Then** se eleva `ProviderRequestError` clasificado, igual que hoy
- [ ] **Given** un job materializado por el orquestador de photoshoots con modo `try_on`, **When** se ejecuta contra el adaptador de Replicate, **Then** produce una imagen persistible, sin regresión sobre el pipeline VTON existente

## Technical Notes

- El adaptador debe traducir entre la forma de `input_data` de `GenerationJob` y la firma `generate(garment: bytes, model: bytes, cloth_type: str)` de `CatVTONReplicateProvider`, sin duplicar la lógica de llamada a Replicate.
- No modificar `services/vton/catvton_replicate_provider.py`; envolverlo, no reescribirlo.
- Ejecutar la regresión de los jobs `text` del intent 008 antes de cerrar el bolt: esta historia toca `_get_provider`, que es compartido.

## Dependencies

### Requires
- Ninguna

### Enables
- `002-stage-pipeline-execution` (unidad `003`)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Replicate devuelve una URL de resultado en vez de bytes inline | El adaptador descarga el contenido antes de persistirlo, igual que `CatVTONReplicateProvider.generate` ya hace |
| `input_data` sin las claves que Replicate necesita (por ejemplo `cloth_type`) | `ProviderRequestError` clasificado, no una excepción no controlada |

## Out of Scope

- Migrar los modos `text`, `edit`, `extraction` a Replicate
- Cambiar el esquema del modelo Replicate configurado (`CATVTON_REPLICATE_MODEL`)
