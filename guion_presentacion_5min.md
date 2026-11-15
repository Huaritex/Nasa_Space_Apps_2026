# RotaClima — Guion de Presentación (5 Minutos) y Defensa por Diapositiva

> **Objetivo:** Presentar **RotaClima** (*Field Shift* — NASA Space Apps 2026) en **5:00 minutos (9 diapositivas)** combinando impacto humano, rigor científico determinista, honestidad estadística y sostenibilidad Open Science + B2B.
> **Regla de oro al hablar:** En voz alta usá números limpios/redondeados (*"más de 2 meses"*, *"casi 81 días"*, *"+15% de productividad"*); dejá los decimales exactos visibles en pantalla para el ojo técnico del jurado.

---

## Mapa de Tiempos (5:00 min totales)

| Slide | Tema | Tiempo | Duración |
|---|---|---|---|
| **1** | Portada & El Problema (*Field Shift* en Santa Cruz) | `0:00 – 0:25` | 25 s |
| **2** | Evidencia NASA POWER: *Tu clima cambió* (1991–2025) | `0:25 – 1:00` | 35 s |
| **3** | Arquitectura Científica: 100% Determinista, Cero Cajas Negras | `1:00 – 1:30` | 30 s |
| **4** | Diagnóstico de la Rotación Actual (`soya@11-16 + soya@05-01`) | `1:30 – 2:05` | 35 s |
| **5** | 4 Estrategias Comparadas + Trade-offs Reales | `2:05 – 2:50` | 45 s |
| **6** | Trazabilidad (`evidence`) + Backtest Satelital MODIS | `2:50 – 3:30` | 40 s |
| **7** | Honestidad Científica: Límites Declarados (`S1–S12`) | `3:30 – 4:00` | 30 s |
| **8** | Sostenibilidad: Abierto al Productor + B2B Institucional | `4:00 – 4:35` | 35 s |
| **9** | Cierre de Impacto (*3 clics, 0 alucinaciones*) | `4:35 – 5:00` | 25 s |

---

## Guion Slide por Slide

### Slide 1 · Portada & El Problema (*Field Shift*) — `0:00 – 0:25` (25 s)
* **En pantalla:** Globo/terreno 3D (Three.js) haciendo zoom sobre Cuatro Cañadas / Pailón, Santa Cruz (`-17.30°, -62.25°`), título **RotaClima** y subtítulo *"Tu rotación fue diseñada para un clima que ya no existe"*.
* **Qué decir:**
  > *"Un productor en el este de Santa Cruz sigue sembrando hoy con el calendario de hace 20 años: soya en noviembre y soya en mayo. El problema no es su manejo: es que su campo cambió de clima sin que él se mueva de lugar. **RotaClima** cruza 35 años de datos diarios reales de **NASA POWER** con física agronómica determinista — sin cajas negras ni IA inventando cifras — para responderle en 3 clics qué sembrar y cuándo."*
* **Clave de defensa:** Arrancar con el problema del agricultor, no con la arquitectura de software.

---

### Slide 2 · Evidencia NASA POWER: *Tu clima cambió* — `0:25 – 1:00` (35 s)
* **En pantalla:** Comparación visual `1991–2006` vs `2010–2025` sobre `12,784` días de NASA POWER (`10` variables diarias), agrupados por campaña agrícola del hemisferio sur (`07-01`), prueba Mann-Whitney U ($\alpha = 0.10$).
  - Lluvia total: `1342 → 1146 mm` (`-195.9 mm`, $p = 0.0114$).
  - Lluvia Q2 (siembra verano): `-178.3 mm` ($p = 0.0006$).
  - Estación lluviosa: `-64.1 días` más corta ($p = 0.0055$), inicio `+27.6 días` más tarde.
  - Calor extremo ($>35\text{ °C}$): `52.7 → 80.5 días/campaña` ($p = 0.0084$).
  - Insignia visible en gris: **`ET0 total` y `lluvia Q1`: *No significativo*** ($p = 0.1057$ y $p = 0.9669$).
* **Qué decir:**
  > *"Agrupamos por campaña agrícola real — nunca por año calendario — y comparamos las primeras 15 campañas contra las últimas 15 con Mann-Whitney U. En Santa Cruz, la estación lluviosa se encogió **más de dos meses (`64 días`)**, las lluvias arrancan casi un mes más tarde y los días de calor extremo por encima de 35 °C saltaron de **53 a 81 por campaña**. Y fíjense en este detalle: `ET0 total` y `lluvia Q1` aparecen marcados como **no significativo**. No vendemos ruido como tendencia."*
* **Clave de defensa:** Señalar explícitamente la métrica **"no significativo"** en vivo gana de inmediato al jurado científico.

---

### Slide 3 · Arquitectura Científica: 100% Determinista — `1:00 – 1:30` (30 s)
* **En pantalla:** Diagrama animado del pipeline biofísico:
  `NASA POWER (10 vars)` → `ET0 FAO-56 Penman-Monteith (100% días) + Hargreaves fallback` → `Spin-up 180 días` → `Balance SCS-CN + FAO-56` → `Estrés térmico EcoCrop / Teixeira 2013` → `159 tests en verde` · `crops.json verificado (0 pendientes)`.
* **Qué decir:**
  > *"¿Por qué no usamos un LLM o un Random Forest para recomendar rotaciones? Porque un agricultor no puede arriesgar su capital con una caja negra que alucina cifras ni sobreajustar ML a 34 años de historia. En RotaClima cada número sale de ecuaciones auditables — FAO-56, SCS-CN y EcoCrop — con **180 días de spin-up** previo, validado con `r = 0.55` contra humedad radicular MERRA-2 y blindado por **159 tests automatizados**."*
* **Clave de defensa:** Si un jurado pregunta por qué no hay IA/ML, esta slide ya respondió antes de que levante la mano.

---

### Slide 4 · Diagnóstico de la Rotación Actual — `1:30 – 2:05` (35 s)
* **En pantalla:** Suelo `franco` (`AWC = 155 mm/m`, `CN = 78`), rotación base `soya@11-16 + soya@05-01` sobre `20` campañas (`2005/06–2024/25`). Tira visual de 20 campañas destacando `2016/17` (`I = 0.5541`, **calor**), `2023/24` (`0.6796`, **agua**) y `2015/16` (`0.6814`, **agua**), más salud de suelo `47.90 / 100` (`diversidad 15/100`).
* **Qué decir:**
  > *"Al simular la doble soya actual sobre estas 20 campañas, el promedio parece aceptable (`0.76`), pero oculta el riesgo real: la soya de invierno cae a `0.66`, la campaña **`2016/17`** colapsa por golpe de calor en floración, y **`2023/24`** y **`2015/16`** quedan al borde por déficit hídrico. Además, el monocultivo de leguminosas deja la salud de suelo en **`48 sobre 100`** y protege apenas el **`63%`** de la escorrentía."*
* **Clave de defensa:** Explicar por qué solo `1/20` rompe el umbral `0.60`: la soya de verano amortigua el índice anual, pero el ranking de las 3 peores (`2016/17`, `2023/24`, `2015/16`) coincide exactamente con las crisis históricas.

---

### Slide 5 · 4 Estrategias Comparadas + Trade-offs — `2:05 – 2:50` (45 s)
* **En pantalla:** Tabla/tarjetas comparativas de los **4 perfiles activos**:
  1. **Actual** (`soya@11-16 + soya@05-01`): `100.0%` prod · `1/20` mala · Suelo `47.9`
  2. **Adaptada** (`mijo@11-16 + soya@03-16`): **`112.4%`** prod · **`0/20`** malas · Suelo `63.8` (*cambio mínimo*)
  3. **Regenerativa** (`crotalaria@10-16 + sorgo@02-16 | girasol@11-01 + mijo@04-16`): `86.3%` prod · **`0/20`** malas · Suelo **`79.0`** (*86% protección erosiva, 100% MO*)
  4. **Diversificada** (`algodon@09-16 + sorgo@04-01 | mijo@11-16 + girasol@03-16`): **`115.4%`** prod · **`0/20`** malas · Suelo `60.6` (*trade-off: Nitrógeno `10/100`*)
* **Qué decir:**
  > *"El motor evalúa todas las combinaciones válidas — promediando fases en ciclos de 2 años para evitar sesgos de años pares o impares — y entrega **3 alternativas concretas**: **Adaptada** sube la productividad **`+12%`** con `0` campañas malas cambiando solo un cultivo; **Regenerativa** dispara la salud de suelo a **`79/100`** protegiendo el **`86%`** de la escorrentía; y **Diversificada** logra el máximo comercial (**`115%`**, `0/20` malas), pero declarando de frente su trade-off: el nitrógeno cae a **`10/100`** al no incluir leguminosas. El productor decide con todas las cartas sobre la mesa."*
* **Clave de defensa:** Destacar el trade-off de `Diversificada` demuestra que el sistema no vende soluciones mágicas.

---

### Slide 6 · Trazabilidad NASA + Backtest MODIS — `2:50 – 3:30` (40 s)
* **En pantalla:** Chip de evidencia (`text ⊂ evidence[].value`) + Tarjeta `ModisBacktestCard` (`MOD13Q1 v061`, `250 m`, `80` compuestos estivales `2005/06–2024/25`, 100% offline):
  - `2016/17` (`max_ndvi = 0.7160`) cae en tercil inferior (`<= 0.7260`, **`1/1`**).
  - Spearman honesto sin maquillar: **`ρ = -0.062` ($p = 0.796$)**.
* **Qué decir:**
  > *"Cada afirmación en pantalla tiene un invariante testeado: toda cifra del texto existe en su evidencia ligada a las variables exactas de NASA POWER. Y fuimos un paso más allá: cruzamos el modelo **offline** contra **80 compuestos MODIS a 250 m**. La única campaña mala del modelo (`2016/17`) cayó en el tercil más bajo de NDVI satelital (**`1 de 1`**). En años normales, el Spearman da `-0.06` porque un píxel de 250 m refleja el manejo real cambiante de ese lote, no una rotación fija teórica a 50 km. Lo mostramos tal cual salió."*
* **Clave de defensa:** Encuadrar `ρ = -0.062` antes de que el jurado pregunte lo convierte en una medalla de integridad científica.

---

### Slide 7 · Honestidad Científica: Límites Declarados (`S1–S12`) — `3:30 – 4:00` (30 s)
* **En pantalla:** Tarjeta sobria con 4 límites explícitos y su porqué de diseño:
  1. **Clima regional (~50 km, `S1`):** mide desplazamiento del régimen, no tormentas de finca.
  2. **Suelo desacoplado (`S4`):** `soil.py` no altera `TAW`/`Y_rel` sin calibración en parcela.
  3. **Sin precios inventados (`S10`):** rendimiento relativo invariante para enchufar márgenes locales.
  4. **Evaluación histórica, no pronóstico estacional:** mide resiliencia en 20 zafras reales.
* **Qué decir:**
  > *"En agronomía, ocultar supuestos cuesta cosechas. RotaClima declara doce supuestos explícitos en el producto: usamos clima regional de 50 km para comparar resiliencia relativa sin inventar precios ni curvas de suelo no calibradas localmente. Esto nos da una base limpia sobre la cual construir escala institucional."*
* **Clave de defensa:** En lugar de pedir disculpas por los límites, presentarlos como arquitectura modular disciplinada.

---

### Slide 8 · Sostenibilidad: Abierto al Productor + B2B Institucional — `4:00 – 4:35` (35 s)
* **En pantalla:** Arquitectura dual clara:
  - **Nivel Productor (100% Gratuito, Anónimo, Sin Paywall):** lote único en 3 clics, datos NASA abiertos completos, `p-valores` y supuestos `S1–S12` íntegros.
  - **Nivel B2B Institucional (Cooperativas · Aseguradoras · Bancos rurales · Semilleras):**
    1. Escala por polígono (`CHIRPS ~5 km` / `IMERG ~10 km` + `MODIS/Sentinel-2`).
    2. Ponderación prospectiva con **ENSO (`ONI`)** y ensambles `NMME`.
    3. Calibración privada (`GDD`, $K_y$, márgenes `$/ha` con rindes reales).
    4. API `/analyze/batch` multi-lote con `X-API-Key` fuera de `engine/`.
* **Qué decir:**
  > *"¿Cómo se sostiene esto sin traicionar los datos abiertos de la NASA? El productor individual siempre tendrá la herramienta **100% gratuita, sin registro y sin recortes**. La sostenibilidad viene del **B2B con cooperativas, bancos y aseguradoras agrícolas**: ellos pagan por volumen multi-lote vía API, lluvia de mayor resolución por polígono (`CHIRPS`/`Sentinel-2`), ponderación por fase **ENSO** y calibración con sus propios datos reales de cosecha y precios."*
* **Clave de defensa:** Explica por qué **no** cobramos por "datos NASA" ni metemos ML opaco a productores individuales.

---

### Slide 9 · Cierre de Impacto — `4:35 – 5:00` (25 s)
* **En pantalla:** Síntesis visual de 3 métricas: **`35 años` NASA POWER** · **`159` tests deterministas** · **`3 clics` para decidir qué sembrar**.
* **Qué decir:**
  > *"RotaClima convierte 35 años de ciencia espacial de la NASA en una decisión concreta de campo en 3 clics — auditable, transparente y pensada para que ningún agricultor siga sembrando para el clima de hace veinte años. Muchas gracias."*

---

## Respuestas Rápidas ante Preguntas Críticas (Chuleta de Defensa)

- **"¿Por qué no muestran ganancia en dólares (`$/ha`)?"**
  → *Los precios y costos logísticos cambian cada zafra y por comprador; el rendimiento relativo biofísico (`115.4%`) es invariante y permite que una cooperativa o productor multiplique por sus propios márgenes en la capa B2B.*
- **"¿El modelo predice si el próximo año viene Niña o Niño?"**
  → *Hoy mide riesgo histórico determinista sobre 20 campañas reales (`2005/06–2024/25`). Justamente el siguiente paso natural en la capa institucional es ponderar esas campañas análogas usando el índice ENSO (`ONI`) y ensambles estacionales (`NMME`).*
- **"¿Por qué `MODIS` da $\rho = -0.062$?"**
  → *Porque un píxel de 250 m refleja lo que sembró ese lote real cada año (cultivos distintos, barbechos, fechas cambiantes), mientras simulamos una rotación teórica fija con clima de 50 km. Aun así, la única campaña mala del modelo (`2016/17`) sí cayó en el tercil inferior satelital (`1/1`), y mostramos el `p = 0.796` sin maquillaje.*
- **"¿Por qué no cobraron en la app al agricultor por más datos?"**
  → *Los datos de NASA son públicos y un productor no paga por pronósticos a 50 km; si recortás la versión gratis generás desconfianza. Quien paga por escala multi-lote, polígonos de alta resolución y calibración con rindes reales es el ecosistema B2B (cooperativas, aseguradoras y bancos).*
