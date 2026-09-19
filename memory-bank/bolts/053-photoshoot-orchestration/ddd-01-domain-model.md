---
unit: 003-photoshoot-orchestration
bolt: 053-photoshoot-orchestration
stage: model
status: complete
updated: 2026-09-19T15:55:00Z
---

# Static Model - photoshoot-orchestration

## Bounded Context

**Orquestación de photoshoot** (Photoshoot Orchestration). Cierra G2.

Este contexto recibe *qué* quiere el staff (una imagen de origen lista y unas características), decide *qué pipeline* corresponde al `input_kind`, coordina las etapas sobre servicios que ya existen, y materializa cada imagen producida como un `GenerationJob` completado — la única forma que el camino de publicación (bolts 047/048) reconoce.

Virtual Closet es la única autoridad del agregado. BFashion nombra el deseo, nunca el pipeline: no envía `tryoff` ni `vton`. El orquestador no llama al proveedor ni reimplementa inferencia. No crea un tipo de resultado publicable nuevo.

**Dentro del contexto (este bolt, 053)**

- Validar y aceptar un disparo de alto nivel (`submit_photoshoot`)
- Calcular `expected_results` en el momento del disparo, antes de que exista ningún resultado
- Persistir la instantánea de configuración efectiva
- Crear las cuatro filas de etapa y encolar el trabajo (solo identificadores por el broker)
- Ejecutar el pipeline por etapas según `input_kind`, aislando ramas (un modelo no cancela a otro)
- Materializar cada resultado de pose como `GenerationJob` + `PhotoshootResult`
- Adjuntar overlay (`ProductOverlay` + `CompositionVersion`) cuando hay overlay, sin bloquear el candidato base
- Derivar el estado del photoshoot para que no quede colgado en `running`

**Fuera del contexto (este bolt)**

- `GET .../photoshoots/{id}` como vista agregada + `candidates[]` (historia 004, bolt 054)
- Idempotencia HTTP `Idempotency-Key` / huella / reintento sin duplicar (historia 005, bolt 054)
- Lógica de variantes de color; solo se reserva el asiento `variant_key` (historia 006, bolt 054)
- Crear o reactivar `ProductLink` / `StaffIdentityLink` (unidad 001)
- Presign / confirm de imagen de origen (unidad 002)
- Cableado Replicate, guarda de credencial, tope global, timeouts (unidad 004; se **consumen**)
- Catálogo de opciones (unidad 005); el disparo valida contra los mismos repositorios, no contra el endpoint
- Reimplementar `TryoffJobService`, `VTONJobService`, `PoseSetService`, `BatchSubmissionService`, `SkuCompositionService`
- Modificar `publication_service.py` o `sync_delivery_service.py`
- Cancelación de un photoshoot en curso
- Migrar flujos cookie-auth al puente
- Crear `PublicationSelection` al completar (completar ≠ publicar)

Contextos vecinos: **Aprovisionamiento del puente**, **Admisión de imagen de origen**, **Fiabilidad Replicate**, **Pose Set / Batch VTON**, **TryOff**, **Composición / Overlay**, **Publicación** (solo lectura de candidatos), **Tenancy / Auth** (`ServiceClient`).

---

## Verificación de dominio: ¿PoseSet + BatchJob cubren N poses?

Riesgo marcado en el unit-brief y en la historia 002. Verificado **contra artefactos de dominio** (bolt 030, ADRs 043/044/045, modelo de BatchJob del bolt 023). No se leyó código fuente en esta etapa.

### Lo que el contrato interno ya cubre

1. **Un PoseSet = un modelo × N poses de esa prenda.** `submit_pose_set(mayorista_id, garment_id, model_id, cloth_type, pose_ids)` crea un `BatchJob` con `total_items = len(pose_ids)` y un `BatchItem` por pose (intent 006 FR-4/FR-5; bolt 030).
2. **`PoseSet.batch_id` es UNIQUE (1:1).** No hay dos agrupaciones sobre el mismo batch. Creación atómica con el batch (ADR-043): no queda PoseSet huérfano ni batch huérfano si la operación tiene éxito.
3. **`BatchItem.model_id` guarda el `ModelPhoto.id` de la pose, no el `Model.id`** (ADR-044). El orquestador debe traducir `pose_ids` del disparo a fotos de pose del modelo pedido.
4. **Tope de poses = las que tenga el modelo (hoy 1..3).** Duplicados o poses de otro modelo se rechazan en el servicio de PoseSet.
5. **Tenancy se pasa explícitamente** en la sumisión interna (ADR-045). El puente no puede omitir `tenant_id`.
6. **El fallo de un `BatchItem` no cancela los demás** (estado `partial` del batch). Encaja con «el fallo de una rama no cancela las demás».

### Lo que este agregado debe añadir (sin cambiar el contrato de PoseSet)

7. **Un photoshoot de M modelos no es un PoseSet.** Es **M sumisiones** del mismo contrato, una por modelo superviviente, cada una con las N poses resueltas. `expected_results = M × N` se calcula *antes*; las M sumisiones ocurren *después*.
8. **PoseSet no materializa `GenerationJob`.** Sus resultados viven en media de batch/`VtonJob`. Este contexto es el que copia/ancla cada imagen durable a un `GenerationJob` completado.
9. **PoseSet exige `garment_id`.** Para `flat_garment` es la media registrada de la reserva `ready`. Para `garment_on_model` es la prenda plana que produce `tryoff`. Sin esa prenda no hay etapa `poses`.
10. **Riesgo residual (Stage 4 / NFR-7):** la verificación *por ejecución* (un PoseSet real de 3 poses completa y proyecta 3 medias) sigue abierta. El modelo de dominio es sólido; el cableado interno (sesión compartida, cola, callback) se confirma al implementar, no aquí.

**Conclusión de modelo:** no hace falta un contrato interno nuevo ni un motor de expansión N×M. Hace falta un bucle de orquestación: 1 tryoff compartido → M puertas VTON → M PoseSets → N×M materializaciones.

---

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| **Photoshoot** (nueva, raíz) | `id`, `product_link_id`, `staff_id`, `source_image_id`, `input_kind`, `configuration` (instantánea), `status` (`queued` \| `running` \| `partial` \| `completed` \| `failed`), `expected_results`, `idempotency_key?`, `payload_fingerprint?`, `variant_key?`, `mayorista_id`, `tenant_id`, `error_code?`, `created_at`, `updated_at` | Una petición = un agregado. Nace `queued` con `expected_results > 0` ya calculado. `input_kind`, `source_image_id`, instantánea, `expected_results`, `mayorista_id` y `tenant_id` son inmutables. `mayorista_id` se copia del `ProductLink` (ADR-060), no se inventa. `variant_key` se persiste y se devuelve; en V1 siempre `null` (asiento para 054/006). `idempotency_key` / `payload_fingerprint` existen en el esquema; la semántica HTTP de replay es bolt 054. Completar **no** crea `PublicationSelection`. |
| **PhotoshootStage** (nueva, miembro) | `id`, `photoshoot_id`, `name` (`tryoff` \| `vton` \| `poses` \| `composition`), `status` (`pending` \| `running` \| `skipped` \| `completed` \| `failed`), `external_job_id?`, `error_code?`, `started_at?`, `completed_at?` | Siempre hay **cuatro** filas, creadas al disparar. El orden de nombre es el orden del pipeline. `skipped` es un desenlace válido (no es fallo): `tryoff` si `flat_garment`; `composition` si no hay overlay. Una etapa `failed` no deja el photoshoot en `running` para siempre: se cierra la etapa y se deriva el agregado. `external_job_id` apunta al trabajo delegado (tryoff / vton / pose-set / batch), nunca a un secreto. |
| **PhotoshootResult** (nueva, miembro) | `id`, `photoshoot_id`, `generation_job_id`, `model_id`, `pose_id`, `variant_key?`, `created_at` | Un resultado = una celda del producto cartesiano modelo × pose. Existe solo cuando hay un `GenerationJob` con `result_key` durable. No se deduplica por contenido de imagen. `variant_key` espeja el del photoshoot (`null` en V1). |
| **PhotoshootBranch** (concepto, no fila) | `model_id` + las etapas que le aplican | Unidad de aislamiento. El fallo de VTON o de PoseSet de un modelo no cancela las demás ramas. `tryoff` es compartido: si falla, no hay ramas. |
| **BridgeSourceImage** (existente, referenciada) | `id`, `kind`, `status`, `registered_media_id`, `registered_media_kind`, `product_link_id` | Debe estar `ready` y pertenecer al **mismo** `ProductLink`. `kind` debe ser coherente con `input_kind`. `pending` / `rejected` / ajena → no se encola (422 o 403 según opacidad). |
| **ProductLink** (existente, referenciada) | `id`, `mayorista_id`, `tenant_id`, `is_active` | Ancla de propiedad. Disparo exige vínculo **activo** del `ServiceClient`. `mayorista_id` es el dueño de todos los `GenerationJob` materializados. |
| **GenerationJob** (existente, **fuera** del agregado) | `id`, `owner_id`, `mode`, `provider`, `status`, `result_key`, `input_data` | Portador publicable. Se **materializa** ya resuelto: no se encola para inferir de nuevo. `owner_id` = `product_link.mayorista_id`. `provider` y `mode` reflejan el proveedor real (Replicate / try-on). Nunca `completed` sin `result_key`. `input_data` guarda modelo, pose y etapa de origen; no duplica la instantánea completa ni secretos (ADR-047). |
| **ProductOverlay** / **CompositionVersion** (existentes, fuera) | `UNIQUE(generation_job_id)`; `UNIQUE(overlay_id, spec_hash)` | Se adjuntan *después* de materializar el job base, solo si hay overlay. Fit rechazado → versión `blocked` (ADR-056), el job base sigue siendo candidato. Este contexto no altera esas invariantes. |
| **PoseSet** / **BatchJob** / **BatchItem** (existentes, fuera) | Ver bolt 030 / 023 | Consumidos por la etapa `poses`. Una sumisión por rama. No se rediseñan. |
| **ServiceClient** (existente, actor) | `id`, `system`, `tenant_id`, `is_active` | Identidad del backend llamante. Fail-closed. Aporta `system` y `tenant_id`; nunca se leen del cuerpo. |
| **Mayorista** (existente, espejo) | `id`, `role`, `tenant_id` | `staff_id` se resuelve con `resolve_staff_identity` (ADR-057). Revocado → 403, no se encola. |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| **PhotoshootId** | UUID | Identidad del agregado. Se emite al aceptar el disparo. |
| **InputKind** | `garment_on_model` \| `flat_garment` | Conjunto cerrado. Determina el pipeline. Cualquier otro valor → invariante de valor, 422, sin fila. Debe coincidir con `BridgeSourceImage.kind`. |
| **PhotoshootStatus** | `queued` \| `running` \| `partial` \| `completed` \| `failed` | Máquina: `queued → running → {completed \| partial \| failed}`. No hay `completed → published`. `completed` = disponible para revisión. |
| **StageName** | `tryoff` \| `vton` \| `poses` \| `composition` | Conjunto cerrado y ordenado. BFashion no lo envía; lo crea el servidor. |
| **StageStatus** | `pending` \| `running` \| `skipped` \| `completed` \| `failed` | `skipped` ≠ `failed`. Terminales: `skipped`, `completed`, `failed`. |
| **ExpectedResults** | entero ≥ 1 | `count(models) × count(poses)` resuelto **en el disparo**. Inmutable. No se recalcula al terminar etapas. |
| **ModelSelection** | lista ordenada de `model_id` | No vacía. Cada id debe existir, pertenecer al `mayorista_id` del vínculo (o ser visible para ese mayorista según las mismas reglas del catálogo) y no estar duplicado. Ajeno → 422 antes de encolar. |
| **PoseSelection** | lista ordenada de `pose_id` (`ModelPhoto.id`) | No vacía tras resolver. Cada pose debe pertenecer a **cada** modelo seleccionado, o el disparo declara `pose_ids` globales que se intersectan por modelo (ver decisión 4). Duplicados → 422. |
| **PoseCount** | entero | Rango soportado: 1..3 (OQ-4 / `Model` 1..3). Fuera de rango → 422. Se usa cuando no hay `pose_ids`. |
| **DefaultPosePolicy** | `default_count = 3` (OQ-4) | Si no llegan `pose_ids` ni `pose_count`, se resuelven hasta 3 poses disponibles **por modelo**. Si un modelo tiene menos, `expected_results` usa las realmente resueltas de forma **uniforme**: o bien se exige que todos los modelos cubran el recuento (422 si no), o se documenta recuento por el mínimo común. **Decisión de dominio: el recuento es el mismo para todos los modelos; si algún modelo no tiene suficientes poses para el `pose_count` / default, 422.** Así `expected_results` es un producto cartesiano honesto. |
| **ClothType** | valor del enum cerrado ya expuesto por el catálogo | Desconocido → 422 antes de encolar. |
| **OverlaySpec** | `text`, `placement`, `style` | Opcional. Texto vacío o ausente → disparo **sin** overlay; etapa `composition` nace `skipped`. Texto presente se normaliza (`normalize_sku`); si excede `SKU_MAX_LENGTH` → 422 en el disparo (FR-11), no a mitad de pipeline. |
| **ConfigurationSnapshot** | plantilla efectiva, `model_ids`, `pose_ids` resueltos, `cloth_type`, fondo, colores, overlay, `input_kind`, `source_image_id` | Copia congelada en el disparo (espíritu ADR-052). No es una referencia viva a `ImageTemplate`. Base de regeneración y de FR-13. Inmutable. |
| **TemplateRef** | `template_id?` | Si se envía: debe existir y no estar archivada (FR-3 intent 008). Archivada o inexistente → 422. Ausente: se admite; la instantánea registra «sin plantilla». |
| **VariantKey** | texto? | Reservado. V1: solo `null`. Cualquier valor no nulo en V1 → 422 (no se implementa la pasada de color). |
| **ResultSlot** | `(model_id, pose_id)` | Identidad de una celda del cartesiano. Única por photoshoot. |
| **DurableResultRef** | clave de objeto en bucket `generated` | Autoridad de que hay bytes. Sin ella el job no está `completed`. |
| **PublicationCarrier** | `generation_job_id` | El único ancla que `product_overlays` y `publication_selections` entienden. |
| **StaffId** | UUID | Espejo asertado. Debe pasar `resolve_staff_identity` al disparar. |
| **TenantId** | UUID | Solo del `ServiceClient`. |
| **ExternalProductId** | texto | Se resuelve a `ProductLink`. No implica propiedad. |
| **ExternalWholesalerId** | texto? | Si se envía, se compara fail-closed con el persistido (misma regla que el resto del puente). No elige otro dueño (ADR-060). |
| **CredentialPresence** (unidad 004) | `present` \| `absent` para Replicate | Ausente al disparar → indisponibilidad explícita, **no se encola** (FR-10 / historia 001). No se degrada a OpenAI. |
| **QueueWaitDuration** / **ExecutionDuration** | escritos por unidad 004 | Este contexto los *lee* para honestidad de progreso (bolt 054). No los escribe. |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| **Photoshoot** | Instantánea; 4 `PhotoshootStage`; 0..`expected_results` `PhotoshootResult`; referencias a `ProductLink`, `BridgeSourceImage`, `StaffId`, `TenantId` | Ver invariantes abajo. |

`GenerationJob`, `ProductOverlay`, `PoseSet` y `BatchJob` **no** son miembros. Se referencian tras delegación / materialización. Cada uno sigue siendo raíz de su contexto.

### Invariantes del agregado Photoshoot

1. Nace `queued` solo si la validación previa pasó: vínculo activo, staff vigente, origen `ready` y coherente, selección de modelos/poses/cloth/template/overlay válida, credencial Replicate presente, `expected_results ≥ 1`.
2. Sin validación válida **no hay fila** y no se publica nada al broker.
3. Las cuatro etapas se crean en el mismo instante que la raíz, todas `pending` salvo las que ya nacen `skipped` (`tryoff` si `flat_garment`; `composition` si no hay overlay).
4. `expected_results` es inmutable e igual a `|ModelSelection| × |PoseSelection|` resuelto en el disparo.
5. Un `PhotoshootResult` existe solo con `GenerationJob` en `completed` y `result_key` no nulo. La cardinalidad de resultados completos es ≤ `expected_results`.
6. Cada `ResultSlot` (modelo, pose) materializa **como máximo** un `PhotoshootResult`.
7. El estado agregado se **deriva** (ver máquina), no se escribe a mano en dos sitios.
8. `completed` no implica publicado: cero `PublicationSelection` creadas por este contexto.
9. El fallo de una rama no cancela las demás. `tryoff` compartido es la excepción: su fallo impide `vton`/`poses` de todas las ramas.
10. `input_kind`, instantánea, origen y dueño son inmutables.
11. `tenant_id` y `system` salen del `ServiceClient`; nunca del cuerpo.
12. Propiedad = `product_link_id` resuelto. Un `source_image_id` de otro producto del mismo tenant es ajeno (ADR-061: 403 `SOURCE_IMAGE_FORBIDDEN`, sin filtrar existencia).
13. Staff vigente al disparar. Este bolt no relee vigencia en cada etapa (el trabajo ya está aceptado); la revocación a mitad no borra resultados ya materializados.
14. Ningún secreto de proveedor viaja en HTTP, persistencia de `configuration`/`input_data`, mensaje Celery ni logs (ADR-047).
15. Commit de la raíz `queued` **antes** de publicar la task (ADR-048 / ADR-005).
16. `variant_key` puede persistirse; en V1 es `null`.

### Máquina de estados del photoshoot

```text
queued ──► running ──┬──► completed   (resultados completos == expected_results)
                     ├──► partial     (≥1 completo y (≥1 fallido o huecos irrecuperables))
                     └──► failed      (0 completos y no queda trabajo pendiente)
```

`running` mientras quede alguna etapa `pending`/`running` que aún pueda producir resultados. Una etapa `failed` no mantiene `running` si ya no hay ramas vivas.

### Máquina de una etapa

```text
pending ──► running ──► completed
        └──► skipped     (regla de input_kind / overlay; no corre)
running ──► failed       (error clasificado; error_code + completed_at)
```

No existe `skipped → failed` ni `completed → failed`. Reinicio de worker: etapas `completed`/`skipped` no se repiten; `running` interrumpida se reencola sin duplicar `PhotoshootResult` (NFR-5; detalle de lease en diseño).

### Pipeline por input_kind

```text
garment_on_model:
  tryoff (1, compartido) → vton (puerta por modelo) → poses (1 PoseSet por modelo) → composition (por resultado, si overlay)

flat_garment:
  tryoff = skipped
  vton (puerta por modelo) → poses (1 PoseSet por modelo) → composition (por resultado, si overlay)
```

- **tryoff** → `TryoffJobService`. Produce el `garment_id` plano. Falla ⇒ no hay `vton`/`poses`; photoshoot → `failed` si no hay otro origen.
- **vton** → `VTONJobService`, una invocación por modelo (pose representativa o la primera de `PoseSelection`). Es **puerta de rama**, no candidato publicable. Falla un modelo ⇒ esa rama no entra a `poses`; las otras siguen.
- **poses** → `PoseSetService` / `BatchSubmissionService`, una sumisión por rama viva, `pose_ids` = `PoseSelection`. Produce las N medias por modelo. Solo estas imágenes se materializan.
- **composition** → `SkuCompositionService`, síncrono respecto de cada job ya materializado (ADR-053). Opcional. Falla o `blocked` ⇒ el `GenerationJob` base **sigue** candidato (FR-11, ADR-056).

---

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| **PhotoshootAccepted** | Validación OK + persistencia `queued` + `expected_results` | `photoshoot_id`, `product_link_id`, `input_kind`, `expected_results`, `stage_names` |
| **PhotoshootRejected** | Invariante violada antes de persistir | `external_product_id`, `reason` — sin id de photoshoot |
| **PhotoshootAccessDenied** | Vínculo/staff/origen/tenant ajenos | `external_product_id`, `source_image_id?`, `reason` — **sin filtrar existencia** |
| **PhotoshootCredentialUnavailable** | Credencial Replicate ausente al disparar | `external_product_id`, código de indisponibilidad; no se encola |
| **PhotoshootEnqueued** | Task publicada tras commit | `photoshoot_id` (solo id; ADR-047) |
| **PhotoshootStarted** | Primera etapa pasa a `running` | `photoshoot_id`; status → `running` |
| **StageStarted** / **StageCompleted** / **StageSkipped** / **StageFailed** | Transición de etapa | `photoshoot_id`, `name`, `external_job_id?`, `error_code?` |
| **BranchFailed** | Una puerta VTON o un PoseSet falla para un `model_id` | `photoshoot_id`, `model_id`, `stage`, `error_code`; otras ramas intactas |
| **ResultMaterialized** | `GenerationJob` completed + `PhotoshootResult` + objeto durable | `photoshoot_id`, `generation_job_id`, `model_id`, `pose_id`, `result_key` |
| **ResultPersistDeferred** | Imagen producida pero aún no durable | `photoshoot_id`, `model_id`, `pose_id`; job **no** `completed`; no se rellama al proveedor |
| **OverlayAttached** | `ProductOverlay` + `CompositionVersion` OK | `generation_job_id`, `overlay_id`, `composition_version_id` |
| **OverlayBlocked** | Fit rechazado (ADR-056) | `generation_job_id`, versión `blocked`; candidato base intacto |
| **PhotoshootBecameCompleted** / **Partial** / **Failed** | Derivación terminal | `photoshoot_id`, `completed_count`, `failed_count`, `expected_results` |

V1: persistencia + logs estructurados, sin bus. Nunca loguear secretos, URLs presignadas ni claves de almacenamiento como si fuesen públicas.

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|-------------|
| **PhotoshootSubmissionService** (nuevo) | `submit(client, external_product_id, staff_id, source_image_id, input_kind, characteristics, external_wholesaler_id?) → (Photoshoot, created=true)` | `resolve_staff_identity`, `resolve_active_link`, lectura de `BridgeSourceImage`, catálogo de modelos/poses/cloth/template, `CredentialGateService.require(replicate)` (solo presencia), `PhotoshootRepository`, publicación post-commit |
| **PhotoshootOrchestrationService** (nuevo) | `run(photoshoot_id)`; `run_stage(photoshoot_id, name)`; `advance_branch(photoshoot_id, model_id)` | Servicios delegados de inferencia/composición; `PhotoshootRepository`; no llama al proveedor |
| **ResultMaterializationService** (nuevo) | `materialize(photoshoot_id, durable_bytes_or_key, model_id, pose_id) → (GenerationJob, PhotoshootResult)` | `GenerationJobRepository`; almacenamiento (`generated`); nunca SQL directo sobre jobs |
| **AggregateStatusDeriver** (nuevo) | `derive(photoshoot) → PhotoshootStatus` | Solo etapas + resultados + `expected_results`. Lo usa 053 para no colgar; la vista GET es 054 |
| **PipelinePolicy** (nuevo) | `stages_for(input_kind, overlay?) → [StagePlan]` | Tabla de skipped/required. Única autoridad de «qué corre» |
| **ExpectedResultsCalculator** (nuevo) | `calculate(models, poses) → ExpectedResults` | Corre **antes** de persistir |
| **TryoffJobService** (existente) | Etapa `tryoff` | No se reimplementa |
| **VTONJobService** (existente) | Puerta por modelo | No se reimplementa |
| **PoseSetService** / **BatchSubmissionService** (existentes) | Etapa `poses`, contrato bolt 030 + ADR-045 | Una llamada por rama; `pose_ids` = `ModelPhoto.id` |
| **SkuCompositionService** (existente) | Overlay por job materializado | Síncrono (ADR-053); `blocked` no mata el job |
| **GenerationJobRepository** (existente) | Alta del portador | Reutilizar; no insertar a mano |
| **StaffIdentityService** (existente) | `resolve_staff_identity` | ADR-057; no `_authorize_staff` |
| **CredentialGateService** (existente, 052) | Presencia de `REPLICATE_API_KEY` al disparar | Antes de persistir y de encolar |
| **IdempotencyService** (existente) | No se cablea en 053 | Historia 005 / bolt 054 |

### Reglas de `submit`

1. Autenticar `ServiceClient`. Fallo → no se revela si el producto existe.
2. `resolve_staff_identity`. Fallo → 403.
3. Resolver `ProductLink` activo. Fallo → 404/403 fail-closed (ADR-040 / resto del puente).
4. Cargar `BridgeSourceImage` **del mismo vínculo**. Miss o ajena → 403 `SOURCE_IMAGE_FORBIDDEN` (ADR-061). No `ready` o `kind` ≠ `input_kind` → 422, sin encolar.
5. Validar `input_kind`, `cloth_type`, `template_id`, `model_ids`, poses/`pose_count`/default, overlay/SKU, `variant_key is null`. Cualquier fallo → 422, sin fila.
6. `CredentialGateService.require(replicate)`. Ausente → indisponibilidad explícita, sin encolar.
7. Calcular `expected_results` y congelar `ConfigurationSnapshot` (poses ya resueltas a ids).
8. Persistir raíz + 4 etapas. Commit.
9. Publicar task con **solo** `photoshoot_id` (ADR-047, ADR-048).
10. Responder `202` con `photoshoot_id`, `status: queued`, `stages`, `expected_results`, `created_at`. p95 ≤ 1 s; no espera etapas (NFR-1).

`Idempotency-Key` repetida **no** se implementa aquí: 053 asume contenido nuevo (nota de la historia 001). Los campos existen para no migrar en 054.

### Reglas de orquestación

1. Solo ids cruzan el broker.
2. No reimplementar inferencia.
3. Etapas `skipped` se registran y se cierran; no se delegan.
4. Tras `tryoff` exitoso (o skip), se abren M puertas VTON en paralelo lógico (el tope global de 052 limita las llamadas reales).
5. Cada puerta OK dispara **un** `submit_pose_set` con el `garment_id` efectivo y los `pose_ids` de la instantánea.
6. Cada media de PoseSet/BatchItem → una materialización. No se materializan salidas de tryoff ni de la puerta VTON.
7. Overlay, si aplica, corre por resultado ya durable. `blocked` o fallo de composición no des-completa el job.
8. Tras cada cierre de etapa/rama se llama a `derive`. Nunca se deja `running` sin trabajo pendiente.
9. Entrega duplicada de mensaje: no segunda llamada al proveedor para el mismo intento (NFR-5); la autoridad es «slot ya materializado» + etapas ya terminales.
10. Persistencia fallida del objeto `generated`: se reintenta la copia; **no** se reinvoca Replicate (NFR-5).

### Reglas de materialización

1. Crear el `GenerationJob` vía repositorio, `owner_id` = espejo del vínculo, `provider`/`mode` reales.
2. Marcar `completed` **solo** con `result_key` durable en `generated`.
3. Insertar `PhotoshootResult` con el `ResultSlot`.
4. Dos poses, misma imagen de proveedor → dos jobs (no hay dedup).
5. El job debe aparecer en `GET .../generation-jobs/{id}/publication-candidates` **sin** tocar `publication_service.py`.
6. `POST .../publications` sobre ese job sigue el camino existente **sin** tocar `sync_delivery_service.py`.

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| **PhotoshootRepository** (nuevo) | `Photoshoot` | `add(photoshoot, stages)`; `get(id)`; `get_owned(id, product_link_id, tenant_id)`; `save`; `list_results(id)`; transiciones de etapa condicionales (`pending\|running → …`) |
| **PhotoshootResultRepository** (nuevo, o parte del anterior) | `PhotoshootResult` | `add_if_slot_free(photoshoot_id, slot, generation_job_id)` atómico; `count_completed`; `get_by_slot` |
| **BridgeSourceImageRepository** (existente, solo lectura) | `BridgeSourceImage` | `get_owned(id, product_link_id, tenant_id)` — mismo espíritu que 051 |
| **ProductLinkRepository** (existente, solo lectura) | `ProductLink` | `resolve_active_link` — no cambia |
| **Model / ModelPhoto** (existentes, solo lectura) | selección | Resolver y validar pertenencia al mayorista del vínculo |
| **ImageTemplate** (existente, solo lectura) | plantilla | Existe y no archivada |
| **GenerationJobRepository** (existente) | `GenerationJob` | Crear + completar con `result_key`; no SQL desde el orquestador |
| **ObjectStorage** (existente) | objeto `generated` | Copiar/asegurar clave durable; presign de preview lo usará 054 |
| **PoseSet / Batch** (existentes) | trabajos delegados | `submit_pose_set` interno + lectura de items/medias |
| **GlobalConcurrency / Credential** (052) | no se reimplementan | Se invocan en el camino de inferencia delegado y en el gate de submit |

La unicidad del `ResultSlot` vive en persistencia (`UNIQUE(photoshoot_id, model_id, pose_id)`), no solo en el servicio.

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Photoshoot** | Petición de alto nivel del staff: una foto lista + características. No es un job de inferencia. |
| **Disparo / submit** | Aceptar, calcular `expected_results`, persistir y encolar. Responde `202` sin esperar etapas. |
| **input_kind** | Clase de origen que **elige el pipeline**. Lo envía BFashion; no nombra etapas. |
| **Instantánea** | Copia congelada de la configuración efectiva en el disparo. |
| **expected_results** | M × N calculado *antes* de generar. Promesa al consumidor. |
| **Etapa** | Uno de `tryoff`, `vton`, `poses`, `composition`. Siempre hay cuatro filas. |
| **skipped** | Etapa que no corre por regla de dominio. No es un fallo. |
| **Rama** | Trabajo de un `model_id`. Su fallo no mata otras ramas. |
| **Puerta VTON** | Invocación por modelo que habilita o cierra esa rama. No es candidato. |
| **PoseSet** | Agrupación existente: una prenda × un modelo × N poses. Se invoca una vez por rama. |
| **Resultado / celda** | Par (modelo, pose) materializado como `GenerationJob` + `PhotoshootResult`. |
| **Materializar** | Convertir una imagen ya producida en portador publicable. **No** es volver a inferir. |
| **Portador / GenerationJob** | Única forma que la publicación ya entregada reconoce. |
| **Candidato** | Job completado con `result_key` que `list_candidates` ya sabe leer. |
| **completed (photoshoot)** | Todos los resultados esperados listos para **revisión**. Nunca significa publicado. |
| **partial** | Al menos un candidato útil y al menos un hueco o fallo. |
| **Publicar** | Crear `PublicationSelection`. Solo el staff, en otro contexto. Este bolt no publica. |
| **G2** | Hueco: el puente no ejecutaba el pipeline real ni producía candidatos. Este contexto lo cierra. |
| **Contrato C** | Superficie S2S del intent 009. Este bolt entrega `POST .../photoshoots`. |

## Decisiones de dominio que condicionan el diseño

1. **Orquestador nuevo, no cablear `vton` en `_get_provider`.** Un solo `GenerationJob` no cubre N×M ni el estado agregado. Los resultados de `vton_job` / `batch_job` / `pose_set` no son publicables.
2. **Materializar ≠ inferir.** El `GenerationJob` se crea como portador de una imagen ya producida. Encolarlo otra vez duplicaría coste y latencia.
3. **PoseSet se reutiliza sin cambiar contrato.** La expansión N es nativa; la expansión M es M llamadas. `BatchItem.model_id` = `ModelPhoto.id` (ADR-044).
4. **Producto cartesiano uniforme.** Todos los modelos comparten la misma `PoseSelection`. Si un modelo no tiene esas poses (o el recuento pedido), 422 en el disparo. No hay `expected_results` «aproximado».
5. **Cuatro filas siempre.** `skipped` hace visible el pipeline a BFashion (`stages` en el `202`) sin fingir un fallo.
6. **Composición opcional y no letal.** Sin overlay → `skipped`. Overlay `blocked` → candidato base vivo.
7. **tryoff compartido, resto por rama.** Un fallo de tryoff tumba el photoshoot; un fallo de modelo lo deja `partial` o `failed` según queden resultados.
8. **Commit then enqueue.** ADR-048/005. El `202` no se envía si no hay fila durable.
9. **Dueño = espejo del vínculo.** ADR-060. Todos los jobs materializados llevan ese `owner_id`.
10. **Origen ajeno = 403 opaco.** ADR-061, no 404 de reserva.
11. **Staff por `resolve_staff_identity`.** ADR-057. No `_authorize_staff`.
12. **Credencial Replicate se mira al disparar y en el worker.** 053 no encola sin clave; 052 sigue fallando cerrado si desaparece después.
13. **Idempotencia HTTP y GET agregado se aplazan a 054**, pero el esquema ya tiene `idempotency_key`, `payload_fingerprint` y `variant_key` para no migrar dos veces.
14. **OQ-4:** default 3 poses, configurable. El modelo fija la política (cartesiano uniforme + 422 si no hay cobertura); el número exacto de default es de producto y se lee de configuración en diseño.
15. **Taxonomía de rechazo** (HTTP exacto en Stage 2):
    - Cliente inválido → no autenticado
    - Staff inválido/revocado → 403
    - Vínculo inexistente/inactivo/otro tenant → 404/403, sin filtrar
    - `source_image_id` miss/ajeno → 403 `SOURCE_IMAGE_FORBIDDEN`
    - Origen no `ready` o `kind` incoherente → 422
    - Selección/cloth/template/pose_count/overlay/SKU/`variant_key` → 422
    - Credencial Replicate ausente → indisponibilidad explícita (no 202)
    - Photoshoot de otro producto en lecturas futuras → 404/403 opaco (054)

## Story Coverage

| Story | Cubierta por |
|-------|----------------|
| **001-photoshoot-submission** | `PhotoshootSubmissionService.submit`; VOs `InputKind`, `ExpectedResults`, `ConfigurationSnapshot`, `ModelSelection`, `PoseSelection`, `PoseCount`, `ClothType`, `OverlaySpec`, `TemplateRef`; eventos `Accepted` / `Rejected` / `AccessDenied` / `CredentialUnavailable`; 202 sin esperar etapas; fail-closed de vínculo/staff/origen |
| **002-stage-pipeline-execution** | `PipelinePolicy` + `PhotoshootOrchestrationService`; 4 etapas; `skipped` de tryoff en `flat_garment`; aislamiento de ramas; registro de `status`/`started_at`/`completed_at`/`error_code`; derivación para no colgar; delegación PoseSet × M; secretos solo en worker |
| **003-generation-job-materialization** | `ResultMaterializationService`; N×M `GenerationJob` + `PhotoshootResult`; `owner_id` del vínculo; overlay UNIQUE; candidato vía camino existente; jamás `completed` sin `result_key`; no dedup; persistencia reintentable sin re-inferir |

Historias 004/005/006 quedan nombradas como borde (campos reservados, `derive` interno) y **no** se dan por cubiertas.

## Prior Decisions Applied

- **ADR-043 / 044 / 045**: PoseSet+Batch atómico; `BatchItem.model_id` = foto de pose; `tenant_id` en la sumisión interna.
- **ADR-047**: solo `photoshoot_id` (y luego ids de trabajos delegados) por el broker; cero secretos en `configuration` / `input_data` / logs.
- **ADR-048 / ADR-005**: commit de `queued` antes de publicar Celery.
- **ADR-049 / 050 / 065 / 066**: el orquestador no llama a Replicate; el camino delegado hereda timeout, lease por job y tope global.
- **ADR-052**: instantánea por copia, no referencia viva a plantilla.
- **ADR-053 / 054 / 055 / 056**: composición síncrona, spec-hash, versiones append-only, `blocked` no destruye el base.
- **ADR-057 / 058 / 060**: staff por resolve; espejo por link; `mayorista_id` del vínculo es el dueño de los jobs.
- **ADR-061**: origen scoped miss → 403, no 404.
- **ADR-012 / 040**: tenant del cliente; no filtrar existencia cross-tenant/cross-product.
- **ADR-046**: no se altera el contrato `VTONProvider`; este contexto no añade adaptadores.
- **ADR-001**: contrato C servidor-a-servidor; no abre cookie del espejo.

## Open Questions Retained

- **OQ-4**: número exacto de poses por defecto (propuesta 3, configurable). El modelo ya fija *cómo* se aplica el default (cartesiano uniforme, 422 si un modelo no cubre).
- **OQ-3**: tope global de Replicate (unidad 004; propuesta 2). Este contexto no lo redefine; M×N llamadas competirán por ese pool y el 202 no espera.
- **Verificación por ejecución de PoseSet** (NFR-7 / nota del bolt): pendiente de Stage 4/5. El modelo no depende de cambiar el contrato interno.
- **¿La puerta VTON es estrictamente necesaria si PoseSet ya infiere?** El unit-brief y la historia 002 exigen delegar en `VTONJobService` *y* en `PoseSetService` en ese orden. Se modela como puerta de rama (no candidata). Stage 2 puede decidir si esa puerta reutiliza un modo ligero o un VTON completo; no se elimina la etapa.
