---
unit: 004-replicate-execution-reliability
bolt: 052-replicate-execution-reliability
stage: model
status: complete
updated: 2026-09-19T01:35:10Z
---

# Static Model - replicate-execution-reliability

## Bounded Context

**Fiabilidad de ejecución contra Replicate** (Replicate Execution Reliability).

Este contexto gobierna *cómo* un `GenerationJob` ya persistido se ejecuta en un despliegue cuyo proveedor de producción es Replicate. No crea jobs, no orquesta photoshoots y no redefine reintentos, lease por job ni contabilidad de consumo. Extiende el agregado `GenerationJob` de los bolts 043/044 para que el worker pueda completar un job `provider = replicate` sin una credencial de OpenAI, sin una ráfaga descontrolada de llamadas y sin un timeout pensado para OpenAI.

**Dentro del contexto**

- Resolver el adaptador del proveedor persistido en el job (`openai` | `replicate`)
- Comprobar la credencial *del proveedor del job* antes de cualquier lease o llamada de red
- Limitar las llamadas simultáneas al proveedor con un tope global de despliegue
- Aplicar un timeout configurable por proveedor y clasificar el vencimiento como `timed_out`

**Fuera del contexto**

- Crear o validar `GenerationJob` (bolt 043)
- Lease por job, historial de intentos, reintentos e idempotencia (bolt 044)
- Normalización de consumo de Replicate y overlay de slugs (historias 005/006, bolt 055)
- Orquestación de photoshoot, materialización de jobs y estado agregado (unidad 003 / bolt 053)
- Migrar modos `text`, `edit`, `extraction` a Replicate
- Escribir un cliente HTTP de Replicate nuevo
- Facturación o cuotas comerciales por uso
- Rotación de credenciales o validación de claves en el arranque de la aplicación

Contextos vecinos: **Image Generation** (`GenerationJob`, `ImageGenerationProvider`), **Generation Reliability** (`ProviderInvocation`, `ConcurrencyLease`, `RetryPolicyService`), **VTON / Replicate existente** (`CatVTONReplicateProvider`), **Photoshoot Orchestration** (consume este contexto para completar contra Replicate).

Decisiones previas que este modelo trata como invariantes: ADR-046 (protocolo de generación distinto de `VTONProvider`), ADR-047 (secretos solo en el worker), ADR-049 (timeout = resultado desconocido, reintento manual), ADR-050 (lease por job en Postgres, no se reutiliza como tope global).

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| **GenerationJob** (existente, raíz) | `id`, `provider`, `mode`, `status`, `input_data`, `error_code`, `retry_count`, `lock_token`, `locked_at` | El `provider` queda persistido al crear el job y **no se cambia en silencio** si la ejecución falla o el otro proveedor está configurado. Un job `replicate` no exige credencial de OpenAI. Un job `openai` no exige credencial de Replicate. `input_data` nunca contiene secretos (ADR-047). |
| **ProviderInvocation** (existente) | `id`, `job_id`, `attempt_number`, `provider`, `status`, `error_code`, `error_category`, `retryable`, `started_at`, `completed_at` | Un intento registra el proveedor del job, no un sustituto. `timed_out` es distinto de `failed` (ADR-049). Ningún campo guarda la credencial, el cuerpo crudo de la petición ni el de la respuesta. |
| **GlobalConcurrencySlot** (nuevo, transitorio) | `job_id`, `acquired_at`, `released_at?` | Representa un hueco ocupado del tope global. Existe solo mientras hay una llamada al proveedor en vuelo. No sustituye al `ConcurrencyLease` del job. Un waiter no ocupa slot. Un holder que muere no puede reducir el pool de forma permanente. |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| **GenerationProvider** | `name`: `openai` \| `replicate` | Conjunto cerrado para este bolt. Cualquier otro valor es desconocido y produce error clasificado (`ProviderRequestError`), igual que hoy. No se introduce un alias silencioso (`vton` ≠ `replicate` en este contexto). |
| **CredentialRequirement** | `provider`, `setting_name` | `openai` → `OPENAI_API_KEY`. `replicate` → `REPLICATE_API_KEY`. Nunca ambas a la vez para un mismo job. El valor de la clave no forma parte del objeto. |
| **CredentialPresence** | `present` \| `absent` | Se decide por presencia de un valor no vacío en settings del worker. No valida la clave contra el proveedor (una clave inválida es fallo HTTP posterior, no de esta guarda). |
| **CredentialRejection** | `error_code`, `category = terminal`, `retryable = false` | Código distinguible de un fallo del proveedor (4xx/5xx/timeout). No reintentable: una credencial ausente no se arregla reintentando. El mensaje y los logs no incluyen el valor de ninguna clave. |
| **ProviderAdapterRef** | `provider`, `capability` | `replicate` + modo `try_on` apunta al adaptador que envuelve la ruta Replicate existente. `openai` apunta al adaptador ya entregado en el intent 008. El adaptador traduce `input_data` a la firma `generate(garment, model, cloth_type)` sin duplicar la llamada HTTP. |
| **TryOnInputContract** | `garment`, `model`, `cloth_type` | Claves mínimas que Replicate necesita para `try_on`. Si faltan, `ProviderRequestError` clasificado, no una excepción no controlada. |
| **GlobalConcurrencyCap** | `max_in_flight: int` | Valor de **despliegue**, no de código. Debe ser ≥ 1; 0 o negativo se rechazan en configuración, no en tiempo de ejecución. Propuesta de partida: 2 (NFR-2 / OQ-3), ajustable sin cambiar el modelo. El tope es global al despliegue, no por photoshoot, no por tenant, no por job. |
| **SlotAcquisition** | `outcome`: `acquired` \| `queued`, `queued_at?`, `acquired_at` | El excedente **encola y no falla**. No hay descarte de trabajo por exceso de concurrencia. `queued` no es un error de dominio. |
| **QueueWaitDuration** | `started_at`, `ended_at`, `seconds` | Tiempo desde que el job está listo para llamar al proveedor hasta que obtiene el hueco. Distinto de `ExecutionDuration`. Lo registra este contexto; el estado agregado del photoshoot (unidad 003) lo expone. |
| **ExecutionDuration** | `started_at`, `ended_at`, `seconds` | Tiempo de la llamada al proveedor, desde que el slot está adquirido hasta que termina (éxito, fallo o timeout). |
| **ProviderTimeout** | `provider`, `seconds` | Específico por proveedor. OpenAI conserva un valor corto (orden de decenas de segundos). Replicate usa un valor de minutos: partida ≥ 900 s; precedente del repositorio `TRYOFF_MODEL_TIMEOUT_SECONDS = 1800`. Ambos valores son independientes: igualarlos por error de config no rompe el dominio, pero deja de reflejar NFR-3. |
| **ErrorClassification** (existente, bolt 044) | `code`, `category` (`transient` \| `terminal`), `retryable` | `429` → transient, máximo 2 reintentos, honra `Retry-After`. Timeout de worker → `timed_out`, `usage_status = unknown`, **sin** reintento automático (ADR-049). 4xx no transitorios → terminal, sin reintento. Este bolt no reescribe la política; solo alimenta el timeout correcto. |
| **ConcurrencyLease** (existente, ADR-050) | `job_id`, `holder_token`, `acquired_at` | Sigue siendo exclusión mutua **por job** (anti-duplicado de entrega). No cuenta llamadas simultáneas al proveedor. Coexiste con `GlobalConcurrencyCap`. |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| **GenerationJob** (existente, frontera extendida) | `ProviderInvocation` (0..N, append-only), `ConcurrencyLease`, `provider` inmutable, duraciones de cola/ejecución | (1) El proveedor ejecutado es el persistido; no hay failover silencioso a OpenAI ni a Replicate. (2) La guarda de credencial corre **antes** del lease y **antes** de cualquier red. (3) Sin credencial del proveedor del job el agregado termina en fallo clasificado no reintentable y no abre invocación de red. (4) Un job `replicate` puede completar con `OPENAI_API_KEY` vacío. (5) Un timeout alimenta `RetryPolicyService.classify_timeout`; el job no se reencola solo. |
| **GlobalConcurrencyPool** (nuevo, singleton de despliegue) | `GlobalConcurrencyCap`, slots en vuelo (0..cap), waiters | (1) En ningún instante `in_flight > cap`. (2) Un waiter no falla ni se descarta. (3) Dos photoshoots distintos compiten por el mismo pool. (4) Reiniciar un worker no pierde el trabajo en cola: se retoma respetando el tope. (5) Un waiter que muere no consume slot; un holder que muere libera o recupera el slot. (6) El pool no sustituye ni observa el `ConcurrencyLease` por job. |

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| **ProviderResolved** | `_resolve_provider` encuentra un adaptador para `job.provider` | `job_id`, `provider` |
| **ProviderUnresolved** | `provider` desconocido o sin adaptador para el modo | `job_id`, `provider`, `error_code` clasificado |
| **CredentialAccepted** | La credencial del proveedor del job está presente | `job_id`, `provider` (nunca el valor de la clave) |
| **CredentialRejected** | La credencial requerida está ausente | `job_id`, `provider`, `error_code` no reintentable |
| **GlobalSlotQueued** | El job está listo pero el pool está lleno | `job_id`, `queued_at`, `cap` |
| **GlobalSlotAcquired** | El job obtiene un hueco | `job_id`, `acquired_at`, `queue_wait_seconds` |
| **GlobalSlotReleased** | Termina la llamada al proveedor (cualquier desenlace) | `job_id`, `released_at` |
| **ProviderCallStarted** | Comienza la llamada con el timeout del proveedor | `job_id`, `provider`, `timeout_seconds`, `attempt_number` |
| **ProviderCallTimedOut** | Vence el timeout de worker | `job_id`, `provider`, `timeout_seconds`; el estado de fallo queda reflejado en ≤ 30 s |
| **ProviderInvocationSucceeded** (existente) | El adaptador produce una imagen persistible | `job_id`, `attempt_number`, `provider` |
| **ProviderInvocationFailed** (existente) | Error clasificado del proveedor o de entrada | `job_id`, `attempt_number`, `error_classification` |

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| **ProviderResolutionService** | `resolve(job) → ProviderAdapterRef` o error clasificado | Contrato `ImageGenerationProvider` (ADR-046). Para `replicate` + `try_on` envuelve `CatVTONReplicateProvider` / `ReplicateProvider` existentes; no abre un cliente HTTP nuevo. Para `openai` delega al adaptador del intent 008 sin cambiar comportamiento. |
| **CredentialGateService** | `require(job) → CredentialAccepted \| CredentialRejection` | Settings del worker (ADR-047). Lee solo `job.provider`. Se invoca **antes** de `ConcurrencyGuardService.acquire` y antes de `GlobalConcurrencyService.acquire`. |
| **GlobalConcurrencyService** | `acquire(job_id) → SlotAcquisition` (puede esperar), `release(job_id)` | `GlobalConcurrencyPool`. Independiente de `ConcurrencyGuardService`. El excedente espera; no eleva error de dominio. |
| **ProviderTimeoutPolicy** | `timeout_for(provider) → ProviderTimeout` | Configuración de despliegue por proveedor. El valor deja de ser una constante única de módulo. |
| **RetryPolicyService** (existente, no se reescribe) | `classify(...)`, `classify_timeout(...)`, `decide(job, invocation)` | Sigue clasificando `429` (máx. 2, `Retry-After`), no transitorios (sin reintento) y timeouts (reintento explícito, ADR-049). |
| **ConcurrencyGuardService** (existente, no se reescribe) | `acquire(job_id)`, `release(lease)` | Lease Postgres por job (ADR-050). Sigue evitando una segunda llamada del mismo job; no limita el paralelismo global. |
| **ImageGenerationProvider** (existente, adaptador Replicate nuevo) | `generate(...)` | Para Replicate: traduce `input_data` → `(garment, model, cloth_type)`; si el proveedor devuelve URL, descarga bytes antes de persistir (comportamiento ya existente de `CatVTONReplicateProvider.generate`). Aplica `ProviderTimeout` del proveedor resuelto. |

### Orden de ejecución (política de dominio)

```text
1. Cargar GenerationJob por id (solo id viaja por el broker — ADR-047)
2. ProviderResolutionService.resolve(job)
3. CredentialGateService.require(job)     ← antes de lease y de red
4. ConcurrencyGuardService.acquire(job)   ← anti-duplicado por job
5. GlobalConcurrencyService.acquire(job)  ← puede esperar; no falla
6. Invocar adaptador con ProviderTimeout del provider
7. GlobalConcurrencyService.release(job)
8. ConcurrencyGuardService.release(lease)
9. RetryPolicyService.classify / decide
```

Si el paso 2 o 3 falla, no se toma lease, no se toma slot y no hay llamada de red.

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| **GenerationJobRepository** (existente) | `GenerationJob` | `get(job_id)`, `markFailed(job_id, error_code)`, `recordDurations(job_id, queue_wait, execution)` |
| **ProviderInvocationRepository** (existente) | `ProviderInvocation` | `create`, `listByJob`, `markCompleted` — sin campos secretos |
| **GlobalConcurrencyPool** | `GlobalConcurrencySlot` | `tryAcquire(job_id, cap)`, `release(job_id)`, `inFlightCount()` — contrato de dominio; el backing (Redis, broker u otro) se decide en diseño técnico |
| **WorkerSettings** | `CredentialPresence`, `ProviderTimeout`, `GlobalConcurrencyCap` | `credential_for(provider)`, `timeout_for(provider)`, `concurrency_cap()` — solo lecturas de configuración; nunca serializa valores de claves a logs ni a persistencia |

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Proveedor del job** | Valor persistido en `GenerationJob.provider`. Es la única fuente para resolver adaptador, credencial y timeout. |
| **Adaptador** | Implementación del protocolo de generación (ADR-046) que traduce el contrato del job a un proveedor concreto. Envolver ≠ reescribir el cliente Replicate existente. |
| **Guarda de credencial** | Comprobación por proveedor, en el worker, de que existe la clave que *ese* job necesita. No es una guarda global de OpenAI. |
| **Credencial ausente** | Fallo de configuración, terminal y no reintentable, con código distinto de un error del proveedor. |
| **Fallo del proveedor** | Error HTTP o de inferencia *después* de que la guarda aceptó la credencial (incluye clave presente pero rechazada en runtime). |
| **Lease por job** | Derecho exclusivo a ejecutar *este* job (anti-duplicado de entrega). ADR-050. |
| **Tope global** | Máximo de llamadas al proveedor en vuelo en todo el despliegue. No es el lease. |
| **Hueco / slot** | Una unidad ocupada del tope global mientras dura la llamada. |
| **En cola de concurrencia** | El job está listo y espera hueco. No es fallo. El tiempo en cola no es tiempo de ejecución. |
| **Timeout por proveedor** | Límite de espera de la llamada, configurado por `provider`, no una constante única. |
| **timed_out** | Desenlace desconocido: no sabemos si el proveedor terminó. Requiere reintento explícito (ADR-049). |
| **Reintento explícito** | Acción de staff/operador sobre el mismo job; no un retry automático de Celery por timeout. |

## State Transitions

El ciclo de vida del job (`queued → processing → completed | failed`) no cambia. Este bolt añade dos tramos *dentro* de `processing`:

```text
processing
  → credential rejected            → failed (terminal, no retry)
  → provider unresolved            → failed (terminal, classified)
  → waiting for global slot        → (sigue processing; queue wait corre)
  → provider call in flight
       → succeeded                 → completed
       → failed (non-transient)    → failed (no auto-retry)
       → 429                       → RetryScheduled (máx. 2, Retry-After)
       → timed_out                 → timed_out (unknown; no auto-retry)
```

```text
GlobalConcurrencyPool
  free slot available → acquire → in_flight += 1 → release → in_flight -= 1
  pool full           → queued  → (wait) → acquire when a slot frees
```

`in_flight` nunca supera `cap`. `queued` no transita a `failed` por el tope.

## Boundaries

- Las credenciales viven solo en settings del worker. No viajan en el broker, no se persisten en `input_data`, no aparecen en HTTP ni en logs (ADR-047, NFR-6).
- `ProviderResolutionService` no modifica `CatVTONReplicateProvider`; lo envuelve.
- `ConcurrencyGuardService` y `GlobalConcurrencyService` son dos mecanismos: uno evita duplicar *un* job; el otro limita *cuántos* jobs llaman al proveedor a la vez.
- `RetryPolicyService` no se reescribe. Este bolt solo cambia el timeout que la alimenta y confirma que Replicate hereda `429` / no transitorio / `timed_out`.
- Informar indisponibilidad *antes de encolar* (FR-10, redacción del requirement) es un uso futuro del mismo `CredentialRequirement` por la orquestación (bolt 053). Este bolt garantiza la guarda en el worker, que es el bloque inverso actual.
- El estado agregado del photoshoot (unidad 003) *lee* `QueueWaitDuration` y `ExecutionDuration`; este contexto las *escribe*.
- Historias 005 (consumo Replicate) y 006 (overlay de slug) están fuera: `UsageAccountingService` y `CompositionVersion` no se extienden aquí.

## Story Coverage

| Story | Cómo la cubre el modelo |
|-------|-------------------------|
| **001-replicate-provider-wiring** | `GenerationProvider.replicate`, `ProviderResolutionService`, `ProviderAdapterRef`, `TryOnInputContract`. OpenAI sin cambio. Desconocido → `ProviderUnresolved`. |
| **002-provider-credential-gating** | `CredentialRequirement`, `CredentialGateService`, `CredentialRejection` antes de lease y red. Códigos distintos de fallo de proveedor. Sin secretos en logs. |
| **003-global-concurrency-cap** | `GlobalConcurrencyPool`, `GlobalConcurrencyCap`, `SlotAcquisition`, coexistencia con `ConcurrencyLease`. Excedente encola. Duraciones de cola vs ejecución. |
| **004-provider-timeout-policy** | `ProviderTimeout` por proveedor (≥ 900 s Replicate). `ProviderCallTimedOut` ≤ 30 s. ADR-049 + `RetryPolicyService` para 429 / no transitorio / reintento manual. |

## Open Questions Retained

- **OQ-3**: valor de producción del tope. El modelo fija “configurable ≥ 1, propuesta 2”. No decide el número final.
- **Backing del pool** (Redis vs prefetch de RabbitMQ vs otro): decisión de Stage 2, no de este modelo. El contrato de dominio (`acquire` puede esperar, `in_flight ≤ cap`, no se pierde trabajo al reiniciar) es independiente del backing.
