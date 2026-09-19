---
id: 003-generation-job-materialization
unit: 003-photoshoot-orchestration
intent: 009-bfashion-generation-bridge
status: complete
priority: must
created: 2026-09-18T10:34:00.000Z
assigned_bolt: 053-photoshoot-orchestration
implemented: true
---

# Story: 003-generation-job-materialization

## User Story

**As a** camino de publicación ya entregado (bolts 047/048)
**I want** que cada imagen producida por un photoshoot se materialice como una fila `GenerationJob` completada con `result_key` durable
**So that** cada resultado sea un candidato publicable sin que `publication_service.py` ni `sync_delivery_service.py` necesiten cambiar una línea

## Acceptance Criteria

- [ ] **Given** un photoshoot con 3 modelos × 3 poses, **When** completa, **Then** existen 9 filas `GenerationJob` con `status: "completed"` y `result_key` apuntando a un objeto durable del bucket `generated`
- [ ] **Given** cada `GenerationJob` materializado, **When** consulto `owner_id`, **Then** es igual a `product_link.mayorista_id`
- [ ] **Given** un resultado con overlay configurado, **When** se materializa, **Then** existe un `ProductOverlay` con `UNIQUE(generation_job_id)` y al menos una `CompositionVersion` con `UNIQUE(overlay_id, spec_hash)`
- [ ] **Given** un `GenerationJob` materializado por un photoshoot, **When** llamo a `GET .../generation-jobs/{job_id}/publication-candidates`, **Then** aparece como candidato sin que se haya tocado `publication_service.py`
- [ ] **Given** un `GenerationJob` materializado, **When** lo selecciono con `POST .../publications`, **Then** sigue el camino de entrega existente sin modificaciones
- [ ] **Given** un resultado en proceso, **When** su archivo aún no está persistido, **Then** su `GenerationJob` no está en `completed`
- [ ] **Given** cada `GenerationJob` materializado, **When** consulto `PhotoshootResult`, **Then** existe una fila que lo enlaza al `photoshoot_id`, al `model_id` y al `pose_id` correspondientes

## Technical Notes

- Esta es la pieza central de G2: la razón estructural por la que el orquestador materializa `GenerationJob` y no un tipo de resultado nuevo. `product_overlays` y `publication_selections` solo reconocen candidatos anclados a `GenerationJob`.
- Reutilizar `GenerationJobRepository` para la creación; no escribir SQL directo desde el orquestador.
- El `mode` y `provider` del `GenerationJob` materializado reflejan el proveedor real usado (Replicate), coherente con FR-9.
- `input_data` del `GenerationJob` guarda suficiente contexto (modelo, pose, etapa de origen) para depuración, sin duplicar la instantánea completa que ya vive en el `Photoshoot`.

## Dependencies

### Requires
- `002-stage-pipeline-execution`

### Enables
- `004-aggregate-status-and-candidates`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Un modelo produce imagen pero la subida a MinIO falla | El `GenerationJob` no se marca `completed`; se reintenta la persistencia sin volver a llamar al proveedor (NFR-5) |
| Dos poses del mismo modelo con la misma imagen resultante (edge de proveedor) | Cada una es un `GenerationJob` independiente; no se deduplican por contenido |
| Overlay configurado pero el texto no cabe | El `GenerationJob` base sigue completándose; la `CompositionVersion` queda `blocked` (ver `006-product-slug-overlay-fit` en la unidad `004`) |

## Out of Scope

- Deduplicación de imágenes visualmente idénticas
- Compresión o postprocesado de las imágenes resultantes
