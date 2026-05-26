# Épicas y Historias de Usuario — Virtual Closet MVP
## NikaCommerce · Versión 1.0

**Basado en:** PRD v1.0 · Arquitectura Técnica v1.0 · UX Design Spec v1.0  
**Stack:** Next.js 14 App Router · FastAPI · PostgreSQL 16 · RabbitMQ · MinIO · Tailwind + shadcn/ui  
**Entornos:** Docker Compose (dev) · k3s/Hetzner (prod)  
**GPU dev:** NVIDIA Titan RTX (Docker + nvidia runtime) · GPU prod: Replicate API (IDM-VTON)

---

## Épica 1 — Autenticación y Onboarding

**Objetivo:** El mayorista puede crear una cuenta, acceder al producto y completar su primer catálogo dentro del free trial de 30 días.

**Contexto técnico:**
- Auth: JWT en HttpOnly cookie, 7 días de validez, refresh automático
- Tabla: `mayorista` (id, email, password_hash, nombre_negocio, plan, trial_activo, trial_expira_en, whatsapp, created_at)
- Frontend: Next.js App Router, rutas protegidas en `/dashboard/**`
- Backend: FastAPI en `app/routers/auth.py`, tokens con python-jose
- Tests: pytest para endpoints, Playwright para flujo E2E de registro

---

### Historia US-101 · Registro de mayorista
**Story Key:** `1-1-registro-mayorista`

```
Como mayorista,
quiero registrarme con mi email y contraseña,
para acceder al dashboard y empezar a subir prendas.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que accedo a /registro
When completo email, contraseña (≥8 chars) y nombre del negocio
And hago click en "Crear cuenta"
Then se crea mi cuenta con plan=base, trial_activo=true, trial_expira_en=now()+30d
And recibo un email de bienvenida (no bloqueante)
And soy redirigido al dashboard

Given que intento registrarme con un email ya existente
When hago click en "Crear cuenta"
Then veo un mensaje de error claro: "Este email ya está registrado"

Given que ingreso una contraseña menor a 8 caracteres
When hago click en "Crear cuenta"
Then veo un mensaje de validación inline bajo el campo contraseña
```

**Notas técnicas:**
- bcrypt para hash de contraseña (costo=12)
- Email: usar Resend API (SMTP fallback)
- Ruta pública: `POST /api/auth/register`
- Redirección post-registro: `/dashboard/onboarding`
- Source: `arquitectura-tecnica.md` § Schema PostgreSQL

---

### Historia US-102 · Login de mayorista
**Story Key:** `1-2-login-mayorista`

```
Como mayorista registrado,
quiero iniciar sesión con mi email y contraseña,
para acceder a mi dashboard y mis catálogos.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que accedo a /login con credenciales válidas
When hago click en "Iniciar sesión"
Then recibo un JWT en HttpOnly cookie con 7 días de expiración
And soy redirigido a /dashboard

Given que ingreso credenciales incorrectas
When hago click en "Iniciar sesión"
Then veo un error genérico: "Email o contraseña incorrectos"
And NO se revela qué campo falló (seguridad)

Given que mi JWT está por expirar
When realizo cualquier request autenticado
Then el token se renueva automáticamente sin interrumpir la sesión
```

**Notas técnicas:**
- Ruta pública: `POST /api/auth/login`
- Ruta de logout: `POST /api/auth/logout` (elimina cookie)
- Middleware Next.js para proteger `/dashboard/**`
- No almacenar JWT en localStorage (solo HttpOnly cookie)
- Source: `ux-design-specification.md` § Core Interaction Design

---

### Historia US-103 · Onboarding guiado (primera vez)
**Story Key:** `1-3-onboarding-guiado`

```
Como mayorista que acaba de registrarse,
quiero ver una pantalla de bienvenida que me guíe al primer paso,
para saber exactamente qué hacer sin necesidad de leer instrucciones.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que acabo de registrarme y entro al dashboard por primera vez
When la pantalla carga
Then veo una pantalla de onboarding con CTA único: "Subir tu primera prenda"
And la pantalla explica: "30 días gratis en Plan Base, sin tarjeta — hasta 40 prendas al mes"
And NO hay menú de navegación lateral — solo el CTA

Given que ya subí al menos 1 prenda y recargo el dashboard
When la pantalla carga
Then NO se muestra la pantalla de onboarding
And veo el dashboard normal con mis prendas

Given que cierro sesión y vuelvo a entrar sin haber subido prendas
When la pantalla carga
Then veo nuevamente el onboarding
```

**Notas técnicas:**
- Condición: `prendas_count == 0` del mayorista → mostrar onboarding
- Ruta: `/dashboard/onboarding` (redirect desde `/dashboard` si aplica)
- Componente shadcn/ui: sin sidebar/nav para este paso
- Source: `ux-design-specification.md` § User Journey Flows

---

## Épica 2 — Gestión de Prendas

**Objetivo:** El mayorista puede subir, nombrar y ver el estado de sus prendas en el dashboard.

**Contexto técnico:**
- Tabla: `prenda` (id, mayorista_id, nombre, imagen_original_url, estado, created_at, updated_at)
- Estados: `pendiente` → `procesando` → `lista` | `error`
- MinIO bucket: `originals/{mayorista_id}/{prenda_id}/original.jpg`
- Upload: presigned URL de MinIO, frontend sube directo (evita pasar por backend)
- Límite: 40 prendas/mes en plan Base (contar por mes calendario)
- Source: `arquitectura-tecnica.md` § MinIO + Schema PostgreSQL

---

### Historia US-201 · Subir foto de prenda
**Story Key:** `2-1-subir-prenda`

```
Como mayorista,
quiero subir una foto de mi prenda desde la galería o la cámara,
para iniciar el proceso de generación IA.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que estoy en el dashboard y hago click en "Nueva prenda"
When selecciono una foto JPG, PNG o HEIC desde mi galería
Then veo un preview inmediato de la imagen antes de confirmar
And puedo hacer click en "Confirmar" o "Elegir otra"

Given que confirmo la foto
Then la imagen se redimensiona a máximo 1024px en el cliente
And se sube a MinIO via presigned URL
And la prenda se crea en DB con estado=pendiente

Given que selecciono un archivo que no es JPG/PNG/HEIC
When intento subirlo
Then veo un error claro: "Solo se aceptan JPG, PNG o HEIC"

Given que selecciono un archivo mayor a 20MB
When intento subirlo
Then veo un error claro: "La imagen no puede superar 20MB"

Given que ya alcancé el límite de 40 prendas este mes (plan Base)
When intento subir una nueva
Then veo un mensaje de límite alcanzado con opción de upgrade
```

**Notas técnicas:**
- Presigned URL: `GET /api/prendas/upload-url` devuelve URL de MinIO firmada (15 min TTL)
- Redimensión: usar `browser-image-compression` en el frontend
- Ruta upload: `originals/{mayorista_id}/{prenda_id}/original.{ext}`
- Contar prendas del mes: `WHERE mayorista_id=X AND created_at >= date_trunc('month', now())`
- Source: `arquitectura-tecnica.md` § MinIO

---

### Historia US-202 · Nombrar prenda (opcional)
**Story Key:** `2-2-nombrar-prenda`

```
Como mayorista,
quiero poder ponerle nombre a mi prenda,
para identificarla fácilmente en mi catálogo.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que estoy subiendo una prenda
When veo el campo de nombre
Then tiene un placeholder con sugerencia: "Prenda #N" (N = total prendas + 1)

Given que omito el campo de nombre y confirmo
When la prenda se crea
Then se guarda con nombre automático: "Prenda #N"

Given que ingreso un nombre de más de 80 caracteres
When intento confirmar
Then veo un error inline: "Máximo 80 caracteres"

Given que la prenda ya fue creada
When edito su nombre desde el dashboard
Then el nombre se actualiza via PATCH /api/prendas/{id}
And veo feedback toast: "Nombre actualizado"
```

---

### Historia US-203 · Ver listado de prendas en el dashboard
**Story Key:** `2-3-ver-listado-prendas`

```
Como mayorista,
quiero ver todas mis prendas con su estado actual,
para saber cuáles están listas, procesando o con error.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que tengo prendas en distintos estados
When cargo el dashboard
Then veo un grid: 2 columnas en mobile (<768px), 3 en desktop

Given una prenda con estado=lista
When la veo en el grid
Then muestra: imagen generada (thumbnail 400px), nombre, badge "Lista" (emerald)
And al tap navego a la pantalla de resultado

Given una prenda con estado=procesando
When la veo en el grid
Then muestra: imagen original, nombre, badge "Procesando" (amber + barra animada)

Given una prenda con estado=error
When la veo en el grid
Then muestra badge "Error" (rojo) y opción de reintentar

Given que no tengo ninguna prenda
When cargo el dashboard
Then veo empty state con CTA "Subir primera prenda"
```

**Notas técnicas:**
- Ruta: `GET /api/prendas` con paginación (cursor-based, 20 por página)
- Actualización en tiempo real via WebSocket para cambios de estado
- Thumbnails: URL presignada MinIO con TTL 24h, renovadas al cargar el listado
- Source: `arquitectura-tecnica.md` § WebSocket + MinIO

---

### Historia US-204 · Eliminar prenda
**Story Key:** `2-4-eliminar-prenda`

```
Como mayorista,
quiero poder eliminar una prenda de mi dashboard,
para mantener mi catálogo organizado.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que abro el menú contextual (···) de una prenda
When hago click en "Eliminar"
Then veo un modal de confirmación: "¿Eliminar esta prenda? Esta acción no se puede deshacer"

Given que confirmo la eliminación
When el modal se cierra
Then la prenda desaparece del dashboard inmediatamente (optimistic update)
And se eliminan la prenda y sus generaciones de DB y MinIO

Given que la prenda estaba en un catálogo publicado
When confirmo la eliminación
Then la prenda se elimina también de ese catálogo
```

---

## Épica 3 — Pipeline de Generación IA

**Objetivo:** El mayorista puede seleccionar un modelo IA y obtener una imagen profesional de su prenda en menos de 90 segundos.

**Contexto técnico:**
- RabbitMQ exchange: `vton.direct`
- Queues: `vton.generation.normal` (plan Base), `vton.generation.priority` (plan Pro), `vton.generation.dead`
- Tabla: `generacion` (id, mayorista_id, prenda_id, modelo_ia_id, estado, imagen_generada_key, thumbnail_key, costo_inferencia_usd, error_message, created_at, updated_at)
- Tabla: `modelo_ia` (id, nombre, descripcion, thumbnail_key, plan_minimo, created_at)
- Worker: Celery + FastAPI, clase `VTONProvider` abstrae LocalGPU (dev) y Replicate (prod)
- WebSocket: notificación al completar job via `ConnectionManager` de Epic 2
- Env var: `VTON_PROVIDER=local|replicate`, `REPLICATE_API_KEY`, `RABBITMQ_URL`
- MinIO buckets: `generated/`, `thumbnails/`, `model-thumbnails/`
- **Implementado:** Sprint 2 (2026-05-20) — backend completo + frontend completo + tests
- Source: `arquitectura-tecnica.md` § VTONProvider + RabbitMQ

---

### Historia US-301 · Seleccionar modelo IA
**Story Key:** `3-1-seleccionar-modelo`

```
Como mayorista,
quiero elegir entre los modelos IA disponibles en mi plan,
para generar la imagen de mi prenda sobre el modelo que prefiero.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que tengo plan Base
When abro el selector de modelo
Then veo 6 modelos disponibles (thumbnail 56px + nombre + descripción breve)
And veo los modelos Pro bloqueados con icono de lock (no interactivos)

Given que selecciono un modelo
Then se resalta con highlight + checkmark
And aparece el botón "Generar" en la bottom bar

Given que tengo una generación previa
When abro el selector de modelo para una nueva prenda
Then el último modelo usado aparece pre-seleccionado
```

**Notas técnicas:**
- Ruta: `GET /api/modelos-ia` filtrando por plan del mayorista
- Modelos almacenados en tabla `modelo_ia`, thumbnails en MinIO bucket `model-thumbnails/`
- Persistir `ultimo_modelo_id` en localStorage del frontend
- **Implementado:** Model, Repo, Service, Schema, Router + `ModelSelectorScreen` frontend
- Seed script: `backend/scripts/seed_modelos_ia.py` (6 modelos, 4 base + 2 pro)
- Source: `arquitectura-tecnica.md` § Schema + `ux-design-specification.md` § Component Strategy

---

### Historia US-302 · Iniciar generación de imagen IA
**Story Key:** `3-2-iniciar-generacion`

```
Como mayorista,
después de seleccionar el modelo,
quiero iniciar la generación presionando un botón,
para ver mi prenda sobre el modelo en menos de 90 segundos.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que seleccioné un modelo y hago click en "Generar"
Then se crea un job en RabbitMQ (queue según el plan del mayorista)
And navego a la pantalla de progreso
And la prenda cambia a estado=procesando

Given que estoy en la pantalla de progreso
When el job avanza
Then veo 3 estados secuenciales: "Analizando prenda..." → "Aplicando modelo..." → "Finalizando..."

Given que salgo de la pantalla de progreso
When el job completa
Then recibo notificación WebSocket: "¡Tu prenda [nombre] está lista!"

Given que el job tarda más de 90 segundos
When sigo en la pantalla de progreso
Then veo mensaje: "Tomando más tiempo de lo usual, casi listo..."

Given que el worker falla
Then se reintenta automáticamente hasta 3 veces
And si falla las 3 veces, el job pasa a la dead-letter queue
And la prenda cambia a estado=error
```

**Notas técnicas:**
- Ruta: `POST /api/generaciones` → publica en RabbitMQ via Celery `send_task` y devuelve `generacion_id`
- Mensajes RabbitMQ: `durable=True` para sobrevivir restarts
- WebSocket: endpoint `wss://api/ws/{mayorista_id}` para notificaciones via `ConnectionManager`
- VTONProvider.generate(garment_img, model_img) → bytes de imagen generada
- La imagen generada se sube a MinIO: `generated/{mayorista_id}/{generacion_id}.jpg`
- Thumbnail 400px: `thumbnails/{mayorista_id}/{generacion_id}.jpg`
- **Implementado:** VTONProvider (base + replicate + local), Celery task `generate_vton`, Model, Repo, Service, Schema, Router + `ProgressScreen` frontend
- Source: `arquitectura-tecnica.md` § RabbitMQ + VTONProvider

---

### Historia US-303 · Ver resultado de generación (momento WOW)
**Story Key:** `3-3-ver-resultado`

```
Como mayorista,
quiero ver la imagen generada a pantalla completa,
para evaluar si el resultado es adecuado para mi catálogo.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que la generación completó exitosamente
When la pantalla de resultado carga
Then veo la imagen generada a pantalla completa (viewport height)

Given que hago tap en "Ver original"
Then veo la foto original con un fade suave (transition 300ms)
And puedo volver a la vista generada con otro tap

Given que hago tap en "Agregar al catálogo"
Then la prenda se agrega al catálogo activo (o se me pide crear uno)
And veo feedback toast: "Prenda agregada al catálogo"

Given que hago tap en "Regenerar"
Then vuelvo al selector de modelo con la prenda pre-cargada

Given que la generación falló
When cargo la pantalla de resultado
Then veo pantalla de error con descripción + botón "Reintentar"
```

**Notas técnicas:**
- La imagen generada tiene URL presignada MinIO (24h TTL) via bucket `generated/`
- También se genera thumbnail 400px: `thumbnails/{mayorista_id}/{generacion_id}.jpg`
- Componente: `GenerationResultScreen` con toggle de comparación original/generado
- Guardar `costo_inferencia_usd` del job en la tabla `generacion`
- **Implementado:** `GET /api/generaciones/{id}` con presigned URLs + `GenerationResultScreen` frontend
- Source: `ux-design-specification.md` § Design Direction (Direction 1: Card Flow — WOW result screen)

---

### Historia US-304 · Regenerar con otro modelo
**Story Key:** `3-4-regenerar-modelo`

```
Como mayorista,
quiero regenerar la imagen con un modelo diferente,
para encontrar la mejor combinación para mi prenda.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que estoy viendo un resultado de generación
When hago tap en "Regenerar"
Then vuelvo al selector de modelo con la misma prenda pre-cargada

Given que inicio una nueva generación con otro modelo
Then se crea un nuevo job — la generación anterior NO se elimina
And el mayorista puede tener múltiples generaciones de la misma prenda

Given que quiero ver generaciones anteriores de una prenda
When las listo
Then veo todas las generaciones ordenadas por fecha, con el modelo usado
```

**Notas técnicas:**
- Una prenda puede tener N generaciones en tabla `generacion`
- Al mostrar la prenda en el catálogo se usa la generación más reciente (o la que el mayorista elija)
- **Implementado:** `GET /api/prendas/{id}/generaciones` + carrusel horizontal en `ResultScreen` + navegación con `prendaId` query params
- Source: PRD § US-304

---

## Épica 4 — Gestión de Catálogos

**Objetivo:** El mayorista puede organizar sus prendas listas en un catálogo y publicarlo con un link único.

**Contexto técnico:**
- Tabla: `catalogo` (id, mayorista_id, nombre, slug, estado, created_at, updated_at)
- Estados catálogo: `despublicado` | `publicado`
- Tabla: `catalogo_prenda` (catalogo_id, prenda_id, orden) — M:N
- Slug: basado en nombre del catálogo, slugify, único por mayorista
- URL pública: `/c/{slug}` — SSR con Next.js
- Source: `arquitectura-tecnica.md` § Schema PostgreSQL

---

### Historia US-401 · Crear catálogo
**Story Key:** `4-1-crear-catalogo`

```
Como mayorista,
quiero crear un catálogo y ponerle nombre,
para organizar mis prendas por colección.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que estoy en la tab "Catálogos" del dashboard
When hago click en "Nuevo catálogo"
Then veo un formulario con campo de nombre (obligatorio, máx 80 chars)

Given que ingreso un nombre y confirmo
Then se crea el catálogo en estado=despublicado
And soy llevado a la vista del catálogo para agregar prendas

Given que omito el nombre e intento crear
Then veo error inline: "El nombre del catálogo es requerido"
```

---

### Historia US-402 · Agregar prendas a un catálogo
**Story Key:** `4-2-agregar-prendas`

```
Como mayorista,
quiero agregar prendas a mi catálogo,
para armar la colección que voy a compartir con mis revendedores.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que estoy en la vista de un catálogo
When hago click en "Agregar prendas"
Then veo un selector que muestra solo prendas con estado=lista

Given que selecciono prendas y confirmo
Then las prendas se agregan al catálogo con su orden actual

Given que quiero reordenar las prendas
When en desktop: hago drag-and-drop | en mobile: uso botones ↑↓
Then el orden se guarda en catalogo_prenda.orden

Given que quiero agregar una prenda que ya está en otro catálogo
Then puedo agregarla (una prenda puede estar en múltiples catálogos)
```

---

### Historia US-403 · Publicar catálogo
**Story Key:** `4-3-publicar-catalogo`

```
Como mayorista,
quiero publicar mi catálogo con un link único,
para poder compartirlo con mis revendedores por WhatsApp.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que tengo un catálogo con al menos 1 prenda
When hago click en "Publicar"
Then se genera un slug único: slugify(nombre) → "verano-2026"
And si el slug ya existe: se agrega sufijo → "verano-2026-2"
And se genera un código QR del link

Given que el catálogo se publica exitosamente
Then navego a la pantalla celebratoria (CatalogShareSheet)
And el catálogo es accesible en /c/{slug} inmediatamente

Given que quiero despublicar el catálogo
When hago click en "Despublicar"
Then el catálogo cambia a estado=despublicado
And la URL /c/{slug} devuelve 404
And los catálogos ya compartidos ya no son accesibles
```

**Notas técnicas:**
- QR: usar librería `qrcode` (Python) o `qrcode.react` (frontend)
- Ruta: `POST /api/catalogos/{id}/publicar`
- SSR: Next.js genera la página `/c/{slug}` on-demand (ISR con revalidación)
- Source: `arquitectura-tecnica.md` § Kubernetes Ingress (public catalog route)

---

### Historia US-404 · Compartir catálogo
**Story Key:** `4-4-compartir-catalogo`

```
Como mayorista,
quiero compartir mi catálogo publicado por WhatsApp con un tap,
para que mis revendedores puedan verlo inmediatamente.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que estoy en la pantalla celebratoria post-publicación
When hago tap en "Compartir por WhatsApp"
Then WhatsApp abre con texto: "Te comparto mi catálogo [nombre]: [link]"

Given que hago tap en "Copiar link"
Then la URL se copia al portapapeles
And veo toast: "Link copiado"

Given que hago tap en "Descargar QR"
Then descargo el QR como imagen PNG

Given que vuelvo a ver el catálogo después (no en pantalla celebratoria)
Then los 3 métodos (WhatsApp, copiar link, descargar QR) están disponibles
```

---

## Épica 5 — Catálogo Público (Vista del Revendedor)

**Objetivo:** El revendedor puede ver el catálogo completo desde su teléfono sin necesidad de cuenta, login o app.

**Contexto técnico:**
- Ruta: `/c/{slug}` — Next.js SSR (Server Component)
- Sin autenticación requerida
- Optimizado para mobile-first, Android, conexión 3G
- LCP < 3s en 3G — imágenes con lazy loading y presigned URLs MinIO
- Tabla: `catalogo_view_event` (id, catalogo_id, ip_hash, user_agent, timestamp)
- Source: `arquitectura-tecnica.md` § Next.js SSR + `ux-design-specification.md` § Responsive

---

### Historia US-501 · Ver catálogo público
**Story Key:** `5-1-ver-catalogo-publico`

```
Como revendedor que recibí un link por WhatsApp,
quiero abrir el catálogo en mi browser sin instalar nada,
para ver las prendas disponibles y decidir qué pedir.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que abro /c/{slug} de un catálogo publicado
When la página carga
Then funciona sin autenticación y sin JavaScript habilitado (SSR)
And LCP es < 3 segundos en conexión 3G
And veo: nombre de colección, nombre del mayorista, número de prendas

Given que accedo a /c/{slug} de un catálogo inexistente o despublicado
Then veo una página 404 con mensaje claro
```

**Notas técnicas:**
- Next.js Server Component con fetch cacheado (ISR revalidate: 300s)
- `<Image>` de Next.js con `priority={true}` para las primeras 2 prendas
- Source: `ux-design-specification.md` § Public Catalog (Dirección 1: Card Flow)

---

### Historia US-502 · Ver detalle de prenda en catálogo
**Story Key:** `5-2-ver-detalle-prenda`

```
Como revendedor,
quiero ver claramente cada prenda sobre el modelo con sus detalles,
para tomar una decisión de compra con confianza.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que estoy viendo el catálogo
When scrolleo por las prendas
Then cada prenda muestra: imagen generada (full ancho en mobile), nombre, descripción

Given que hago tap en una imagen
Then se abre en vista pantalla completa (fullscreen modal)

Given que las imágenes cargan
Then las primeras 2 tienen loading="eager", el resto loading="lazy"
And las URLs son presignadas MinIO con TTL 24h (renovadas al cargar la página)
```

---

### Historia US-503 · Contactar al mayorista desde el catálogo
**Story Key:** `5-3-contactar-mayorista`

```
Como revendedor,
quiero poder contactar al mayorista directamente desde el catálogo,
para hacer mi pedido sin salir de la experiencia.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que el mayorista configuró su número de WhatsApp
When veo el catálogo
Then hay un botón sticky en el bottom: "Hacer pedido por WhatsApp"
And al tap abre WhatsApp con: "Hola, vi tu catálogo [nombre]. Quiero hacer un pedido."

Given que el mayorista NO configuró su número de WhatsApp
When veo el catálogo
Then el botón de WhatsApp NO aparece en la página
```

**Notas técnicas:**
- Botón sticky: `position: fixed; bottom: 0` — siempre visible al scrollear
- WhatsApp deep link: `https://wa.me/{numero}?text={mensaje_encoded}`
- Source: `ux-design-specification.md` § Component Strategy

---

### Historia US-504 · Registro de visualización de catálogo
**Story Key:** `5-4-registro-visualizacion`

```
Como sistema,
quiero registrar cada vez que alguien abre el catálogo,
para que el mayorista pueda ver cuántas vistas tuvo su colección.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que alguien abre /c/{slug}
Then se registra un evento: catalogo_id, ip_hash (SHA-256 anonimizado), user_agent, timestamp
And NO se registra ningún dato personal identificable

Given que el mayorista ve su dashboard
Then ve el contador de vistas de cada catálogo (número simple)
```

**Notas técnicas:**
- Fire-and-forget: POST asíncrono desde el Server Component, no bloquea la carga
- IP hash: SHA-256 del IP + salt rotativo diario (privacidad)
- Contar: `SELECT COUNT(*) FROM catalogo_view_event WHERE catalogo_id=X`
- Source: PRD § US-504

---

## Épica 6 — Billing y Free Trial

**Objetivo:** El mayorista puede activar su suscripción después del free trial con tarjeta de crédito.

**Contexto técnico:**
- Stripe Checkout (hosted) — no almacenar datos de tarjeta
- Tabla `mayorista`: columnas `plan`, `trial_activo`, `trial_expira_en`, `stripe_customer_id`, `suscripcion_activa`
- Stripe webhook: `checkout.session.completed` → activar suscripción
- Stripe Customer Portal para facturas y cancelación
- Source: `arquitectura-tecnica.md` § Stripe + `modelo-precios.md`

---

### Historia US-601 · Free trial de 30 días
**Story Key:** `6-1-free-trial`

> Política canónica: `modelo-precios.md` § Política de free trial.

```
Como mayorista recién registrado,
quiero usar el producto gratis durante 30 días,
para evaluar si vale la pena pagar antes de comprometerme.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que me registré hace menos de 30 días y trial_activo=true
When uso el dashboard
Then puedo generar imágenes con los límites del Plan Base (hasta 40 prendas/mes)
And no existe un tope adicional de "5 prendas gratis" distinto del trial de 30 días
And veo en el dashboard: "X días restantes de tu prueba gratuita" (barra de progreso)

Given que faltan 5 días o menos para el vencimiento del trial
When abro el dashboard
Then veo un banner de aviso con CTA para suscribirse

Given que el trial vence sin suscripción
When intento generar una nueva imagen
Then la función de generación está bloqueada
And veo CTA para suscribirse
And los catálogos ya publicados siguen accesibles para los revendedores
```

---

### Historia US-602 · Suscripción al plan Base
**Story Key:** `6-2-suscripcion-base`

```
Como mayorista que quiere continuar usando el producto,
quiero suscribirme al plan Base con mi tarjeta de crédito,
para seguir generando imágenes y publicando catálogos.
```

**Criterios de aceptación (BDD):**

```gherkin
Given que hago click en "Suscribirme — $39/mes"
When soy redirigido a Stripe Checkout
Then completo el pago de forma segura (Stripe hosted)

Given que el pago es exitoso
Then recibo webhook de Stripe: checkout.session.completed
And en DB: plan=base, trial_activo=false, suscripcion_activa=true
And recibo email de confirmación de pago

Given que quiero ver mis facturas
When accedo al Customer Portal desde el dashboard
Then veo el historial de pagos (Stripe Customer Portal)

Given que quiero cancelar
When hago click en "Cancelar suscripción" (desde Stripe Customer Portal)
Then mantengo acceso hasta el fin del período pagado
```

**Notas técnicas:**
- Stripe mode: production `price_XXXX`, test `price_XXXX_test`
- Webhook secret configurado en env: `STRIPE_WEBHOOK_SECRET`
- Ruta webhook: `POST /api/billing/webhook` (sin auth, verificar firma Stripe)
- Price ID del plan Base: configurar en Stripe Dashboard y referenciar en env
- Source: `modelo-precios.md` § Plan Base $39/mes

---

## Resumen del Backlog

| Story Key | US | Épica | Sprint | Prioridad |
| --- | --- | --- | --- | --- |
| 1-1-registro-mayorista | US-101 | Auth | 1 | Must |
| 1-2-login-mayorista | US-102 | Auth | 1 | Must |
| 1-3-onboarding-guiado | US-103 | Auth | 1 | Should |
| 2-1-subir-prenda | US-201 | Prendas | 1 | Must |
| 2-2-nombrar-prenda | US-202 | Prendas | 1 | Should |
| 2-3-ver-listado-prendas | US-203 | Prendas | 2 | Must |
| 2-4-eliminar-prenda | US-204 | Prendas | 4 | Could |
| 3-1-seleccionar-modelo | US-301 | Pipeline IA | 2 | Must |
| 3-2-iniciar-generacion | US-302 | Pipeline IA | 2 | Must |
| 3-3-ver-resultado | US-303 | Pipeline IA | 2 | Must |
| 3-4-regenerar-modelo | US-304 | Pipeline IA | 2 | Should |
| 4-1-crear-catalogo | US-401 | Catálogos | 3 | Must |
| 4-2-agregar-prendas | US-402 | Catálogos | 3 | Must |
| 4-3-publicar-catalogo | US-403 | Catálogos | 3 | Must |
| 4-4-compartir-catalogo | US-404 | Catálogos | 3 | Should |
| 5-1-ver-catalogo-publico | US-501 | Catálogo Público | 3 | Must |
| 5-2-ver-detalle-prenda | US-502 | Catálogo Público | 3 | Must |
| 5-3-contactar-mayorista | US-503 | Catálogo Público | 3 | Should |
| 5-4-registro-visualizacion | US-504 | Catálogo Público | 4 | Could |
| 6-1-free-trial | US-601 | Billing | 4 | Must |
| 6-2-suscripcion-base | US-602 | Billing | 4 | Should |
