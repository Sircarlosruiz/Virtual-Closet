---
id: 001-photoshoot-submission
unit: 003-photoshoot-orchestration
intent: 009-bfashion-generation-bridge
status: draft
priority: must
created: 2026-09-18T10:30:00Z
assigned_bolt: 053-photoshoot-orchestration
implemented: false
---

# Story: 001-photoshoot-submission

## User Story

**As a** backend de BFashion
**I want** disparar un único trabajo de alto nivel que describa qué quiere el staff, sin nombrar pipelines internos
**So that** Virtual Closet decida qué ejecutar y yo reciba de inmediato cuántos resultados esperar

## Acceptance Criteria

- [ ] **Given** un vínculo activo, un `staff_id` vigente y un `source_image_id` en `ready`, **When** llamo a `POST /api/integration/v1/products/{external_product_id}/photoshoots` con `input_kind`, modelos, poses, `cloth_type`, fondo, colores y overlay, **Then** recibo `202` con `photoshoot_id`, `status: "queued"`, `stages`, `expected_results` y `created_at`
- [ ] **Given** un `source_image_id` que no está en `ready`, **When** disparo el photoshoot, **Then** recibo `422` y no se encola nada
- [ ] **Given** `input_kind: garment_on_model` sin ningún `model_id`, **When** disparo, **Then** recibo `422` antes de encolar y antes de cualquier llamada al proveedor
- [ ] **Given** un `cloth_type` desconocido, **When** disparo, **Then** recibo `422`
- [ ] **Given** un `pose_count` fuera del rango soportado, **When** disparo, **Then** recibo `422`
- [ ] **Given** la petición aceptada, **When** leo `expected_results`, **Then** coincide con el número de combinaciones modelo × pose que se calcularon en el momento del disparo, antes de que exista ningún resultado
- [ ] **Given** el photoshoot creado, **When** lo inspecciono, **Then** existe una instantánea persistida de la configuración efectiva (plantilla, modelos, poses, fondo, colores, overlay)
- [ ] **Given** un vínculo o un `staff_id` inválidos, **When** disparo, **Then** recibo `403`/`404` fail-closed, con las mismas reglas del resto del puente

## Technical Notes

- El `input_kind` determina el pipeline; BFashion nunca nombra `tryoff` ni `vton` en la petición.
- `expected_results` se calcula en el momento del disparo (número de modelos × número de poses), no se infiere después de que corran las etapas.
- La instantánea de configuración es la base de FR-13 (la publicación reutiliza esta configuración) y de la regenerabilidad de FR-10 del intent 008.
- El `Idempotency-Key` de esta petición se procesa en `005-photoshoot-idempotency-and-retry`; esta historia asume contenido nuevo sin esa cabecera repetida.

## Dependencies

### Requires
- `001-product-link-creation`
- `002-staff-identity-provisioning`
- `002-source-image-confirm`

### Enables
- `002-stage-pipeline-execution`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `template_id` que no existe o está archivado | `422`, coherente con la regla de FR-3 del intent 008: archivar impide seleccionar la plantilla |
| Overlay con texto vacío | Se acepta el disparo sin overlay; el overlay es opcional según FR-4 del intent 008 |
| `model_ids` con un identificador que no pertenece al tenant | `422` antes de encolar |
| Disparo válido pero `REPLICATE_API_KEY` no configurada | Ver `002-provider-credential-gating`: se informa indisponibilidad explícita, no se encola |

## Out of Scope

- Cálculo del tope de concurrencia (lo cubre la unidad `004`)
- Selección o publicación de resultados
