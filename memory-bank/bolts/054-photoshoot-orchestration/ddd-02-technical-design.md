---
unit: 003-photoshoot-orchestration
bolt: 054-photoshoot-orchestration
stage: design
status: complete
updated: 2026-09-19T16:48:00Z
---

# Technical Design - photoshoot-orchestration (vista, idempotencia, asiento)

## Architecture Pattern

**Layered DDD dentro del monolito FastAPI**, continuación de 053 (`api/routers → services → repositories → models`).

No hay contexto nuevo. No hay router paralelo. El contrato C ya vive en `integration`. Este bolt **añade** una query (`GET .../photoshoots/{id}`), **cierra** el replay de `POST .../photoshoots`, y **ajusta** el asiento `variant_key`. El worker Celery y el pipeline de 053 no se rediseñan.

Razones:

- `get_service_client` y `resolve_active_link` son el borde de los GET del puente (catálogo 056, jobs 047). El polling no pide `staff_id`.
- `derive` de 053 es la autoridad de status. El GET la **recalcula en lectura** (sin write) para no servir un `running` colgado.
- `publication_service.list_candidates` y `preview_object_url` ya producen la forma que BFashion lee. Importar el schema; no clonar campos a ojo.
- `compute_payload_fingerprint` (044) es la huella. El UNIQUE del photoshoot **no** copia el índice compuesto de `generation_jobs`.
- Tick, lease y copia ADR-070 ya cubren el reintento de ejecución. 054 los **prueba**, no los reimplementa.
- Contrato A / `SyncDeliveryService` ya son idempotentes por `publication_selection_id`. 054 los **verifica**, no los edita.

## Layer Structure

```text
┌─────────────────────────────────────────────────────────────┐
│ Presentation                                                │
│   api/routers/integration.py     +GET photoshoot; POST replay│
│   api/schemas/integration.py     DTOs GET / POST created     │
│   PublicationCandidateResponse   IMPORTADO, no duplicado     │
├─────────────────────────────────────────────────────────────┤
│ Application                                                 │
│   services/photoshoot_query_service.py           NUEVO       │
│   services/photoshoot_idempotency_service.py     NUEVO       │
│   services/photoshoot_submission_service.py      EXTENDIDO   │
│   services/photoshoot_status.py                  EXTENDIDO   │
│   publication_service.list_candidates            solo lectura│
│   preview_object_url                             solo lectura│
├─────────────────────────────────────────────────────────────┤
│ Domain                                                      │
│   models/photoshoot.py   UNIQUE parcial de reserva  EXTENDIDO│
│   AggregateStatusDeriver + AggregateCounters                 │
│   excepciones Replay / Conflict / OpaqueMiss                 │
├─────────────────────────────────────────────────────────────┤
│ Infrastructure                                              │
│   repositories/photoshoot_repo.py   find_by_idempotency      │
│   alembic/*_photoshoot_idempotency_unique.py        NUEVO    │
│   tasks/photoshoot_orchestration.py                 SIN CAMBIO│
│   publication_service.py / sync_delivery_service.py SIN CAMBIO│
└─────────────────────────────────────────────────────────────┘
```

Responsabilidades:

- **Router GET**: `Depends(get_service_client)`, traduce miss → 404 opaco, no deriva reglas.
- **Router POST**: lee `Idempotency-Key`; el servicio decide created / replayed / conflict. 422 de body **antes** de tocar la reserva.
- **Query service**: vínculo + `get_owned` + derive + contadores + `results[]` + concat de `list_candidates` + preview.
- **Idempotency service**: `resolve(scope, key, fingerprint)` → outcome. No crea el agregado; eso sigue en submit.
- **Submission**: paso 0 = resolve si hay clave; `replayed` short-circuit; `conflict` 409; resto = 053 menos el 422 de `variant_key`.
- **Status**: `derive` + `counters(expected, results, stages, external_refs)`.
- **Repo**: lookup por reserva; carga agregada para el GET (raíz + etapas + resultados + jobs).
- **Task**: no se toca. Slot UNIQUE y `external_refs` ya hacen el tick idempotente (ADR-068).

`integration_service.py` **no** se edita.

---

## Components

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Schema | `PhotoshootViewResponse` | Cuerpo del GET (FR-8 + `variant_key` de raíz) |
| Schema | `PhotoshootResultItem` | `generation_job_id`, `status`, `preview_url`, `variant_key`, `model_id`, `pose_id` |
| Schema | `PublicationCandidateResponse` | **El tipo existente** (publication / integration). `candidates: list[That]` |
| Schema | POST 202 | Campos 053 + `created: bool` + `variant_key` |
| Service | `PhotoshootQueryService.get_view` | Lectura fail-closed, cero proveedor |
| Service | `PhotoshootIdempotencyService.resolve` | Reserva / replay / 409 |
| Service | `photoshoot_submission_service.submit` | Paso 0 idempotencia; acepta `variant_key` |
| Service | `photoshoot_status.derive` + `counters` | Autoridad única de status y `failed_results` |
| Repo | `find_by_idempotency(product_link_id, key)` | Una fila o none; siempre con `tenant_id` del cliente |
| Repo | `get_view_bundle(id, product_link_id, tenant_id)` | Raíz + stages + results + jobs en pocas queries |
| Model | `Photoshoot` | UNIQUE parcial `(product_link_id, idempotency_key)` |
| Router | `GET .../photoshoots/{photoshoot_id}` | 200 |
| Router | `POST .../photoshoots` | 202 replay o created; 409 conflicto |
| Alembic | índice único parcial | Aditivo; limpia duplicados 053 si los hay |
| Tests | query + idempotency + variant + publication reuse | Sin patch de publication/sync |

---

## Decision: UNIQUE de la reserva es la clave, no `(key, fingerprint)`

044 indexa `generation_jobs` por `(idempotency_key, payload_fingerprint)` y detecta el 409 en servicio. Ese índice **permite** dos filas con la misma clave y distinta huella: el 409 es una carrera.

FR-12 exige “a lo sumo un photoshoot por clave en este producto”. Por tanto:

```text
UNIQUE (product_link_id, idempotency_key) WHERE idempotency_key IS NOT NULL
```

`product_link_id` ya es UUID global; no hace falta meter `tenant_id` en el índice (el GET/POST siempre resuelven el vínculo del cliente antes).

Flujo bajo carrera:

1. Lookup por `(product_link_id, key)`.
2. Hit + huella igual → replay.
3. Hit + huella distinta → 409, sin write.
4. Miss → insert en la txn de submit. Si `IntegrityError` → releer: igual → replay; distinta → 409.

No se reutiliza `IdempotencyService` como clase si está acoplada a `GenerationJob`. Se reutiliza **`compute_payload_fingerprint`** (mismo algoritmo, cero tercera huella) y un servicio delgado sobre `PhotoshootRepository`. Extraer un protocolo genérico queda fuera: no es necesario para V1.

Candidato ADR (Stage 3).

## Decision: el GET re-deriva y no escribe

El status persistido lo actualiza el tick. Un proceso caído puede dejar `running` con cero trabajo pendiente.

`get_view` llama a `derive(...)` sobre el bundle leído y **no hace UPDATE**. El cuerpo refleja la verdad actual. El siguiente tick (si aún hay work o un reconciliador) persistirá. Polling de BFashion no tiene efecto de write (NFR-1, historia 004).

## Decision: `candidates[]` es el tipo existente, concatenado por job

No se declara un DTO paralelo. El campo se tipa con `PublicationCandidateResponse` (el de publicación / el alias que ya use el puente).

```text
for result in results_in_slot_order:
    candidates.extend(list_candidates(generation_job_id))
```

Volumen V1 acotado (OQ-4: ≤3×3 = 9). Un loop in-process cumple p95 ≤ 1 s. No se añade paginación.

`list_candidates` ya incluye el resultado base (`kind: generation_result`) y las `CompositionVersion` del overlay. Overlay `blocked` no es seleccionable (048) pero el **base sigue**. Si el assembler existente expone versiones `blocked` con status, se pasan. Si no, FR-11 se cubre con `stages[composition].error_code = COMPOSITION_BLOCKED` (053 ya lo persiste). **No** se parchea `publication_service.py` para “añadir blocked al GET”.

`preview_url` de cada candidato lo emite `list_candidates` / `preview_object_url`. `results[].preview_url` se firma desde `GenerationJob.result_key` con la **misma** función. Nunca la clave cruda.

## Decision: `variant_key` se persiste; se elimina `VARIANT_NOT_SUPPORTED`

053 rechazaba no-nulos. Historia 006 (edge) manda aceptar.

- Pydantic: `variant_key: str | None = None`. `extra = "ignore"` se mantiene.
- `""` / whitespace → `null` al persistir.
- Cualquier otro texto se guarda en raíz y se copia a cada `PhotoshootResult` en la materialización (053 ya tiene la columna).
- GET y POST 202 lo devuelven siempre (JSON `null` si vacío).
- Ningún filtro, agrupación ni FK.
- Huella: el valor canónico (null vs texto) **entra** en el fingerprint: cambiar `variant_key` con la misma clave → 409.

## Decision: POST replay responde 202 con el estado **actual**

No se finge `queued`. BFashion ya va a pollar el GET; devolver `completed` en un replay es honesto.

Cuerpo 202 (created y replay):

- campos 053 (`photoshoot_id`, `external_product_id`, `status`, `expected_results`, `stages`, `created_at`)
- `created: true | false`
- `variant_key`

Replay **no** llama `CredentialGate`, **no** `on_commit` enqueue, **no** re-valida origen (la reserva ya apunta a un agregado durable). Body inválido (Pydantic) → 422 **antes** del lookup, para no 409-ar un JSON roto contra una reserva sana.

---

## API Design

Base: `/api/integration/v1`. Auth: `X-Service-Id` + `X-Service-Secret`. Sin cookie. Schemas sin `system` / `tenant_id`. `extra = "ignore"`.

### GET `/api/integration/v1/products/{external_product_id}/photoshoots/{photoshoot_id}`

Sin query params. Sin `staff_id`. Sin `If-None-Match` (recurso vivo; cada 200 resigna preview).

**Response 200**

```json
{
  "photoshoot_id": "uuid",
  "external_product_id": "string",
  "status": "queued | running | partial | completed | failed",
  "variant_key": "string | null",
  "expected_results": 9,
  "completed_results": 3,
  "failed_results": 0,
  "error_code": "string | null",
  "stages": [
    {
      "name": "tryoff",
      "status": "skipped | pending | running | completed | failed",
      "error_code": "string | null",
      "started_at": "iso | null",
      "completed_at": "iso | null"
    }
  ],
  "results": [
    {
      "generation_job_id": "uuid",
      "model_id": "uuid",
      "pose_id": "uuid",
      "status": "completed",
      "preview_url": "https://…",
      "variant_key": "string | null"
    }
  ],
  "candidates": []
}
```

`candidates` es `list[PublicationCandidateResponse]` **sin campos extra ni de menos**. Orden: por `PhotoshootResult.created_at` (estable), y dentro de cada job el orden que ya use `list_candidates` (base primero, luego versiones).

`results[]` solo celdas materializadas (tienen `result_key`). Huecos irrecuperables no inventan filas: viven en `failed_results`.

**Errores GET**

| Caso | HTTP | Code |
|------|------|------|
| Auth inválida | 401 | cuerpo idéntico |
| Vínculo ausente / inactivo / otro tenant | 404 | `PRODUCT_LINK_NOT_FOUND` |
| `photoshoot_id` UUID válido, no existe | 404 | `PHOTOSHOOT_NOT_FOUND` |
| Existe pero otro `product_link` / otro tenant | 404 | `PHOTOSHOOT_NOT_FOUND` (mismo cuerpo; ADR-040) |
| MinIO no puede firmar preview | 503 | `PREVIEW_UNAVAILABLE` — **no** devolver claves |

### POST `/api/integration/v1/products/{external_product_id}/photoshoots`

Body 053, con `variant_key` opcional (ya no 422).

Cabecera opcional `Idempotency-Key`.

**Response 202** — created o replay, misma forma, `created` distingue.

**409** — `{"detail": {"code": "IDEMPOTENCY_CONFLICT", "message": "...", "context": {}}}` sin photoshoot_id ajeno ni body.

El resto de errores 053 se mantienen **excepto** `VARIANT_NOT_SUPPORTED`.

---

## Data Persistence

Sin tablas nuevas. Sin cambios en `generation_jobs`, `publication_selections`, `product_overlays`.

### `photoshoots` (existente, 053)

| Cambio | Detalle |
|--------|---------|
| UNIQUE parcial | `uq_photoshoots_link_idempotency` on `(product_link_id, idempotency_key) WHERE idempotency_key IS NOT NULL` |
| `variant_key` | Ya nullable VARCHAR. Se deja. Se **deja de** forzar null en submit |
| `payload_fingerprint` | Ya VARCHAR null. Se rellena siempre que haya clave; se compara en replay |

Índice de lectura GET: 053 ya tiene `ix_photoshoots_owned (tenant_id, product_link_id, id)`. Suficiente para `get_owned`.

### `photoshoot_results.variant_key`

Ya existe. Materialización copia `photoshoot.variant_key`. Sin backfill: resultados 053 quedan `null`, coherente con disparos V1.

### Migración Alembic (aditiva)

1. **Limpieza de duplicados 053** (dev/test pudieron crear dos filas con la misma clave): para cada `(product_link_id, idempotency_key)` con count > 1, conservar la de `created_at` mínimo; poner `idempotency_key = NULL` (y `payload_fingerprint = NULL`) en las demás. Esas filas quedan `unprotected`.
2. `CREATE UNIQUE INDEX uq_photoshoots_link_idempotency ON photoshoots (product_link_id, idempotency_key) WHERE idempotency_key IS NOT NULL`.
3. Downgrade: `DROP INDEX`. No se restauran claves nulled (ADR-041 espíritu: data step no se revierte).

Sin `NOT NULL` nuevo. Sin tocar `publication_selections`.

### Fingerprint canónico

Entrada: dict del body **ya validado** por Pydantic, más `staff_id` / `external_wholesaler_id`.

```text
{
  staff_id,
  source_image_id,
  input_kind,
  template_id,
  model_ids: sorted UUID strings,
  pose_ids: sorted | null,          # tipos, no ModelPhoto.id
  pose_count: int | null,
  cloth_type,
  background,
  colors: canonical JSON,
  overlay: canonical | null,        # text vacío ≡ null
  variant_key: null o texto strip,
  external_wholesaler_id
}
```

No entra: `Idempotency-Key`, `system`, `tenant_id`, path `external_product_id` (el scope es el vínculo).

`compute_payload_fingerprint(canonical)` — la función 044 (orden de claves irrelevante). Prohibido un `hashlib.sha256(json.dumps(...))` paralelo “por si acaso”.

---

## Use-case flows

### `get_view`

```text
1. get_service_client → 401 idéntico
2. resolve_active_link(external_product_id) → 404 PRODUCT_LINK_NOT_FOUND
3. repo.get_view_bundle(photoshoot_id, link.id, client.tenant_id)
     miss → 404 PHOTOSHOOT_NOT_FOUND
4. status = derive(stages, result_count, expected, branches_open)
   counters = counters(...)          # ver abajo
   NO flush / NO commit de status
5. results[] = cada PhotoshootResult + job.result_key
     preview_url = preview_object_url(result_key)
6. candidates[] = concat list_candidates(job_id) en el mismo orden
7. 200. Cero Celery. Cero Replicate.
```

Queries objetivo: 1 bundle (selectinload stages + results + jobs) + N `list_candidates` in-process (N ≤ expected ≤ 9). Si `list_candidates` hace su propio load de overlay, se acepta; no se reescribe.

### Contadores

```text
completed_results = count(PhotoshootResult)

slots_dead = Σ (poses_de_la_instantánea) para cada rama
             con ref vton/poses status=failed
             (tryoff failed ⇒ todas las celdas dead)

still_open = hay etapa pending/running que aún puede producir slots
             o hay items de batch no terminales en ramas vivas

failed_results =
  if not still_open: expected_results - completed_results
  else:              slots_dead
```

`queued` con 0 resultados: `completed=0`, `failed=0`.  
Overlay `blocked` **no** incrementa `failed_results`.  
`COMPOSITION_BLOCKED` vive en la etapa y, si el assembler lo expone, en el candidato de versión.

### `submit` (054 delta sobre 053)

```text
1. get_service_client
2. Validar body Pydantic (SIN exigir variant_key is null)
     inválido → 422, sin lookup de reserva
3. resolve_active_link
4. key = header Idempotency-Key strip | None
5. if key:
     fingerprint = compute_payload_fingerprint(canonical_body)
     outcome = idempotency.resolve(link.id, key, fingerprint)
       replayed → 202 created=false, vista ligera del existente
                  (status derivado, stages, expected, variant_key, created_at)
                  NO credential gate, NO enqueue
       conflict → 409 IDEMPOTENCY_CONFLICT
       miss → continuar 053 desde staff resolve, persistiendo key+fingerprint
              IntegrityError → resolver como 5 (replay o 409)
6. if no key:
     continuar 053 (unprotected). idempotency_key permanece NULL
7. variant_key: strip → None si vacío; persistir en raíz
8. Resto 053 (staff, origin, selection, credential, plan, commit, on_commit tick)
```

Materialización 053: al insertar `PhotoshootResult`, `variant_key = photoshoot.variant_key`.

### Reintento de ejecución (sin código nuevo de orquestación)

Contrato de prueba, no de rediseño:

- Tick duplicado: `add_result_if_slot_free` + `external_refs` ya poblados → 0 jobs extra, 0 llamadas a Replicate.
- Lease ADR-050 en el worker delegado: segundo `generate` del mismo job no arranca.
- Copia MinIO fallida: job no `completed`; tick siguiente copia, no infiere (ADR-070).

### Reintento de publicación (sin código nuevo)

Tests sobre el camino 048 existente, anclados a un `GenerationJob` de photoshoot:

- `Idempotency-Key = publication_selection_id` en contrato A; 409 = duplicado OK.
- `transfer_url` se reminta desde `storage_key` / `result_key`.
- Destino `bfashion` failed ×2 + `virtual_closet` synced → estados independientes.
- Borrar o fallar el sync **no** borra `photoshoot_results` ni el objeto `generated/photoshoots/...`.

---

## Security Design

| Concern | Approach |
|---------|----------|
| Autenticación | `get_service_client`; 401 idéntico |
| GET sin staff | Igual que catálogo 056 / GET job 047. Polling es S2S |
| POST staff | Sigue `resolve_staff_identity` en created; **no** en replay |
| Tenant / producto | `get_owned` con `tenant_id` + `product_link_id`. Miss y ajeno → mismo 404 |
| Preview | Presign de vida corta. Fallo → 503, nunca clave |
| Secretos | Cero API keys, cero `result_key` en JSON, cero preview en logs (ADR-047, NFR-6) |
| Idempotency-Key | No se loguea en claro; sí `photoshoot_id` + outcome |
| Replay | No relanza `failed`; no es un bypass de credencial para **crear** (no crea) |
| Publicación | Completar / GET no crean `PublicationSelection` |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| NFR-1 GET p95 ≤ 1 s | Lookups indexados + ≤9 candidatos. Cero Replicate. Cero tick |
| NFR-1 POST replay | Un SELECT por clave; 202 sin enqueue |
| NFR-5 disparo | UNIQUE + fingerprint. IntegrityError cerrado |
| NFR-5 ejecución | Slot UNIQUE + tick observación + lease 050 (ya en 053/052) |
| NFR-5 sync | ADR-070 + tests 048: el objeto y el job sobreviven |
| NFR-6 | 401/404 opacos; GET ajeno no distingue existencia |
| NFR-2 | GET no consume cap global |

## Error Handling

Forma de dominio: `{"detail": {"code", "message", "context"}}`. 401 plano.

| Error Type | HTTP | Code | Side effect |
|------------|------|------|-------------|
| Auth | 401 | — | — |
| Vínculo | 404 | `PRODUCT_LINK_NOT_FOUND` | — |
| Photoshoot miss / ajeno | 404 | `PHOTOSHOOT_NOT_FOUND` | — |
| Body POST inválido | 422 | validación | sin reserva |
| Huella distinta, misma clave | 409 | `IDEMPOTENCY_CONFLICT` | sin fila, sin enqueue |
| Preview MinIO | 503 | `PREVIEW_UNAVAILABLE` | sin claves |
| Resto submit | igual que 053 | **salvo** `VARIANT_NOT_SUPPORTED` (eliminado) | |

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| BFashion | Poll GET; reintenta POST con clave | REST S2S |
| `ProductLinkService` | Scope de GET y de reserva | Interno |
| `compute_payload_fingerprint` | Huella | Interno (044) |
| `list_candidates` | `candidates[]` | Interno, **solo lectura** |
| `preview_object_url` | `preview_url` | Interno, **solo lectura** |
| `SyncDeliveryService` | Verificación FR-12/13 | Interno, **sin editar** |
| PostgreSQL | UNIQUE + bundle GET | SQLAlchemy async |
| MinIO | Solo presign de lectura en GET | StorageService |
| Replicate / Celery photoshoot | No invocados por GET ni por replay | — |

## Transaction & concurrency

- **GET:** sesión de lectura. Autocommit. Cero writes. Derive in-memory.
- **POST created:** igual 053 (una txn + `on_commit` tick) más insert de key/fingerprint.
- **POST replay:** read-only tras el lookup. Sin commit de negocio.
- **POST conflict:** read-only.
- **Carrera created/created:** UNIQUE; el perdedor relee y replay/409.
- **Tick vs GET:** GET no bloquea el tick. Lectura committed. Puede verse `running` un instante antes del derive persistido; el derive in-memory lo corrige si los hijos ya están terminales.
- Sin Redis nuevo. Sin lease de photoshoot.

## Logging

- info: `photoshoot_view_read` (id, status, counters, tenant_id); `photoshoot_replayed`; `photoshoot_created` (053)
- warn: `photoshoot_idempotency_conflict`; `photoshoot_view_denied` **sin** revelar si existía
- never: `preview_url`, `transfer_url`, `result_key`, `Idempotency-Key` cruda, secretos

## Testing plan (contrato; Stage 5)

**004**

- GET queued 0 resultados → `status=queued`, `candidates=[]`, `completed=0`, `failed=0`
- GET running no llama proveedor (mock Replicate 0 hits)
- GET completed → `completed_results == expected`, `failed=0`, `candidates` no vacío, 0 `PublicationSelection` nuevas
- `candidates[]` instancia el mismo schema que el GET de publication-candidates de un job del photoshoot
- Overlay blocked: base en `candidates[]`; `failed_results` no sube; etapa composition `COMPOSITION_BLOCKED` o equivalente del assembler
- Photoshoot de otro producto / tenant → 404 `PHOTOSHOOT_NOT_FOUND` (cuerpo idéntico a miss)
- UUID inexistente → 404
- Vínculo irresoluble → 404 `PRODUCT_LINK_NOT_FOUND`
- 401 idéntico
- `preview_url` ≠ `result_key`; regenerable (dos GET, URLs distintas o firmas nuevas, misma clave interna)
- GET durante sync de un candidato anterior: status del photoshoot independiente
- `variant_key` presente en raíz y en cada result (null o texto)

**005**

- Misma clave + mismo body → mismo `photoshoot_id`, `created=false`, 1 sola fila, 1 solo enqueue histórico
- Misma clave + body distinto → 409, filas sin cambio
- Sin clave → dos POSTs = dos filas (documentado)
- Replay de `failed` → mismo id `failed`, 0 ticks nuevos
- Tick duplicado / redelivery: N jobs, no N+1 (053 slot UNIQUE, reafirmado)
- Publicación reintento: `Idempotency-Key = selection_id`; 409 BFashion mock = OK; 0 llamadas proveedor
- Sync `bfashion` fail + `virtual_closet` ok → estados independientes; `result_key` intacto
- `transfer_url` caducada se reminta desde clave (test 048 reusado o análogo)

**006**

- Columna nullable en `photoshoots` y `photoshoot_results`
- POST con `variant_key: "navy"` persiste y GET lo devuelve; V1 no filtra
- POST con `variant_key: null` / omitido → null
- UNIQUE publication_selections: dos jobs (dos “variantes”) del mismo `product_link` insertan dos selecciones sin colisión
- Migración UNIQUE: aditiva; duplicados 053 se nullean salvo el más antiguo

## Out of scope (reafirmado)

- Relanzar `failed` con la misma clave
- Deduplicar cuerpos distintos con distinta clave
- ETag/304 en el GET
- WebSocket, paginación, cancelación
- Editar `publication_service.py`, `sync_delivery_service.py`, `integration_service.py`
- Lógica de color / `ProductVariant`
- Duraciones cola vs ejecución (no están en FR-8)

## ADR candidates (Stage 3)

1. **UNIQUE parcial `(product_link_id, idempotency_key)` en lugar del índice compuesto 044 `(key, fingerprint)`** — cierra la carrera del 409 y acota la clave al producto. Desvío intencional del patrón de `GenerationJob`.
2. **Servicio de idempotencia del photoshoot + `compute_payload_fingerprint`, no reusar la clase `IdempotencyService` acoplada a jobs** — mismo algoritmo de huella, otro agregado. Evita un tercer hash y evita forzar un protocolo genérico ahora.

No ADR: aceptar `variant_key` (lo manda la historia 006); GET sin staff (precedente 056/047); sin ETag (el recurso es vivo).
