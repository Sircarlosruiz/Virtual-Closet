# Criterio de Decisión — Validación de Headline
## Virtual Closet · NikaCommerce

**Hipótesis:** "Ver una prenda sobre un modelo real genera suficiente confianza para que el revendedor aumente el tamaño de su pedido."

**Muestra mínima:** 5 entrevistas con mayoristas activos  
**Fecha límite para decidir:** ____________

---

## Las 3 métricas que importan

### M1 — Tasa de confirmación (P9 del script)
¿Cuántos entrevistados dicen que la imagen sobre modelo generaría más pedidos?

| Resultado | Interpretación |
|---|---|
| 4–5 de 5 dicen que sí | Señal fuerte — headline válido |
| 3 de 5 dicen que sí | Señal débil — revisar condiciones (tipo de prenda, perfil de revendedor) |
| 0–2 de 5 dicen que sí | Hipótesis incorrecta — pivote necesario |

---

### M2 — Incremento estimado de piezas (P10 del script)
Promedio del % de aumento que los entrevistados estiman al ver imagen IA vs. maniquí.

| Resultado | Interpretación |
|---|---|
| ≥ 30% de incremento promedio | Headline fuerte — usar como claim principal |
| 15–29% de incremento promedio | Headline moderado — usar con evidencia, no como único argumento |
| < 15% de incremento promedio | Impacto insuficiente — buscar otro ángulo de valor |

**Cómo calcular:**
```
Entrevistado A: pide 6 con maniquí → estima 9 con modelo IA = +50%
Entrevistado B: pide 12 → estima 15 = +25%
Entrevistado C: pide 6 → estima 8 = +33%
Entrevistado D: pide 24 → estima 30 = +25%
Entrevistado E: pide 10 → estima 10 = 0%

Promedio = (50+25+33+25+0) / 5 = 26.6% → headline moderado
```

---

### M3 — Naturaleza de las objeciones (P11 del script)
Clasifica cada objeción en una de estas categorías:

| Tipo de objeción | Qué significa | Qué hacer |
|---|---|---|
| **"No se ve real / parece editada"** | Problema de calidad del output | Mejorar modelo o selección de imágenes de ejemplo |
| **"Mis revendedores no confían en fotos IA"** | Problema de adopción / educación | El headline sigue siendo válido; el reto es el go-to-market |
| **"El volumen lo define el precio, no la foto"** | El pain no es visual | Pivote: buscar otro ángulo de valor (velocidad, costo, catálogo compartible) |
| **"Ya uso fotos con modelo real"** | Segmento equivocado | Este mayorista no es tu ICP — descartarlo para la muestra |
| **"Mis revendedores piden igual sin importar la foto"** | Mercado no sensible a visual | Investigar si hay segmento donde sí importe |

---

## Matriz de decisión final

Cruza M1 y M2 para saber qué hacer:

```
                    M2: Incremento promedio
                    < 15%      15-29%      ≥ 30%
                 ┌──────────┬──────────┬──────────┐
M1: 4-5 de 5    │ Revisar   │ Lanzar   │ Lanzar   │
confirman       │ el ángulo │ con datos│ fuerte   │
                ├──────────┼──────────┼──────────┤
M1: 3 de 5      │ Pivote    │ Segmentar│ Segmentar│
confirman       │ necesario │ y probar │ y probar │
                ├──────────┼──────────┼──────────┤
M1: 0-2 de 5    │  Pivote   │  Pivote  │ Revisar  │
confirman       │ necesario │ necesario│ muestra  │
                └──────────┴──────────┴──────────┘
```

---

## Qué hacer según el resultado

### Caso A — Headline validado (lanzar fuerte)
*M1 ≥ 4/5 y M2 ≥ 30%*

Acciones:
- Reemplazar `[Nombre de revendedora beta]` en el PRFAQ con una cita real de las entrevistas
- Agregar el % de incremento real en P3 del FAQ ("resultado observado: +X% en pedidos")
- Usar la imagen de ejemplo como pieza central del landing page

---

### Caso B — Headline moderado (lanzar con matices)
*M1 ≥ 4/5 y M2 entre 15–29%*

Acciones:
- Ajustar el headline: en vez de "pedidos más grandes", usar "más confianza para arriesgar en prendas nuevas"
- Documentar en qué tipo de prenda o perfil de revendedor el impacto es mayor
- Buscar 2–3 casos con M2 ≥ 30% para usarlos como testimonios específicos

---

### Caso C — Segmentar antes de lanzar
*M1 = 3/5, cualquier M2*

Acciones:
- Identificar qué tienen en común los 3 que confirmaron (tipo de prenda, tamaño de red, canal de venta)
- Redefinir el ICP más estrechamente antes de invertir en adquisición
- Hacer 3 entrevistas adicionales solo con ese segmento

---

### Caso D — Pivote necesario
*M1 ≤ 2/5 o M2 < 15% con M1 < 4/5*

Acciones inmediatas:
1. No invertir en adquisición con el mensaje actual
2. Revisar las objeciones de M3 para encontrar el pain real
3. Pivotar el headline hacia el ángulo que sí generó resonancia:
   - Si el pain es **tiempo/costo** → "Catálogo listo en 5 minutos, sin fotógrafo"
   - Si el pain es **distribución** → "Tu catálogo en el teléfono de cada revendedor, hoy"
   - Si el pain es **profesionalismo** → "El catálogo que tus revendedores sí van a compartir"
4. Repetir validación con nuevo headline

---

## Plantilla de resumen ejecutivo post-entrevistas

```
Fecha: ____________
Entrevistados: ___ mayoristas
Ciudad(es): ____________

RESULTADOS:
- M1 (tasa de confirmación): ___ / 5
- M2 (incremento promedio estimado): ____%
- Objeción más frecuente: ____________

DECISIÓN: [ ] Lanzar fuerte  [ ] Lanzar con matices  [ ] Segmentar  [ ] Pivotar

AJUSTE AL HEADLINE:
Original: "Confianza visual → pedidos más grandes por colección"
Ajustado: ____________

SIGUIENTE PASO INMEDIATO:
____________
```
