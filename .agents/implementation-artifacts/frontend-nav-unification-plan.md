# Plan Técnico — Unificación de Navegación UI/UX

**Fecha:** 2026-06-05  
**Autor:** Frontend Engineer  
**Estado:** P0 implementado, P1/P2 pendientes

---

## 1. Análisis del Estado Actual

### 1.1 Estructura de rutas

```
frontend/app/
├── (auth)/                        # Grupo de rutas públicas (login, registro)
│   ├── layout.tsx
│   ├── login/page.tsx
│   └── registro/page.tsx
├── (dashboard)/                   # ← PROBLEMA: SIN layout.tsx propio hasta este PR
│   ├── batches/
│   │   ├── [batchId]/page.tsx
│   │   ├── new/page.tsx
│   │   └── page.tsx
│   ├── extraction/
│   │   ├── new/page.tsx
│   │   └── status/page.tsx
│   ├── generate/page.tsx
│   ├── jobs/
│   │   ├── [id]/page.tsx
│   │   └── page.tsx
│   └── media/
│       └── extracted/page.tsx
├── dashboard/                     # Layout principal con auth + DashboardShell
│   ├── layout.tsx                 # Auth guard + DashboardShell
│   ├── page.tsx                   # "/dashboard" → Mis prendas
│   ├── catalogos/...
│   ├── customers/...
│   ├── generacion/...             # Flujo antiguo de generación
│   ├── onboarding/page.tsx
│   └── prendas/nueva/page.tsx
└── portal/                        # Área pública de catálogos B2B
```

### 1.2 Componentes de navegación

| Componente | Rol |
|---|---|
| `AppSidebar.tsx` | Sidebar con items de nav, plan card, logout |
| `dashboard-nav.ts` | Lógica de `isActive` y `getPageTitle` |
| `DashboardShell.tsx` | Wrapper: `SidebarProvider + AppSidebar + DashboardTopBar + children` |
| `DashboardTopBar.tsx` | Header sticky con título de página (consume `getDashboardPageTitle`) |
| `dashboard/layout.tsx` | Auth guard SSR + DashboardShell. Protegía SOLO rutas bajo `/dashboard/*` |

### 1.3 Problema raíz

Las páginas en `app/(dashboard)/` **no tenían layout.tsx propio**. En Next.js App Router, los grupos de rutas `(nombre)` son transparentes para la URL pero **sí necesitan su propio `layout.tsx`** para heredar estructura visual. Al no tenerlo:

- Las rutas `/generate`, `/jobs/*`, `/batches/*`, `/extraction/*`, `/media/extracted` renderizaban sin sidebar ni auth guard.
- Los enlaces usaban el prefijo `/dashboard/` incorrecto (e.g., `/dashboard/jobs/123` en lugar de `/jobs/123`), causando 404 o redireccionando al layout del grupo `dashboard/` incorrecto.

---

## 2. Estrategia Adoptada: Layout en `(dashboard)/layout.tsx`

### Opción A — Crear `(dashboard)/layout.tsx` (estrategia elegida ✅)
Replica exactamente el auth guard y `DashboardShell` de `dashboard/layout.tsx`. Las URLs permanecen cortas (sin prefijo `/dashboard/`).

**Ventajas:**
- URLs limpias (`/generate`, `/batches`, `/jobs`) — mejor para SEO y UX
- Mínimo cambio de archivos: solo se crea un layout y se corrigen los enlaces
- No rompe rutas existentes bajo `/dashboard/`
- El grupo `(dashboard)` ya estaba declarado — arquitectura intencional del dev original

**Desventajas:**
- Duplicación lógica del auth guard (mitigada: ambos archivos son idénticos; extracción a helper es P1)

### Opción B — Mover rutas bajo `/dashboard/`
Mover todos los archivos de `(dashboard)/` a `dashboard/`, haciendo las URLs `/dashboard/generate`, `/dashboard/batches`, etc.

**Descartada porque:**
- Requiere mover ~12 archivos + cambiar todas las URLs
- Las rutas `/dashboard/jobs` ya tienen links que apuntan sin el prefijo, creando el círculo del error
- Mayor riesgo de regresiones

---

## 3. Archivos Modificados / Creados

### Creados
| Archivo | Descripción |
|---|---|
| `frontend/app/(dashboard)/layout.tsx` | Auth guard + DashboardShell para todas las rutas del grupo |

### Modificados — Corrección de enlaces
| Archivo | Cambio |
|---|---|
| `app/(dashboard)/generate/page.tsx` | `/dashboard/jobs/${jobId}` → `/jobs/${jobId}` |
| `app/(dashboard)/batches/page.tsx` | `/dashboard/batches/new` → `/batches/new`; `/dashboard/batches/${id}` → `/batches/${id}` |
| `app/(dashboard)/batches/[batchId]/page.tsx` | `/dashboard/batches` → `/batches` |
| `app/(dashboard)/batches/new/page.tsx` | `/dashboard/batches/${id}` → `/batches/${id}` |
| `app/(dashboard)/jobs/[id]/page.tsx` | `/dashboard/jobs` → `/jobs` |
| `components/dashboard/DashboardContent.tsx` | `/dashboard/media/extracted` → `/media/extracted` |
| `components/tryoff/extracted-garments-grid.tsx` | `/dashboard/extraction/new` → `/extraction/new` |
| `components/tryoff/job-card.tsx` | `/dashboard/generate?garment_id=` → `/generate?garment_id=` |
| `components/tryoff/garment-preview-modal.tsx` | `/dashboard/generate?garment_id=` → `/generate?garment_id=` |
| `components/tryoff/extracted-garment-card.tsx` | `/dashboard/generate?garment_id=` → `/generate?garment_id=` |
| `components/vton/ResultDisplay.tsx` | `/dashboard/generate` → `/generate` (×2) |
| `components/vton/JobHistoryList.tsx` | `/dashboard/jobs/${id}` → `/jobs/${id}`; `/dashboard/generate` → `/generate` |

### Modificados — Navegación
| Archivo | Cambio |
|---|---|
| `components/dashboard/dashboard-nav.ts` | Añadidos títulos para: `/extraction/new`, `/extraction/status`, `/media/extracted`, `/generate`, `/jobs`, `/jobs/[id]`, `/batches`, `/batches/new`, `/batches/[id]` |
| `components/dashboard/AppSidebar.tsx` | Eliminado item Settings (ruta inexistente); añadido grupo VTON con Extracción (`/extraction/new`), Generaciones (`/generate`), Lotes (`/batches`) |

---

## 4. Fases de Implementación

### P0 — Crítico (implementado ✅)
- [x] Crear `app/(dashboard)/layout.tsx` con auth guard + DashboardShell
- [x] Corregir todos los 14 enlaces rotos listados arriba
- [x] Actualizar `getDashboardPageTitle` con rutas nuevas
- [x] Añadir ítems de nav al sidebar (Extracción, Generaciones, Lotes)
- [x] Eliminar ítem Settings (ruta inexistente `/dashboard/settings`)

### P1 — Importante (pendiente)
- [ ] **Extraer `getMe()` a helper compartido** (`lib/auth/get-me.ts`) para eliminar la duplicación entre `app/dashboard/layout.tsx` y `app/(dashboard)/layout.tsx`
- [ ] **Añadir `SidebarGroupLabel`** al grupo VTON para separarlo visualmente del grupo principal
- [ ] **Corregir topbar CTA**: el botón "Nueva prenda" solo aparece en `pathname === "/dashboard"` — extender a rutas de grupo `(dashboard)` si aplica
- [ ] **Página de Configuración** (`/dashboard/settings`): crear stub o decidir si va en `(dashboard)/settings`

### P2 — Mejoras (pendiente)
- [ ] Breadcrumbs dinámicos en `DashboardTopBar`
- [ ] Indicador de "Lotes en progreso" en sidebar (badge con conteo)
- [ ] Unificar los flujos de generación: `app/dashboard/generacion/` (flujo antiguo) y `app/(dashboard)/generate/` (flujo nuevo) — evaluar deprecar el antiguo
- [ ] Internacionalizar labels en `JobCard` y `GarmentPreviewModal` (actualmente en inglés)

---

## 5. Riesgos y Testing Manual

### Riesgos identificados
| Riesgo | Mitigación |
|---|---|
| Doble layout si Next.js aplica ambos `dashboard/layout.tsx` y `(dashboard)/layout.tsx` | **No aplica**: los grupos `(dashboard)/` y `dashboard/` son segmentos de ruta distintos. Next.js solo aplica el layout del segmento activo. |
| Auth duplicado genera dos peticiones a `/api/auth/me` | Aceptable hasta P1. Con `cookies()` y `cache: "no-store"` cada layout hace su propia validación al ser RSC. |
| `isDashboardNavActive` no marca activo los items de VTON | Corregido: la función ya compara por `pathname.startsWith(href + "/")`, funciona para rutas exactas y anidadas. |

### Testing manual sugerido

1. **Sin sesión**: navegar a `/generate` → debe redirigir a `/login`
2. **Con sesión**: navegar a `/generate` → debe mostrar sidebar + topbar
3. **Links internos**:
   - Desde `/generate`, enviar generación → debe redirigir a `/jobs/{id}` con sidebar
   - Desde `/batches`, click en lote → debe ir a `/batches/{id}`
   - Desde `/batches/{id}`, botón Volver → debe ir a `/batches`
4. **Sidebar**:
   - Items "Extracción", "Generaciones", "Lotes" deben aparecer y marcar activo según ruta
   - Item "Configuración" **NO debe aparecer**
5. **Títulos**: el topbar debe mostrar títulos correctos en cada ruta del grupo `(dashboard)/`
6. **Rutas `/dashboard/*`**: verificar que siguen funcionando normalmente (Mis prendas, Catálogos, Clientes)
