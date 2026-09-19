---
unit: 003-photoshoot-orchestration
bolt: 054-photoshoot-orchestration
stage: model
status: complete
updated: 2026-09-19T16:45:00Z
---

# Static Model - photoshoot-orchestration (vista, idempotencia, asiento)

## Bounded Context

**Orquestación de photoshoot** — segundo bolt del mismo contexto que 053.

053 ya es la autoridad de *aceptar, orquestar y materializar*. Este bolt **no** reabre el pipeline, no añade etapas y no crea un segundo agregado. Cierra tres superficies que 053 aplazó a propósito:

1. **Vista agregada de lectura** (`GET .../photoshoots/{id}`): el único recurso que BFashion sondea (FR-8).
2. **Idempotencia de disparo y reintento sin duplicar** (FR-12): semántica HTTP sobre campos que 053 ya persistió sin UNIQUE ni replay.
3. **Asiento `variant_key`** (FR-14): el campo ya existe; este bolt define cómo se persiste, se devuelve y se garantiza que la segunda pasada no exige migración destructiva.

Virtual Closet sigue siendo la única autoridad del agregado. Consultar no dispara inferencia. Reintentar no vuelve a llamar al proveedor. Completar sigue sin publicar.

**Dentro del contexto (este bolt, 054)**

- Derivar y exponer estado agregado, etapas, contadores, `results[]` y `candidates[]` en una sola lectura
- Regenerar `preview_url` de vida corta desde claves durables (nunca exponer `result_key` / `minio_key`)
- Replay de `POST .../photoshoots` con `Idempotency-Key` + huella (mismo contenido → mismo id; distinto → 409)
- Garantizar que una entrega duplicada de Celery no produce segundo `PhotoshootResult` ni segunda llamada al proveedor
- Verificar —sin modificar el camino— que un fallo de sync con BFashion reutiliza `GenerationJob` + `result_key` y que los destinos `virtual_closet` / `bfashion` son independientes
- Persistir y devolver `variant_key` (nullable) en raíz y en cada resultado

**Fuera del contexto (este bolt)**

- Rediseñar submit, etapas, PoseSet, materialización o overlay (cerrado en 053; ADRs 067–070)
- Reimplementar inferencia o llamar a Replicate desde el GET
- Modificar `publication_service.py` o `sync_delivery_service.py` (solo lectura / verificación)
- Relanzar automáticamente un photoshoot `failed` con la misma clave
- Deduplicar contenido semánticamente idéntico con distinta `Idempotency-Key`
- Lógica de variantes de color: filtrado, agrupación, resolución de `ProductVariant`
- WebSocket de progreso, paginación de `results[]`, cancelación
- ETag / 304 en el GET del photoshoot (eso es del catálogo, ADR-064; este GET firma preview en cada 200)

Contextos vecinos: los de 053, más **Publicación / SyncDelivery** (contrato A, solo verificación) e **Idempotencia de GenerationJob** (patrón a reutilizar, no a copiar a ciegas).

---

## Herencia de 053 (no se redefine)

El modelo estático de 053 sigue vigente: raíz `Photoshoot`, cuatro `PhotoshootStage`, 0..N `PhotoshootResult`, `GenerationJob` fuera del agregado, `derive` como autoridad del status, cartesiano uniforme, `skipped` ≠ `failed`, completar ≠ publicar.

Lo que 053 dejó explícitamente abierto y este bolt cierra:

| Hueco 053 | Cierre 054 |
|-----------|------------|
| `GET .../photoshoots/{id}` no registrado | Vista de lectura `PhotoshootView` |
| `idempotency_key` / `payload_fingerprint` persistidos **sin** UNIQUE ni replay | Reserva única + `resolve_or_replay` |
| `variant_key` en esquema; V1 422 `VARIANT_NOT_SUPPORTED` como placeholder | Asiento real: persistir, devolver, no usar |
| `derive` interno para no colgar en `running` | La misma derivación alimenta el GET; no hay segunda columna de status |
| Slot `UNIQUE(photoshoot_id, model_id, pose_id)` + lease delegado | Se **prueba** como la garantía NFR-5 de etapa/mensaje duplicado |

---

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| **Photoshoot** (existente, semántica ampliada) | Las de 053 + semántica de reserva: `idempotency_key?`, `payload_fingerprint?`, `variant_key?` | Si hay `idempotency_key`, el par `(product_link_id, idempotency_key)` es **único** en el tenant del vínculo. La huella se congela en el primer accept y no se reescribe. Replay con la misma reserva **nunca** crea fila, **nunca** encola, **nunca** relanza un `failed`. Sin clave: se permite; no hay protección de duplicado (responsabilidad de BFashion). `status` persistido es el último `derive`; no existe un status paralelo de lectura. |
| **PhotoshootStage** (existente) | Sin campos nuevos | El GET las proyecta tal cual (`name`, `status`, `error_code`, marcas de tiempo). No se recalculan. `skipped` se expone como desenlace, no como fallo. |
| **PhotoshootResult** (existente, semántica ampliada) | Las de 053 + `variant_key?` | Existe solo con `GenerationJob` `completed` y `result_key` durable. `variant_key` espeja el de la raíz en V1 (puede ser `null` o el texto que vino en el disparo). Un slot = como máximo un resultado (ya UNIQUE). Un fallo de sync posterior **no** borra esta fila ni su `result_key`. |
| **PhotoshootView** (nueva, no persistida) | Proyección de lectura: identidad + status derivado + etapas + contadores + `results[]` + `candidates[]` + `variant_key` + `error_code` | Se construye en una consulta de dominio. **Cero** llamadas al proveedor. **Cero** writes. Independiente del estado de `PublicationSelection` / destinos de sync. `completed` = disponible para revisión, nunca publicado. |
| **IdempotencyReservation** (concepto; vive en columnas de Photoshoot) | `scope` = `(tenant_id, product_link_id)`, `key`, `fingerprint`, `photoshoot_id` | Misma clave + misma huella → la misma reserva. Misma clave + huella distinta → conflicto, no overwrite. Clave ausente → no hay reserva. La clave **no** es global al tenant: dos productos pueden reutilizar el mismo string. |
| **ResultSlot** (053, reafirmado) | `(model_id, pose_id)` | Autoridad anti-duplicado de materialización. Un mensaje Celery duplicado que llega a un slot ya ocupado no crea segundo job ni segunda imagen. |
| **GenerationJob** (existente, fuera) | Portador publicable | Este bolt lo **lee** para armar `results[]` / `candidates[]`. No lo re-encola. Lease (`ConcurrencyGuardService`) sigue siendo por job delegado / materializado, no por el Photoshoot entero. |
| **PublicationCandidate** (existente, fuera) | Forma de `PublicationCandidateResponse` | El GET **proyecta** candidatos reutilizando `list_candidates` / la misma forma. No inventa un DTO paralelo. Overlay `blocked` no elimina el candidato base. |
| **PublicationSelection** / **SyncDestination** (existentes, fuera) | Contrato A: `Idempotency-Key = publication_selection_id`; destinos `virtual_closet` y `bfashion` | Este bolt **no** los escribe. Invariantes a verificar: reintento de entrega no regenera; `transfer_url` se remite fresco desde `storage_key`; fallo en un destino no revierte el otro; un resultado ya materializado sobrevive a un 5xx de BFashion. |
| **ProductLink** / **ServiceClient** (existentes) | Ancla de GET y de POST replay | GET: cliente autenticado + vínculo activo del `external_product_id`. Photoshoot de otro producto / otro tenant → respuesta opaca, sin filtrar existencia. POST replay exige el **mismo** vínculo que la reserva. |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| **PhotoshootId** | UUID | Identidad del agregado. En replay se **devuelve**, no se emite otra. |
| **PhotoshootStatus** | `queued` \| `running` \| `partial` \| `completed` \| `failed` | Misma máquina 053. El GET no tiene un status distinto. `completed` ≠ publicado. |
| **AggregateCounters** | `expected_results`, `completed_results`, `failed_results` | `expected` inmutable (053). `completed` = cardinalidad de `PhotoshootResult` con job `completed` + `result_key`. `failed` = huecos **irrecuperables** (rama muerta / photoshoot terminal sin ese slot). `failed` **no** cuenta overlay `blocked`. `completed + failed + still_open = expected`. En `queued` con 0 resultados: `completed=0`, `failed=0`. |
| **ResultProjection** | `generation_job_id`, `status`, `preview_url`, `variant_key`, `model_id?`, `pose_id?` | Una fila por `PhotoshootResult`. `status` es el del portador (`completed`). Sin `result_key` no hay proyección. `preview_url` es grant de vida corta, nunca la clave. |
| **CandidateProjection** | **la misma forma** que `PublicationCandidateResponse` | Compatibilidad estructural, no un alias informal. BFashion usa un solo lector. Incluye el candidato base aunque el overlay esté `blocked`. No incluye destinos de publicación ni `PublicationSelection`. |
| **PreviewGrant** | URL presignada, TTL corto, regenerable | Se emite **por lectura 200** desde `result_key` / `rendered_key` vía la función ya usada por publicación (`preview_object_url`). Nunca se persiste. Nunca se loguea. Nunca se sustituye por la clave de almacenamiento. GET 304 no aplica aquí (cada 200 resigna). |
| **IdempotencyKey** | texto no vacío, caller-supplied | Opcional en POST. Si falta, no hay reserva. No se infiere. No se reutiliza entre productos. |
| **PayloadFingerprint** | hash determinista del cuerpo **normalizado** | Misma función de espíritu que `compute_payload_fingerprint` (bolt 044). Entran: `staff_id`, `source_image_id`, `input_kind`, selección de modelos/poses, `cloth_type`, plantilla, overlay, `variant_key`, `external_wholesaler_id` si vino. No entra la propia `Idempotency-Key`. No entra `system` / `tenant_id` (salen del cliente). Orden de claves JSON irrelevante. |
| **IdempotencyOutcome** | `created` \| `replayed` \| `conflict` \| `unprotected` | `created`: primera vez con clave (o sin clave). `replayed`: misma reserva + misma huella → mismo `photoshoot_id`, `created=false`, HTTP 202, sin enqueue. `conflict`: misma reserva + huella distinta → 409, sin fila nueva. `unprotected`: POST sin clave. |
| **VariantKey** | texto libre o `null` | **No** es FK. `ProductVariant(color_label)` vive en BFashion. V1: se acepta y se persiste si viene; se devuelve siempre (incluso `null`). Ninguna regla de V1 filtra, agrupa ni valida contra un catálogo de colores. Esto **sustituye** el 422 `VARIANT_NOT_SUPPORTED` de 053, que era placeholder mientras 006 no estaba en alcance. |
| **PublicationReuseToken** | `publication_selection_id` | Contrato A. El reintento de entrega usa `Idempotency-Key =` este id. 409 de BFashion = duplicado exitoso, no error de negocio. |
| **DurableResultRef** | clave en `generated/photoshoots/...` (ADR-070) | Autoridad de que el resultado sobrevive a un fallo de sync. El reintento lee esta clave, no una URL caducada. |
| **OpaqueMiss** | señal de acceso denegado o no encontrado | Photoshoot inexistente → 404. Photoshoot de otro producto o tenant, o vínculo irresoluble → 404/403 **sin** filtrar si el id existe. Tras resolver el vínculo, un id ajeno no revela “existe pero no es tuyo”. |
| **QueueWaitDuration** / **ExecutionDuration** | duraciones (unidad 004) | El unit-brief pide honestidad de cola vs ejecución. **No** están en el contrato FR-8 de V1. Este bolt **no** las añade al GET. Quedan como extensión futura, no como campo inventado. |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| **Photoshoot** (el de 053, extendido) | Instantánea; 4 etapas; resultados; reserva de idempotencia; asiento de variante | Todas las invariantes 053 **más** las de abajo. |

`PhotoshootView` **no** es agregado: es un read model derivado. `PublicationSelection` sigue fuera.

### Invariantes añadidas (054)

1. El status que ve BFashion es el de `derive(etapas, resultados, expected, ramas abiertas)`. No hay tabla de “status de polling”.
2. `GET` es de solo lectura: no encola, no tick, no llama al proveedor, no materializa, no publica.
3. `candidates[]` ⊂ proyección de `list_candidates` sobre los `GenerationJob` de los resultados. Misma forma que `PublicationCandidateResponse`.
4. `preview_url` ∈ `PreviewGrant`. La clave durable nunca viaja como URL pública.
5. Completar el photoshoot crea **cero** `PublicationSelection`. El GET de un `completed` no implica publicado, aunque un candidato anterior de *otro* flujo esté entregándose.
6. Con `Idempotency-Key` K en el producto P: a lo sumo un `Photoshoot`. Replay = misma identidad. Conflicto = 409.
7. Replay de un photoshoot `failed` / `partial` / `completed` **no** lo relanza.
8. Sin `Idempotency-Key` no hay unicidad: dos POSTs idénticos pueden crear dos agregados (documentado; BFashion debe enviar la clave).
9. Un `ResultSlot` ocupado no acepta segunda materialización (ya UNIQUE). Un tick duplicado (ADR-068) observa el slot y las etapas terminales.
10. El lease anti-doble-llamada al proveedor es **por job delegado** (ADR-050 / 065 / 066), no un lease del Photoshoot completo.
11. Un `GenerationJob` + `result_key` ya persistidos sobreviven a cualquier fallo posterior de sync. Reintentar entrega **no** reinvoca Replicate (ADR-070).
12. Destinos `virtual_closet` y `bfashion` son independientes (FR-13). Este contexto no los acopla.
13. `variant_key` en raíz y en cada `PhotoshootResult` es coherente con el disparo. Se devuelve en el GET aunque sea `null`.
14. `uq_publication_selections_candidate` (`product_link_id`, `generation_job_id`, `composition_version_id`, `nulls_not_distinct`) **no** colisiona entre variantes futuras: cada variante produce `generation_job_id` distintos. V1 no cambia ese UNIQUE.
15. `tenant_id` y `system` siguen saliendo del `ServiceClient`. El GET no pide `staff_id` (mismo patrón que los GET del contrato B/C).
16. Ningún secreto, URL presignada ni clave de objeto se loguea (ADR-047, NFR-6).

### Máquina de estados (sin cambio)

```text
queued ──► running ──┬──► completed   (completed_results == expected_results)
                     ├──► partial     (≥1 completo y ≥1 hueco irrecuperable)
                     └──► failed      (0 completos y no queda trabajo)
```

El GET solo **observa**. Un photoshoot `queued` con 0 resultados y etapas `pending` → `candidates: []`.

### Replay vs relanzar

```text
POST + Key K + fingerprint F
  ├─ no existe reserva (P, K)     → created (053 submit)
  ├─ existe (P, K) y huella == F  → replayed (mismo id, sin enqueue)
  └─ existe (P, K) y huella ≠ F   → conflict (409)

POST sin Key                      → unprotected (siempre created)
```

No existe transición `failed → queued` por replay.

---

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| **PhotoshootViewRead** | GET autorizado construye la vista | `photoshoot_id`, `status`, `completed_results`, `failed_results` — **sin** URLs ni claves |
| **PhotoshootViewDenied** | Vínculo/tenant/producto/id ajenos o miss | `external_product_id`, `photoshoot_id?`, `reason` — **sin filtrar existencia** |
| **PhotoshootReplayed** | POST con reserva + huella iguales | `photoshoot_id`, `idempotency_key` (no el valor crudo en logs si se considera secreto de correlación; sí un hash), `status` actual |
| **PhotoshootIdempotencyConflict** | POST con reserva + huella distinta | `product_link_id`, `reason=fingerprint_mismatch` — no el body |
| **DuplicateTickObserved** | Tick/mensaje duplicado sobre agregado ya avanzado | `photoshoot_id`; no se emite `ResultMaterialized` de nuevo |
| **SlotAlreadyMaterialized** | `add_if_slot_free` pierde la carrera | `photoshoot_id`, `model_id`, `pose_id`, `existing_generation_job_id` |
| **PublicationRetryReusedResult** | Reintento de entrega (verificación) | `publication_selection_id`, `generation_job_id` — sin nueva inferencia |
| **SyncDestinationDiverged** | Un destino OK y el otro failed (verificación) | `publication_selection_id`, destinos y estados — sin revertir el OK |
| **VariantKeyRecorded** | Disparo (o replay) con `variant_key` no nulo | `photoshoot_id`, presencia del asiento — no se interpreta el valor |

V1: persistencia + logs estructurados, sin bus. Nunca loguear `preview_url`, `transfer_url`, `result_key`, secretos.

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| **PhotoshootQueryService** (nuevo) | `get_view(client, external_product_id, photoshoot_id) → PhotoshootView` | Resolver vínculo; `PhotoshootRepository.get_owned`; `derive` (053); `list_candidates` **solo lectura**; `preview_object_url` por resultado/candidato |
| **AggregateStatusDeriver** (053, autoridad única) | `derive(...) → PhotoshootStatus` + alimenta `AggregateCounters` | Etapas + resultados + `expected_results` + ramas abiertas. El GET no tiene otro deriver. |
| **PhotoshootIdempotencyService** (nuevo, o adaptación del existente) | `resolve(scope, key, fingerprint) → IdempotencyOutcome` | Reutiliza `IdempotencyService` / `compute_payload_fingerprint` si el contrato del servicio es lo bastante genérico; si está acoplado a `GenerationJob`, se aplica **el mismo patrón** sobre `PhotoshootRepository`, no un tercer algoritmo. |
| **PhotoshootSubmissionService** (053, extendido) | `submit(...)` ahora **empieza** por `resolve` cuando hay clave | Si `replayed`, return existente (`created=false`) **antes** de validar de nuevo el origen/credencial de forma que pudiera crear otra fila. Si `conflict`, 409. Si `created`/`unprotected`, el submit 053. |
| **ResultMaterializationService** (053) | `add_if_slot_free` sigue siendo la guarda de imagen duplicada | Este bolt añade la **prueba** explícita, no otra ruta de insert. |
| **ConcurrencyGuardService** (existente) | Lease por job de inferencia | Consumido por el camino delegado (052/053). 054 exige que un tick duplicado no pase el lease. |
| **PublicationCandidateAssembler** (existente, solo lectura) | `list_candidates(generation_job_id)` | No se edita `publication_service.py`. El query service itera jobs del photoshoot y concatena. |
| **PreviewUrlIssuer** (existente) | `preview_object_url(key) → PreviewGrant` | Misma función que publicación. Regenera en cada GET 200. |
| **SyncDeliveryService** (existente, **no se modifica**) | Reintento de contrato A | 054 solo **verifica** reuso de `storage_key`, `Idempotency-Key = publication_selection_id`, independencia de destinos. |

### Reglas de `get_view`

1. Autenticar `ServiceClient`. Fallo → no se revela si el producto o el photoshoot existen.
2. Resolver `ProductLink` activo para `external_product_id` + tenant del cliente. Fallo → 404/403 opaco.
3. `get_owned(photoshoot_id, product_link_id, tenant_id)`. Miss o ajeno → `OpaqueMiss` (404 para id inexistente; 404/403 opaco si es de otro producto/tenant).
4. No se pide `staff_id`. No se re-chequea vigencia de staff (el trabajo ya fue aceptado).
5. Cargar etapas + resultados + jobs portadores en lecturas a Postgres. Cero Replicate. Cero Celery.
6. `status = derive(...)`. Contadores según `AggregateCounters`.
7. `results[]` = proyección de cada `PhotoshootResult` (con `variant_key` explícito).
8. `candidates[]` = ensamblado por job, forma `PublicationCandidateResponse`. Overlay `blocked` no oculta el base.
9. Firmar `preview_url` por cada imagen visible. Fallo de MinIO al firmar → error de disponibilidad de lectura, **no** se degrada a devolver la clave.
10. Responder 200. p95 ≤ 1 s excluyendo transferencia (NFR-1).

### Reglas de idempotencia de disparo

1. Si no hay cabecera → `unprotected`, submit 053.
2. Calcular `PayloadFingerprint` del body ya validado en forma canónica. (Si el body es inválido → 422 **sin** tocar la reserva.)
3. `resolve(scope=(tenant, product_link), key, fingerprint)` bajo carrera: UNIQUE + relectura.
4. `replayed` → 202 con el photoshoot existente (`photoshoot_id` idéntico, `created=false`). No `CredentialGate`. No enqueue. No nuevas etapas.
5. `conflict` → 409. No se actualiza la huella. No se crea fila.
6. `created` → submit 053, persistiendo clave + huella en la misma transacción que la raíz.
7. Replay de `failed` devuelve `failed`. El cliente que quiera otro intento usa **otra** clave (fuera de alcance relanzar).

### Reglas de reintento de ejecución (NFR-5)

1. Autoridad de “ya hecho”: etapa terminal, `ResultSlot` ocupado, `GenerationJob.result_key` presente.
2. Tick duplicado (ADR-068) es idempotente: observa Postgres, no Replicate.
3. Lease ADR-050 en cada llamada al proveedor del camino delegado.
4. Persistencia fallida del objeto `generated`: reintentar **copia**, nunca inferencia (053 + ADR-070).
5. Este bolt no introduce un lease a nivel Photoshoot: M ramas no se serializan detrás de un único lock.

### Reglas de reintento de publicación (verificación)

1. No se toca el contrato A.
2. `Idempotency-Key = publication_selection_id`. 409 de BFashion = ya entregado.
3. `transfer_url` se vuelve a firmar desde `storage_key` / `result_key`; no se reutiliza un presign caducado.
4. Destinos independientes: dos fallos a `bfashion` + éxito en `virtual_closet` dejan esos estados.
5. Un 5xx de BFashion **después** de materializar no borra `PhotoshootResult` ni el objeto ADR-070.

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| **PhotoshootRepository** (053, extendido) | `Photoshoot` | `get_owned`; `find_by_idempotency(product_link_id, tenant_id, key)`; `add_aggregate` (ya UNIQUE-safe); `list_results_with_jobs(id)` para el GET |
| **PhotoshootResultRepository** (053) | `PhotoshootResult` | `add_if_slot_free` (sin cambio de contrato); `count_completed`; `get_by_slot` |
| **IdempotencyGuard** (persistencia) | reserva | UNIQUE parcial `(product_link_id, idempotency_key) WHERE idempotency_key IS NOT NULL`. Migración **aditiva**. Colisión → el servicio decide replay vs 409 leyendo la huella. |
| **GenerationJobRepository** (existente, lectura) | `GenerationJob` | Cargar portadores de los resultados; no crear desde el GET |
| **PublicationCandidate read** (existente) | candidato | `list_candidates` por `generation_job_id` |
| **ObjectStorage** (existente) | objeto | Solo **presign de descarga** en el GET; nunca PUT/inferencia |
| **ProductLinkRepository** (existente) | `ProductLink` | `resolve_active_link` |

No se añade tabla nueva. `variant_key` ya está; si 053 la creó, 054 no la vuelve a migrar. La UNIQUE de idempotencia **sí** es migración aditiva de este bolt (053 documentó que no la puso).

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Vista agregada / PhotoshootView** | Única respuesta de polling: status, etapas, contadores, resultados y candidatos. |
| **Derivar** | Calcular status y contadores desde etapas + resultados. No “actualizar status a mano”. |
| **Candidato** | Proyección `PublicationCandidateResponse` de un `GenerationJob` materializado. |
| **Resultado** | Celda (modelo, pose) ya materializada. Subconjunto del cartesiano. |
| **completed (photoshoot)** | Todos los resultados esperados listos para **revisión**. Nunca publicado. |
| **Preview grant** | URL corta regenerada por lectura. No es la clave. |
| **Reserva de idempotencia** | `(producto, Idempotency-Key)` → a lo sumo un photoshoot. |
| **Replay** | Devolver el photoshoot existente sin crear ni encolar. |
| **Conflicto de idempotencia** | Misma clave, distinto contenido → 409. |
| **Sin protección** | POST sin `Idempotency-Key`. BFashion asume el riesgo de duplicado. |
| **Relanzar** | Crear un photoshoot **nuevo** (otra clave). No ocurre por replay. |
| **Hueco irrecuperable** | Slot que ya no puede materializarse (rama muerta). Suma `failed_results`. Overlay `blocked` **no** es un hueco. |
| **Reusar resultado** | Reintentar entrega o sync desde `result_key` durable. No inferir otra vez. |
| **variant_key** | Asiento de texto libre para una futura variante de color. En V1 se guarda y se muestra; no se interpreta. |
| **Contrato C (lectura)** | `GET .../photoshoots/{id}`. Este bolt lo entrega. |
| **Contrato A** | Entrega a BFashion. Este bolt solo verifica que el reintento no duplica. |

## Decisiones de dominio que condicionan el diseño

1. **Un GET, no cinco.** FR-8. BFashion no sondea tryoff/vton/batch/job/publicación por separado.
2. **Un solo `derive`.** El status del 202, del worker y del GET es la misma función. Prohibido un campo “read_status”.
3. **`candidates[]` es la forma existente, no un parecido.** Un segundo DTO rompe el lector único de BFashion.
4. **Preview siempre resignado.** Igual espíritu que catálogo (ADR-064) pero **sin** 304: el body del photoshoot cambia con el progreso y firmar es barato frente a inferencia.
5. **Reserva acotada al `ProductLink`.** La clave de BFashion no es un mutex global del tenant.
6. **Reutilizar el patrón 044, no inventar otro.** `IdempotencyService` + `compute_payload_fingerprint`. Si el servicio actual solo habla de `GenerationJob`, se extrae el patrón; no se clona la semántica a ojo.
7. **UNIQUE parcial aditiva.** 053 no la puso. 054 sí. Sin backfill destructivo: filas 053 sin clave siguen válidas; dos filas 053 que ya compartan clave (si el test lo permitió) se resuelven en diseño técnico, no aquí.
8. **Replay no relanza.** Incluye `failed`. Historia 005 edge case.
9. **Clave ausente = permitido y desprotegido.** No se inventa una clave servidor.
10. **Lease por job, no por photoshoot.** Coherente con ADR-068 (tick) y con M ramas paralelas bajo el tope global.
11. **Publicación es verificación, no feature nueva.** Prohibido editar `publication_service.py` / `sync_delivery_service.py` para “hacer idempotente” lo que el contrato A ya es.
12. **`variant_key` se acepta.** Sustituye el 422 de 053. V1 no valida contra BFashion. Migración (si faltara) solo aditiva nullable.
13. **Selecciones futuras por variante no tocan el UNIQUE de publication.** Cada variante ⇒ otro `generation_job_id`. Se deja **probado**, no rediseñado.
14. **GET sin staff.** Polling es máquina a máquina. Fail-closed es del `ServiceClient` + vínculo + `get_owned`.
15. **FR-11 en la vista:** overlay `blocked` se ve en el candidato/composición, no como `failed_results`.
16. **Taxonomía HTTP (lectura y replay):**
    - Cliente inválido → no autenticado
    - Vínculo inexistente/inactivo/otro tenant → 404/403, sin filtrar
    - `photoshoot_id` inexistente → 404
    - Photoshoot de otro producto (vínculo ya resuelto) → 404/403 opaco
    - Replay OK → 202, mismo id
    - Conflicto de huella → 409
    - Body inválido en POST (antes de reserva) → 422, sin tocar reserva
    - GET OK → 200, cero inferencia

## Story Coverage

| Story | Cubierta por |
|-------|----------------|
| **004-aggregate-status-and-candidates** | `PhotoshootQueryService.get_view`; VOs `PhotoshootView`, `AggregateCounters`, `ResultProjection`, `CandidateProjection`, `PreviewGrant`, `OpaqueMiss`; eventos `ViewRead` / `ViewDenied`; `completed` ≠ publicado; GET no llama proveedor; overlay `blocked` no oculta el base; independencia del sync de publicación |
| **005-photoshoot-idempotency-and-retry** | `PhotoshootIdempotencyService` + UNIQUE; `IdempotencyOutcome`; replay / 409 / unprotected; no relanzar `failed`; `ResultSlot` + lease (NFR-5); verificación contrato A (`PublicationReuseToken`, destinos independientes, reuso de `DurableResultRef`) |
| **006-color-variant-forward-compat** | VO `VariantKey`; columnas en raíz y resultado; devolución explícita en GET; UNIQUE de `publication_selections` sin cambio; cero lógica de color; migración solo aditiva |

Historias 001–003 se **consumen**, no se reabren. El submit se extiende solo en el paso 0 de idempotencia.

## Prior Decisions Applied

- **ADR-054 / ADR-010**: unicidad en base + fast-path de servicio. La reserva de photoshoot sigue ese espíritu.
- **ADR-068**: tick + reagenda. El reintento de etapa es observar Postgres, no bloquear ni re-llamar al proveedor.
- **ADR-070**: copia bajo `generated/photoshoots/...`. Un fallo de sync no mata el candidato.
- **ADR-067 / 069**: no se tocan. GET solo proyecta etapas y celdas ya resueltas a `ModelPhoto.id`.
- **ADR-050 / 065 / 066**: lease y tope global en el camino delegado; 054 los exige en la prueba de mensaje duplicado.
- **ADR-047**: GET y logs sin secretos ni claves.
- **ADR-048 / 005**: replay **no** publica otra task; el primer accept ya hizo commit-then-enqueue.
- **ADR-061 / 040 / 012**: miss opaco. GET anidado al producto: 404 del id; 404/403 si es ajeno tras resolver el vínculo.
- **ADR-057**: GET no usa staff. POST replay no exige re-resolve para *crear*; el existente ya fue aceptado con staff vigente.
- **ADR-060**: dueño = espejo del vínculo. La reserva se acota a ese vínculo.
- **ADR-064**: se **lee** como precedente de preview regenerable; **no** se copia ETag al GET del photoshoot (el agregado cambia).
- **Contrato A / bolt 048**: `Idempotency-Key = publication_selection_id`; 409 = duplicado OK.

## Open Questions Retained

- **Forma exacta de `PublicationCandidateResponse`:** el modelo exige igualdad estructural. Stage 2 la copia campo a campo desde el schema existente (sin leer implementación en esta etapa). Si el schema creció con campos de overlay, `candidates[]` los lleva todos.
- **Filas 053 ya persistidas con la misma `Idempotency-Key`:** 053 permitió dos POSTs = dos filas. Stage 2 decide cómo la UNIQUE aditiva trata un entorno sucio de dev (índice no único previo, limpieza, o UNIQUE solo hacia adelante). El dominio exige: a partir de 054, a lo sumo una reserva por `(product_link, key)`.
- **¿`IdempotencyService` es genérico o solo de jobs?** Stage 2 lo confirma. El dominio no permite un tercer algoritmo de huella.
- **OQ-4 / duraciones de cola:** no entran en el contrato V1 del GET.

## Decisiones que el humano debe confirmar

1. **`variant_key` no nulo en V1 se acepta** (historia 006, edge case), en lugar del 422 `VARIANT_NOT_SUPPORTED` de 053.
2. **GET sin `staff_id`**, alineado a los GET del puente, no al POST.
3. **Sin ETag/304** en este GET (el recurso es vivo; preview se resigna cada 200).
