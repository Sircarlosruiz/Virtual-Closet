# UX Navigation Unification — Virtual Closet

**Versión:** 1.0  
**Autor:** UX Researcher (quality/ux_researcher)  
**Fecha:** 2026-06-05  
**Estado:** Listo para revisión  
**Basado en:** `ux-design-specification.md` · `prd-virtual-closet.md` · `PROJECT.md`

---

## 1. Resumen Ejecutivo

### Problema

El frontend de Virtual Closet creció con dos arquitecturas de rutas paralelas sin integrar. El grupo `/dashboard/*` tiene shell completa (sidebar, auth guard, topbar), mientras que el route group `(dashboard)/` carece de layout, sidebar y auth guard visible. Esto produce:

- **5 destinos huérfanos** sin sidebar ni auth: `/extraction/*`, `/media/extracted`, `/generate`, `/jobs/*`, `/batches/*`
- **5 enlaces rotos** en componentes que apuntan a rutas con prefijo `/dashboard/` que no existen
- **2 flujos de generación coexistiendo** sin integración: flujo legacy (`prendas/nueva → generacion/*`) y flujo VTON moderno (`extraction → media/extracted → generate → jobs|batches`)
- `/dashboard/settings` referenciado en el sidebar devuelve 404
- El mayorista no puede completar el journey de punta a punta sin topparse con un enlace roto o una pantalla sin navegación

### Solución Propuesta

**Unificar todo bajo `/dashboard/*` con el shell existente.** Migrar las rutas del route group `(dashboard)/` al prefijo `/dashboard/`, eliminar el route group huérfano, y deprecar/redirigir el flujo legacy hacia el flujo VTON moderno. Resultado: una sola arquitectura de rutas, un solo layout con sidebar y auth guard, y un journey mayorista sin interrupciones.

---

## 2. Sitemap Unificado

```
/ (marketing / landing)
│
├── /login                          ← EXISTE  [auth]
├── /registro                       ← EXISTE  [auth]
│
├── /dashboard                      ← EXISTE  [shell + auth] Home prendas / onboarding
│   ├── /onboarding                 ← EXISTE  (redirigir desde / si prendas=0)
│   │
│   ├── /prendas                    ← MOVER  de /dashboard (home) a ruta explícita
│   │   └── /nueva                  ← EXISTE  wizard subir prenda (DEPRECAR - ver §4)
│   │
│   ├── /extraction                 ← MOVER  de /(dashboard)/extraction/
│   │   ├── /new                    ← MOVER  [activo]
│   │   └── /status                 ← MOVER  [activo]
│   │
│   ├── /media
│   │   └── /extracted              ← MOVER  de /(dashboard)/media/extracted
│   │
│   ├── /generate                   ← MOVER  de /(dashboard)/generate
│   │
│   ├── /jobs                       ← MOVER  de /(dashboard)/jobs/
│   │   └── /[id]                   ← MOVER  [activo]
│   │
│   ├── /batches                    ← MOVER  de /(dashboard)/batches/
│   │   ├── /new                    ← MOVER  [activo]
│   │   └── /[batchId]              ← MOVER  [activo]
│   │
│   ├── /catalogos                  ← EXISTE  [activo]
│   │   ├── /[id]                   ← EXISTE  [activo]
│   │   └── /agregar                ← EXISTE  [activo]
│   │
│   ├── /customers                  ← EXISTE  [activo]
│   │
│   └── /settings                   ← CREAR  (actualmente 404)
│       ├── /perfil                 ← CREAR
│       ├── /plan                   ← CREAR
│       └── /notificaciones         ← CREAR
│
├── /portal                         ← EXISTE  [portal revendedor - separado]
│   ├── /request-link               ← EXISTE
│   ├── /auth                       ← EXISTE
│   ├── /                           ← EXISTE
│   └── /catalogs/[id]              ← EXISTE
│
└── /not-found                      ← EXISTE
```

**Leyenda:**
- `EXISTE` — ruta en producción, no requiere migración de archivo
- `MOVER` — archivo existe en `(dashboard)/`, requiere mover a `dashboard/`
- `CREAR` — ruta nueva que debe implementarse
- `DEPRECAR` — ruta que se reemplaza (mantener redirect 301)

---

## 3. Diagrama Mermaid — Journey Mayorista Unificado

```mermaid
flowchart TD
    START([Mayorista abre Virtual Closet]) --> AUTH{¿Sesión activa?}
    AUTH -->|No| LOGIN[/login]
    LOGIN --> REGISTER[/registro]
    REGISTER --> ONBOARD
    AUTH -->|Sí| DASH[/dashboard]

    DASH --> ONBOARD{¿Primera vez?}
    ONBOARD -->|Sí| WELCOME[/dashboard/onboarding\nCard bienvenida + CTA único]
    ONBOARD -->|No| HOME[/dashboard\nGrid de prendas]

    WELCOME --> EXT_NEW

    HOME --> CTA_NUEVA[Tap 'Nueva prenda']
    CTA_NUEVA --> EXT_NEW[/dashboard/extraction/new\nSubir foto de prenda]

    EXT_NEW --> EXT_STATUS[/dashboard/extraction/status\nExtrayendo prenda de la foto IA]
    EXT_STATUS -->|Error| EXT_NEW
    EXT_STATUS -->|Éxito| MEDIA[/dashboard/media/extracted\nGrid prendas extraídas — elegir]

    MEDIA --> GENERATE[/dashboard/generate\nSeleccionar modelo IA + disparar VTON]
    GENERATE -->|Job individual| JOB_DETAIL[/dashboard/jobs/id\nProgreso + resultado]
    GENERATE -->|Lote batch| BATCH_NEW[/dashboard/batches/new\nConfigurar lote]
    BATCH_NEW --> BATCH_DETAIL[/dashboard/batches/batchId\nProgreso lote]

    JOB_DETAIL -->|WOW: ver resultado| RESULT_OK{¿Conforme?}
    BATCH_DETAIL -->|WOW: ver resultados| RESULT_OK

    RESULT_OK -->|No — regenerar| GENERATE
    RESULT_OK -->|Sí| ADD_CAT[Agregar al catálogo]

    ADD_CAT --> CATALOGOS[/dashboard/catalogos\nLista de catálogos]
    CATALOGOS --> CAT_DETAIL[/dashboard/catalogos/id\nEditar / publicar catálogo]
    CAT_DETAIL --> SHARE[CatalogShareSheet\nBotón WhatsApp + QR]
    SHARE --> WA([WhatsApp — revendedor recibe link])

    HOME --> CATALOGOS
    HOME --> CUSTOMERS[/dashboard/customers]
    HOME --> SETTINGS[/dashboard/settings]
```

---

## 4. Decisión de Flujos — Unificación Legacy + VTON

### Opción A — Mantener ambos flujos en paralelo

Mantener `/dashboard/prendas/nueva` y `generacion/*` tal como están, y también mantener el flujo VTON. El usuario elegiría.

**Pros:** cero migración, no rompe nada existente.  
**Contras:** UX fragmentada, el usuario no sabe cuál usar, doble mantenimiento, el legacy usa un modelo de datos distinto, el onboarding es ambiguo.

### Opción B — Eliminar legacy y forzar flujo VTON

Borrar `/dashboard/prendas/nueva` y `generacion/*`. Todo pasa por `extraction/new → media/extracted → generate`.

**Pros:** una sola ruta, máxima consistencia, sin deuda técnica.  
**Contras:** si hay datos o prendas creadas con el flujo legacy, quedan huérfanas sin migración.

### Opción C — Deprecar legacy con redirect, promover flujo VTON ✅ RECOMENDADO

- El CTA "Nueva prenda" en sidebar y dashboard apunta a `/dashboard/extraction/new` (flujo VTON)
- `/dashboard/prendas/nueva` queda como redirect 301 → `/dashboard/extraction/new`
- `/dashboard/generacion/*` queda como redirect 301 → `/dashboard/generate` (o `/dashboard/jobs` según subpantalla)
- Las prendas existentes del flujo legacy se muestran en el mismo grid del dashboard (compatibilidad hacia atrás)

**Justificación de la recomendación:**  
El flujo VTON (extraction → media → generate → jobs/batches) es más coherente con el modelo mental del usuario: *"subo la foto → la IA extrae la prenda → elijo el modelo → veo el resultado"*. Es también el flujo que está siendo activamente desarrollado. La Opción C permite migrar sin romper referencias externas ni datos existentes.

**Flujo unificado resultante:**

```
/dashboard/extraction/new   →   Subir foto de prenda
/dashboard/extraction/status →  Extrayendo (polling / WebSocket)
/dashboard/media/extracted  →   Elegir prenda extraída para generar
/dashboard/generate         →   Selector de modelo IA + confirmar
/dashboard/jobs/[id]        →   Resultado individual (WOW)
/dashboard/batches/new      →   Configurar lote (múltiples prendas)
/dashboard/batches/[id]     →   Progreso y resultados del lote
```

---

## 5. Spec Navegación Desktop — Sidebar

### Estructura del Sidebar (DashboardShell)

```
┌─────────────────────────────┐
│  [Logo] Virtual Closet      │
│         {nombre_negocio}    │
├─────────────────────────────┤
│  PRINCIPAL                  │
│  🏠  Inicio           [/dashboard]         │
│  👕  Mis prendas      [/dashboard]         │
│  📚  Catálogos        [/dashboard/catalogos]│
│  👥  Clientes         [/dashboard/customers]│
├─────────────────────────────┤
│  GENERACIÓN IA              │
│  ✂️  Nueva extracción [/dashboard/extraction/new]  │
│  🖼️  Prendas extraídas[/dashboard/media/extracted] │
│  ⚡  Generar VTON     [/dashboard/generate]        │
│  📋  Historial jobs   [/dashboard/jobs]            │
│  📦  Lotes            [/dashboard/batches]         │
├─────────────────────────────┤
│  [Card Plan: Base/Trial]    │
├─────────────────────────────┤
│  ⚙️  Configuración    [/dashboard/settings]        │
│  🔒  {email}  [Salir]       │
└─────────────────────────────┘
```

### Items con iconos Lucide sugeridos

| Sección | Item | Icono Lucide | Ruta |
|---------|------|-------------|------|
| Principal | Inicio / Mis prendas | `Shirt` | `/dashboard` |
| Principal | Catálogos | `BookOpen` | `/dashboard/catalogos` |
| Principal | Clientes | `Users` | `/dashboard/customers` |
| Generación IA | Nueva extracción | `Scissors` | `/dashboard/extraction/new` |
| Generación IA | Prendas extraídas | `Images` | `/dashboard/media/extracted` |
| Generación IA | Generar VTON | `Sparkles` | `/dashboard/generate` |
| Generación IA | Historial jobs | `History` | `/dashboard/jobs` |
| Generación IA | Lotes | `Layers` | `/dashboard/batches` |
| Config | Configuración | `Settings` | `/dashboard/settings` |
| Acción rápida | Nueva prenda (CTA) | `Plus` | `/dashboard/extraction/new` |

### Reglas del Sidebar

- La sección "Generación IA" puede colapsarse en mobile (acordeón) — los ítems son avanzados y el usuario nuevo no los necesita desde el onboarding
- El CTA "Nueva prenda" siempre visible, nunca dentro del acordeón
- Estado activo: `bg-indigo-50 text-indigo-700 font-medium` (shadcn `isActive`)
- Collapsible en modo icono (desktop con sidebar contraída): todos los items muestran tooltip
- Card de plan siempre visible en desktop, oculta en modo icono

---

## 6. Spec Navegación Mobile — Bottom Nav + CTA flotante

### Bottom Navigation Bar (máx 5 items)

El sidebar de desktop se reemplaza por una barra inferior fija en mobile. Máximo 5 items para que cada touch target tenga ≥ 44px.

```
┌──────────────────────────────────────────────┐
│                                              │
│              [contenido]                     │
│                                              │
│                   [+]  ← FAB #EC4899         │
├────────┬────────┬────────┬────────┬──────────┤
│  🏠    │  📚    │  [+]   │  📦    │  ⚙️      │
│ Inicio │Catálogos│ Nueva │ Lotes  │ Config   │
└────────┴────────┴────────┴────────┴──────────┘
```

**5 items del bottom nav:**

| Posición | Label | Icono | Ruta |
|----------|-------|-------|------|
| 1 | Inicio | `Home` | `/dashboard` |
| 2 | Catálogos | `BookOpen` | `/dashboard/catalogos` |
| 3 | Nueva prenda (FAB) | `Plus` | `/dashboard/extraction/new` |
| 4 | Historial | `History` | `/dashboard/jobs` |
| 5 | Más | `Menu` | Sheet de opciones adicionales |

### FAB (Floating Action Button)

- Posición: centrado en bottom nav, elevado 8px, `bg-pink-500` (#EC4899)
- Icono: `Plus` blanco, 24px
- `aria-label="Nueva prenda"` 
- Al tapear: navega a `/dashboard/extraction/new`
- En pantallas de flujo multi-paso (extraction, generate, jobs/[id]) el FAB se oculta para no distraer

### Sheet "Más" (ítem 5 del bottom nav)

Abre un `Sheet` desde abajo con los items avanzados que no caben en la barra:

```
┌──────────────────────────────┐
│  ✂️  Nueva extracción         │
│  🖼️  Prendas extraídas        │
│  ⚡  Generar VTON             │
│  📦  Lotes                    │
│  👥  Clientes                 │
│  ⚙️  Configuración            │
│  ── ── ── ── ── ── ── ── ──  │
│  🔒  Salir                   │
└──────────────────────────────┘
```

### Breakpoint de cambio

- `< md (768px)` → bottom nav + FAB + Sheet
- `≥ md (768px)` → sidebar collapsible (DashboardShell actual)

---

## 7. Wireframes Textuales — 10 Pantallas Prioritarias

---

### W-01 — Dashboard Inicio (con prendas)
**Ruta:** `/dashboard`  
**Nav desktop:** Sidebar — "Inicio" activo  
**Nav mobile:** Bottom nav — item 1 activo  

```
┌─────────────────────────────────────────────┐
│ [sidebar]  Mis prendas              [+ Nueva]│
│            ─────────────────────────────────│
│            Filtros: [Todas] [Listas] [En proceso] [Error]
│            ─────────────────────────────────│
│            ┌──────┐ ┌──────┐ ┌──────┐      │
│            │ img  │ │ img  │ │ img  │      │
│            │      │ │ ●proc│ │ ✓list│      │
│            │Camisa│ │Blusa │ │Polo  │      │
│            └──────┘ └──────┘ └──────┘      │
│            ┌──────┐ ┌──────┐ ┌──────┐      │
│            │  ... │ │ ...  │ │  +   │      │
│            └──────┘ └──────┘ └──────┘      │
│                                             │
│  [banner sticky bottom] Compartir catálogo  │
│  [botón WhatsApp #EC4899 full-width mobile] │
└─────────────────────────────────────────────┘
```

**Estados vacío:** `OnboardingCard` — ilustración + "Subí tu primera prenda" + CTA  
**Estado cargando:** Grid de 6 `Skeleton` cards  
**Conexiones:** CTA "Nueva" → `/dashboard/extraction/new` | Card prenda → `/dashboard/jobs/[id]` si tiene job | Banner → `CatalogShareSheet`

---

### W-02 — Extracción Nueva
**Ruta:** `/dashboard/extraction/new`  
**Nav:** Header con ← "Cancelar" + "Paso 1 de 4" — sin bottom nav  

```
┌─────────────────────────────────────────────┐
│ ← Cancelar         Nueva prenda    Paso 1/4 │
│ ─────────────────────────────────────────── │
│                                             │
│      ┌─────────────────────────────┐        │
│      │                             │        │
│      │   📷  Subir foto de prenda  │        │
│      │                             │        │
│      │   Arrastrá o seleccioná     │        │
│      │   una imagen                │        │
│      │                             │        │
│      └─────────────────────────────┘        │
│                                             │
│   ┌──────────────┐  ┌──────────────┐        │
│   │  📷 Cámara   │  │  🖼️ Galería  │        │
│   └──────────────┘  └──────────────┘        │
│                                             │
│   Tips: fondo claro · prenda sin doblar     │
│                                             │
│   [Continuar →]  (deshabilitado hasta foto) │
└─────────────────────────────────────────────┘
```

**Estado vacío:** área de drop con instrucción visual  
**Estado con imagen:** preview de la foto + botón "Continuar" habilitado  
**Estado error:** toast rojo "Solo imágenes JPG/PNG · máx 10MB" + área limpia  
**Conexiones:** Continuar → `/dashboard/extraction/status` | ← → `/dashboard`

---

### W-03 — Extracción en proceso
**Ruta:** `/dashboard/extraction/status`  
**Nav:** Header con ← + indicador de paso — sin bottom nav  

```
┌─────────────────────────────────────────────┐
│ ← Atrás           Extrayendo prenda  2/4    │
│ ─────────────────────────────────────────── │
│                                             │
│          [preview foto subida]              │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  ✂️  Extrayendo prenda de la foto…   │   │
│  │  ████████████████░░░░░░░░░░  65%    │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  💡 Podés ir a otra pantalla — te          │
│     avisaremos cuando termine.             │
│                                             │
│  [Ir al dashboard]                          │
└─────────────────────────────────────────────┘
```

**Estado completado:** navega automáticamente a `/dashboard/media/extracted`  
**Estado error:** mensaje + botón "Reintentar" + botón "Subir otra foto"  
**Conexiones:** auto-navigate éxito → `/dashboard/media/extracted` | error retry → `/dashboard/extraction/new`

---

### W-04 — Prendas Extraídas
**Ruta:** `/dashboard/media/extracted`  
**Nav desktop:** Sidebar — "Prendas extraídas" activo  
**Nav mobile:** Sheet "Más" → "Prendas extraídas" activo  

```
┌─────────────────────────────────────────────┐
│ [sidebar]   Prendas extraídas               │
│             ── ── ── ── ── ── ── ── ── ──  │
│             Seleccioná prendas para generar │
│             ─────────────────────────────── │
│  ┌────────┐ ┌────────┐ ┌────────┐          │
│  │ ✓ sel │ │        │ │        │          │
│  │  img   │ │  img   │ │  img   │          │
│  │Camisa  │ │Blusa   │ │Vestido │          │
│  └────────┘ └────────┘ └────────┘          │
│                                             │
│  1 seleccionada                             │
│                                             │
│  [Generar con modelo →]  (primary #6366F1) │
└─────────────────────────────────────────────┘
```

**Estado vacío:** "No hay prendas extraídas aún" + CTA "Subir prenda"  
**Estado 0 seleccionadas:** botón deshabilitado  
**Conexiones:** "Generar" → `/dashboard/generate` con prendas seleccionadas como query params | "Subir prenda" → `/dashboard/extraction/new`

---

### W-05 — Generador VTON
**Ruta:** `/dashboard/generate`  
**Nav:** Header con ← + "Paso 3 de 4" — sin bottom nav  

```
┌─────────────────────────────────────────────┐
│ ← Atrás            Elegir modelo    3/4     │
│ ─────────────────────────────────────────── │
│                                             │
│  Prenda: [img pequeña] Camisa azul ✓       │
│                                             │
│  Elegí un modelo IA:                        │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │ [foto] Modelo 1 — Tez clara · Cabello    │
│  │        castaño · Talla S-M               │
│  └────────────────────────────────────┘    │
│  ┌────────────────────────────────────┐    │
│  │ ● [foto] Modelo 2 — Tez morena · Cabello │
│  │        negro · Talla M-L    ← SELECCIONADO│
│  └────────────────────────────────────┘    │
│  ┌────────────────────────────────────┐    │
│  │ [foto] Modelo 3 — [🔒 Plan Pro]         │
│  └────────────────────────────────────┘    │
│                                             │
│  Modo: ● Individual  ○ Lote (múltiples)    │
│                                             │
│  [Generar imagen →]  (primary)             │
└─────────────────────────────────────────────┘
```

**Estado cargando modelos:** 3 filas `Skeleton`  
**Estado sin selección:** botón deshabilitado  
**Conexiones:** "Generar individual" → `/dashboard/jobs/[id]` | "Generar lote" → `/dashboard/batches/new` | ← → `/dashboard/media/extracted`

---

### W-06 — Resultado Job Individual (WOW)
**Ruta:** `/dashboard/jobs/[id]`  
**Nav desktop:** Sidebar activo "Historial jobs"  
**Nav mobile:** bottom nav item "Historial"  

```
┌─────────────────────────────────────────────┐
│ ← Volver           Resultado                │
│ ─────────────────────────────────────────── │
│                                             │
│  [imagen generada a pantalla completa]      │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 👁️ Ver original  |  🖼️ Ver generada  │   │  ← toggle
│  └─────────────────────────────────────┘   │
│                                             │
│  Estado: ✅ Lista · Modelo 2 · hace 2 min   │
│                                             │
│  ┌──────────────┐   ┌──────────────┐       │
│  │ 🔄 Regenerar │   │ + Al catálogo│       │
│  └──────────────┘   └──────────────┘       │
│                                             │
│  [Compartir catálogo WhatsApp] #EC4899      │
└─────────────────────────────────────────────┘
```

**Estado procesando:** `ProgressPipeline` — "Extrayendo... → Aplicando modelo... → Finalizando..."  
**Estado error:** mensaje claro + botón "Reintentar" + botón "Cambiar modelo"  
**Estado > 90s:** "Tomando más tiempo de lo usual, casi listo..."  
**Conexiones:** "+ Al catálogo" → dialog selector de catálogo | "Regenerar" → `/dashboard/generate` | "Compartir" → `CatalogShareSheet`

---

### W-07 — Historial de Lotes
**Ruta:** `/dashboard/batches`  
**Nav desktop:** Sidebar — "Lotes" activo  
**Nav mobile:** bottom nav item "Historial" → tab "Lotes"  

```
┌─────────────────────────────────────────────┐
│ [sidebar]   Historial de Lotes  [+ Nuevo]   │
│             ─────────────────────────────── │
│  Jobs  |  Lotes ← tab activo               │
│  ─────────────────────────────────────────  │
│  ┌──────────────────────────────────────┐  │
│  │ Colección Verano 2026   ● Completado │  │
│  │ 15 jun 2026 · 12 prendas            │  │
│  │                          ✓10  ✗2    │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ Blusas Nuevas            ○ En proceso│  │
│  │ 14 jun 2026 · 8 prendas             │  │
│  │ ████████░░░░░░  6/8                 │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  Estado vacío: [Crear primer lote]         │
└─────────────────────────────────────────────┘
```

**Estado vacío:** ilustración + "No tenés lotes aún" + CTA "Crear primer lote"  
**Estado cargando:** 3 filas `Skeleton`  
**Conexiones:** row → `/dashboard/batches/[id]` | "+ Nuevo" → `/dashboard/batches/new`

---

### W-08 — Catálogos
**Ruta:** `/dashboard/catalogos`  
**Nav desktop:** Sidebar — "Catálogos" activo  
**Nav mobile:** bottom nav item "Catálogos" activo  

```
┌─────────────────────────────────────────────┐
│ [sidebar]   Mis Catálogos   [+ Nuevo]       │
│             ─────────────────────────────── │
│  ┌──────────────────────────────────────┐  │
│  │ [img] Colección Verano 2026          │  │
│  │       12 prendas · Publicado 15 jun  │  │
│  │       [Compartir ▼]  [Ver] [Editar]  │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ [img] Blusas Verano                  │  │
│  │       5 prendas · Borrador           │  │
│  │       [Publicar]  [Editar]           │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  Estado vacío: "Creá tu primer catálogo"   │
│  + CTA [+ Nuevo catálogo]                  │
└─────────────────────────────────────────────┘
```

**Estado vacío:** ilustración + "Aún no tenés catálogos" + botón primario  
**Conexiones:** "Compartir" → `CatalogShareSheet` | "Ver" → `/portal/catalogs/[id]` (nueva pestaña) | "Editar" → `/dashboard/catalogos/[id]`

---

### W-09 — Configuración
**Ruta:** `/dashboard/settings`  
**Nav desktop:** Sidebar — "Configuración" activo  
**Nav mobile:** Sheet "Más" → "Configuración"  

```
┌─────────────────────────────────────────────┐
│ [sidebar]   Configuración                   │
│             ─────────────────────────────── │
│  Perfil del negocio                         │
│  ┌──────────────────────────────────────┐  │
│  │ Nombre del negocio: [Mi Tienda]  ✏️  │  │
│  │ Email: maria@mi-tienda.com       ✏️  │  │
│  │ Teléfono: +505 8888-9999         ✏️  │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  Plan y facturación                         │
│  ┌──────────────────────────────────────┐  │
│  │ Plan Base · Trial activo             │  │
│  │ 22 días restantes                    │  │
│  │ Prendas: 11/40 este mes             │  │
│  │ [Ver planes y precios →]            │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  Notificaciones                             │
│  ┌──────────────────────────────────────┐  │
│  │ Email al completar generación  [ON]  │  │
│  │ Email al publicar catálogo     [ON]  │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  [Cerrar sesión]                            │
└─────────────────────────────────────────────┘
```

**Conexiones:** "Ver planes" → Stripe Customer Portal / `/dashboard/settings/plan`

---

### W-10 — Catálogo Público Revendedor
**Ruta:** `/portal/catalogs/[id]`  
**Nav:** Sin sidebar, sin bottom nav. Solo scroll + botón WhatsApp sticky.  

```
┌─────────────────────────────────────────────┐
│                                             │
│     [Logo negocio o nombre]                 │
│     Colección Verano 2026                   │
│     ─────────────────────────────────────  │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │                                     │   │
│  │      [imagen prenda sobre modelo]   │   │
│  │                                     │   │
│  │  Camisa Oxford Azul                 │   │
│  │  Tallas: S M L XL                  │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │                                     │   │
│  │      [imagen prenda sobre modelo]   │   │
│  │                                     │   │
│  │  Blusa Manga Larga                  │   │
│  │  Tallas: XS S M L                  │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [sticky] 📱 Pedir por WhatsApp  #EC4899   │
└─────────────────────────────────────────────┘
```

**Estado cargando:** `Skeleton` en 2 cards  
**Sin JS:** funciona con SSR (Next.js RSC)  
**Conexiones:** botón WhatsApp → `wa.me/{tel}?text=Hola, vi tu catálogo y quiero pedir: [link]`

---

## 8. Tabla de Migración de Rutas

| Ruta actual | Estado | Acción | Ruta definitiva | Prioridad |
|-------------|--------|--------|-----------------|-----------|
| `/extraction/new` | `(dashboard)` sin layout | MOVER archivo + redirect | `/dashboard/extraction/new` | P0 |
| `/extraction/status` | `(dashboard)` sin layout | MOVER archivo + redirect | `/dashboard/extraction/status` | P0 |
| `/media/extracted` | `(dashboard)` sin layout | MOVER archivo + redirect | `/dashboard/media/extracted` | P0 |
| `/generate` | `(dashboard)` sin layout | MOVER archivo + redirect | `/dashboard/generate` | P0 |
| `/jobs` | `(dashboard)` sin layout | MOVER archivo + redirect | `/dashboard/jobs` | P0 |
| `/jobs/[id]` | `(dashboard)` sin layout | MOVER archivo + redirect | `/dashboard/jobs/[id]` | P0 |
| `/batches` | `(dashboard)` sin layout | MOVER archivo + redirect | `/dashboard/batches` | P0 |
| `/batches/new` | `(dashboard)` sin layout | MOVER archivo + redirect | `/dashboard/batches/new` | P0 |
| `/batches/[batchId]` | `(dashboard)` sin layout | MOVER archivo + redirect | `/dashboard/batches/[batchId]` | P0 |
| `/dashboard/settings` | 404 — no existe | CREAR | `/dashboard/settings` | P0 |
| `/dashboard/prendas/nueva` | EXISTE legacy | REDIRECT 301 | `/dashboard/extraction/new` | P1 |
| `/dashboard/generacion/model-selector` | EXISTE legacy | REDIRECT 301 | `/dashboard/generate` | P1 |
| `/dashboard/generacion/progress` | EXISTE legacy | REDIRECT 301 | `/dashboard/jobs` | P1 |
| `/dashboard/generacion/result` | EXISTE legacy | REDIRECT 301 | `/dashboard/jobs/[id]` | P1 |
| `/dashboard/batches/[id]` (ruta rota en `batches/page.tsx`) | enlace roto en código | CORREGIR link | `/dashboard/batches/[batchId]` | P0 |
| AppSidebar: `/dashboard/prendas/nueva` CTA | apunta a legacy | ACTUALIZAR href | `/dashboard/extraction/new` | P0 |
| AppSidebar: sección VTON | ausente | AGREGAR items nav | ver §5 | P1 |

### Redirects a implementar en `next.config.js`

```js
// next.config.js — redirects
async redirects() {
  return [
    // Flujo legacy → flujo VTON
    { source: '/dashboard/prendas/nueva', destination: '/dashboard/extraction/new', permanent: true },
    { source: '/dashboard/generacion/model-selector', destination: '/dashboard/generate', permanent: true },
    { source: '/dashboard/generacion/progress', destination: '/dashboard/jobs', permanent: true },
    { source: '/dashboard/generacion/result', destination: '/dashboard/jobs', permanent: true },

    // Route group (dashboard) sin prefijo → /dashboard prefijado
    { source: '/extraction/new', destination: '/dashboard/extraction/new', permanent: true },
    { source: '/extraction/status', destination: '/dashboard/extraction/status', permanent: true },
    { source: '/media/extracted', destination: '/dashboard/media/extracted', permanent: true },
    { source: '/generate', destination: '/dashboard/generate', permanent: true },
    { source: '/jobs', destination: '/dashboard/jobs', permanent: true },
    { source: '/jobs/:id', destination: '/dashboard/jobs/:id', permanent: true },
    { source: '/batches', destination: '/dashboard/batches', permanent: true },
    { source: '/batches/new', destination: '/dashboard/batches/new', permanent: true },
    { source: '/batches/:batchId', destination: '/dashboard/batches/:batchId', permanent: true },
  ]
}
```

---

## 9. Tickets para Frontend Engineer

### P0 — Bloqueantes (impide flujos completos)

---

**FE-NAV-001** `P0` — Mover route group `(dashboard)` bajo `/dashboard/`

> **Problema:** 9 rutas bajo `app/(dashboard)/` no tienen layout ni auth guard.  
> **Acción:** Mover los siguientes archivos de `app/(dashboard)/` a `app/dashboard/`:
> - `extraction/new/page.tsx`
> - `extraction/status/page.tsx`
> - `media/extracted/page.tsx`
> - `generate/page.tsx`
> - `jobs/page.tsx`
> - `jobs/[id]/page.tsx`
> - `batches/page.tsx`
> - `batches/new/page.tsx`
> - `batches/[batchId]/page.tsx`
>
> El `app/dashboard/layout.tsx` existente ya provee auth guard y DashboardShell.  
> Eliminar la carpeta `app/(dashboard)/` una vez completado el movimiento.  
> **Criterio de aceptación:** todas las rutas `/dashboard/extraction/*`, `/dashboard/media/*`, `/dashboard/generate`, `/dashboard/jobs/*`, `/dashboard/batches/*` muestran sidebar y requieren auth.

---

**FE-NAV-002** `P0` — Agregar redirects en `next.config.js`

> **Problema:** Los enlaces rotos en código y bookmarks existentes apuntan a rutas sin prefijo `/dashboard/`.  
> **Acción:** Implementar los 14 redirects de la §8 en `next.config.js`.  
> **Criterio de aceptación:** Todas las URLs antiguas redirigen con HTTP 301 a las nuevas sin error.

---

**FE-NAV-003** `P0` — Corregir links rotos en `batches/page.tsx`

> **Problema:** `BatchHistoryPage` y `BatchRow` tienen `router.push('/dashboard/batches/new')` y `router.push('/dashboard/batches/${batch.id}')` que eran incorrectos cuando la ruta estaba en `(dashboard)/batches/`.  
> **Acción:** Verificar que todos los `router.push` y `Link href` dentro de las páginas movidas apunten a las rutas con prefijo `/dashboard/`.  
> **Criterio de aceptación:** Navegar a `/dashboard/batches` y hacer click en un batch navega a `/dashboard/batches/[batchId]` sin 404.

---

**FE-NAV-004** `P0` — Crear página `/dashboard/settings` (mínimo viable)

> **Problema:** El sidebar muestra "Configuración" pero la ruta devuelve 404.  
> **Acción:** Crear `app/dashboard/settings/page.tsx` con 3 secciones: Perfil del negocio (solo lectura), Plan y facturación, Notificaciones toggle.  
> **Criterio de aceptación:** La ruta `/dashboard/settings` muestra contenido y no devuelve 404. El sidebar marca "Configuración" como activo.

---

**FE-NAV-005** `P0` — Actualizar CTA "Nueva prenda" en AppSidebar

> **Problema:** `AppSidebar` tiene el CTA "Nueva prenda" apuntando a `/dashboard/prendas/nueva` (flujo legacy).  
> **Acción:** Cambiar el `href` del CTA en `NAV_ITEMS` de `/dashboard/prendas/nueva` a `/dashboard/extraction/new`.  
> **Criterio de aceptación:** Click en "Nueva prenda" en el sidebar navega a `/dashboard/extraction/new`.

---

### P1 — Importantes (mejora de navegabilidad)

---

**FE-NAV-006** `P1` — Agregar sección "Generación IA" al AppSidebar

> **Problema:** Los items de extracción, generación, jobs y batches no aparecen en el sidebar.  
> **Acción:** Agregar en `AppSidebar.tsx` una nueva sección colapsable "Generación IA" con los 5 items de la §5 (iconos Lucide: `Scissors`, `Images`, `Sparkles`, `History`, `Layers`).  
> **Criterio de aceptación:** Los 5 items nuevos aparecen en el sidebar y marcan el estado activo correctamente según la ruta actual.

---

**FE-NAV-007** `P1` — Implementar Bottom Nav mobile

> **Problema:** En mobile, el usuario no tiene acceso rápido a las secciones principales.  
> **Acción:** Crear componente `BottomNav.tsx` con 5 items según §6. Renderizarlo dentro de `DashboardShell` condicionalmente en `< md`. Ocultar en rutas de flujo multi-paso (extraction, generate, jobs/[id]).  
> **Criterio de aceptación:** En viewport < 768px aparece bottom nav. No aparece durante flujos multi-paso.

---

**FE-NAV-008** `P1` — FAB "Nueva prenda" mobile

> **Problema:** No hay acceso rápido a crear prenda en mobile.  
> **Acción:** Agregar FAB centrado en BottomNav con `bg-pink-500`, icono `Plus`, navegando a `/dashboard/extraction/new`. El FAB se oculta en páginas de flujo (`/dashboard/extraction/*`, `/dashboard/generate`, `/dashboard/jobs/[id]`).  
> **Criterio de aceptación:** FAB visible en `/dashboard`, `/dashboard/catalogos` y `/dashboard/batches`. Ausente en páginas de flujo.

---

**FE-NAV-009** `P1` — Tabs unificados: Jobs + Batches

> **Problema:** Jobs y Batches son páginas separadas sin navegación entre ellas, el usuario no sabe que existen ambas.  
> **Acción:** Agregar `Tabs` de shadcn/ui en `/dashboard/jobs` con tabs "Generaciones individuales" y "Lotes", o unificar en `/dashboard/historial` con tabs.  
> **Criterio de aceptación:** Desde `/dashboard/jobs` el usuario puede cambiar a ver lotes sin volver al sidebar.

---

**FE-NAV-010** `P1` — Indicador de paso en flujos multi-pantalla

> **Problema:** Las pantallas del flujo (extraction/new → status → media/extracted → generate → jobs/[id]) no muestran progreso ni permiten volver al paso anterior.  
> **Acción:** Implementar header de flujo con ← "Cancelar/Atrás" + "Paso N de 4". Ocultar sidebar y bottom nav durante el flujo.  
> **Criterio de aceptación:** En `/dashboard/extraction/new` se muestra "Paso 1 de 4" con botón cancelar. El botón atrás navega al paso anterior sin perder datos.

---

### P2 — Deseables (pulido y UX+)

---

**FE-NAV-011** `P2` — Breadcrumbs en desktop para rutas profundas

> **Acción:** Agregar breadcrumb `Catálogos / Colección Verano 2026` en `/dashboard/catalogos/[id]` y `Lotes / Colección Verano` en `/dashboard/batches/[batchId]`.

---

**FE-NAV-012** `P2` — Toast de notificación WebSocket con link a job

> **Acción:** Cuando el WebSocket notifica "job completado", el `Toast` debe incluir un botón "Ver resultado" que navega a `/dashboard/jobs/[id]`.

---

**FE-NAV-013** `P2` — Deprecar y ocultar rutas legacy del filesystem

> **Acción:** Después de confirmar que los redirects funcionan y no hay tráfico real en las rutas legacy, eliminar los archivos:
> - `app/dashboard/prendas/nueva/page.tsx`
> - `app/dashboard/generacion/` (directorio completo)

---

**FE-NAV-014** `P2` — Estado activo correcto en AppSidebar para rutas VTON

> **Acción:** Actualizar `isDashboardNavActive` en `dashboard-nav.ts` para que los 5 nuevos items de la sección "Generación IA" calculen correctamente el estado activo (ej: cualquier ruta bajo `/dashboard/batches/*` marca "Lotes" como activo).

---

## 10. Decisiones Abiertas para Product Owner

| # | Decisión | Opciones | Impacto | Urgencia |
|---|----------|----------|---------|---------|
| D-01 | ¿"Mis prendas" en el sidebar es el mismo que el home `/dashboard`? | A) Sí, `/dashboard` es la biblioteca de prendas · B) Crear `/dashboard/prendas` separado del home | Afecta sidebar NAV_ITEMS y estructura de rutas | Alta — bloquea FE-NAV-006 |
| D-02 | ¿Jobs y Batches van en una sola pantalla `/dashboard/historial` con tabs, o quedan separados? | A) Unificar en `/historial` con tabs · B) Mantener separados con navegación entre ellos | Afecta bottom nav y sidebar | Alta — bloquea FE-NAV-009 |
| D-03 | ¿El flujo legacy (`prendas/nueva → generacion/*`) tiene usuarios activos con datos? | A) Sí — mantener redirect + mostrar sus prendas en el grid · B) No — borrar directamente | Afecta si se necesita migración de datos o solo redirects | Alta — bloquea FE-NAV-001 |
| D-04 | ¿Clientes (`/dashboard/customers`) es parte del MVP o está en roadmap? | A) Parte del MVP — mantener en sidebar principal · B) Roadmap — ocultar del sidebar en esta etapa | Afecta items del sidebar y bottom nav | Media |
| D-05 | ¿La sección "Generación IA" del sidebar empieza colapsada o expandida? | A) Expandida siempre · B) Colapsada por defecto en primera visita, luego persiste preferencia | Afecta onboarding y descubribilidad del flujo VTON | Media |
| D-06 | ¿`/dashboard/settings` necesita integración con Stripe Customer Portal en el MVP? | A) Sí — botón "Ver planes" abre Stripe Portal · B) No — mostrar info del plan, billing pendiente para v2 | Afecta scope y tiempo de FE-NAV-004 | Media |
| D-07 | ¿El portal revendedor `/portal/*` requiere autenticación en algún punto del MVP? | A) No — el link es el único acceso, sin login · B) Sí — magic link opcional para revendedores frecuentes | Afecta arquitectura de auth y rutas del portal | Baja (v2) |

---

*Documento generado por UX Researcher · Virtual Closet · NikaCommerce*  
*Siguiente paso sugerido: revisar decisiones abiertas D-01, D-02, D-03 con el Product Owner antes de asignar tickets P0 al Frontend Engineer.*
