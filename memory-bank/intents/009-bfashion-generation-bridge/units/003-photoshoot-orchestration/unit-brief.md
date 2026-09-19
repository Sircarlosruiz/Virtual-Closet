---
unit: 003-photoshoot-orchestration
intent: 009-bfashion-generation-bridge
phase: inception
status: draft
unit_type: backend
default_bolt_type: ddd-construction-bolt
created: 2026-09-18T09:55:00Z
updated: 2026-09-18T09:55:00Z
---

# Unit Brief: photoshoot-orchestration

## Purpose

Cerrar G2 con el agregado **`Photoshoot`**: recibe *qué* quiere el staff (una foto y unas características), decide *qué pipeline* ejecutar, coordina `tryoff → vton → poses → composición` sobre los servicios que ya funcionan, materializa cada imagen producida como una fila `GenerationJob` publicable, y expone un único estado agregado con sus candidatos.

Hoy el puente crea un `GenerationJob` que el worker no sabe ejecutar: `_get_provider` solo devuelve `OpenAIImageProvider`, cuyo `generate` solo soporta `mode == "text"`. Un job `try_on` disparado desde BFashion termina en `failed`. Mientras tanto, los pipelines que sí funcionan (`vton_job`, `tryoff_job`, `batch_job`, `pose_set`) tienen sus propias tablas y sus propias tasks, y no están detrás del puente.

## Por qué orquestador nuevo y no cablear `vton` en `_get_provider`

La razón es estructural, no estética. El camino de publicación ya entregado solo reconoce candidatos anclados a `GenerationJob`:

- `product_overlays` tiene `UNIQUE(generation_job_id)`
- `publication_selections` es única por `(product_link_id, generation_job_id, composition_version_id)`
- `publication_service.list_candidates` parte de un `GenerationJob` y recorre sus `CompositionVersion`

Los resultados de `vton_job`, `batch_job` y `pose_set` **no son candidatos publicables**. Un photoshoot de N poses necesita N filas `GenerationJob` para producir N candidatos. Cablear `vton` dentro de `_get_provider` produciría un único resultado por job, no cubriría la expansión a N poses ni el estado agregado, y dejaría dos modelos de job paralelos que habría que migrar para la segunda pasada de variantes de color.

El orquestador consume los servicios existentes; no reimplementa inferencia.

## Scope

### In Scope
- `POST /api/integration/v1/products/{external_product_id}/photoshoots` (con `Idempotency-Key`)
- `GET /api/integration/v1/products/{external_product_id}/photoshoots/{photoshoot_id}`
- Nuevos modelos `Photoshoot` y `PhotoshootStage` + revisión Alembic
- `PhotoshootOrchestrationService` y sus tasks Celery
- Materialización de cada resultado como `GenerationJob` completado con `result_key` durable
- Adjuntar `ProductOverlay` + `CompositionVersion` por resultado cuando hay overlay
- Derivación del estado agregado a partir de etapas y resultados
- Instantánea de la configuración efectiva del photoshoot
- Campo `variant_key` reservado (`null` en V1) para la segunda pasada

### Out of Scope
- Reimplementar inferencia: se consumen `TryoffJobService`, `VTONJobService`, `PoseSetService`, `SkuCompositionService`
- Modificar `publication_service.py` o `sync_delivery_service.py`: el camino de publicación se reutiliza tal cual
- Modificar el contrato A hacia BFashion
- Implementar lógica de variantes de color: solo se reserva el asiento
- Cancelación de un photoshoot en curso
- Migrar los flujos cookie-auth existentes al puente

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-5 | Disparo del photoshoot | Must |
| FR-6 | Orquestación por etapas | Must |
| FR-7 | Materialización como candidato publicable | Must |
| FR-8 | Estado agregado y candidatos en una sola consulta | Must |
| FR-12 | Idempotencia y reintento del photoshoot | Must |
| FR-13 | Publicación manual reutilizando el camino existente | Must |
| FR-14 | Preparación para variantes de color | Should |

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| `Photoshoot` (**nuevo**) | Raíz del agregado: una petición de alto nivel del staff | `id`, `product_link_id`, `staff_id`, `source_image_id`, `input_kind`, `configuration` (JSONB), `status` (`queued` \| `running` \| `partial` \| `completed` \| `failed`), `expected_results`, `idempotency_key`, `payload_fingerprint`, `variant_key` (nullable, reservado), `mayorista_id`, `tenant_id`, `error_code`, `created_at`, `updated_at` |
| `PhotoshootStage` (**nuevo**) | Una etapa del pipeline y su desenlace | `id`, `photoshoot_id`, `name` (`tryoff` \| `vton` \| `poses` \| `composition`), `status` (`pending` \| `running` \| `skipped` \| `completed` \| `failed`), `external_job_id`, `error_code`, `started_at`, `completed_at` |
| `PhotoshootResult` (**nuevo**) | Enlace entre el photoshoot y cada `GenerationJob` materializado | `id`, `photoshoot_id`, `generation_job_id`, `model_id`, `pose_id`, `variant_key` (nullable), `created_at` |
| `GenerationJob` (existente) | Portador del resultado publicable | `owner_id`, `mode`, `provider`, `status`, `result_key` |
| `ProductOverlay` / `CompositionVersion` (existentes) | Superposición determinista del identificador de producto | `UNIQUE(generation_job_id)`, `UNIQUE(overlay_id, spec_hash)` |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `submit_photoshoot` | Valida, calcula `expected_results`, persiste y encola | vínculo, `staff_id`, `source_image_id`, características, `Idempotency-Key` | `Photoshoot` en `queued`, `created: bool` |
| `run_stage` | Ejecuta una etapa delegando en el servicio correspondiente | `photoshoot_id`, nombre de etapa | `PhotoshootStage` actualizada |
| `materialize_result` | Convierte una imagen producida en `GenerationJob` completado | `photoshoot_id`, bytes/clave, `model_id`, `pose_id` | `GenerationJob` + `PhotoshootResult` |
| `derive_status` | Calcula el estado agregado desde etapas y resultados | `photoshoot_id` | `status`, contadores |
| `get_photoshoot_view` | Estado agregado + resultados + candidatos | vínculo, `photoshoot_id` | Respuesta de FR-8 |

### Máquina de estados del photoshoot

```text
queued ──► running ──┬──► completed   (todos los resultados esperados, completos)
                     ├──► partial     (al menos uno completo, al menos uno fallido)
                     └──► failed      (ningún resultado completo)
```

`completed` significa **disponible para revisión**, nunca publicado.

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 6 |
| Must Have | 5 |
| Should Have | 1 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| `001-photoshoot-submission` | Disparar un photoshoot desde BFashion | Must | Planned |
| `002-stage-pipeline-execution` | Ejecutar el pipeline por etapas según el tipo de entrada | Must | Planned |
| `003-generation-job-materialization` | Materializar cada resultado como candidato publicable | Must | Planned |
| `004-aggregate-status-and-candidates` | Consultar estado agregado y candidatos | Must | Planned |
| `005-photoshoot-idempotency-and-retry` | Reintentar sin duplicar trabajos ni imágenes | Must | Planned |
| `006-color-variant-forward-compat` | Reservar el asiento de las variantes de color | Should | Planned |

---

## Dependencies

### Depends On

| Unit | Reason |
|------|--------|
| `001-bridge-provisioning` | El disparo exige un `ProductLink` y un `staff_id` vigentes |
| `002-source-image-intake` | El disparo exige un `source_image_id` en estado `ready` |
| `004-replicate-execution-reliability` | Sin credencial por proveedor, tope de concurrencia y timeouts adecuados, el pipeline no completa contra Replicate |

### Depended By

Ninguna unidad de este intent. El consumidor es BFashion (intent 020).

### External Dependencies

| System | Purpose | Risk |
|--------|---------|------|
| Replicate | Inferencia real del pipeline | Alto — latencia de minutos, coste, límites de tasa |
| RabbitMQ / Celery | Ejecución asíncrona de etapas | Medio — entregas duplicadas, mitigadas por lease e idempotencia |
| MinIO / S3 | Persistencia durable de N resultados | Medio |
| BFashion (intent 020) | Consume el disparo y el polling del estado agregado | Alto — contrato nuevo, desarrollo paralelo |

---

## Technical Context

### Suggested Technology

`PhotoshootOrchestrationService` en `services/`, con tasks Celery en `tasks/`. El orquestador **no** llama al proveedor directamente: delega en `TryoffJobService`, `VTONJobService`, `PoseSetService` y `SkuCompositionService`, que ya saben encolar y ejecutar sus propios pipelines. Solo cruza identificadores por el broker (ADR-047).

La idempotencia reutiliza `IdempotencyService` y `compute_payload_fingerprint`, que ya implementan la semántica exigida por FR-12 (misma clave + mismo contenido → mismo trabajo; misma clave + contenido distinto → `409`).

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| `TryoffJobService` | Etapa `tryoff` | Interno + Celery |
| `VTONJobService` | Etapa `vton` | Interno + Celery |
| `PoseSetService` / `BatchSubmissionService` | Etapa `poses` | Interno + Celery |
| `SkuCompositionService` | Etapa `composition` | Interno |
| `GenerationJobRepository` | Materialización de resultados | Interno |
| `publication_service.list_candidates` | Candidatos del estado agregado | Interno |
| `IdempotencyService` | Idempotencia del disparo | Interno |

### Data Storage

| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| `photoshoots` | SQL | Una fila por petición del staff | Permanente |
| `photoshoot_stages` | SQL | 4 filas por photoshoot | Permanente |
| `photoshoot_results` | SQL | N×M filas por photoshoot | Permanente |
| Resultados | Objeto (bucket `generated`) | N×M imágenes por photoshoot | Permanente |

---

## Constraints

- El estado agregado se **deriva**, no se mantiene a mano en dos sitios.
- Un `GenerationJob` nunca queda `completed` sin `result_key`.
- El fallo de una rama no cancela las demás: el photoshoot puede terminar en `partial`.
- Completar un photoshoot **no** crea ninguna `PublicationSelection`. Solo la selección explícita del staff publica.
- Un fallo de sincronización con BFashion no puede perder un resultado ya generado aquí.
- Combinaciones no soportadas se rechazan con `422` antes de encolar y antes de cualquier llamada al proveedor.
- El `input_kind` determina el pipeline: BFashion nunca nombra `tryoff` ni `vton`.
- `publication_service.py` y `sync_delivery_service.py` no se modifican.
- Revisión Alembic obligatoria por los tres modelos nuevos.
- Ver **OQ-4**: número de poses por defecto cuando BFashion no especifica `pose_ids`.

---

## Success Criteria

### Functional
- [ ] Un photoshoot `garment_on_model` ejecuta `tryoff → vton → poses → composición` y produce N×M resultados
- [ ] Un photoshoot `flat_garment` omite `tryoff` marcándolo `skipped`, no `failed`
- [ ] Cada resultado es un `GenerationJob` completado con `result_key` durable
- [ ] Cada resultado aparece como candidato en `GET .../generation-jobs/{job_id}/publication-candidates` sin modificar `publication_service.py`
- [ ] `GET .../photoshoots/{id}` devuelve estado agregado, etapas, contadores y candidatos en una sola llamada
- [ ] El fallo de un modelo deja el photoshoot en `partial` con el resto de resultados intactos
- [ ] Misma `Idempotency-Key` + mismo contenido devuelve el photoshoot existente sin encolar de nuevo
- [ ] Misma `Idempotency-Key` + contenido distinto responde `409`
- [ ] Completar un photoshoot no crea ninguna `PublicationSelection`
- [ ] `variant_key` se persiste y se devuelve, `null` en V1

### Non-Functional
- [ ] El disparo responde `202` en p95 ≤ 1 s sin esperar ninguna etapa (NFR-1)
- [ ] La consulta de estado agregado no dispara llamadas al proveedor (NFR-1)
- [ ] Reiniciar servicios conserva photoshoots, etapas, resultados y estado de sincronización (NFR-5)
- [ ] Una entrega duplicada de mensaje no inicia dos llamadas al proveedor para el mismo intento (NFR-5)
- [ ] Un photoshoot de otro producto o de otro tenant responde `404`/`403` sin filtrar existencia (NFR-6)
- [ ] Al menos 4 photoshoots reales contra Replicate validados según NFR-7

### Quality
- [ ] Cobertura de código > 80 %
- [ ] Todos los criterios de aceptación cubiertos por pruebas
- [ ] Revisión de código aprobada

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| `053-photoshoot-orchestration` | ddd | 001, 002, 003 | El agregado, el pipeline y los candidatos publicables |
| `054-photoshoot-orchestration` | ddd | 004, 005, 006 | Estado agregado, idempotencia y asiento de variantes |

---

## Notes

Es la unidad más grande del intent y la que integra a las otras tres. El mayor riesgo de diseño es la expansión de resultados: un photoshoot con 3 modelos × 3 poses son 9 llamadas a Replicate y 9 filas `GenerationJob`. Con el tope de concurrencia propuesto en 2 (**OQ-3**) eso son varios minutos de cola, y el estado agregado tiene que exponer el tiempo en cola por separado del de ejecución para que BFashion pueda mostrar algo honesto al staff.

Verificar en la etapa de modelo que `PoseSet` + `BatchJob` cubren la expansión a N poses sin cambios de contrato interno. `PoseSet` ya es `UNIQUE(batch_id)` y agrupa modelo × prenda × poses, así que el supuesto parece sólido, pero no está verificado por ejecución.
