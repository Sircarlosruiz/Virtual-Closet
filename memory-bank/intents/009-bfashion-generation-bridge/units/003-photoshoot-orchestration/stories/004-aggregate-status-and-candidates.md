---
id: 004-aggregate-status-and-candidates
unit: 003-photoshoot-orchestration
intent: 009-bfashion-generation-bridge
status: draft
priority: must
created: 2026-09-18T10:36:00Z
assigned_bolt: 054-photoshoot-orchestration
implemented: false
---

# Story: 004-aggregate-status-and-candidates

## User Story

**As a** backend de BFashion haciendo polling de un trabajo de minutos
**I want** consultar un único recurso que me diga el estado agregado y me entregue los candidatos listos
**So that** no tenga que sondear cinco recursos distintos para saber si puedo mostrarle la galería al staff

## Acceptance Criteria

- [ ] **Given** un `photoshoot_id` válido, **When** llamo a `GET /api/integration/v1/products/{external_product_id}/photoshoots/{photoshoot_id}`, **Then** recibo `status`, `stages[]`, `expected_results`, `completed_results`, `failed_results`, `results[]` y `candidates[]` en una sola respuesta
- [ ] **Given** un photoshoot en curso, **When** lo consulto, **Then** `status` refleja `queued`/`running`/`partial`/`completed`/`failed` derivado de las etapas y resultados reales, no un valor mantenido a mano
- [ ] **Given** `candidates[]` en la respuesta, **When** comparo su forma con `PublicationCandidateResponse`, **Then** son estructuralmente compatibles: BFashion no necesita dos lectores distintos
- [ ] **Given** un photoshoot `completed`, **When** lo leo, **Then** eso significa disponible para revisión, nunca publicado
- [ ] **Given** un photoshoot de otro producto o de otro tenant, **When** intento consultarlo, **Then** recibo `404`/`403` sin filtrar si existe
- [ ] **Given** un photoshoot en curso, **When** lo consulto repetidamente, **Then** ninguna de esas consultas dispara una llamada al proveedor
- [ ] **Given** las `preview_url` en la respuesta, **When** las inspecciono, **Then** son de vida corta y regenerables, nunca una clave de almacenamiento expuesta como si fuese pública

## Technical Notes

- El estado agregado se calcula leyendo `PhotoshootStage` y `PhotoshootResult`/`GenerationJob`; no existe una columna `status` que otro proceso deba mantener sincronizada aparte.
- Reutilizar `preview_object_url` (`publication_service.py`) para las URL de vista previa, coherente con el resto del puente.
- Esta consulta es de solo lectura y debe cumplir NFR-1 (p95 ≤ 1 s excluyendo transferencia e inferencia) incluso con photoshoots grandes (varios modelos × poses).

## Dependencies

### Requires
- `003-generation-job-materialization`

### Enables
- Consumo directo por BFashion (fuera de este intent)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Photoshoot con 0 resultados completados y todas las etapas aún `pending` | `status: "queued"`, `candidates: []` |
| Photoshoot `partial` con overlay `blocked` en algunos resultados | Los resultados base sin overlay siguen apareciendo en `candidates[]` |
| Consulta durante una entrega de publicación en curso de un candidato anterior | El estado agregado del photoshoot es independiente del estado de publicación de sus candidatos |
| `photoshoot_id` sintácticamente válido pero inexistente | `404` |

## Out of Scope

- Suscripción por WebSocket al progreso (existe `ws.py` en el proyecto pero no es parte de este contrato)
- Paginación de `results[]` (V1 asume volúmenes acotados por producto)
