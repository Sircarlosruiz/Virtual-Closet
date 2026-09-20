---
unit: 004-replicate-execution-reliability
intent: 009-bfashion-generation-bridge
phase: inception
status: complete
unit_type: backend
default_bolt_type: ddd-construction-bolt
created: 2026-09-18T10:00:00.000Z
updated: 2026-09-18T10:00:00.000Z
---

# Unit Brief: replicate-execution-reliability

## Purpose

Hacer que el worker de generación sea realmente utilizable en un despliegue Replicate-only, que es la decisión de producción. Hoy no lo es, y no por una carencia sutil: `tasks/image_generation.py::generate_image_task` eleva `ValueError("Image generation is unavailable: provider is not configured")` si `OPENAI_API_KEY` está vacío, **antes** de mirar qué proveedor pide el job. Con Replicate como único proveedor configurado, todo job falla.

Alrededor de ese bloqueante hay tres piezas más que se diseñaron con forma de OpenAI y no sirven para latencias de minutos ni para la telemetría que Replicate sí emite: no existe tope global de concurrencia, el timeout por llamada es de 60 s, y la normalización de consumo filtra a campos de tokens. Esta unidad las corrige con criterios de aceptación propios.

Cierra además el comportamiento del overlay ante el texto que BFashion va a enviar de verdad: no un SKU corto, sino el **slug del producto**.

## Scope

### In Scope
- Resolución del proveedor de Replicate en `_get_provider`
- Comprobación de credencial **por proveedor**, en lugar de la guarda global de `OPENAI_API_KEY`
- Tope global configurable de llamadas simultáneas al proveedor
- Timeouts configurables por proveedor, acordes a latencias de minutos
- Ampliación de `UsageAccountingService` para reconocer la forma de Replicate
- Comportamiento verificable del overlay con slugs largos reales

### Out of Scope
- Sustituir OpenAI por Replicate en los modos `text`, `edit` y `extraction` del intent 008
- Escribir un cliente de Replicate nuevo: se reutiliza el existente
- Cambiar la política de reintentos ya entregada en `RetryPolicyService` más allá de los timeouts
- Facturación o cuotas comerciales por uso
- Cambiar la semántica determinista del compositor (ADR-054) sin decisión de producto (**OQ-1**)

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-9 | Ejecución contra Replicate | Must |
| FR-10 | El worker arranca sin credencial de OpenAI (bloqueante) | Must |
| FR-11 | Superposición del identificador de producto con texto largo | Must |

Verifica además NFR-2 (concurrencia), NFR-3 (timeouts), NFR-4 (consumo) y NFR-7 (overlay).

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| `GenerationJob` (existente) | Portador del proveedor elegido y del desenlace | `provider`, `status`, `error_code`, `retry_count`, `lock_token`, `usage_status`, `usage_model`, `usage_call_count` |
| `ProviderInvocation` (existente) | Un intento contra el proveedor | `attempt_number`, `provider`, `status`, `error_code`, `error_category`, `retryable`, `usage_*` |
| `UsageRecord` (existente, valor) | Consumo normalizado | `status` (`reported` \| `unknown`), `model`, `call_count`, `raw` |
| `CompositionVersion` (existente) | Versión de overlay, `valid` o `blocked` | `sku_normalized`, `placement`, `style`, `spec_hash`, `status`, `fit_result` |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `resolve_provider` | Devuelve el adaptador del proveedor del job | `provider` del job | Adaptador o error clasificado |
| `require_credential` | Verifica la credencial **del proveedor del job** | `provider` | OK o fallo no reintentable |
| `acquire_global_slot` | Toma un hueco del tope global de concurrencia | — | Hueco o espera en cola |
| `normalize_usage` | Normaliza consumo de OpenAI o de Replicate | `provider`, `model`, telemetría cruda | `UsageRecord` |
| `evaluate_fit` | Mide si el texto cabe con la configuración pedida | tamaño de imagen, texto, `placement`, `style` | `fits`, dimensiones medidas, motivo |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 6 |
| Must Have | 6 |
| Should Have | 0 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| `001-replicate-provider-wiring` | Cablear el proveedor de Replicate al worker | Must | Planned |
| `002-provider-credential-gating` | Comprobar la credencial del proveedor del job | Must | Planned |
| `003-global-concurrency-cap` | Limitar las llamadas simultáneas al proveedor | Must | Planned |
| `004-provider-timeout-policy` | Tiempos de espera acordes a Replicate | Must | Planned |
| `005-replicate-usage-accounting` | Registrar el consumo que Replicate sí informa | Must | Planned |
| `006-product-slug-overlay-fit` | Superponer el slug largo de forma predecible | Must | Planned |

---

## Dependencies

### Depends On

Ninguna. Es trabajo de worker y configuración; puede desarrollarse en paralelo a `001` y `002`.

### Depended By

| Unit | Reason |
|------|--------|
| `003-photoshoot-orchestration` | Sin credencial por proveedor, tope de concurrencia y timeouts adecuados, el pipeline no completa contra Replicate |

### External Dependencies

| System | Purpose | Risk |
|--------|---------|------|
| Replicate | Inferencia real | Alto — latencia de minutos, coste, límites de tasa, esquema del modelo |
| Pillow | Medición y render del overlay | Bajo |

---

## Technical Context

### Suggested Technology

Reutilizar la ruta Replicate existente (`services/vton/catvton_replicate_provider.py`, `services/providers/replicate_provider.py`) en lugar de escribir un cliente nuevo. Los timeouts se declaran en `core/config.py` por proveedor; `TRYOFF_MODEL_TIMEOUT_SECONDS = 1800` es el precedente de este repositorio para un pipeline lento.

El tope global de concurrencia es una pieza nueva: `ConcurrencyGuardService` es un *lease por job* (anti-duplicado de entrega) y no limita llamadas simultáneas. Conviene mantener ambos separados y no sobrecargar el lease existente con una segunda responsabilidad.

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| `tasks/image_generation.py::_get_provider` | Resolución del proveedor | Interno |
| `tasks/image_generation.py::generate_image_task` | Guarda de credencial | Interno |
| `ConcurrencyGuardService` | Lease por job (se conserva) | Interno |
| `RetryPolicyService` | Clasificación y reintento | Interno |
| `UsageAccountingService` | Normalización de consumo | Interno |
| `sku_renderer` / `composition_spec` | Medición y render del overlay | Interno |

### Data Storage

| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| `provider_invocations` | SQL | Una fila por intento | Permanente |
| Configuración de proveedor | Variables de entorno | — | — |

---

## Constraints

- Ninguna credencial de proveedor sale del contexto del worker. El navegador jamás la ve.
- El proveedor elegido queda persistido por job y no se cambia silenciosamente si falla.
- Lo que el proveedor no informa se registra como `unknown`, **nunca** como cero. Cualquier coste calculado se identifica como estimación.
- Un timeout con resultado desconocido no se reintenta automáticamente: requiere reintento explícito.
- Los `429` se reintentan como máximo 2 veces respetando `Retry-After`. Los errores no transitorios no se reintentan.
- El overlay no recorta, no escala en silencio ni dibuja fuera del lienzo: si no cabe, la versión queda `blocked` con motivo medido.
- Cambiar la política de ajuste del overlay altera `spec_hash` y la semántica determinista de ADR-054. No se hace sin decisión de producto (**OQ-1**).

---

## Success Criteria

### Functional
- [ ] Con `OPENAI_API_KEY` vacío y `REPLICATE_API_KEY` presente, un job de Replicate completa
- [ ] Un job de OpenAI sin `OPENAI_API_KEY` falla de forma clasificada y no reintentable
- [ ] La ausencia de credencial produce un código de error distinguible de un fallo del proveedor
- [ ] `_get_provider` resuelve el proveedor de Replicate para los modos que este flujo usa
- [ ] Un photoshoot que expande a 12 resultados con el tope en 2 completa con los 12 resultados
- [ ] En ningún instante medido hay más llamadas simultáneas al proveedor que el tope configurado
- [ ] Una llamada a Replicate de 10 minutos no se corta por timeout con la configuración de partida
- [ ] Tras un photoshoot real, al menos un `provider_invocation` queda con `usage_status = "reported"` y su modelo identificado
- [ ] Un slug de más de 30 caracteres produce texto completo dentro de la imagen, o una versión `blocked` con motivo medido
- [ ] Un overlay `blocked` no impide que el resultado base siga siendo candidato publicable

### Non-Functional
- [ ] Al vencer un timeout, el estado de fallo se refleja en ≤ 30 s (NFR-3)
- [ ] El tiempo en cola se expone por separado del tiempo de ejecución (NFR-2)
- [ ] Ninguna credencial aparece en respuestas HTTP ni en registros (NFR-6)
- [ ] Validación visual de al menos 4 photoshoots reales, con al menos un slug de más de 30 caracteres (NFR-7)

### Quality
- [ ] Cobertura de código > 80 %
- [ ] Todos los criterios de aceptación cubiertos por pruebas
- [ ] Revisión de código aprobada

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| `052-replicate-execution-reliability` | ddd | 001, 002, 003, 004 | El worker ejecuta de verdad contra Replicate |
| `055-replicate-execution-reliability` | ddd | 005, 006 | Consumo y overlay verificados con datos reales |

El bolt `055` se ejecuta después de la orquestación porque sus dos historias necesitan imágenes generadas de verdad y slugs reales de BFashion contra los que medir.

---

## Notes

Las historias `002` (credencial por proveedor) y `003` (tope global) tienen efecto sobre todo el worker de generación, no solo sobre este flujo: también afectan a los jobs `text` del intent 008. Ninguna de las dos cambia el comportamiento observable de un despliegue con `OPENAI_API_KEY` configurado, pero conviene ejecutar la regresión de 008 antes de cerrar el bolt `052`.

La historia `006` es la que puede escalar a una decisión de producto. Si al medir slugs reales de BFashion la mayoría no cabe en una línea con `ImageFont.load_default`, las opciones (ajuste automático de tamaño, o partir en dos líneas) cambian `spec_hash` y la semántica determinista de ADR-054, y eso no se decide dentro del bolt.
