---
unit: 004-replicate-execution-reliability
bolt: 055-replicate-execution-reliability
stage: design
status: complete
updated: 2026-09-19T17:28:00Z
---

# Technical Design - replicate-execution-reliability (consumo y overlay)

## Architecture Pattern

Sigue el patrón por capas de 043/044/052 (`router → service → repository → model`, worker Celery en el borde). Este bolt **no abre endpoints de comando nuevos**. Hay dos superficies distintas:

1. **Consumo Replicate** — ampliación de un servicio de dominio ya existente (`UsageAccountingService`) y un sidecar de telemetría en el adaptador de 052. Persistencia en columnas `usage_*` / `usage_raw` JSONB ya entregadas en 044.
2. **Overlay con slug largo** — **verificación** del compositor 046 y de las garantías 053/054. Sin cambio de semántica de `spec_hash`, fuente ni política de una línea.

Rationale: 044 ya centralizó la normalización; el fallo actual es una whitelist con forma de OpenAI. 046/053/054 ya implementan FR-11. Meter un compositor nuevo o una tabla de billing violaría ADR-054 y el fuera-de-alcance de facturación.

## Layer Structure

```text
┌─────────────────────────────┐
│      Presentation           │  GET job (usage existente). GET photoshoot
│                              │  (blocked vs failed — verificación 054).
│                              │  Sin POST de coste. Sin editor de overlay.
├─────────────────────────────┤
│      Application            │  generate_image_task: pasa (provider, model,
│                              │  raw) a normalize tras la llamada.
│                              │  Photoshoot submit / composition: sin
│                              │  rediseño; tests de slug y SKU_MAX_LENGTH.
├─────────────────────────────┤
│        Domain               │  UsageAccountingService (whitelist por
│                              │  proveedor). ReplicateUsageRecognizer
│                              │  (rama interna). OverlayFitValidator /
│                              │  SkuCompositionService sin cambio de
│                              │  semántica.
├─────────────────────────────┤
│     Infrastructure          │  ReplicateTryOnAdapter sidecar de
│                              │  predicción. Postgres usage_raw JSONB.
│                              │  Pillow / sku_renderer (046) intacto.
└─────────────────────────────┘
```

## Components

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Service | `services/usage_accounting_service.py` (extendido) | `normalize(provider, model, raw) → UsageRecord`. Dispatch por proveedor. OpenAI: whitelist 044 intacta. Replicate: whitelist aditiva. Nunca fabrica `0`. |
| Service | rama `ReplicateUsageRecognizer` (mismo módulo, no paquete nuevo) | Extrae el subconjunto saneado; decide `reported` vs `unknown`. |
| Provider | `services/image_generation/replicate_tryon_adapter.py` (052, extendido) | Tras `generate`, expone sidecar `last_usage` / `last_model` (id de predicción, `metrics`, modelo). **No** edita `catvton_replicate_provider.py`. **No** cambia el protocolo ADR-046 (`generate` sigue devolviendo la imagen). |
| Worker | `tasks/image_generation.py` | Llama `normalize(job.provider, model, raw)` en éxito, fallo con telemetría parcial y timeout (`unknown`). Composición no llama a normalize. |
| Domain | `domain/composition_spec.py` / `sku_renderer` (046) | **Sin cambio de semántica.** Tests de slug > 30, una línea, medición = render. |
| Pipeline | submit photoshoot (053) | **Verifica** 422 `OVERLAY_TEXT_TOO_LONG` en disparo. No se reimplementa. |
| Query | GET photoshoot (054) | **Verifica** candidato base vivo + distinción `COMPOSITION_BLOCKED` vs generación fallida. No se parchea `publication_service.py`. |
| Artifact | `memory-bank/bolts/055-replicate-execution-reliability/nfr7-evidence.md` | Evidencia NFR-7 + posible `Oq1Escalation`. No es tabla. |
| Tests | `backend/tests/...` | Unitarios de whitelist; fixtures con forma real capturada; overlay determinista; suite live opcional con flag. |

## Decision: whitelist aditiva indexada por `provider`

Candidatos:

1. Inferir el proveedor por las claves presentes (`total_tokens` ⇒ OpenAI, `predict_time` ⇒ Replicate).
2. Dos servicios (`OpenAiUsageAccountingService` / `ReplicateUsageAccountingService`).
3. Un `normalize(provider, model, raw)` con dos conjuntos de claves.

**Elegido: (3).** El dominio exige que un campo de Replicate en un job OpenAI (o al revés) no contamine `reported`. Inferir por claves falla si un payload mezclado llega por error. Dos servicios duplican la regla `unknown ≠ 0`. El parámetro `provider` ya está en el job.

### Contratos

OpenAI (sin cambio; nombres de la historia 005 / 044):

```text
_SAFE_USAGE_FIELDS_OPENAI =
  total_tokens, input_tokens, output_tokens,
  input_tokens_details, output_tokens_details
```

Replicate (aditivo; nombres **provisionales** hasta capturar una invocación real):

```text
_SAFE_USAGE_FIELDS_REPLICATE =
  prediction_id,      # identidad de la predicción
  predict_time,       # metrics.predict_time
  total_time          # metrics.total_time si existe; si no, se omite
```

Reglas de mapeo (implementación, confirmadas en Stage 4 contra un JSON real):

1. Aceptar tanto plano (`predict_time`) como anidado (`metrics.predict_time`). Aplanar solo claves de la whitelist.
2. Alias de identidad: `id` / `prediction_id` → persistir como `prediction_id`.
3. Valores `null` o ausentes: no se escriben. **Prohibido** coercer a `0`.
4. Claves futuras (`input_token_count` de Replicate, etc.): se **ignoran** (evento de dominio `UnrecognizedUsageFieldDropped`), no rompen.
5. `reported` Replicate ⇔ `model` no vacío **y** al menos uno de `prediction_id` o `predict_time` con valor informado.
6. `reported` OpenAI ⇔ predicado 044 (algún campo de tokens informado + model). Campos Replicate no cuentan.
7. `call_count = 1` por invocación que llega a `normalize` con llamada efectuada. La composición no incrementa.
8. Timeout / sin payload → `status=unknown`, `raw={}`, `model` si se conocía el modelo configurado; si no, `model` null. Sigue ADR-049.

Firma:

```text
normalize(provider: str, model: str | None, raw: Mapping | None) → UsageRecord
```

Si algún caller 044/008 todavía llama `normalize(raw)` posicional, se mantiene un overload compatible: `normalize(raw)` se trata como OpenAI (regresión 008). Preferir la firma explícita en el worker 052. Stage 4 confirma callers y actualiza el worker; no se deja un default silencioso a Replicate.

`usage_raw` JSONB de 044 almacena solo el mapa saneado. **No hay migración** si la columna ya es JSONB (044). Si Stage 4 encuentra un check constraint o un tipado que solo admite claves de tokens, la migración es **aditiva** (soltar el check o documentar que JSONB libre ya vale). El diseño no presupone columnas `predict_time` propias.

## Decision: sidecar en el adaptador, protocolo ADR-046 intacto

El protocolo de generación (ADR-046) devuelve la imagen. Cambiar el valor de retorno rompería el adaptador OpenAI y cualquier test 043/052 del contrato.

**Elegido:** el `ReplicateTryOnAdapter` guarda `last_model` y `last_usage` (dict crudo **antes** de sanitize) en la instancia, en el mismo `generate` que ya envuelve `CatVTONReplicateProvider`. El worker lee el sidecar **después** de `generate` y **antes** de `normalize`. `finally` de 052 (release slot/lease) no se reordena.

```text
result = adapter.generate(...)
raw = getattr(adapter, "last_usage", None)
model = getattr(adapter, "last_model", None) or job.input_data/model configurado
record = UsageAccountingService.normalize(job.provider, model, raw)
repo.mark_invocation_completed(..., usage=record)
```

Cómo obtiene el adaptador la predicción **sin** editar `catvton_replicate_provider.py`:

1. Preferir si el provider envuelto ya expone el objeto predicción (atributo o valor de retorno interno). El wrap lo copia al sidecar.
2. Si el envuelto solo devuelve bytes/URL: el adaptador registra lo que sí conoce (modelo configurado `CATVTON_REPLICATE_MODEL`) y deja `last_usage` mínimo. Entonces `reported` **no** se cumple hasta que el wrap pueda leer `prediction.id` / `metrics` — Stage 4 **debe** lograr al menos id o `predict_time` de una llamada real, o el criterio de cierre de 005 falla.
3. Prohibido: un segundo cliente HTTP «solo para métricas». Prohibido: parsear logs.

OpenAI: el worker sigue pasando el dict de tokens que ya usa 044. El sidecar es opcional ahí.

Timeout: no hay sidecar fiable → `normalize(..., raw=None)` → `unknown`.

## Decision: V1 no expone coste; `UsageEstimate` queda como política, no como API

La historia exige que **si** se expone un coste, se identifique como estimación. Exponer un número inventado a partir de `predict_time` sin tarifa oficial es peor que no exponerlo.

**Elegido:** el GET de job conserva `{status, model, call_count}` (044). No se añade `cost`, `credits` ni `usd`. `usage_raw` **no** se devuelve en HTTP (sigue siendo persistencia interna, ADR-047). Si un log o un admin dump muestra `predict_time`, no se etiqueta como dinero.

`UsageEstimatePolicy` no se implementa como servicio en este bolt. Queda documentada para un intent de billing. Los tests afirman que la API de job **no** contiene campos de coste.

## Decision: overlay = tests de caracterización + evidencia, cero cambio de política

Candidatos:

1. Auto-size o wrap para slugs largos (OQ-1b/c) — **fuera**. Cambia `spec_hash` (ADR-054).
2. Fuente distinta de `default` — **fuera**. Historia 006.
3. Verificar el comportamiento actual y documentar OQ-1 si la mayoría queda `blocked`.

**Elegido: (3).** Stage 4 solo toca compositor/submit/GET si un test de caracterización demuestra un **bug** respecto al modelo (p. ej. recorte silencioso, `failed_results` que cuenta `blocked`, validación de longitud a mitad de pipeline). Un slug que no cabe no es un bug: es ADR-056.

### Superficies a verificar (no a rediseñar)

| Superficie | Criterio |
|------------|----------|
| POST photoshoot `overlay.text` | `normalize_sku`; `len > SKU_MAX_LENGTH` (200) → 422 `OVERLAY_TEXT_TOO_LONG`, cero fila (053). Slug de 31..200 caracteres **no** se rechaza por longitud. |
| `evaluate_fit` / render | Misma medición (046 NFR-3). Una línea. Fuente `default`. Texto completo dentro del lienzo o `blocked` con `fit_result` (anchos/altos + reason). Cero recorte, cero scale, cero overflow. |
| `CompositionVersion` | `blocked` ⇒ `rendered_key` null. Mismo `spec_hash` reusa la fila (ADR-054). |
| GET photoshoot | Base en `candidates[]`. `failed_results` no sube. Distinción vía `stages[composition].error_code = COMPOSITION_BLOCKED` y/o `status` de versión en el assembler (054). Job `failed`/`timed_out` es otro camino. |
| Guiones | `blusa-manga-globo` se normaliza como texto visible, no como SKU especial. |

### Evidencia NFR-7

Archivo `nfr7-evidence.md` en la carpeta del bolt, rellenado en Stage 4/5:

- ≥ 4 photoshoots reales contra Replicate: 2 `garment_on_model`, 2 `flat_garment`; prenda superior, inferior y vestido.
- ≥ 1 slug real de BFashion con `len > 30`.
- Por photoshoot: id, `input_kind`, cloth, slug usado, desenlace overlay (`valid` / `blocked` + motivo), al menos un `provider_invocation.usage_status`.
- ≥ 1 invocación `reported` con modelo.
- Si mayoría de slugs de esa muestra queda `blocked` con defaults → sección **OQ-1 escalado**, sin parche de compositor.

CI:

- Unitarios y de caracterización **siempre** (fixtures: payload Replicate capturado; imagen base + slug > 30).
- Suite live (`@pytest.mark.nfr7_live`) se salta sin `REPLICATE_API_KEY` y flag explícito. No falla el pipeline por falta de GPU/crédito.
- El criterio de **cierre del bolt** exige la evidencia live (o una captura fechada de una ejecución real adjunta al artifact). Un CI verde solo con mocks **no** cierra NFR-7 ni 005.

## API Design

Sin rutas nuevas. Contratos existentes, aserciones nuevas:

| Endpoint | Method | Cambio |
|----------|--------|--------|
| `GET /api/image-generation/jobs/{job_id}` | GET | Tras job Replicate real: `usage.status=reported`, `usage.model` no vacío. Sin campos de coste. `usage_raw` no se serializa. OpenAI: mismo body que 044. |
| `GET .../photoshoots/{id}` (contrato C, 054) | GET | Tests: overlay `blocked` ≠ `failed_results`; candidato `kind: generation_result` presente. |
| `POST .../photoshoots` | POST | Tests: slug > 200 → 422 `OVERLAY_TEXT_TOO_LONG`; slug 31–200 aceptado (si el resto del body es válido). |

Staff composition 046 (`POST /api/generation-jobs/{id}/composition`) no es el camino BFashion, pero los tests de `evaluate_fit` pueden invocarlo o el servicio directo. No se cambia el schema 046.

## Data Persistence

| Table | Columns | Relationships |
|-------|---------|---------------|
| `provider_invocations` | sin columnas nuevas; `usage_status`, `usage_model`, `usage_call_count`, `usage_raw JSONB` (044) | `usage_raw` ⊆ whitelist del `provider` de esa fila |
| `generation_jobs` | `usage_status` / `usage_model` / `usage_call_count` denormalizados (044) | Proyectados desde la invocación que completa |
| `composition_versions` | sin cambio | `fit_result` JSONB ya tiene dimensiones |
| `photoshoots` / etapas | sin cambio | `COMPOSITION_BLOCKED` ya es error de etapa 053 |

Migración: **ninguna** en el camino feliz. Solo si Stage 4 encuentra un constraint que rechaza claves no-token en `usage_raw`.

No Redis nuevo. No tabla de evidencias.

## Security Design

| Concern | Approach |
|---------|----------|
| Secretos | Sidecar y `usage_raw` no incluyen `REPLICATE_API_KEY`, URLs firmadas, bytes de imagen ni prompt. ADR-047. |
| HTTP | GET job no devuelve `usage_raw`. GET photoshoot no expone `result_key`. |
| Logs | `UsageReported`: job_id, provider, model, call_count. No dump de `raw`. `UnrecognizedUsageFieldDropped`: nombre de clave, no valor. |
| Overlay | El slug no es secreto de proveedor; no se loguea completo en NFR-7 si basta un hash + `length`. El artifact de evidencia puede citar el slug porque es dato de producto de prueba. |
| Auth | Sin superficie nueva; mismas dependencias 043/054. |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| NFR-4 / 005 | Whitelist Replicate aditiva; ≥1 invocación real `reported`; unknown ≠ 0; OpenAI intacto; job mixto sin uso en composición |
| FR-11 / 006 | Validación de longitud en disparo; fit una línea; `blocked` medido; base publicable; distinción en GET |
| NFR-7 | `nfr7-evidence.md` + suite live opcional en CI; cierre del bolt exige captura real |
| NFR-6 | Sin secretos en usage/HTTP/logs |
| ADR-049 | Timeout → unknown, sin auto-retry (052 ya; tests de uso lo reafirman) |
| ADR-054/056 | Compositor intacto; OQ-1 solo como escalamiento documentado |

## Error Handling

| Error Type | Code | Response / outcome |
|------------|------|---------------------|
| Telemetría Replicate ausente o no reconocida | (ninguno HTTP) | `usage_status=unknown` en la invocación. El job **puede** completar igual |
| Timeout | `PROVIDER_TIMEOUT` | `timed_out` + usage `unknown` (052/044) |
| Slug > `SKU_MAX_LENGTH` | `OVERLAY_TEXT_TOO_LONG` | 422 en POST photoshoot, sin fila (053) |
| Fit no cabe | `OVERLAY_DOES_NOT_FIT` / etapa `COMPOSITION_BLOCKED` | Versión `blocked`; job base `completed`; photoshoot no trata el slot como `failed_results` |
| Job de inferencia fallido | códigos 052 | Independiente del overlay; no se disfraza de `blocked` |

No hay código HTTP nuevo de billing ni de «usage missing». Faltar telemetría no falla el job.

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| Replicate | Inferencia + telemetría real | Mismo wrap 052. Sidecar de predicción. Una captura live para fijar nombres de campo |
| PostgreSQL | `usage_raw` JSONB, composition_versions | AsyncSession existente |
| Pillow / fuente `default` | Fit y render | 046, sin fuente nueva |
| BFashion (dato de prueba) | Slugs reales | No hay llamada nueva; los slugs se copian a fixtures/evidencia |

## Integration Points (worker, solo tramo de uso)

El orden 052 se conserva. Se inserta persistencia de uso donde 044 ya la tenía, ahora con `provider`:

```text
# ... resolve, gate, lease, slot, call ...
try:
    result = adapter.generate(..., timeout=...)
    raw = adapter.last_usage          # sidecar Replicate; OpenAI: dict existente
    model = adapter.last_model or configured_model
    usage = UsageAccountingService.normalize(job.provider, model, raw)
    mark invocation succeeded + usage
except Timeout:
    UsageAccountingService.normalize(job.provider, model, None)  # unknown
    classify_timeout
finally:
    release slot, release lease
# composición (photoshoot tick) no llama a UsageAccountingService
```

## Compatibility

- Jobs OpenAI 008: misma whitelist, mismos tests de tokens. Firma `normalize(raw)` compatible.
- 052: mismo orden de task; mismo wrap; sin tocar Redis ni timeouts.
- 046: `spec_hash`, fuente, una línea, append-only.
- 053/054: mismos códigos `OVERLAY_TEXT_TOO_LONG` y `COMPOSITION_BLOCKED`.
- `CatVTONReplicateProvider`: import-only, salvo que Stage 4 demuestre que el sidecar es imposible sin un hook mínimo — en ese caso el hook es el **menor** cambio que exponga `prediction` (id + metrics), no un cliente nuevo. Eso sería candidato a ADR en Stage 3 si aparece.

## Test Plan (contrato para Stage 5)

**Uso**

1. `normalize("replicate", model, {prediction_id, predict_time})` → `reported`, `raw` solo whitelist, `call_count=1`
2. `normalize("replicate", model, {total_tokens: 3})` → `unknown` (no contaminación)
3. `normalize("openai", model, tokens...)` → `reported` igual que 044
4. `normalize("openai", model, {predict_time: 1.2})` → `unknown`
5. Campo Replicate ausente o `null` → no se escribe `0`
6. Clave futura ignorada; no exception
7. `raw=None` / timeout → `unknown`
8. Worker Replicate (adaptador fake con sidecar) persiste invocación `reported`
9. Composición no escribe `usage_*`
10. GET job Replicate no incluye coste; no incluye `usage_raw`
11. Captura real (live o artifact): ≥1 `provider_invocation` `reported` + modelo

**Overlay**

12. POST overlay texto de 201 caracteres → 422 `OVERLAY_TEXT_TOO_LONG`, 0 photoshoots
13. Slug `len>30` y ≤200 aceptado en disparo (resto válido)
14. `normalize_sku("blusa-manga-globo")` estable; `spec_hash` incluye el texto normalizado
15. `evaluate_fit` y render: mismas dimensiones; si `fits` el texto está completo y dentro
16. Si no cabe: versión `blocked`, `rendered_key` null, `fit_result` con required vs available
17. GET photoshoot: base en `candidates[]`; `failed_results` inalterado; código de etapa o status de versión distingue de job `failed`
18. Re-compose mismo spec `blocked` → misma fila (ADR-054)
19. Fixture slug > 30 documentado en evidencia

**NFR-7 / OQ-1**

20. `nfr7-evidence.md` con la muestra exigida, o skip live documentado **más** captura adjunta. Mayoría `blocked` → sección OQ-1, compositor sin diff de política.

## Open Questions Carried

- **Nombres exactos del SDK:** Stage 4 captura una predicción real y ajusta alias (`id` vs `prediction_id`, `metrics.predict_time`). El predicado `reported` no cambia.
- **¿El envuelto ya expone la predicción?** Si no, Stage 3 decide si un hook mínimo en `CatVTONReplicateProvider` merece ADR. Preferencia: solo el adaptador.
- **Constraint de `usage_raw`:** confirmar JSONB libre. Migración solo si hace falta.
- **OQ-1:** pendiente de producto. Este diseño no la cierra.
- **Live en CI:** no es obligatorio para cada PR; sí para declarar el bolt completo.

## Decisiones que el humano debe confirmar

1. Sidecar en el adaptador, sin cambiar el retorno de ADR-046.
2. Sin API de coste en V1.
3. Overlay solo se toca si hay bug vs el modelo, no para hacer caber slugs.
4. Cierre NFR-7/005 exige evidencia real, no solo mocks de CI.
