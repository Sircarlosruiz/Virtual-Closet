---
project: Virtual Closet
version: 1.0
stepsCompleted: [1, 2, 3]
lastStep: 3
inputDocuments:
  - .agents/planning-artifacts/prfaq-virtual-closet.md
  - .agents/planning-artifacts/arquitectura-tecnica.md
  - .agents/planning-artifacts/entrevista-validacion-headline.md
communicationLanguage: es
---

# UX Design Specification — Virtual Closet

## NikaCommerce

---

## Executive Summary

### Project Vision

Virtual Closet convierte fotos planas de prendas en catálogos profesionales con modelos IA, y los distribuye a revendedores vía link compartible — sin fotógrafo, sin app, en menos de 5 minutos.

### Target Users

| Usuario | Contexto | Dispositivo | Tech savvy |
| --- | --- | --- | --- |
| **Mayorista** | Sube prendas, genera catálogo, lo comparte por WhatsApp | Mobile principalmente, desktop para gestión | Bajo — opera por WhatsApp e Instagram |
| **Revendedor** | Recibe el link, navega el catálogo, decide qué pedir | Mobile (abre link desde WhatsApp) | Muy bajo — no instala nada |

### Key Design Challenges

1. **Onboarding sin fricción para el mayorista** — Opera en WhatsApp, no en dashboards. El primer catálogo tiene que ser generado con el mínimo de pasos posibles.
2. **Estado de espera del procesamiento IA** — La generación tarda 30–90s. La UX tiene que manejar esa espera sin ansiedad.
3. **Catálogo público mobile-first para el revendedor** — Tiene que abrir perfecto desde un link de WhatsApp en un teléfono Android básico, sin login, sin fricción.

### Design Opportunities

1. **El momento WOW** — Cuando el mayorista ve por primera vez su prenda sobre un modelo real. Ese momento tiene que estar diseñado conscientemente — es el principal driver de retención.
2. **Compartir con un tap** — El botón de compartir catálogo por WhatsApp tiene que ser el CTA más prominente del dashboard.
3. **Confianza visual del catálogo** — El revendedor abre el link sin contexto previo. El catálogo tiene que comunicar profesionalismo desde el primer scroll.

---

## Core User Experience

### Defining Experience

Hay dos loops de uso completamente distintos que deben diseñarse en paralelo:

#### Loop del Mayorista (productivo, recurrente)

```text
Subir fotos de prenda → Seleccionar modelo IA → Esperar generación
→ Revisar resultado → Publicar catálogo → Compartir link por WhatsApp
```

La acción más frecuente es **subir prendas y compartir el catálogo**. Todo lo demás es soporte a ese flujo. La UX debe hacer que ese ciclo completo sea posible en menos de 5 minutos desde cualquier teléfono.

#### Loop del Revendedor (pasivo, consultivo)

```text
Recibir link por WhatsApp → Abrir catálogo → Navegar prendas
→ Ver detalle con modelo → Decidir qué pedir → Contactar al mayorista
```

El revendedor nunca crea nada — solo consume. La fricción cero es el único objetivo de su experiencia.

### Platform Strategy

| Superficie | Plataforma | Prioridad | Justificación |
| --- | --- | --- | --- |
| Dashboard del mayorista | Web responsive, mobile-first | Alta | Opera desde teléfono, gestión ocasional desde desktop |
| Catálogo del revendedor | Web pública SSR, mobile-first | Crítica | Llega desde link de WhatsApp en Android básico |
| Upload de prendas | Web + PWA (camera access) | Alta | Permite captura directa desde cámara del teléfono |
| App nativa | No en MVP | — | Link web cubre el caso de uso sin fricción de instalación |

Consideraciones de plataforma:

- **Android básico (4G, pantalla 5–6")** es el dispositivo de referencia para el revendedor
- **Sin offline** — el catálogo requiere conexión; no hay acciones críticas offline
- **Camera API** para upload directo desde cámara en mobile

### Effortless Interactions

Estas acciones deben requerir cero pensamiento del usuario:

- **Subir foto:** tap en el área de upload → cámara o galería → foto seleccionada. Sin formularios previos.
- **Seleccionar modelo IA:** grid visual de modelos con preview. Un tap selecciona y dispara la generación.
- **Compartir catálogo:** botón fijo "Compartir por WhatsApp" siempre visible en el dashboard. Un tap abre WhatsApp con el link y texto pre-escrito.
- **Navegar catálogo (revendedor):** scroll vertical infinito, imágenes que cargan progresivamente. Sin paginación, sin filtros complejos en MVP.

Lo que debe pasar **automáticamente** sin acción del usuario:

- Generación de thumbnail al completar cada imagen IA
- Generación del código QR al publicar el catálogo
- Pre-escritura del mensaje de WhatsApp con el link del catálogo

### Critical Success Moments

**Momento 1 — El WOW del mayorista** *(make-or-break)*

Cuando el mayorista ve por primera vez su prenda procesada sobre un modelo real. Si este momento no genera una reacción positiva inmediata, no hay retención. El diseño debe:

- Mostrar la imagen generada con una transición suave (no un parpadeo)
- Poner la imagen IA al lado de la foto original para que el contraste sea inmediato
- El texto contextual debe ser mínimo — la imagen habla sola

**Momento 2 — Primer catálogo compartido** *(primer valor entregado)*
El mayorista comparte el link por primera vez. El flujo debe terminar con una confirmación satisfactoria: "Tu catálogo está listo. Compártelo con tus revendedores." Un botón directo a WhatsApp.

**Momento 3 — El revendedor abre el link** *(confianza inmediata)*
Los primeros 3 segundos del catálogo determinan si el revendedor se queda o cierra. La primera imagen tiene que cargarse rápido y verse profesional. Sin pantallas de carga largas, sin logins, sin popups.

**Momento crítico de fallo — Espera de procesamiento IA**
Si el mayorista sube una prenda y no recibe feedback durante 90 segundos, asume que algo falló. La UX debe mostrar progreso real y continuo desde el momento de upload.

### Experience Principles

1. **Lo visual primero, lo textual después** — El producto vende imágenes. Cada pantalla debe estar dominada por las fotos de las prendas, no por texto, formularios o navegación.

2. **Un paso a la vez** — El mayorista no es un usuario de software. Cada pantalla presenta una sola decisión. Sin flujos paralelos, sin opciones avanzadas visibles en MVP.

3. **El procesamiento nunca es silencioso** — Toda operación asíncrona (generación IA, publicación) tiene feedback visual activo. El usuario siempre sabe que algo está pasando.

4. **Compartir es el destino, no una opción** — El botón de compartir por WhatsApp es el elemento más prominente del dashboard. No está en un menú — está siempre visible.

5. **El catálogo se defiende solo** — La página pública del catálogo no tiene navegación, branding ni distracciones. Solo las prendas. El diseño limpio es la confianza.
