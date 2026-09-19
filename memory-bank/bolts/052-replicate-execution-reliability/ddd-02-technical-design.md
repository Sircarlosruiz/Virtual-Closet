---
unit: 004-replicate-execution-reliability
bolt: 052-replicate-execution-reliability
stage: design
status: complete
updated: 2026-09-19T01:37:20Z
---

# Technical Design - replicate-execution-reliability

## Architecture Pattern

Sigue el patrón por capas ya usado en los bolts 043/044 (`router → service → repository → model`, con el worker Celery en el borde de infraestructura). Este bolt **no abre endpoints nuevos de escritura**. Toda la lógica nueva vive como servicios de dominio invocados desde `generate_image_task`, más configuración de despliegue.

Rationale: el bloqueante actual está en el worker, no en el contrato HTTP. Meter la guarda, el tope y el timeout en servicios testables evita inflar la task y no acopla Replicate al router.

## Layer Structure

```text
┌─────────────────────────────┐
│      Presentation           │  GET job detail (campos aditivos de duración).
│                              │  Estado agregado del photoshoot: bolt 053.
├─────────────────────────────┤
│      Application            │  generate_image_task orquesta el orden
│                              │  resolve → gate → lease → slot → call
├─────────────────────────────┤
│        Domain               │  ProviderResolution, CredentialGate,
│                              │  GlobalConcurrency, ProviderTimeoutPolicy
│                              │  (+ RetryPolicy y ConcurrencyGuard, sin reescritura)
├─────────────────────────────┤
│     Infrastructure          │  Redis (pool global), Settings, adaptador
│                              │  Replicate (wrap), Postgres (duraciones)
└─────────────────────────────┘
```

## Components

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Config | `core/config.py` | `IMAGE_GENERATION_GLOBAL_CONCURRENCY` (≥ 1, default 2), `IMAGE_GENERATION_OPENAI_TIMEOUT_SECONDS` (default 60), `IMAGE_GENERATION_REPLICATE_TIMEOUT_SECONDS` (default 900), `IMAGE_GENERATION_SLOT_RETRY_COUNTDOWN_SECONDS` (default 2), buffer de `time_limit` Celery |
| Service | `services/credential_gate_service.py` | `require(provider)` → ok o `PROVIDER_CREDENTIAL_MISSING`. No lee la clave del otro proveedor |
| Service | `services/global_concurrency_service.py` | `try_acquire(job_id)` / `release(job_id)` sobre Redis. No bloquea dentro de la task |
| Service | `services/provider_timeout_policy.py` | `timeout_for(provider)` desde settings. OpenAI y Replicate independientes |
| Provider | `services/image_generation/replicate_tryon_adapter.py` | Implementa el protocolo de generación (ADR-046). Envuelve `CatVTONReplicateProvider`; **no** edita `catvton_replicate_provider.py`. Traduce `input_data` → `(garment, model, cloth_type)` |
| Worker | `tasks/image_generation.py` | Sustituye la guarda global de `OPENAI_API_KEY`. `_get_provider` resuelve `replicate`. Orquesta el orden del modelo. Reagenda si no hay hueco |
| Model | `models/generation_job.py` | Columnas aditivas de espera/ejecución |
| Repository | `repositories/generation_job_repo.py` | `record_concurrency_wait_started`, `record_provider_call_started`, `record_durations` |
| Schema | `api/schemas/image_generation.py` | Campos opcionales `queue_wait_seconds`, `execution_seconds` en el GET de job |
| Tests | `backend/tests/...` | Gate, resolución, tope Redis (fake), timeouts, regresión `text` del intent 008 |

## Decision: backing del tope global = Redis

Candidatos de la historia 003: semáforo Redis vs `worker_prefetch_multiplier` en RabbitMQ.

**Elegido: semáforo Redis no bloqueante + reagenda Celery.**

1. El tope es **global al despliegue**, no por proceso. `prefetch × N workers` no puede garantizar `in_flight ≤ 2` si hay más de un worker.
2. `REDIS_URL` ya existe (denylist de sesión, ADR-016/023/027). El tope es coordinación efímera cross-worker: encaja en ese precedente.
3. ADR-050 rechazó Redis para el **lease por job** porque ese lease es 1:1 con una fila Postgres. El pool global **no** es 1:1 con una fila; no contradice ADR-050. Los dos mecanismos coexisten.
4. Bloquear con `BLPOP` dentro de la task ocuparía un worker durante toda la espera y chocaría con `time_limit` de Celery (una espera de 50 min + llamada de 10 min no cabe en un `time_limit` acotado al timeout de Replicate).
5. Reagendar con `countdown` deja el excedente en RabbitMQ: no falla, sobrevive a un restart del worker, y no incrementa `retry_count` del proveedor.

### Contrato Redis

- SET `imggen:global_in_flight` — miembros = `job_id` en vuelo
- STRING `imggen:slot:{job_id}` — TTL = `timeout_for(provider) + 60s` (recuperación si el worker muere con el hueco)
- Script Lua `try_acquire(job_id, cap)`:
  - si `job_id` ya está en el SET → éxito idempotente (redelivery del holder)
  - si `SCARD < cap` → `SADD` + `SET` con TTL → éxito
  - si no → denegado
- `release(job_id)`: `SREM` + `DEL` de la clave TTL
- Cada `try_acquire` expulsa del SET los `job_id` cuya clave TTL ya no existe (holder muerto)

`cap` se lee de settings en cada acquire (cambio de env requiere restart del worker; es valor de despliegue, no de código).

Validación: Pydantic `Field(ge=1)` en `IMAGE_GENERATION_GLOBAL_CONCURRENCY`. 0 o negativo tumba el arranque, no el job.

## Decision: espera de hueco = reagenda, no bloqueo

Si `try_acquire` deniega:

1. Liberar el lease por job (si se tomó)
2. Persistir `concurrency_wait_started_at` solo la primera vez
3. Reencolar `generate_image_task(job_id)` con `countdown = IMAGE_GENERATION_SLOT_RETRY_COUNTDOWN_SECONDS`
4. Return OK de la task — **no** es `failed`, **no** crea `ProviderInvocation`, **no** incrementa `retry_count`

Tope de seguridad de reagendas de hueco: `IMAGE_GENERATION_SLOT_WAIT_MAX_SECONDS` (default 6 h). Solo entonces se marca fallo clasificado `GLOBAL_CONCURRENCY_WAIT_EXHAUSTED` (terminal, caso patológico de pool atascado). El camino feliz de 12 jobs × minutos cabe holgadamente.

### Orden efectivo en la task (refina el modelo)

El modelo pone lease antes de slot para no gastar un hueco si el lease falla. Eso se mantiene con acquire **no bloqueante** de ambos:

```text
resolve provider
require credential          # si falla: job failed, sin lease ni Redis ni red
try lease                   # si ocupado y no stale: exit (duplicado real)
try global slot             # si denegado: release lease, requeue, return
record provider_call_started + queue_wait_seconds
invoke adapter(timeout)
release slot
release lease
classify via RetryPolicyService
```

Si el worker muere **esperando** (entre denegaciones): no hay slot, el lease ya se soltó, Celery reentrega. Si muere **en vuelo**: el TTL de Redis libera el hueco; el lease huérfano sigue siendo la limitación conocida de ADR-050.

No se añade heartbeat al lease en este bolt. La reagenda suelta el lease, así que la espera larga no lo retiene.

## Decision: timeout en el adaptador + red de seguridad Celery

| Capa | OpenAI | Replicate |
|------|--------|-----------|
| Timeout de llamada | `IMAGE_GENERATION_OPENAI_TIMEOUT_SECONDS` (60) | `IMAGE_GENERATION_REPLICATE_TIMEOUT_SECONDS` (900) |
| Dónde se aplica | Cliente/adaptador OpenAI existente | Borde del `ReplicateTryOnAdapter` (`asyncio.wait_for` o timeout del cliente envuelto). **No** se edita `catvton_replicate_provider.py` |
| Celery `soft_time_limit` | `REPLICATE + 45s` | igual (misma task) |
| Celery `time_limit` | `REPLICATE + 60s` | igual |

El timeout que “cuenta” para NFR-3 es el del adaptador, específico por proveedor. Celery solo evita una task colgada: al disparar `soft_time_limit`, el handler persiste `timed_out` y libera slot+lease en ≤ 30 s (NFR-3).

`RetryPolicyService.classify_timeout` no se toca. `429` sigue con máximo 2 reintentos y `Retry-After`. Errores no transitorios no se reintentan.

Prueba explícita: los dos timeouts son independientes (cambiar uno no muta el otro).

## API Design

Este bolt no añade rutas de comando. Extiende el GET ya entregado para que las duraciones sean verificables sin esperar al bolt 053.

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `GET /api/image-generation/jobs/{job_id}` (extendido) | GET | — | Campos existentes + `queue_wait_seconds: int \| null` + `execution_seconds: int \| null`. Nunca credenciales |
| Estado agregado photoshoot | — | — | Fuera de alcance. 053 leerá las mismas columnas |

No hay POST nuevo. La guarda de credencial **no** se expone como endpoint de health; FR-10 “antes de encolar” lo consume 053 reutilizando `CredentialGateService`.

## Data Persistence

| Table | Columns | Relationships |
|-------|---------|---------------|
| `generation_jobs` (extendida) | `concurrency_wait_started_at TIMESTAMPTZ NULL`, `provider_call_started_at TIMESTAMPTZ NULL`, `queue_wait_seconds INT NULL`, `execution_seconds INT NULL` | Aditivas, nullable. Jobs 008 existentes siguen válidos (null) |
| `provider_invocations` | sin cambio de esquema | El intento usa `started_at`/`completed_at` ya existentes; `execution_seconds` del job se alinea con ellos |
| Redis | claves efímeras arriba | No es fuente de verdad del job |

Migración Alembic aditiva. Downgrade: drop de las 4 columnas.

Fórmulas:

- `queue_wait_seconds = provider_call_started_at - concurrency_wait_started_at` (0 si hubo hueco inmediato)
- `execution_seconds = completed_at - provider_call_started_at`

## Security Design

| Concern | Approach |
|---------|----------|
| Secretos | ADR-047: el broker sigue llevando solo `job_id`. La guarda lee settings en el worker. El valor de la clave no entra en excepciones, logs, Redis ni columnas |
| Guarda | `bool(settings.<KEY>)` — presencia, no eco del valor. Mensaje fijo: `Image generation is unavailable: {provider} is not configured` |
| Autenticación | GET job: la misma dependencia de staff/ownership de 043. Sin superficie nueva de escritura |
| Redis | Claves con `job_id` UUID, sin tokens de proveedor |
| Logging | `info` en resolve/acquire/release; `warn` en credencial ausente y reagenda de hueco; `error` en timeout. Nunca `settings.OPENAI_API_KEY` / `REPLICATE_API_KEY` |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| FR-9 / 001 | `_get_provider("replicate")` → `ReplicateTryOnAdapter` wrapping la ruta existente. `openai` intacto. Desconocido → `ProviderRequestError` clasificado |
| FR-10 / 002 | Gate por `job.provider` **antes** de lease, Redis y red. OpenAI vacío + Replicate presente = job Replicate completa |
| NFR-2 / 003 | Redis SET + cap de settings. 12 resultados / cap 2 completan. Tests miden `SCARD` máximo. Excedente reencola |
| NFR-3 / 004 | Timeout ≥ 900 s Replicate; OpenAI corto. Soft limit persiste `timed_out` en ≤ 30 s. Sin retry automático |
| NFR-6 | Código `PROVIDER_CREDENTIAL_MISSING` sin valor de clave. Tests de log/HTTP assertion |
| Regresión 008 | Suite `text` de image generation debe pasar: misma resolución OpenAI, mismo timeout OpenAI, gate solo mira `openai` en esos jobs |

## Error Handling

| Error Type | Code | Response / job outcome |
|------------|------|------------------------|
| Credencial del proveedor del job ausente | `PROVIDER_CREDENTIAL_MISSING` | Job → `failed`, `retryable=false`. Distinto de `PROVIDER_ERROR` |
| Proveedor desconocido | `PROVIDER_REQUEST_ERROR` (existente) | Job → `failed`, clasificado, sin red |
| `input_data` sin `garment`/`model`/`cloth_type` en try-on Replicate | `PROVIDER_REQUEST_ERROR` | Job → `failed`, sin llamada HTTP nueva |
| Hueco no disponible | (ninguno) | Reagenda; job sigue `processing` |
| Espera de hueco > máximo de seguridad | `GLOBAL_CONCURRENCY_WAIT_EXHAUSTED` | Job → `failed` (patológico) |
| Timeout de adaptador o soft_time_limit | `PROVIDER_TIMEOUT` | `timed_out`, usage `unknown`, sin auto-retry (ADR-049) |
| HTTP 429 | `PROVIDER_RATE_LIMITED` | Transient, máx. 2, `Retry-After` |
| 4xx/5xx no transitorio | `PROVIDER_ERROR` | Terminal, sin auto-retry |

`ValueError("Image generation is unavailable: provider is not configured")` deja de ser la guarda de arranque. Ese camino se sustituye por `PROVIDER_CREDENTIAL_MISSING` clasificado.

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| Replicate | Inferencia try-on de producción | SDK/ruta ya existente vía `CatVTONReplicateProvider`. Este bolt solo envuelve |
| Redis | Tope global | `REDIS_URL` existente. Fail-closed si Redis no está: no se llama al proveedor (no fail-open). Las reagendas continúan cuando Redis vuelve |
| PostgreSQL | Job + duraciones + lease | `AsyncSession` existente |
| Celery / RabbitMQ | Ejecución y reagenda de hueco | Misma task; `countdown` distinto del retry de proveedor |
| OpenAI | Jobs `text`/`edit`/`extraction` | Sin cambio de comportamiento observable si `OPENAI_API_KEY` está |

### Redis down

Fail-closed: `try_acquire` eleva error de infraestructura, la task se reagenda como si no hubiera hueco (no se abre la llamada). No se “salta” el tope. Alineado con ADR-027 (fail-closed en Redis de auth), aplicado aquí al gasto de inferencia.

## Integration Points (worker)

```text
generate_image_task(job_id)
  job = repo.get(job_id)
  adapter = _get_provider(job)                    # 001
  CredentialGateService.require(job.provider)     # 002
  lease = ConcurrencyGuardService.acquire(job.id)
  slot = GlobalConcurrencyService.try_acquire(job.id, cap)
  if not slot:
      guard.release(lease)
      repo.ensure_wait_started(job.id)
      retry task(countdown=slot_delay)            # 003, no retry_count
      return
  repo.record_call_started(job.id)
  try:
      result = adapter.generate(..., timeout=policy.timeout_for(job.provider))  # 004
  finally:
      GlobalConcurrencyService.release(job.id)
      guard.release(lease)
  RetryPolicyService.classify / persist
```

## Compatibility

- Jobs `openai` del intent 008: misma resolución, mismo timeout por defecto (60 s), gate que solo exige `OPENAI_API_KEY`.
- `ConcurrencyGuardService`, `RetryPolicyService`, `UsageAccountingService`: sin cambio de contrato. El consumo Replicate es bolt 055.
- `CatVTONReplicateProvider` y `services/providers/replicate_provider.py`: solo se importan. Sin cambio de modelo Replicate (`CATVTON_REPLICATE_MODEL`).
- Columnas nuevas nullable: jobs viejos siguen leyéndose.
- Modos `text` / `edit` / `extraction` no se migran a Replicate.

## Test Plan (contrato para Stage 5)

1. `_get_provider(replicate)` devuelve adaptador; `openai` intacto; desconocido → error clasificado
2. Adaptador reutiliza la ruta existente (mock del provider envuelto, cero cliente HTTP nuevo)
3. `OPENAI_API_KEY` vacío + `REPLICATE_API_KEY` presente → job Replicate no eleva ValueError y llega a `generate`
4. Job OpenAI sin clave → `PROVIDER_CREDENTIAL_MISSING`, no reintentable
5. Job Replicate sin clave → mismo código, no reintentable
6. Ambas claves presentes → ninguno ve la del otro
7. Logs/respuestas sin valor de clave
8. Gate ocurre antes de `acquire` lease y antes de Redis (spies de orden)
9. Cap 2, 12 acquires concurrentes → `in_flight` máximo 2; los 12 terminan
10. Denegación de hueco → reagenda, job no `failed`
11. Lease y tope coexisten (duplicado no llama al proveedor; tope no sustituye al lease)
12. Llamada Replicate de 10 min simulada no corta con timeout 900
13. Timeouts OpenAI y Replicate son settings distintos
14. Timeout → `timed_out`, persistido ≤ 30 s, sin `retry_count++`
15. 429 → máx. 2 con `Retry-After`; 4xx no transitorio → sin retry
16. Regresión jobs `text` del intent 008

## Open Questions Carried

- **OQ-3**: valor de producción del tope. Default 2. Ajustable por env.
- Bolt 053 debe leer `queue_wait_seconds` / `execution_seconds` para el estado agregado. Este diseño solo garantiza que se escriben.
