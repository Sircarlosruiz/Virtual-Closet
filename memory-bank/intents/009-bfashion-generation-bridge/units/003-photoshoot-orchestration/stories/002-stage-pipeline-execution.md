---
id: 002-stage-pipeline-execution
unit: 003-photoshoot-orchestration
intent: 009-bfashion-generation-bridge
status: complete
priority: must
created: 2026-09-18T10:32:00.000Z
assigned_bolt: 053-photoshoot-orchestration
implemented: true
---

# Story: 002-stage-pipeline-execution

## User Story

**As a** orquestador de photoshoots
**I want** ejecutar en Celery el pipeline real correspondiente al tipo de entrada, delegando en los servicios que ya funcionan
**So that** un photoshoot `garment_on_model` o `flat_garment` produzca resultados de verdad, sin reimplementar inferencia y sin que el fallo de una rama cancele las demás

## Acceptance Criteria

- [ ] **Given** un photoshoot `garment_on_model` en `queued`, **When** el worker lo procesa, **Then** ejecuta en orden `tryoff → vton → poses → composición`, delegando en `TryoffJobService`, `VTONJobService`, `PoseSetService`/`BatchSubmissionService` y `SkuCompositionService`
- [ ] **Given** un photoshoot `flat_garment` en `queued`, **When** el worker lo procesa, **Then** ejecuta `vton → poses → composición`, y la etapa `tryoff` queda registrada como `skipped`, no `failed`
- [ ] **Given** una etapa que falla para un modelo concreto, **When** el resto de modelos siguen su curso, **Then** esos otros modelos completan sus resultados con normalidad
- [ ] **Given** cualquier etapa, **When** se ejecuta, **Then** su fila registra `status`, `started_at`, `completed_at` y `error_code` cuando corresponde
- [ ] **Given** una etapa que falla, **When** inspecciono el photoshoot, **Then** no queda colgado en `running` de forma indefinida: transiciona según la máquina de estados documentada en el unit-brief
- [ ] **Given** el pipeline en ejecución, **When** inspecciono las credenciales usadas, **Then** ninguna credencial de proveedor sale del contexto del worker
- [ ] **Given** la etapa `poses`, **When** se ejecuta, **Then** produce tantos resultados como modelos × poses configurados, usando `PoseSet` para la agrupación

## Technical Notes

- Solo identificadores de trabajo cruzan el broker (ADR-047); ningún byte de imagen ni credencial viaja por el mensaje de Celery.
- El orquestador no reimplementa inferencia: llama a los servicios existentes y espera sus resultados vía polling interno o encadenamiento de tasks Celery, según lo que resulte más consistente con el resto del proyecto.
- Verificar en la etapa de modelo (antes de implementar) que `PoseSet` + `BatchJob` cubren la expansión a N poses sin cambios de contrato interno; el unit-brief marca esto como supuesto no verificado por ejecución.
- La etapa `composición` es opcional: solo corre si el photoshoot incluye overlay.

## Dependencies

### Requires
- `001-photoshoot-submission`
- `001-replicate-provider-wiring` (unidad `004`)

### Enables
- `003-generation-job-materialization`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Todos los modelos fallan en `vton` | El photoshoot transiciona a `failed`, no a `partial` |
| Un modelo completa pero su composición falla | Ese resultado queda sin overlay pero sigue siendo candidato base publicable (ver FR-11) |
| `tryoff` falla para `garment_on_model` | Las etapas posteriores de esa rama no se ejecutan; el photoshoot puede terminar en `failed` si es el único modelo |
| Reinicio del worker a mitad de ejecución | Las etapas ya completadas no se repiten; las pendientes se reencolan sin duplicar resultados |

## Out of Scope

- Reimplementar la lógica de inferencia de `tryoff`, `vton` o `pose_set`
- Cancelación manual de una etapa en curso
