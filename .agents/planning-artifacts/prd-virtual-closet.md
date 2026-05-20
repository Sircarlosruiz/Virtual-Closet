# Product Requirements Document — Virtual Closet MVP
## NikaCommerce · Versión 1.0

**Estado:** Borrador  
**Basado en:** PRFAQ v1.0 · Arquitectura Técnica v1.0 · UX Design Spec v1.0  
**Alcance:** MVP — prendas superiores, modelos predefinidos, catálogo compartible por link

---

## 1. Objetivos del MVP

### Problema a resolver
Los mayoristas de ropa en Nicaragua y Centroamérica no pueden publicar catálogos profesionales sin contratar fotografía ($800–$3,000 por colección, 2–4 semanas). Comparten fotos de maniquí por WhatsApp que no generan confianza en el revendedor para pedir volumen.

### Objetivo del MVP
Que un mayorista pueda subir una foto de prenda y compartir un catálogo profesional con imágenes sobre modelo real en menos de 5 minutos, sin conocimientos técnicos ni inversión en fotografía.

### Métricas de éxito del MVP

| Métrica | Meta |
| --- | --- |
| Tiempo primer catálogo generado | < 5 minutos desde el registro |
| Tasa de conversión free trial → pago | ≥ 30% |
| Mayoristas activos al mes 3 | ≥ 20 |
| Retención mes 2 | ≥ 70% |
| NPS post-primera generación | ≥ 50 |

---

## 2. Usuarios

### Usuario primario — Mayorista

- Propietario o administrador de un negocio de venta mayorista de ropa
- Opera principalmente por WhatsApp e Instagram
- Tech-savviness: bajo — usa el teléfono pero no herramientas de software
- Dispositivo principal: Android mobile, secundario desktop para gestión
- Dolor principal: fotografía de catálogo cara, lenta, o directamente ausente

### Usuario secundario — Revendedor

- Comprador B2B que recibe el link del catálogo por WhatsApp
- No tiene cuenta en Virtual Closet — accede solo al catálogo público
- Tech-savviness: muy bajo — debe funcionar sin fricción desde el link
- Dispositivo: mobile (Android mayoritariamente)
- Necesidad: ver cómo queda la prenda en una persona real antes de pedir

---

## 3. Out of Scope (MVP)

Los siguientes features están explícitamente fuera del MVP:

| Feature | Razón |
| --- | --- |
| Virtual try-on con foto propia del revendedor | Complejidad técnica + privacidad — roadmap v2 |
| Pantalones, vestidos, calzado | Madurez tecnológica inferior en VTON |
| App móvil nativa | PWA suficiente para el caso de uso |
| Integración WhatsApp Business API | Link compartido cubre el caso de uso |
| Analytics avanzados para el mayorista | No es el pain principal |
| Marketplace de mayoristas | Cambiaría el modelo de negocio |
| Multi-usuario por cuenta | Complejidad innecesaria para PyME |

---

## 4. Épicas e Historias de Usuario

---

### Épica 1 — Autenticación y Onboarding

**Objetivo:** El mayorista puede crear una cuenta, acceder al producto y completar su primer catálogo dentro del free trial de 30 días.

---

**US-101 · Registro de mayorista**

```
Como mayorista,
quiero registrarme con mi email y contraseña,
para acceder al dashboard y empezar a subir prendas.
```

Criterios de aceptación:
- [ ] El formulario solicita: email, contraseña (mínimo 8 caracteres), nombre del negocio
- [ ] Email debe ser único en el sistema — error claro si ya existe
- [ ] Al registrarse exitosamente, el plan queda en `base` con `trial_activo = true` por 30 días
- [ ] Se envía email de bienvenida con link de confirmación (no bloqueante para usar el producto)
- [ ] El mayorista es redirigido al dashboard después del registro

---

**US-102 · Login de mayorista**

```
Como mayorista registrado,
quiero iniciar sesión con mi email y contraseña,
para acceder a mi dashboard y mis catálogos.
```

Criterios de aceptación:
- [ ] JWT válido por 7 días almacenado en HttpOnly cookie
- [ ] Refresh automático antes de la expiración en cada request autenticado
- [ ] Error genérico si email o contraseña son incorrectos (sin revelar cuál falló)
- [ ] Botón "Olvidé mi contraseña" visible — flujo de reset por email

---

**US-103 · Onboarding guiado (primera vez)**

```
Como mayorista que acaba de registrarse,
quiero ver una pantalla de bienvenida que me guíe al primer paso,
para saber exactamente qué hacer sin necesidad de leer instrucciones.
```

Criterios de aceptación:
- [ ] Al primer login se muestra pantalla de onboarding con CTA único: "Subir tu primera prenda"
- [ ] La pantalla explica el free trial: "Tus primeras 5 prendas son gratis, sin tarjeta"
- [ ] No hay menú de navegación en esta pantalla — solo el CTA
- [ ] Si el mayorista recarga o vuelve más tarde, no se muestra el onboarding si ya subió al menos 1 prenda

---

### Épica 2 — Gestión de Prendas

**Objetivo:** El mayorista puede subir, nombrar y ver el estado de sus prendas en el dashboard.

---

**US-201 · Subir foto de prenda**

```
Como mayorista,
quiero subir una foto de mi prenda desde la galería o la cámara,
para iniciar el proceso de generación IA.
```

Criterios de aceptación:
- [ ] Formatos aceptados: JPG, PNG, HEIC — error claro para otros formatos
- [ ] Tamaño máximo: 20MB — error claro si se supera
- [ ] Al seleccionar la foto se muestra preview inmediato antes de confirmar
- [ ] La imagen se redimensiona a máximo 1024px antes de almacenar en MinIO
- [ ] La prenda queda en estado `pendiente` hasta que se seleccione modelo y se confirme generación
- [ ] Plan Base: máximo 40 prendas por mes — error claro al superar el límite

---

**US-202 · Nombrar prenda (opcional)**

```
Como mayorista,
quiero poder ponerle nombre a mi prenda,
para identificarla fácilmente en mi catálogo.
```

Criterios de aceptación:
- [ ] Campo de nombre opcional con sugerencia auto-generada: "Prenda #N"
- [ ] Máximo 80 caracteres
- [ ] Si el mayorista omite el campo, se usa la sugerencia auto-generada
- [ ] El nombre es editable después de la generación desde el dashboard

---

**US-203 · Ver listado de prendas en el dashboard**

```
Como mayorista,
quiero ver todas mis prendas con su estado actual,
para saber cuáles están listas, procesando o con error.
```

Criterios de aceptación:
- [ ] Grid de 2 columnas en mobile, 3 en desktop
- [ ] Cada card muestra: imagen (generada si lista, original si no), nombre, badge de estado
- [ ] Estados: `Pendiente` (gris) · `Procesando` (amber + barra animada) · `Lista` (emerald) · `Error` (rojo)
- [ ] Tap en una card lista → navega al resultado de generación
- [ ] Tap en una card con error → muestra opción de reintentar
- [ ] Dashboard vacío → empty state con CTA "Subir primera prenda"

---

**US-204 · Eliminar prenda**

```
Como mayorista,
quiero poder eliminar una prenda de mi dashboard,
para mantener mi catálogo organizado.
```

Criterios de aceptación:
- [ ] Opción de eliminar accesible desde el menú contextual de la card (long press o icono ···)
- [ ] Modal de confirmación: "¿Eliminar esta prenda? Esta acción no se puede deshacer"
- [ ] Al confirmar: se elimina la prenda y sus generaciones de la DB y de MinIO
- [ ] La prenda desaparece del dashboard inmediatamente
- [ ] Si la prenda estaba en un catálogo publicado, se elimina también de ese catálogo

---

### Épica 3 — Pipeline de Generación IA

**Objetivo:** El mayorista puede seleccionar un modelo IA y obtener una imagen profesional de su prenda en menos de 90 segundos.

---

**US-301 · Seleccionar modelo IA**

```
Como mayorista,
quiero elegir entre los modelos IA disponibles en mi plan,
para generar la imagen de mi prenda sobre el modelo que prefiero.
```

Criterios de aceptación:
- [ ] Se muestran los modelos disponibles según el plan del mayorista (6 en Base, 15 en Pro)
- [ ] Cada modelo se muestra en fila: thumbnail 56px + nombre + descripción breve
- [ ] Modelos de plan superior aparecen bloqueados con icono de lock — no interactivos
- [ ] Tap en modelo → highlight + checkmark → botón "Generar" aparece en bottom bar
- [ ] Solo un modelo seleccionado a la vez
- [ ] El último modelo usado queda pre-seleccionado en la próxima generación

---

**US-302 · Iniciar generación de imagen IA**

```
Como mayorista,
después de seleccionar el modelo,
quiero iniciar la generación presionando un botón,
para ver mi prenda sobre el modelo en menos de 90 segundos.
```

Criterios de aceptación:
- [ ] Tap en "Generar" publica un job en RabbitMQ y navega a la pantalla de progreso
- [ ] La pantalla de progreso muestra 3 estados secuenciales con ícono y texto descriptivo
- [ ] Si el mayorista sale de la pantalla, el job continúa en background
- [ ] Notificación WebSocket al completar: "¡Tu prenda [nombre] está lista!"
- [ ] Si el job tarda más de 90s: mensaje "Tomando más tiempo de lo usual, casi listo..."
- [ ] Máximo 3 reintentos automáticos ante error del worker — dead-letter queue al superar

---

**US-303 · Ver resultado de generación (momento WOW)**

```
Como mayorista,
quiero ver la imagen generada a pantalla completa,
para evaluar si el resultado es adecuado para mi catálogo.
```

Criterios de aceptación:
- [ ] La imagen generada se muestra a pantalla completa al completar el job
- [ ] Toggle "Ver original" permite comparar con la foto original (fade suave)
- [ ] Botón "Regenerar" permite volver al selector de modelo y repetir el proceso
- [ ] Botón "Agregar al catálogo" (CTA primary) agrega la prenda al catálogo activo
- [ ] Si la generación falló: pantalla de error con descripción + botón "Reintentar"
- [ ] La imagen generada queda almacenada en MinIO con thumbnail 400px

---

**US-304 · Regenerar con otro modelo**

```
Como mayorista,
quiero regenerar la imagen con un modelo diferente,
para encontrar la mejor combinación para mi prenda.
```

Criterios de aceptación:
- [ ] Tap en "Regenerar" vuelve al selector de modelo con la prenda pre-cargada
- [ ] Cada regeneración es un nuevo job — la generación anterior se conserva
- [ ] El mayorista puede tener múltiples generaciones de la misma prenda y elegir cuál usar
- [ ] Cada generación registra `costo_inferencia_usd` para tracking de margen

---

### Épica 4 — Gestión de Catálogos

**Objetivo:** El mayorista puede organizar sus prendas listas en un catálogo y publicarlo con un link único.

---

**US-401 · Crear catálogo**

```
Como mayorista,
quiero crear un catálogo y ponerle nombre,
para organizar mis prendas por colección.
```

Criterios de aceptación:
- [ ] CTA "Nuevo catálogo" visible en la tab de Catálogos del dashboard
- [ ] Campo de nombre obligatorio — máximo 80 caracteres
- [ ] El catálogo se crea en estado `despublicado` hasta que el mayorista lo publique
- [ ] Un mayorista puede tener múltiples catálogos

---

**US-402 · Agregar prendas a un catálogo**

```
Como mayorista,
quiero agregar prendas a mi catálogo,
para armar la colección que voy a compartir con mis revendedores.
```

Criterios de aceptación:
- [ ] Solo se pueden agregar prendas en estado `lista` (generación completada)
- [ ] Se puede agregar desde el resultado de generación ("Agregar al catálogo ✓") o desde el catálogo (selección múltiple)
- [ ] El orden de las prendas en el catálogo es editable (drag-and-drop en desktop, up/down en mobile)
- [ ] Una prenda puede estar en múltiples catálogos

---

**US-403 · Publicar catálogo**

```
Como mayorista,
quiero publicar mi catálogo con un link único,
para poder compartirlo con mis revendedores por WhatsApp.
```

Criterios de aceptación:
- [ ] Tap en "Publicar" genera un `slug` único basado en el nombre del catálogo (ej: `verano-2026`)
- [ ] Si el slug ya existe, se agrega un sufijo numérico (ej: `verano-2026-2`)
- [ ] Se genera un código QR del link automáticamente
- [ ] Al publicar se navega a la pantalla celebratoria (`CatalogShareSheet`)
- [ ] El catálogo publicado es inmediatamente accesible en `/c/{slug}`
- [ ] El mayorista puede despublicar el catálogo en cualquier momento

---

**US-404 · Compartir catálogo**

```
Como mayorista,
quiero compartir mi catálogo publicado por WhatsApp con un tap,
para que mis revendedores puedan verlo inmediatamente.
```

Criterios de aceptación:
- [ ] Botón "Compartir por WhatsApp" abre WhatsApp con texto pre-escrito: "Te comparto mi catálogo [nombre]: [link]"
- [ ] Botón "Copiar link" copia la URL al portapapeles con feedback toast
- [ ] QR descargable como imagen PNG
- [ ] Estos tres métodos disponibles desde la pantalla celebratoria y desde la vista del catálogo

---

### Épica 5 — Catálogo Público (Vista del Revendedor)

**Objetivo:** El revendedor puede ver el catálogo completo desde su teléfono sin necesidad de cuenta, login o app.

---

**US-501 · Ver catálogo público**

```
Como revendedor que recibí un link por WhatsApp,
quiero abrir el catálogo en mi browser sin instalar nada,
para ver las prendas disponibles y decidir qué pedir.
```

Criterios de aceptación:
- [ ] La página `/c/{slug}` es pública — no requiere autenticación
- [ ] Renderizado SSR (Next.js) — funciona con JS deshabilitado para dispositivos lentos
- [ ] Tiempo de carga en 3G: < 3 segundos para el primer contenido visible (LCP)
- [ ] El catálogo muestra: nombre de colección, nombre del mayorista, número de prendas
- [ ] Si el catálogo no existe o está despublicado → página 404 con mensaje claro

---

**US-502 · Ver detalle de prenda en catálogo**

```
Como revendedor,
quiero ver claramente cada prenda sobre el modelo con sus detalles,
para tomar una decisión de compra con confianza.
```

Criterios de aceptación:
- [ ] Cada prenda muestra: imagen generada (full ancho en mobile), nombre, descripción (si existe)
- [ ] Tap en imagen → vista expandida a pantalla completa
- [ ] Las imágenes se cargan con `loading="lazy"` excepto las primeras 2
- [ ] Las URLs de imagen son presignadas con TTL de 24h — se renuevan automáticamente al cargar el catálogo

---

**US-503 · Contactar al mayorista desde el catálogo**

```
Como revendedor,
quiero poder contactar al mayorista directamente desde el catálogo,
para hacer mi pedido sin salir de la experiencia.
```

Criterios de aceptación:
- [ ] Botón sticky en el bottom de la página: "Hacer pedido por WhatsApp"
- [ ] Al tap: WhatsApp abre con mensaje pre-formateado: "Hola, vi tu catálogo [nombre]. Quiero hacer un pedido."
- [ ] El número de WhatsApp del mayorista se configura en su perfil (campo opcional en onboarding)
- [ ] Si el mayorista no configuró WhatsApp, el botón no aparece en el catálogo

---

**US-504 · Registro de visualización de catálogo**

```
Como sistema,
quiero registrar cada vez que alguien abre el catálogo,
para que el mayorista pueda ver cuántas vistas tuvo su colección.
```

Criterios de aceptación:
- [ ] Cada apertura registra: `catalogo_id`, `ip_hash` (anonimizado), `user_agent`, `timestamp`
- [ ] No se registra información personal — solo datos agregados
- [ ] El contador de vistas es visible en el dashboard del mayorista (número simple, no por usuario)

---

### Épica 6 — Billing y Free Trial

**Objetivo:** El mayorista puede activar su suscripción después del free trial con tarjeta de crédito.

---

**US-601 · Free trial de 30 días**

```
Como mayorista recién registrado,
quiero usar el producto gratis durante 30 días,
para evaluar si vale la pena pagar antes de comprometerme.
```

Criterios de aceptación:
- [ ] Al registrarse, el plan queda en `base` con `trial_expira_en = now() + 30 días`
- [ ] Las primeras 5 prendas se procesan sin costo ni restricción
- [ ] El dashboard muestra una barra de progreso del trial: "X días restantes de tu prueba gratuita"
- [ ] Al llegar a 5 días antes del vencimiento: banner de aviso visible en el dashboard
- [ ] Al vencer el trial sin suscripción: las funciones de generación quedan bloqueadas — los catálogos publicados siguen accesibles (no se ocultan al revendedor)

---

**US-602 · Suscripción al plan Base**

```
Como mayorista que quiere continuar usando el producto,
quiero suscribirme al plan Base con mi tarjeta de crédito,
para seguir generando imágenes y publicando catálogos.
```

Criterios de aceptación:
- [ ] Integración con Stripe Checkout — no se almacenan datos de tarjeta en el sistema
- [ ] Al completar el pago: `plan = base`, `trial_activo = false`, `suscripcion_activa = true`
- [ ] El mayorista recibe email de confirmación de pago
- [ ] Factura disponible en el dashboard (Stripe Customer Portal)
- [ ] Cancelación disponible desde el dashboard — acceso hasta el fin del período pagado

---

## 5. Requisitos No Funcionales

| Requisito | Especificación |
| --- | --- |
| Tiempo de respuesta API | < 500ms para endpoints síncronos (p95) |
| Tiempo de generación IA | < 90s por imagen (p90) |
| Disponibilidad | 99% uptime — excluyendo mantenimiento programado |
| Carga inicial catálogo público | LCP < 3s en conexión 3G |
| Seguridad de imágenes | URLs presignadas MinIO con TTL 24h |
| Privacidad | No se almacenan fotos de revendedores en MVP |
| WCAG | Nivel AA en todas las pantallas |

---

## 6. Dependencias Técnicas

| Dependencia | Impacto | Mitigación |
| --- | --- | --- |
| Replicate API (IDM-VTON) | Si cae, no hay generaciones | Dead-letter queue + retry + estado visible al mayorista |
| MinIO en Kubernetes | Si falla, no hay imágenes | Backups diarios a Hetzner Object Storage |
| RabbitMQ | Si cae, los jobs se pierden | Mensajes durables (`durable=True`) — sobreviven restart |
| Stripe | Si cae, no hay nuevas suscripciones | Los usuarios activos no se ven afectados — solo nuevos pagos |

---

## 7. Priorización del Backlog (MoSCoW)

### Must Have (MVP bloqueante)
- US-101, US-102 — Auth
- US-201, US-203 — Upload y listado de prendas
- US-301, US-302, US-303 — Pipeline de generación completo
- US-401, US-402, US-403 — Crear y publicar catálogo
- US-501, US-502 — Catálogo público funcional
- US-601 — Free trial

### Should Have (MVP completo)
- US-103 — Onboarding guiado
- US-202 — Nombre de prenda
- US-304 — Regenerar con otro modelo
- US-404 — Compartir por WhatsApp
- US-503 — Contactar mayorista desde catálogo
- US-602 — Billing con Stripe

### Could Have (post-MVP)
- US-204 — Eliminar prenda
- US-504 — Analytics de vistas

### Won't Have (explícitamente fuera)
- Virtual try-on con foto propia del revendedor
- App móvil nativa
- Multi-usuario por cuenta

---

## 8. Épicas → Sprints (referencia a arquitectura técnica)

| Sprint | Épica | Historias |
| --- | --- | --- |
| Sprint 1 | Auth + Upload | US-101, US-102, US-103, US-201, US-202 |
| Sprint 2 | Pipeline IA | US-301, US-302, US-303, US-304, US-203 |
| Sprint 3 | Catálogo + Sharing | US-401, US-402, US-403, US-404, US-501, US-502, US-503 |
| Sprint 4 | Billing + Launch | US-601, US-602, US-504 |
