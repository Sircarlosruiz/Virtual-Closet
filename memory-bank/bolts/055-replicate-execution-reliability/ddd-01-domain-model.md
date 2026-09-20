---
unit: 004-replicate-execution-reliability
bolt: 055-replicate-execution-reliability
stage: model
status: complete
updated: 2026-09-19T17:22:00Z
---

# Static Model - replicate-execution-reliability (consumo y overlay)

## Bounded Context

**Fiabilidad de ejecución contra Replicate** — segundo bolt del mismo contexto que 052.

052 ya hace que el worker complete un job `provider = replicate` sin credencial de OpenAI, con tope global y timeout de minutos. Este bolt **no** reabre resolución de proveedor, guarda de credencial, pool de concurrencia ni política de timeout. Cierra las dos superficies que 052 aplazó a propósito porque necesitan datos reales:

1. **Contabilidad de uso con forma de Replicate** (NFR-4 / historia 005): `UsageAccountingService` deja de tratar la telemetría de Replicate como ruido de tokens y produce al menos un `UsageRecord` `reported` con modelo identificado.
2. **Overlay predecible con slug largo** (FR-11 / NFR-7 / historia 006): se **verifica** el compositor determinista existente contra slugs reales de BFashion, sin cambiar su semántica. Si la mayoría queda `blocked`, se escala a **OQ-1**, no se resuelve aquí.

Virtual Closet sigue siendo la única autoridad de consumo y de composición. Normalizar uso no factura. Medir overlay no recorta, no escala en silencio y no dibuja fuera del lienzo.

**Dentro del contexto (este bolt, 055)**

- Distinguir la forma de telemetría por `provider` al normalizar
- Reconocer campos de Replicate (identidad de predicción, tiempo de predicción, métricas) sin exigir tokens de OpenAI
- Conservar la regla: lo que el proveedor no informa es `unknown`, **nunca** `0`
- Marcar cualquier coste derivado como **estimación**, nunca como hecho de dominio
- Validar el slug en el disparo contra `SKU_MAX_LENGTH` (ya modelado en 053; este bolt lo exige contra slugs reales)
- Medir fit con la misma función que renderiza; persistir `blocked` con motivo medido (ADR-056)
- Distinguir en la vista «overlay bloqueado» de «generación fallida» (ya en 054; este bolt lo verifica)
- Documentar evidencia NFR-7 (photoshoots reales, incluido un slug de más de 30 caracteres)
- Escalar a OQ-1 si la mayoría de slugs reales queda `blocked` con la configuración por defecto

**Fuera del contexto (este bolt)**

- Resolver proveedor, guarda de credencial, tope global, timeouts (cerrado en 052; ADRs 065/066)
- Crear jobs, orquestar photoshoots, materializar candidatos, GET agregado (unidades 003 / bolts 053–054)
- Reescribir `RetryPolicyService` más allá de lo que 044/052 ya clasifican
- Escribir un cliente HTTP de Replicate nuevo
- Facturación, cuotas comerciales, alertas o límites de gasto
- Cambiar la semántica determinista del compositor (ADR-054): auto-ajuste de fuente, texto multilínea, fuentes extra
- Editor visual de posición del overlay
- Sustituir OpenAI por Replicate en modos `text`, `edit`, `extraction`

Contextos vecinos: **Image Generation / Reliability** (`GenerationJob`, `ProviderInvocation`, `UsageRecord` — bolts 043/044), **Replicate Execution Reliability** (052), **Template Composition** (`ProductOverlay`, `CompositionVersion` — 046), **Photoshoot Orchestration** (053/054: dispara overlay, proyecta candidatos).

Decisiones previas que este modelo trata como invariantes: ADR-046 (protocolo de generación), ADR-047 (secretos solo en el worker; `usage_raw` no es el cuerpo crudo), ADR-049 (timeout → `usage_status = unknown`, sin reintento automático), ADR-053 (composición síncrona local), ADR-054 (`spec_hash` determinista en BD), ADR-055 (versiones append-only), ADR-056 (`blocked` persistido, no publicable), FR-11 / 054 (overlay `blocked` no oculta el candidato base).

---

## Herencia de 052 y 044 (no se redefine)

El modelo estático de 052 sigue vigente: `GenerationJob.provider` inmutable, guarda por proveedor, `GlobalConcurrencyPool`, `ProviderTimeout`, orden de ejecución 1–9.

Lo que 044 ya definió y 052 dejó explícitamente abierto, este bolt cierra:

| Hueco 044 / 052 | Cierre 055 |
|-----------------|------------|
| `UsageAccountingService.normalize` filtra a campos de tokens de OpenAI | Distinción por `provider`; whitelist Replicate **aditiva** |
| Un job Replicate completaría siempre `unknown` por diseño | Al menos una invocación real queda `reported` con modelo |
| Campos no informados | Siguen `unknown`; **prohibido** coercer a `0` |
| Overlay / `CompositionVersion` | Fuera de 052; este bolt **verifica** 046+053+054 contra slugs reales |
| NFR-7 (4 photoshoots reales, slug > 30) | Evidencia de este bolt, no un agregado nuevo |

---

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| **GenerationJob** (existente, semántica de uso ampliada) | Las de 043/044/052 + `usage_status`, `usage_model`, `usage_call_count` | El `UsageRecord` final se toma de la invocación que **completa** (044). Un job `replicate` puede quedar `reported` sin ningún campo de tokens. Un job `openai` no cambia su forma de normalización. La composición local **no** escribe `usage_*` del job. `usage_status` arranca `unknown` y nunca se defaulta a cero. |
| **ProviderInvocation** (existente, semántica de uso ampliada) | Las de 044/052 + `model`, `usage` (`UsageRecord`) | Un intento registra consumo **solo** de la llamada al proveedor. Overlay / `SkuCompositionService` no crean invocación ni uso. `timed_out` (ADR-049) ⇒ `usage_status = unknown`. Ningún campo guarda credencial, cuerpo crudo de petición ni de respuesta: `raw` es el subconjunto saneado de la whitelist. |
| **ProductOverlay** (existente, fuera; se consume) | `id`, `generation_job_id`, `base_image_key`, … | Se adjunta *después* de materializar el job base, solo si hay overlay (053). Este bolt no cambia su frontera. UNIQUE por `generation_job_id`. |
| **CompositionVersion** (existente, fuera; se verifica) | `spec`, `spec_hash`, `fit_result`, `status` (`valid` \| `blocked`), `rendered_key` | `blocked` ⇒ `rendered_key = null` + `fit_result` medido (ADR-056). `valid` ⇒ texto **completo** dentro del lienzo, con la misma medición que decidió que cabía. Append-only (ADR-055). `UNIQUE (overlay_id, spec_hash)` (ADR-054). Re-pedir el mismo spec que no cabe **reusa** la versión `blocked`, no apila ruido. |
| **Photoshoot** / **PhotoshootView** (existentes, fuera; se verifican) | Vista 054 | `failed_results` **no** cuenta overlay `blocked`. `candidates[]` incluye el job base aunque la versión de overlay esté `blocked`. El GET distingue explícitamente ambos desenlaces. |
| **Nfr7Evidence** (nuevo, no persistido; artefacto de verificación) | conjunto de photoshoots reales ejecutados, slugs usados, desenlace de overlay (`valid` \| `blocked` + motivo), invocaciones `reported` | No es entidad de producción. Documenta NFR-7: ≥ 4 photoshoots reales (2 `garment_on_model`, 2 `flat_garment`; superior, inferior, vestido) y ≥ 1 slug de más de 30 caracteres. Si la mayoría de slugs queda `blocked`, el artefacto **incluye** el escalamiento a OQ-1. |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| **GenerationProvider** (052) | `openai` \| `replicate` | La normalización **se ramifica** por este valor. No hay un tercer proveedor en este bolt. Un valor desconocido no inventa uso: degrada a `unknown`. |
| **UsageRecord** (044, reafirmado) | `status` (`reported` \| `unknown`), `model`, `call_count`, `raw` | `reported` exige modelo identificado **y** al menos un campo reconocido de la whitelist del proveedor. `unknown` cuando falta telemetría, el timeout dejó desenlace desconocido, o ningún campo reconocido está presente. `unknown` **nunca** se coerciona a `0`. `call_count` cuenta llamadas al proveedor, no pasos de composición. `raw` ⊆ whitelist; campos futuros se **ignoran**, no se adivinan. |
| **OpenAiUsageShape** (existente, sin cambio) | campos reconocidos: tokens (`total_tokens`, `input_tokens`, `output_tokens` y detalles) | Whitelist **conservada**. Un job OpenAI con esos campos sigue `reported`. Este bolt no la sustituye ni la estrecha. |
| **ReplicateUsageShape** (nuevo) | identidad de predicción, tiempo de predicción, métricas del modelo; `model` | Whitelist **aditiva**, no un reemplazo. No exige campos de tokens. La forma exacta de nombres (p. ej. id de predicción vs `metrics.predict_time`) se **confirma contra una invocación real** en implement/test; el dominio exige *qué* se reconoce (identidad + tiempo/métricas + modelo), no un nombre de SDK congelado en esta etapa. Campos no reconocidos se descartan. Un campo informado a `null`/ausente → `unknown` para ese campo, nunca `0`. |
| **UsageFieldWhitelist** | `provider` → conjunto de claves seguras | Unión de `OpenAiUsageShape` y `ReplicateUsageShape` indexada por proveedor. Mezclar whitelists (tokens en un job Replicate, o `predict_time` en un job OpenAI) no produce `reported` por contaminación cruzada: cada invocación se normaliza con **su** proveedor. |
| **SanitizedUsageRaw** | mapa clave→valor de la whitelist | Subconjunto persistible. Prohibido: credenciales, URLs firmadas, cuerpos de imagen, prompts, bytes. Si un campo de métricas viniera con PII o secreto, se descarta (NFR-6). |
| **IdentifiedModel** | identificador de modelo no vacío | Obligatorio para `reported`. Si Replicate completa sin modelo identificable → `unknown` (no se inventa un nombre). |
| **UsageEstimate** | `kind = estimate`, magnitud opcional, base (`predict_time` u otra métrica reconocida) | Cualquier coste en dinero o «créditos» derivado de la telemetría es **estimación**. Nunca se persiste como `UsageRecord.status = reported` de dinero. Si se expone, el contrato lo etiqueta explícitamente como estimación. Fuera de alcance facturar. |
| **SkuText** (046, reafirmado) | texto normalizado | `normalize_sku` no depende de semántica de SKU: un slug con guiones (`blusa-manga-globo`) se trata igual que un código. Tras normalizar: no vacío; longitud ≤ `SKU_MAX_LENGTH` (200). El valor almacenado es el mismo que se mide y se pinta. |
| **SkuLengthBound** | `SKU_MAX_LENGTH = 200` | Se aplica **en el disparo** del photoshoot (053 `OverlaySpec`), no a mitad de pipeline. Exceso → 422, cero jobs, cero composición. Un slug de más de 30 caracteres **cabe** en este bound; 30 no es un máximo de dominio, es el umbral de evidencia NFR-7. |
| **OverlayPlacement** / **OverlayStyle** (046) | ancla, offsets, `max_width?`, fuente, tamaño, color | Una sola línea. Única fuente V1: `default` (`ImageFont.load_default`). `max_width` ausente → ancho de imagen menos offset (046). Este bolt **no** añade wrap, auto-size ni fuentes. |
| **SkuOverlaySpec** (046) | `SkuText` + placement + style | Inmutable. Igualdad por valor. Alimenta `spec_hash`. |
| **SpecHash** (ADR-054) | `sha256(normalized_sku, placement, style, base_image_key, font_version)` | Cualquier cambio de política de ajuste (auto-size, dos líneas, otra fuente) **cambia** este hash. Por eso OQ-1 no se resuelve aquí. |
| **OverlayFitResult** (046) | `fits`, anchos/altos requeridos vs disponibles, `reason?` | Función pura de spec + dimensiones de la imagen base + métricas de la fuente pinneada. La medición de `evaluate_fit` es **la misma** que usa el render (criterio de 006 / NFR-3 del intent 008). Nunca aleatoria. Nunca depende de Replicate. |
| **CompositionStatus** (046) | `valid` \| `blocked` | `valid`: texto completo, dentro del lienzo, `rendered_key` presente. `blocked`: no cabe; no hay recorte, no hay escala silenciosa, no hay dibujo fuera; `rendered_key` null. |
| **OverlayOutcomeVsJobOutcome** | par (`composition_status`, `job_status`) | `blocked` + job `completed` = overlay fallido, **generación viva**. Job `failed` / `timed_out` = generación fallida, independiente del overlay. La vista 054 debe poder distinguirlos; `failed_results` no incrementa por `blocked`. |
| **Oq1Escalation** | `majority_blocked: bool`, muestra de slugs, configuración usada | Si, con placement/style por defecto y fuente `default`, la **mayoría** de slugs reales de la evidencia NFR-7 queda `blocked`, el resultado del bolt es el escalamiento documentado, **no** un cambio de compositor. V1 asume opción (a) de OQ-1: fallo explícito y no destructivo. |
| **LongSlugEvidence** | slug real de BFashion, `length > 30`, desenlace | Obligatorio en NFR-7. El dominio no exige que ese slug quepa; exige que el desenlace sea `valid` con texto completo **o** `blocked` con motivo medido. |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| **GenerationJob** (existente, frontera de uso extendida) | `ProviderInvocation` (0..N, append-only), `UsageRecord` final | (1) El uso del job es el de la invocación que completa, o `unknown` si esa invocación no reportó. (2) Un job `replicate` no necesita campos de tokens para ser `reported`. (3) Un job `openai` conserva la whitelist de tokens. (4) Timeout / desenlace desconocido ⇒ `unknown`, nunca `0` (ADR-049). (5) Composición no muta `usage_*`. (6) `raw` ⊆ whitelist del proveedor de **esa** invocación. |
| **ProductOverlay** (existente, 046; no se reabre) | `CompositionVersion` append-only | Invariantes 046 1–9 + ADR-054/055/056. Este bolt **añade** la verificación: el `SkuText` puede ser un slug largo; la política de una línea y fuente `default` no cambia. |
| **Photoshoot** (existente, 053/054; no se reabre) | etapas, resultados, vista | Overlay `blocked` no es hueco irrecuperable. El candidato base permanece. Validación de longitud del slug ocurre en submit. |

No se crea un tercer agregado. `Nfr7Evidence` y `Oq1Escalation` son artefactos de cierre, no raíces.

### Invariantes añadidas (055)

1. `UsageAccountingService.normalize(provider, model, raw)` elige whitelist por `provider`. No hay una whitelist única global.
2. Replicate `reported` ⇔ `IdentifiedModel` presente **y** al menos un campo de `ReplicateUsageShape` reconocido con valor informado. Tokens de OpenAI **no** cuentan para este predicado.
3. OpenAI `reported` ⇔ predicado existente de 044 (campos de tokens). Campos de Replicate **no** cuentan para este predicado.
4. Campo ausente, no reconocido o nulo → se omite o `unknown`. **Prohibido** persistir `0` fabricado.
5. Cualquier magnitud monetaria/crédito derivada viaja como `UsageEstimate`, nunca como uso `reported` de dinero.
6. Tras al menos un photoshoot real contra Replicate, existe ≥ 1 `ProviderInvocation` con `usage_status = reported` y modelo identificado. Eso es criterio de cierre, no un invariante de cada invocación (un timeout sigue pudiendo ser `unknown`).
7. Un job mixto (inferencia + composición) tiene uso **solo** en la parte que llamó al proveedor.
8. `SKU_MAX_LENGTH` se aplica en el disparo. Pipeline y compositor nunca ven un texto que lo exceda.
9. Fit se decide sobre el **texto completo** normalizado. Si no cabe: versión `blocked` + motivo medido; **cero** recorte, **cero** auto-scale, **cero** overflow de lienzo.
10. Medición y render comparten la misma función de métricas. Un `valid` no puede contradecir el `evaluate_fit` que lo autorizó.
11. `blocked` no elimina ni oculta el `GenerationJob` base como candidato (FR-11, ADR-056, 054).
12. La respuesta agregada distingue overlay bloqueado de generación fallida. `failed_results` no incluye `blocked`.
13. `spec_hash` y `font_version` no se redefinen. Fuente V1 = `default` únicamente.
14. OQ-1 no se cierra en este bolt. Mayoría `blocked` → `Oq1Escalation` documentada.
15. Credenciales y `raw` completo del proveedor no aparecen en HTTP ni en logs (ADR-047, NFR-6).

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| **UsageReported** | `normalize` produce `status = reported` y se persiste en la invocación | `job_id`, `invocation_id`, `provider`, `model`, `call_count` — **sin** `raw` completo en logs |
| **UsageUnknownRecorded** | telemetría ausente, timeout, o ningún campo reconocido | `job_id`, `invocation_id`, `provider`, `reason` (`missing` \| `timeout` \| `unrecognized`) |
| **UnrecognizedUsageFieldDropped** | llega una clave fuera de la whitelist | `provider`, `field_name` (no el valor) |
| **UsageEstimateExposed** | un caller pide coste derivado | `job_id`, `kind=estimate`, base de la estimación — nunca como hecho |
| **SlugRejectedAtSubmit** | texto normalizado > `SKU_MAX_LENGTH` | `product_link_id?`, `length`, `max` — no el texto completo si se considera ruidoso; **sin** encolar |
| **OverlayFitMeasured** | `evaluate_fit` corre sobre un slug (cabe o no) | `overlay_id?`, `fits`, dimensiones requeridas vs disponibles |
| **OverlayFitRejected** (046, reafirmado) | no cabe | `overlay_id`, `version_id`, `fit_result`, `reason` |
| **OverlayFitAccepted** | cabe y se renderiza texto completo | `overlay_id`, `version_id`, `rendered_key` |
| **BaseCandidatePreserved** | versión `blocked` y el job base sigue en `candidates[]` | `photoshoot_id`, `generation_job_id`, `composition_version_id` |
| **OverlayBlockedDistinguished** | la vista expone overlay bloqueado ≠ job fallido | `photoshoot_id`, `generation_job_id` |
| **Nfr7EvidenceRecorded** | se cierra la validación previa a entrega | conteo de photoshoots, mix de `input_kind`/prenda, presencia de slug > 30, desenlaces |
| **Oq1Escalated** | mayoría de slugs reales `blocked` con defaults | muestra, configuración, referencia a OQ-1 — **sin** cambio de compositor |

V1: persistencia + logs estructurados, sin bus. Nunca loguear credenciales, `usage_raw` completo, URLs presignadas ni el slug completo si no hace falta (NFR-6).

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| **UsageAccountingService** (existente, extendido) | `normalize(provider, model, raw) → UsageRecord` | Whitelist por proveedor. **Nunca** fabrica un número donde el proveedor calló. OpenAI: comportamiento 044 intacto. Replicate: `ReplicateUsageShape`. |
| **ReplicateUsageRecognizer** (nuevo, o rama interna del anterior) | `recognized_fields(raw) → SanitizedUsageRaw`; `is_reported(model, sanitized) → bool` | No llama a Replicate. No cobra. Confirma nombres de campo contra una invocación real en Stage 4/5, no contra un SDK imaginado. |
| **UsageEstimatePolicy** (nuevo, opcional / de exposición) | `estimate(record) → UsageEstimate \| none` | Solo si se expone coste. Siempre `kind = estimate`. No persiste dinero en `provider_invocations`. |
| **SkuTextNormalizer** (046, sin cambio) | `normalize(raw) → SkuText` | Guiones y ausencia de espacios son texto visible, no semántica especial. |
| **OverlayFitValidator** / **sku_renderer.evaluate_fit** (046, sin cambio de semántica) | `validate(spec, image_dimensions, font_metrics) → OverlayFitResult` | Una línea, fuente `default`. Comparte medición con el render. |
| **SkuCompositionService** (046, sin cambio de semántica) | `compose` / `recompose` | Persist `blocked` (ADR-056). Idempotencia por `spec_hash` (ADR-054). No llama al proveedor. |
| **PhotoshootSubmissionService** (053, verificación) | rechaza slug > `SKU_MAX_LENGTH` con 422 **antes** de crear agregado | Este bolt no reimplementa submit; exige el criterio de 006 contra slugs reales. |
| **PhotoshootQueryService** (054, verificación) | `get_view` distingue overlay `blocked` de job fallido; conserva candidato base | Este bolt no edita el GET; lo verifica como evidencia. |
| **PublicationCandidateAssembler** (existente, verificación) | `list_candidates` no elimina el base por overlay `blocked` | Coherente con ADR-056 + 054. |

### Orden de normalización de uso (política de dominio)

```text
1. Recibir (provider, model, raw) al completar (o timeout) una ProviderInvocation
2. Elegir UsageFieldWhitelist[provider]
3. Conservar solo claves reconocidas → SanitizedUsageRaw
4. Campos no reconocidos → UnrecognizedUsageFieldDropped (no rompen)
5. Si provider call timed_out (ADR-049) → UsageRecord(unknown), fin
6. Si model ausente o sanitized vacío de valores informados → unknown
7. Si hay IdentifiedModel + ≥1 campo informado de esa whitelist → reported
8. Persistir en la invocación; proyectar al GenerationJob si es la invocación que completa
9. Composición / overlay no entran en este flujo
```

### Orden de overlay (política de dominio — verificación, no rediseño)

```text
1. Disparo: normalize_sku(slug) ; length > SKU_MAX_LENGTH → 422, stop
2. Pipeline genera GenerationJob base (Replicate) → candidato
3. Si hay overlay: evaluate_fit(spec, base dimensions, default font)
     ├─ fits    → render con la misma medición → CompositionVersion valid
     └─ !fits   → CompositionVersion blocked + fit_result; rendered_key null
4. PhotoshootView: job base en candidates[]; blocked ≠ failed_results
5. Si evidencia NFR-7 muestra mayoría blocked → Oq1Escalation (no cambiar spec_hash)
```

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| **ProviderInvocationRepository** (044, extendido en semántica) | `ProviderInvocation` | `markCompleted(..., usage: UsageRecord)` — `usage.raw` ya saneado; no hay columna de tokens obligatoria |
| **GenerationJobRepository** (044) | `GenerationJob` | `updateUsageStatus(job_id, usageRecord)` — proyecta el record de la invocación que completa |
| **CompositionVersionRepository** (046) | `CompositionVersion` | `append`, `find_by_spec_hash` — este bolt **lee** para evidencia; no cambia contratos |
| **ProductOverlayRepository** (046) | `ProductOverlay` | lectura por `generation_job_id` |
| **PhotoshootRepository** (053/054) | `Photoshoot` | lectura de vista para distinguir `blocked` vs `failed` |
| **Nfr7EvidenceLog** (artefacto) | evidencia | no es tabla de producción; vive en el test report / notes del bolt |

No se exige migración de esquema para el uso: las columnas `usage_*` ya existen. Si Stage 2 descubre que `usage_raw` no puede representar métricas Replicate (p. ej. solo tokens tipados), **entonces** hay cambio aditivo; el dominio no lo presupone. Overlay no añade tablas.

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Forma de Replicate** | Telemetría que el proveedor sí emite: identidad de predicción, tiempo de predicción, métricas, modelo. No tokens. |
| **Forma de OpenAI** | Telemetría de tokens. Intacta. |
| **Whitelist por proveedor** | Conjunto de claves que `normalize` puede persistir para *ese* `provider`. Aditiva, no sustitutiva. |
| **reported** | Hay modelo identificado y al menos un campo reconocido informado. |
| **unknown** | El proveedor no informó (o el desenlace es desconocido). Distinto de cero. |
| **Cero fabricado** | Escribir `0` donde no hubo dato. Prohibido. |
| **Estimación** | Coste derivado de métricas. Nunca un hecho de facturación. |
| **Invocación real** | Llamada efectiva a Replicate (no un stub) contra la que se verifica `reported`. |
| **Slug** | Identificador de producto que BFashion estampa (`blusa-manga-globo`). Es `SkuText`, no un SKU corto. |
| **SKU_MAX_LENGTH** | Tope de 200 caracteres en el disparo. No es el umbral de evidencia (30). |
| **Una línea** | Política V1 de fit: el texto completo en una sola línea con fuente `default`. |
| **blocked** | El texto no cabe. Versión persistida con motivo medido; sin imagen recortada. |
| **Candidato base** | El `GenerationJob` generado, publicable aunque el overlay esté `blocked`. |
| **Generación fallida** | El job de inferencia no completó. No es overlay `blocked`. |
| **OQ-1** | Decisión de producto sobre auto-size o multilínea. Fuera de este bolt salvo escalamiento documentado. |
| **Evidencia NFR-7** | Photoshoots reales + slug > 30 + desenlace de overlay + al menos un uso `reported`. |

## State Transitions

El ciclo de vida del job y del photoshoot **no cambia**. Este bolt añade desenlaces *dentro* de invocación y de composición:

```text
ProviderInvocation (uso)
  complete with recognized Replicate fields + model → usage reported
  complete with OpenAI token fields + model         → usage reported (sin cambio)
  complete with no recognized fields                → usage unknown
  timed_out                                         → usage unknown (ADR-049)
  unrecognized extra fields                         → dropped; no rompen
```

```text
CompositionVersion (slug largo, política V1 = OQ-1a)
  evaluate_fit fits     → valid + rendered_key
  evaluate_fit !fits    → blocked + fit_result + rendered_key null
                          GenerationJob base permanece candidato
  slug > SKU_MAX_LENGTH → ni siquiera nace (422 en disparo)
```

```text
OQ-1
  mayoría de slugs reales valid   → no se escala; evidencia documentada
  mayoría blocked con defaults    → Oq1Escalated; compositor intacto
```

## Boundaries

- `UsageAccountingService` posee la normalización. El worker le pasa `(provider, model, raw)` y no interpreta tokens vs métricas por su cuenta.
- La whitelist de OpenAI no se borra. La de Replicate se **suma**.
- Composición no consume cuota de proveedor y no escribe `UsageRecord`.
- `SkuCompositionService` / `sku_renderer` / `composition_spec` **no cambian de semántica**. Este bolt los verifica y, si hace falta, documenta OQ-1.
- El GET de photoshoot (054) y el submit (053) no se rediseñan; se verifican criterios de 006 que ya declararon.
- Facturación, cuotas y alertas de gasto están fuera. `UsageEstimate` es etiquetado, no cobrado.
- NFR-7 es criterio de **cierre del intent**, no un endpoint nuevo.

## Story Coverage

| Story | Cómo la cubre el modelo |
|-------|-------------------------|
| **005-replicate-usage-accounting** | `ReplicateUsageShape`, `UsageFieldWhitelist` aditiva, `UsageAccountingService.normalize` por proveedor, `UsageReported` / `UsageUnknownRecorded`, prohibición de cero fabricado, `UsageEstimate`, OpenAI intacto, job mixto sin uso en composición, ≥1 invocación real `reported` |
| **006-product-slug-overlay-fit** | `SkuText` como slug, `SkuLengthBound` en disparo, `OverlayFitResult` compartido con render, `CompositionStatus.blocked` con motivo, `OverlayOutcomeVsJobOutcome`, candidato base preservado, distinción en vista, `LongSlugEvidence`, `Oq1Escalation` si mayoría blocked, ADR-054/056 intactos |

## Prior Decisions Applied

- **ADR-054**: `spec_hash` incluye texto + placement + style + base + `font_version`. Auto-size o wrap lo romperían → OQ-1 fuera.
- **ADR-055**: versiones append-only; re-medir el mismo slug no muta una versión `valid` previa.
- **ADR-056**: no cabe ⇒ `blocked` persistido, no un 422 vacío ni un render recortado. El base sigue publicable.
- **ADR-053**: composición síncrona local; no genera `ProviderInvocation`.
- **ADR-049**: timeout ⇒ uso `unknown`, sin retry automático.
- **ADR-047**: `SanitizedUsageRaw` y logs sin secretos.
- **ADR-046**: el adaptador Replicate ya existe (052); este bolt solo lee la telemetría que ese adaptador puede exponer.
- **052**: no reabre wiring, credencial, cap ni timeout.
- **053 OverlaySpec**: 422 de longitud en el disparo.
- **054**: `failed_results` no cuenta `blocked`; `candidates[]` conserva el base.

## Open Questions Retained

- **Nombres exactos de campos Replicate:** el dominio fija el *conjunto semántico* (id de predicción, tiempo de predicción, métricas, modelo). Stage 2/4 confirma el mapeo contra una invocación real y el SDK, como pide la historia 005. No se congelan nombres aquí.
- **¿`usage_raw` JSONB ya admite métricas no-token?** Stage 2 lo confirma contra el esquema existente. Si estuviera acoplado a tokens, la migración es **aditiva**. El dominio no inventa columnas nuevas de antemano.
- **OQ-1:** pendiente de producto. V1 = (a) bloquear. Este bolt solo escala si la evidencia lo obliga.
- **Umbral de «mayoría» para OQ-1:** la muestra es la de NFR-7 (slugs reales usados en los ≥ 4 photoshoots, incluido el de > 30 caracteres). No se exige un censo de catálogo BFashion.

## Decisiones que el humano debe confirmar

1. **Whitelist aditiva por proveedor**, no un normalizador distinto ni el reemplazo de la forma OpenAI.
2. **Forma Replicate confirmada contra invocación real** en implement/test; el modelo no finge nombres de SDK.
3. **Overlay: verificar, no rediseñar.** Cualquier auto-size / wrap queda OQ-1.
4. **Criterio de cierre NFR-7** (4 photoshoots reales + slug > 30 + ≥1 `reported`) es de este bolt, último del intent.
