# Modelo de Precios — Virtual Closet
## NikaCommerce · Versión 1.0

**Objetivo:** Definir precio concreto del plan base para completar FAQ P3 del PRFAQ.  
**Modelo de negocio:** SaaS por asientos (revendedores activos/mes)  
**Decisión requerida:** [ ] Aprobado por fundador antes de publicar PRFAQ final

---

## 1. Estructura de costos (por mayorista/mes)

### Costos variables — Inferencia IA

| Parámetro | Estimado conservador | Estimado optimista |
|---|---|---|
| Costo por imagen generada | $0.08 USD | $0.02 USD |
| Imágenes por prenda (variantes de color/ángulo) | 2 | 1 |
| Prendas nuevas por colección | 30 | 20 |
| Colecciones por mes | 1.5 | 1 |
| **Costo de inferencia/mes** | **$7.20** | **$0.40** |

**Estimado de trabajo:** ~$2–5 USD/mes en inferencia por mayorista activo en condiciones normales de uso.

### Costos fijos prorrateados (estimados iniciales)

| Concepto | Costo mensual total | Por cliente (asumiendo 50 clientes) |
|---|---|---|
| Infraestructura cloud (storage, CDN, API) | $200 | $4.00 |
| Mantenimiento del modelo | $100 | $2.00 |
| Soporte (1 persona part-time) | $300 | $6.00 |
| **Total fijos prorrateados** | | **$12.00** |

### Costo total por cliente/mes (escenario base)

```
Inferencia:     $3.50  (punto medio)
Fijos:         $12.00
──────────────────────
Costo total:   $15.50 / cliente / mes
```

---

## 2. Benchmarks de referencia para fijar precio

### ¿Qué reemplaza Virtual Closet?

| Alternativa actual | Costo | Tiempo |
|---|---|---|
| Sesión fotográfica con modelo (20 prendas) | $800–$1,500 | 2–4 semanas |
| Sesión fotográfica con modelo (30 prendas) | $1,200–$2,500 | 2–4 semanas |
| Fotógrafo freelance + maniquí | $150–$400 | 3–7 días |
| Sin fotografía (maniquí o percha propio) | $0 | Inmediato |

### Willingness to pay del mercado B2B SaaS en Centroamérica

| Rango mensual | Perfil de comprador |
|---|---|
| $10–$25/mes | Herramientas de productividad individual |
| $30–$80/mes | Software de gestión para PyME |
| $80–$200/mes | Plataformas con ROI demostrable |
| $200+/mes | Requiere proceso de ventas consultivo |

**Zona de conversión sin fricción:** $29–$79/mes para un mayorista que hoy gasta $0 en fotografía digital pero ve el valor.

---

## 3. Propuesta de estructura de planes

### Plan Base — "Catálogo Digital"
**Precio recomendado: $39/mes**

| Incluye | Límite |
|---|---|
| Revendedores activos con acceso al catálogo | Hasta 50 |
| Prendas procesadas con IA por mes | 40 prendas |
| Modelos de IA disponibles | 6 modelos predefinidos |
| Links de catálogo compartibles | Ilimitados |
| Soporte | Email, 48h |

**Margen bruto estimado:**
```
Precio:         $39.00
Costo:         -$15.50
──────────────────────
Margen bruto:   $23.50  (60%)
```

---

### Plan Pro — "Showroom Completo"
**Precio recomendado: $79/mes**

| Incluye | Límite |
|---|---|
| Revendedores activos con acceso al catálogo | Hasta 150 |
| Prendas procesadas con IA por mes | 100 prendas |
| Modelos de IA disponibles | 15 modelos predefinidos |
| Links de catálogo compartibles | Ilimitados |
| Código QR por catálogo | ✓ |
| Estadísticas de visualización | ✓ |
| Soporte | Chat, 24h |

---

### Plan Enterprise — "Red de Revendedores"
**Precio recomendado: $149/mes**

| Incluye | Límite |
|---|---|
| Revendedores activos con acceso al catálogo | Ilimitados |
| Prendas procesadas con IA por mes | Ilimitadas |
| Modelos de IA disponibles | 15 + personalizados |
| Virtual try-on (foto propia del revendedor) | ✓ (cuando esté disponible) |
| Soporte | Dedicado |

---

## 4. Cálculo de ROI para FAQ P3 (con precio concreto)

*Reemplaza la tabla de estimados del PRFAQ con valores reales:*

| Concepto | Valor |
|---|---|
| Costo de una sesión fotográfica tradicional (20 prendas) | $800 – $1,500 USD |
| Tiempo para publicar la colección | 2–4 semanas |
| Costo de Virtual Closet (Plan Base) | **$39/mes** |
| Equivalente anual | $468/año |
| Punto de equilibrio vs. sesión fotográfica | **< 1 colección** |
| ROI si pedidos crecen 20% en primer mes | Positivo desde el día 1 |

**Frase para el FAQ:**
> "Con el Plan Base a $39/mes, el ahorro frente a una sola sesión fotográfica tradicional cubre más de 20 meses de suscripción. Si el tamaño promedio de pedido de tus revendedores aumenta un 20% — resultado observado en usuarios beta — el retorno sobre la inversión ocurre en el primer pedido de la primera colección."

---

## 5. Política de lanzamiento — Primeros 20 mayoristas

Según el PRFAQ: *"Los primeros 20 mayoristas que se registren recibirán los primeros 30 días sin costo."*

**Recomendación de implementación:**
- Trial de 30 días en Plan Base ($39/mes) sin tarjeta de crédito
- Al día 25: notificación con oferta de conversión
- Conversión esperada en early adopters: 40–60% (referencia SaaS B2B)
- MRR proyectado post-trial con 20 clientes y 50% conversión: **$390/mes**

---

## 6. Preguntas abiertas para decidir antes de publicar

- [ ] **¿Procesamiento ilimitado o por cuota?** Cuota protege el margen pero añade fricción. Recomendación: cuota generosa + overage visible.
- [ ] **¿Precio en USD o córdobas?** USD facilita referencia de precio internacional; córdobas reduce fricción psicológica local. Recomendación: USD con opción de pago en córdobas al tipo de cambio.
- [ ] **¿Descuento anual?** Estándar SaaS: 2 meses gratis (equivale a 16% de descuento). Mejora el LTV y el flujo de caja.
- [ ] **¿Precio de lanzamiento vs. precio permanente?** Considerar precio de lanzamiento ($29/mes por 6 meses) para los primeros 20, luego $39/mes.

---

## Decisión recomendada

**Arrancar con:**
- Plan Base: **$39/mes** — 50 revendedores, 40 prendas/mes
- Plan Pro: **$79/mes** — 150 revendedores, 100 prendas/mes
- Sin Plan Enterprise en lanzamiento (complejidad de soporte no justificada con < 50 clientes)
- Trial: **30 días, sin tarjeta** (ver política abajo)
- Moneda: **USD**

### Política de free trial (fuente de verdad)

| Aspecto | Regla |
| --- | --- |
| Duración | 30 días desde el registro (`trial_expira_en`) |
| Plan durante trial | Plan Base ($39/mes) sin cobro ni tarjeta |
| Límite de uso | Hasta **40 prendas/mes** (cuota del Plan Base); no hay cuota separada de "5 prendas gratis" |
| Al vencer sin suscripción | Bloqueo de nuevas generaciones; catálogos publicados siguen accesibles |
| Mensaje onboarding | "30 días gratis en Plan Base, sin tarjeta — hasta 40 prendas al mes" |

*Revisar precios a los 90 días con datos reales de uso y churn.*
