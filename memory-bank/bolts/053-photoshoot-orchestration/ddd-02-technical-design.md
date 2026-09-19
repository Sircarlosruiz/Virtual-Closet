---
unit: 003-photoshoot-orchestration
bolt: 053-photoshoot-orchestration
stage: design
status: complete
updated: 2026-09-19T15:58:00Z
---

# Technical Design - photoshoot-orchestration

## Architecture Pattern

**Layered DDD dentro del monolito FastAPI**, el patrón del proyecto (`api/routers → services → repositories → models`), con el worker Celery como borde de infraestructura para el pipeline.

No se introduce un contexto hexagonal ni un router paralelo. El contrato C ya vive en `integration`; este bolt **añade** un comando (`POST .../photoshoots`), tres tablas y un orquestador que **delega** inferencia. No llama a Replicate. No modifica `publication_service.py` ni `sync_delivery_service.py`.

Razones:

- `get_service_client` es el borde de autenticación de B y C.
- `StaffIdentityService.resolve_staff_identity` es el único gate de staff de C (ADR-057).
- `ProductLinkService.resolve_active_link` es la autoridad de propiedad (ADR-060).
- `CredentialGateService.require("replicate")` (bolt 052) es la guarda de credencial **antes de encolar**.
- `TryoffJobService`, `VTONJobService`, `PoseSetService` / `BatchSubmissionService` y `SkuCompositionService` ya saben crear y ejecutar su trabajo. El orquestador solo encadena identificadores.
- El camino de publicación solo reconoce `GenerationJob`. Materializar es crear el portador; no es inferir otra vez.

## Layer Structure

```text
┌─────────────────────────────────────────────────────────────┐
│ Presentation                                                │
│   api/routers/integration.py     +1 endpoint contrato C     │
│   api/schemas/integration.py     DTOs submit / 202          │
├─────────────────────────────────────────────────────────────┤
│ Application                                                 │
│   services/photoshoot_submission_service.py      NUEVO      │
│   services/photoshoot_orchestration_service.py   NUEVO      │
│   services/photoshoot_materialization_service.py NUEVO      │
│   services/photoshoot_pipeline_policy.py         NUEVO      │
│   StaffIdentity / ProductLink / CredentialGate   reutilizados│
├─────────────────────────────────────────────────────────────┤
│ Domain                                                      │
│   models/photoshoot.py   Photoshoot, Stage, Result  NUEVO   │
│   AggregateStatusDeriver (función pura)                     │
│   excepciones de dominio en services/                       │
├─────────────────────────────────────────────────────────────┤
│ Infrastructure                                              │
│   repositories/photoshoot_repo.py                NUEVO      │
│   tasks/photoshoot_orchestration.py              NUEVO      │
│   GenerationJobRepository / StorageService       reutilizados│
│   Tryoff / VTON / PoseSet / Composition          delegación │
│   alembic/versions/*_photoshoots.py              NUEVO      │
└─────────────────────────────────────────────────────────────┘
```

Responsabilidades por capa:

- **Router**: `Depends(get_service_client)`, traduce excepciones → HTTP, no contiene reglas, no espera etapas.
- **Submission service**: validación, `expected_results`, persistencia, commit, enqueue.
- **Orchestration service**: máquina de etapas, ramas, delegación, derivación de estado. Lo invoca Celery, no el request HTTP.
- **Materialization service**: portador `GenerationJob` + `PhotoshootResult` + overlay opcional.
- **Repository**: insert del agregado, lookup acotado, transiciones de etapa condicionales, `add_if_slot_free`.
- **Task**: solo `photoshoot_id`; reagenda; cero bytes y cero secretos (ADR-047).

## Components

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Model | `models/photoshoot.py` | ORM `Photoshoot`, `PhotoshootStage`, `PhotoshootResult` |
| Repository | `repositories/photoshoot_repo.py` | `add_aggregate`, `get`, `get_owned`, `transition_stage`, `add_result_if_slot_free`, `save_external_refs` |
| Service | `services/photoshoot_submission_service.py` | `submit(...)` |
| Service | `services/photoshoot_orchestration_service.py` | `tick(photoshoot_id)` — avanza lo que se pueda y devuelve `done \| reschedule` |
| Service | `services/photoshoot_materialization_service.py` | `materialize_slot(...)` |
| Service | `services/photoshoot_pipeline_policy.py` | `plan(input_kind, overlay?)` → cuatro etapas con `required \| skipped` |
| Service | `services/photoshoot_status.py` | `derive(stages, result_count, expected, branches_open) → status` |
| Schema | `api/schemas/integration.py` | Request/response del POST; `extra = "ignore"` |
| Router | `api/routers/integration.py` | `POST .../photoshoots` bajo `/api/integration/v1` |
| Task | `tasks/photoshoot_orchestration.py` | `photoshoot_tick_task(photoshoot_id)` en cola `photoshoot` |
| Auth | `get_service_client` | Reutilizado |
| Staff | `resolve_staff_identity` | Reutilizado; no `_authorize_staff` |
| Link | `resolve_active_link` | Reutilizado |
| Source | `BridgeSourceImage` repo `get_owned` | Reutilizado (051) |
| Gate | `CredentialGateService.require("replicate")` | Reutilizado (052) |
| Jobs | `GenerationJobRepository` | Reutilizado; **sin SQL directo** |
| Config | `core/config.py` | `PHOTOSHOOT_DEFAULT_POSE_COUNT=3`, `PHOTOSHOOT_TICK_COUNTDOWN_SECONDS=5`, `PHOTOSHOOT_MAX_TICKS` (safety) |

`GET .../photoshoots/{id}` **no** se registra en 053 (bolt 054). El `202` ya lleva `stages` y `expected_results`.

`integration_service.py` **no** se edita.

---

## Decision: etapa `vton` es puerta, no inferencia de pago

La historia 002 exige delegar en `VTONJobService` **y** en `PoseSetService`. PoseSet ya expande a N `BatchItem` → N `VtonJob` (bolt 030). Una inferencia extra por modelo **antes** de PoseSet duplicaría coste, latencia y presión sobre el tope global (OQ-3 / cap 2).

**Elegido:** la etapa `vton` **valida y enlaza** cada rama a través de la superficie de `VTONJobService` (propiedad de prenda/modelo, `cloth_type`, que el `garment_id` efectivo existe). No llama a `generate` / no encola un `VtonJob` de pago.

- `garment_on_model`: `garment_id` efectivo = media que dejó `tryoff`.
- `flat_garment`: `garment_id` efectivo = `registered_media_id` de la reserva `ready`.

Si la validación de un modelo falla → esa rama `failed`; las demás siguen. Si pasa → etapa `vton` del agregado se cierra `completed` cuando **todas** las ramas vivas validaron (las fallidas quedan anotadas en `external_refs`). PoseSet es el único sitio que dispara inferencia VTON de este photoshoot.

Si en implementación `VTONJobService` no expone un `validate_pairing` público, se extrae/reutiliza **esa** validación (misma función que el servicio ya usa al crear un job) sin publicar task. No se reimplementa inferencia.

Esto es candidato ADR (Stage 3).

## Decision: `pose_ids` del contrato C son tipos de pose, no `ModelPhoto.id`

El catálogo (056) expone `available_poses: ["front", "side"]`, no ids de foto. PoseSet exige `ModelPhoto.id` (ADR-044).

**Elegido:** el body acepta `pose_ids: ["front", "side"]` **o** `pose_count`. El servidor resuelve, por cada modelo, el `ModelPhoto.id` de ese tipo. El cartesiano es uniforme: todo modelo debe tener **todas** las poses pedidas; si falta una → 422, sin fila.

`pose_count` / default (OQ-4, `PHOTOSHOOT_DEFAULT_POSE_COUNT=3`): se toman las primeras N del orden canónico `front < side < back` **que existan en todos** los modelos. Si el mínimo común es menor que el recuento pedido → 422.

`PhotoshootResult.pose_id` guarda el `ModelPhoto.id` resuelto (identidad de la celda). La instantánea guarda ambos: tipos pedidos y el mapa modelo → fotos.

## Decision: espera = tick + reagenda, no worker bloqueado

Tryoff y PoseSet tardan minutos. Bloquear `photoshoot_tick_task` en un poll in-process choca con `time_limit` (misma razón que ADR-065).

**Elegido:** un único task `photoshoot_tick_task(photoshoot_id)`:

1. Carga el agregado. Si ya es terminal (`completed|partial|failed`) → return.
2. `OrchestrationService.tick`: arranca lo que falte, observa jobs delegados **por Postgres** (cero llamadas a Replicate), materializa slots listos, deriva estado.
3. Si aún hay trabajo → `apply_async` de sí mismo con `countdown = PHOTOSHOOT_TICK_COUNTDOWN_SECONDS`.
4. Si terminal → no reagenda.

Cola dedicada `photoshoot` (precedente ADR-004 `tryoff`): los ticks no compiten por prefetch con inferencia.

El mensaje es `{photoshoot_id}`. Nada más.

---

## API Design

Base: `/api/integration/v1`. Auth: `X-Service-Id` + `X-Service-Secret`. Sin cookie.

Los schemas **no declaran** `system` ni `tenant_id`. `extra = "ignore"`.

Cabecera `Idempotency-Key`: se **acepta y se persiste** si viene, junto con `payload_fingerprint`. En 053 **no** hay replay ni UNIQUE. Dos POSTs = dos photoshoots. Bolt 054 añade la semántica FR-12.

### POST `/api/integration/v1/products/{external_product_id}/photoshoots`

**Request**

```json
{
  "staff_id": "uuid",
  "external_wholesaler_id": "string | null",
  "source_image_id": "uuid",
  "input_kind": "garment_on_model | flat_garment",
  "template_id": "uuid | null",
  "model_ids": ["uuid"],
  "pose_ids": ["front | side | back"],
  "pose_count": "1..3 | null",
  "cloth_type": "upper_body | lower_body | dress",
  "background": "string | null",
  "colors": "string | string[] | null",
  "overlay": {
    "text": "string",
    "placement": "string",
    "style": "string"
  },
  "variant_key": null
}
```

Reglas de body:

- `model_ids` no vacío, sin duplicados.
- `pose_ids` y `pose_count` son mutuamente excluyentes. Si vienen ambos → 422. Si no viene ninguno → default de config (3).
- `overlay` ausente, `null` o `text` vacío/whitespace → photoshoot **sin** overlay.
- `variant_key` distinto de `null` → 422 (`VARIANT_NOT_SUPPORTED`).
- `cloth_type` ∈ enum del catálogo (misma constante que 056). Otro → 422.

**Response 202**

```json
{
  "photoshoot_id": "uuid",
  "external_product_id": "string",
  "status": "queued",
  "expected_results": 9,
  "stages": [
    {"name": "tryoff", "status": "pending"},
    {"name": "vton", "status": "pending"},
    {"name": "poses", "status": "pending"},
    {"name": "composition", "status": "pending"}
  ],
  "created_at": "2026-09-19T15:58:00Z"
}
```

Para `flat_garment`, `tryoff.status` nace `"skipped"`. Sin overlay, `composition.status` nace `"skipped"`.

No se espera ninguna etapa. p95 ≤ 1 s (NFR-1).

HTTP **202** (aceptado para proceso asíncrono), no 201. FR-5 manda sobre la convención genérica de “created”.

---

## Data Persistence

### Tabla nueva `photoshoots`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default `gen_random_uuid()` |
| `product_link_id` | UUID | NOT NULL, FK → `product_links.id` ON DELETE RESTRICT |
| `staff_id` | UUID | NOT NULL, FK → `mayoristas.id` ON DELETE RESTRICT |
| `source_image_id` | UUID | NOT NULL, FK → `bridge_source_images.id` ON DELETE RESTRICT |
| `tenant_id` | UUID | NOT NULL, FK → `tenants.id` |
| `mayorista_id` | UUID | NOT NULL, FK → `mayoristas.id` — copia de `product_links.mayorista_id` |
| `input_kind` | VARCHAR | NOT NULL, check ∈ {`garment_on_model`, `flat_garment`} |
| `configuration` | JSONB | NOT NULL — instantánea congelada |
| `status` | VARCHAR | NOT NULL, default `queued`, check ∈ {`queued`, `running`, `partial`, `completed`, `failed`} |
| `expected_results` | INTEGER | NOT NULL, `> 0` |
| `idempotency_key` | VARCHAR | NULL — asiento 054; sin UNIQUE en 053 |
| `payload_fingerprint` | VARCHAR | NULL — asiento 054 |
| `variant_key` | VARCHAR | NULL — asiento 054/006; V1 siempre NULL |
| `error_code` | VARCHAR | NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default `now()` |

Índices:

- `ix_photoshoots_owned` (`tenant_id`, `product_link_id`, `id`)
- `ix_photoshoots_link_status` (`product_link_id`, `status`)
- `ix_photoshoots_source` (`source_image_id`)

### Tabla nueva `photoshoot_stages`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `photoshoot_id` | UUID | NOT NULL, FK → `photoshoots.id` ON DELETE CASCADE |
| `name` | VARCHAR | NOT NULL, check ∈ {`tryoff`, `vton`, `poses`, `composition`} |
| `status` | VARCHAR | NOT NULL, default `pending`, check ∈ {`pending`, `running`, `skipped`, `completed`, `failed`} |
| `external_job_id` | UUID | NULL — trabajo **compartido** (tryoff) |
| `external_refs` | JSONB | NOT NULL, default `[]` — trabajos **por rama** |
| `error_code` | VARCHAR | NULL |
| `started_at` | TIMESTAMPTZ | NULL |
| `completed_at` | TIMESTAMPTZ | NULL |

`UNIQUE (photoshoot_id, name)` — siempre cuatro filas, nunca duplicadas.

`external_refs` (V1):

```json
[
  {
    "model_id": "uuid",
    "kind": "vton_validate | pose_set | batch",
    "id": "uuid | null",
    "status": "pending | running | completed | failed",
    "error_code": "string | null"
  }
]
```

Una fila de etapa no puede expresar M jobs en `external_job_id`. Los ids por modelo viven en `external_refs`. `tryoff` usa `external_job_id` (un solo trabajo).

### Tabla nueva `photoshoot_results`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `photoshoot_id` | UUID | NOT NULL, FK → `photoshoots.id` ON DELETE RESTRICT |
| `generation_job_id` | UUID | NOT NULL, FK → `generation_jobs.id` ON DELETE RESTRICT, UNIQUE |
| `model_id` | UUID | NOT NULL, FK → `models.id` |
| `pose_id` | UUID | NOT NULL, FK → `model_photos.id` |
| `variant_key` | VARCHAR | NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` |

`UNIQUE (photoshoot_id, model_id, pose_id)` — autoridad del `ResultSlot` (ADR-010 / ADR-054).

### Instantánea `configuration` (JSONB)

```json
{
  "input_kind": "garment_on_model",
  "source_image_id": "uuid",
  "registered_media_id": "uuid",
  "registered_media_kind": "source_image | garment_photo",
  "template_id": "uuid | null",
  "cloth_type": "upper_body",
  "background": "string | null",
  "colors": null,
  "overlay": {"text": "blusa-manga-globo", "placement": "…", "style": "…"} ,
  "model_ids": ["uuid"],
  "pose_types": ["front", "side", "back"],
  "resolved_poses": {
    "<model_id>": [
      {"pose": "front", "model_photo_id": "uuid"}
    ]
  },
  "garment_id_effective": "uuid | null"
}
```

`garment_id_effective` se rellena al cerrar `tryoff` (o al submit si `flat_garment`, desde `registered_media_id`). Copia congelada: no se relee `ImageTemplate` después (ADR-052).

### Tablas existentes

Sin migración en `generation_jobs`, `product_overlays`, `composition_versions`, `pose_sets`, `batch_jobs`. El portador se inserta con las columnas que `GenerationJobRepository` ya conoce: `owner_id`, `mode`, `provider`, `status`, `result_key`, `input_data`.

`mode = try_on`, `provider = replicate` (FR-9). `status` nace distinto de `completed` y pasa a `completed` **solo** con `result_key`.

### Clave durable de resultado

```text
generated/photoshoots/{photoshoot_id}/{model_id}/{pose_id}
```

Si la media del `BatchItem` ya es un objeto durable, se **copia** a esta clave (NFR-5: el photoshoot posee su objeto; un borrado en la biblioteca de batch no apaga el candidato). Si la copia falla, el slot no se materializa y el tick reintenta la copia, **sin** rellamar al proveedor.

### Migración Alembic

Una revisión: tres tablas + índices + FKs + CHECKs. Downgrade: `DROP` en orden `photoshoot_results`, `photoshoot_stages`, `photoshoots`. Sin backfill.

---

## Use-case flows

### `submit`

1. `get_service_client` → 401 idéntico si falla.
2. Validar body Pydantic (enums, exclusividad `pose_ids`/`pose_count`, `variant_key is null`). Inválido → 422, **sin fila**.
3. `staff = resolve_staff_identity(client, staff_id)` → 403 `STAFF_FORBIDDEN`.
4. `link = resolve_active_link(...)` → 404 `PRODUCT_LINK_NOT_FOUND` (misma opacidad que 050/051).
5. `source = bridge_source_repo.get_owned(source_image_id, link.id, client.tenant_id)`.
   Ausente o de otro vínculo → 403 `SOURCE_IMAGE_FORBIDDEN` (ADR-061).
   `status ≠ ready` → 422 `SOURCE_IMAGE_NOT_READY`.
   `kind ≠ input_kind` → 422 `SOURCE_IMAGE_KIND_MISMATCH`.
6. `template_id` informado: existe y no archivada → else 422 `TEMPLATE_NOT_SELECTABLE`.
7. Resolver modelos: todos existen y pertenecen a `link.mayorista_id` (mismas reglas de visibilidad que 056). Ajeno/missing → 422 `MODEL_NOT_AVAILABLE`.
8. Resolver poses (tipos → `ModelPhoto.id` por modelo). Cobertura incompleta o `pose_count` fuera de 1..3 → 422 `POSE_SELECTION_INVALID`.
9. `cloth_type` ∈ constante de catálogo → else 422.
10. Overlay: texto vacío → sin overlay. Texto presente → `normalize_sku`; `len > SKU_MAX_LENGTH` → 422 `OVERLAY_TEXT_TOO_LONG` (FR-11 en el disparo).
11. `CredentialGateService.require("replicate")`. Ausente → 503 `PROVIDER_CREDENTIAL_MISSING`. No se degrada a OpenAI. No se persiste.
12. `expected_results = len(model_ids) * len(pose_types)`. Debe ser ≥ 1.
13. `PipelinePolicy.plan` → 4 etapas (`tryoff` skipped si flat; `composition` skipped si no overlay).
14. `add_aggregate` (raíz `queued` + 4 etapas). Flush.
15. Commit (ADR-048).
16. `photoshoot_tick_task.delay(photoshoot_id)` vía `transaction.on_commit` (ADR-005). Si el publish falla tras commit: la fila `queued` queda; reconciliación = primer tick manual/retry de broker. El `202` ya se puede enviar: hay estado durable.
17. 202. No loguear secretos.

### `tick` (Celery)

Idempotente. Un tick hace **como máximo** un avance de etapa (o materializa los slots ya listos). Luego reagenda si hace falta.

```text
queued → (al entrar) status = running

tryoff pending:
  garment_on_model → TryoffJobService.submit(source, owner) → external_job_id, stage=running
  si tryoff ya completed (DB) → escribir garment_id_effective, stage=completed
  si failed → stage=failed, photoshoot=failed, stop
  si aún running → reschedule

tryoff skipped (flat): garment_id_effective = registered_media_id

vton pending/running:
  para cada model_id sin ref: VTONJobService.validate_pairing(garment, model, cloth_type, mayorista, tenant)
    ok → ref completed; fail → ref failed (rama muerta)
  si todas las ramas decididas → stage completed|failed
  (failed de etapa vton solo si CERO ramas vivas)

poses pending/running:
  para cada rama viva sin pose_set: PoseSetService.submit_pose_set(
        mayorista_id=link.mayorista_id,
        tenant_id=link.tenant_id,          # ADR-045
        garment_id=garment_id_effective,
        model_id=model_id,
        cloth_type,
        pose_ids=[model_photo_id, ...]     # ADR-044
      ) → guardar pose_set_id + batch_id en external_refs
  observar BatchItem por Postgres
  por cada item complete con media: materialize_slot
  etapa poses completed cuando no quedan items pending/processing en ramas vivas
  rama cuyo PoseSet/batch failed → BranchFailed; otras siguen

composition pending (si no skipped):
  por cada PhotoshootResult sin overlay aún: SkuCompositionService.compose(...)  # ADR-053 sync
  UNIQUE(generation_job_id) / UNIQUE(overlay_id, spec_hash) (ADR-054)
  fit fail → CompositionVersion blocked (ADR-056); job base intacto
  stage completed cuando todos los resultados existentes se intentaron
  (un compose failed no des-completa el job)

derive:
  completed si count(results) == expected_results
  partial si count >= 1 y no queda trabajo pendiente y count < expected
  failed si count == 0 y no queda trabajo pendiente
  else running
```

Materialización de un slot:

1. `add_result_if_slot_free` — si el UNIQUE choca, replay: no segundo job.
2. Copiar bytes/clave → `generated/photoshoots/{id}/{model_id}/{pose_id}`.
3. `GenerationJobRepository` crea job `owner_id=link.mayorista_id`, `provider=replicate`, `mode=try_on`, `input_data={photoshoot_id, model_id, pose_id, pose, stage: "poses"}` **sin secretos**.
4. Completar **solo** con `result_key`. Si la copia falló: no completar; el siguiente tick reintenta (NFR-5).
5. El job debe ser visible en `GET .../generation-jobs/{id}/publication-candidates` sin cambios en publication.

Reinicio de worker: ticks `completed`/`skipped` no se rehacen. `submit_pose_set` no se llama si ya hay `pose_set` id en `external_refs`. Slots ya materializados no se vuelven a copiar.

Todas las ramas de un photoshoot fallan en vton → `failed`, no `partial`.

---

## Security Design

| Concern | Approach |
|---------|----------|
| Autenticación de servicio | `get_service_client`; 401 idéntico, sin revelar recurso |
| Autorización de staff | `resolve_staff_identity` al submit (ADR-057) |
| Tenant isolation | `tenant_id` solo del cliente. Lookups con `tenant_id` + `product_link_id`. Listener ADR-012 |
| Propiedad | Dueño = `product_link.mayorista_id` (ADR-060). Ese UUID es el `owner_id` de cada `GenerationJob` |
| Origen | `get_owned`; miss/ajeno → 403 `SOURCE_IMAGE_FORBIDDEN` (ADR-061) |
| Modelos / poses / plantilla | 422 si no son seleccionables para **ese** mayorista. No se oracula existencia en otro tenant (el producto ya resolvió) |
| Secretos | Cero API keys en HTTP, JSONB, `input_data`, mensaje Celery o logs (ADR-047, NFR-6) |
| Broker | Solo `photoshoot_id` |
| Fail-closed | Credencial ausente → 503, no 202. Combinación ilegal → 422, no encola |
| Publicación | Completar no crea `PublicationSelection` |

Staff revocado **después** del 202: el trabajo ya aceptado sigue (los resultados son del vínculo). No se re-resuelve staff en cada tick.

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| NFR-1 p95 ≤ 1 s en el disparo | Submit = lookups indexados + resolve de N≤3 modelos × ≤3 poses + insert + commit. Cero inferencia. Tick es async |
| NFR-1 consulta de estado | GET es 054 y no llama al proveedor. 053 no abre GET |
| NFR-2 tope global | No se reimplementa. PoseSet/VtonJob heredan 052. M×N competirán; el 202 no espera |
| NFR-5 durabilidad | Commit antes de enqueue. Copia a clave propia del photoshoot. Slot UNIQUE. Tick reintenta copia, no Replicate |
| NFR-5 no doble inferencia | `external_refs` + UNIQUE slot. Redelivery de tick es observación |
| NFR-6 aislamiento | Ver Security. Tests 401/403/404/422/503 y ausencia de secretos en logs |
| NFR-7 verificabilidad | Stage 5: al menos el camino de materialización deja jobs listables como candidatos. Photoshoots reales contra Replicate pueden quedar para 055 si el entorno no está |

## Error Handling

Excepciones de dominio en `services/` → HTTP en el router.

Forma de dominio: `{"detail": {"code": "...", "message": "...", "context": {}}}`. 401: `{"detail": "Unauthorized"}`.

| Error Type | HTTP | Code | Response |
|------------|------|------|----------|
| Cabeceras ausentes/inválidas, cliente o tenant inactivo | 401 | — | cuerpo idéntico |
| Staff desconocido, sin rol, otro tenant, o revocado | 403 | `STAFF_FORBIDDEN` | sin fila |
| Vínculo ausente, inactivo, otro tenant, otro mayorista, wholesaler mismatch | 404 | `PRODUCT_LINK_NOT_FOUND` | sin fila |
| `source_image_id` inexistente o de otro producto | 403 | `SOURCE_IMAGE_FORBIDDEN` | mismo cuerpo; sin revelar existencia |
| Origen no `ready` | 422 | `SOURCE_IMAGE_NOT_READY` | sin fila |
| `kind` ≠ `input_kind` | 422 | `SOURCE_IMAGE_KIND_MISMATCH` | sin fila |
| `cloth_type` / `pose_count` / exclusividad poses / body Pydantic | 422 | validación o `POSE_SELECTION_INVALID` | sin fila |
| Modelo o pose no cubiertos para el mayorista | 422 | `MODEL_NOT_AVAILABLE` / `POSE_SELECTION_INVALID` | sin fila |
| Plantilla inexistente o archivada | 422 | `TEMPLATE_NOT_SELECTABLE` | sin fila |
| Overlay texto > `SKU_MAX_LENGTH` | 422 | `OVERLAY_TEXT_TOO_LONG` | sin fila |
| `variant_key` no nulo | 422 | `VARIANT_NOT_SUPPORTED` | sin fila |
| `REPLICATE_API_KEY` ausente | 503 | `PROVIDER_CREDENTIAL_MISSING` | sin fila, no encola |
| Fallo de enqueue tras commit | 202 igual | — | fila `queued`; tick/reconciliación posterior |

Errores de etapa (solo persistidos + logs, no HTTP de submit): `TRYOFF_FAILED`, `VTON_GATE_FAILED`, `POSE_SET_FAILED`, `RESULT_PERSIST_FAILED`, `COMPOSITION_BLOCKED` / `COMPOSITION_FAILED`.

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| BFashion (intent 020) | Dispara el photoshoot; el poll GET es 054 | REST S2S |
| `StaffIdentityService` | Vigencia de staff | Interno (050) |
| `ProductLinkService` | Vínculo activo | Interno |
| `BridgeSourceImage` | Origen `ready` | Interno (051) |
| `CredentialGateService` | Presencia de clave Replicate | Interno (052) |
| `TryoffJobService` | Etapa tryoff | Interno + cola `tryoff` |
| `VTONJobService` | Puerta de rama (validate, no generate) | Interno |
| `PoseSetService` / `BatchSubmissionService` | Expansión N por modelo | Interno + colas batch/vton; ADR-043/044/045 |
| `SkuCompositionService` | Overlay por resultado | Interno, síncrono en el tick (ADR-053) |
| `GenerationJobRepository` | Portador publicable | Interno |
| `publication_service.list_candidates` | Verificación: el job aparece | Interno, **solo lectura**, sin editar el módulo |
| MinIO / S3 | Copia a `generated/photoshoots/...` | `StorageService` |
| RabbitMQ / Celery | Cola `photoshoot` + colas ya existentes | Ids only |
| PostgreSQL | Agregado + observación de jobs delegados | SQLAlchemy async |
| Replicate | Inferencia real | **Solo** vía servicios delegados / worker 052 |

## Transaction & concurrency

- **Submit:** una transacción: validar + insert agregado. Publish Celery en `on_commit`.
- **Tick:** una transacción corta por tick. No abre llamada al proveedor. Observa tablas ajenas en read.
- **Delegación:** cada `submit_pose_set` corre en su propia transacción (contrato 030 / ADR-043). El tick commitea los `external_refs` después de recibir los ids.
- **Materializar:** insert job + copia objeto + insert result en una transacción. UNIQUE de slot: quien pierde relee. Copia de objeto: si el storage falla, rollback del job incompleto (nunca `completed` sin clave).
- **Compose:** síncrono por resultado ya commiteado (ADR-053). Fallo de fit no rollbackea el job.
- Sin Redis nuevo. El tope global sigue en 052.
- Sin lease propio sobre el photoshoot en 053: la idempotencia es de etapa/`external_refs`/slot. (054 puede añadir lease de retry.)

## Logging

`core/logger.py`, estructurado:

- info: `photoshoot_accepted`, `photoshoot_enqueued`, `stage_started`, `stage_completed`, `stage_skipped`, `result_materialized` con ids, `input_kind`, `expected_results`, `tenant_id`
- warn: `branch_failed`, `stage_failed`, `result_persist_deferred`, `credential_missing` con **código**
- never: API keys, URLs presignadas, `X-Service-Secret`, bytes, `storage_key` en eventos de acceso ajeno

## Testing plan (contrato; ejecución en Stage 5)

- Submit 202: `queued`, 4 etapas, `expected_results` = M×N, `created_at`; fila persistida **antes** de que exista resultado
- `flat_garment`: `tryoff=skipped`, no `failed`
- Sin overlay: `composition=skipped`
- `source_image` no ready / kind mismatch → 422, 0 filas
- Sin `model_ids` → 422
- `cloth_type` desconocido → 422
- `pose_count` 0 o 4 → 422
- Modelo sin una pose pedida → 422
- Plantilla archivada → 422
- Overlay texto vacío → acepta sin overlay
- Overlay texto > max → 422
- `variant_key` no nulo → 422
- Staff revocado / vínculo irresoluble / origen ajeno → 403/404; origen ajeno **mismo** 403 que miss
- 401 cuerpo idéntico
- Credencial Replicate ausente → 503, 0 filas
- Respuesta y logs sin secretos
- Tick `garment_on_model`: orden tryoff → vton(validate) → M PoseSets → N×M materializaciones
- Fallo de un modelo: las otras ramas materializan; estado `partial` si hay ≥1 resultado
- Todos los modelos fallan en vton → `failed`
- Tryoff fail → `failed`, sin PoseSet
- 3×3 → 9 `GenerationJob` `completed` con `result_key` y `owner_id = link.mayorista_id`
- Cada uno aparece en `list_candidates` / GET publication-candidates **sin** patch de `publication_service.py`
- Slot UNIQUE: tick duplicado no crea 10º job
- Copia a MinIO fallida: job no `completed`; reintento de tick no llama al proveedor
- Overlay: `ProductOverlay` UNIQUE por job; fit fail → version `blocked`, job sigue candidato
- Completar photoshoot: 0 `PublicationSelection` nuevas
- PoseSet: `BatchItem.model_id` = `ModelPhoto.id`; `tenant_id` pasado (ADR-045)
- Worker restart: etapas `completed` no se re-submiten

## Out of scope (reafirmado)

- GET agregado y `candidates[]` (054)
- Replay `Idempotency-Key` (054)
- Variantes de color (054; columna nullable)
- Cancelación
- Editar publication / sync delivery / `integration_service.py`
- Reimplementar inferencia o cliente Replicate
- Multipart, cookie-auth, catálogo (056 ya existe)

## ADR candidates (Stage 3)

1. **Etapa `vton` como puerta de validación, no inferencia de pago** — evita duplicar M llamadas a Replicate que PoseSet ya hará. Afecta coste, tope global y el significado de `VTONJobService` en este bolt.
2. **Tick Celery + reagenda (cola `photoshoot`) en lugar de worker bloqueado** — misma familia que ADR-065; el orquestador no puede sentarse minutos en un `time_limit`.
3. **`pose_ids` del contrato C = tipos (`front\|side\|back`), resolución a `ModelPhoto.id` en servidor** — alinea 056 con ADR-044. Si se mandaran UUIDs, BFashion no los tiene hoy.
4. **Copia a clave propia `generated/photoshoots/...` en la materialización** — el candidato no depende de que la media de batch siga viva.

1 y 2 tienen más peso ADR (coste / fiabilidad / patrón de worker). 3 es contrato C (vale la pena). 4 es consecuencia de NFR-5; se puede saltar si no aporta.
