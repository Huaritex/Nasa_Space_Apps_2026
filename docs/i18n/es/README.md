# RotaClima

**Idioma:** [English](../../../README.md) · Español · [Português (Brasil)](../pt-BR/README.md) · [中文（简体）](../zh-CN/README.md)

> Herramienta de soporte de decisión agronómica para planificar rotaciones de cultivos ante el cambio climático.
> Desarrollada para el NASA Space Apps Challenge 2026, desafío **"Field Shift"**.

RotaClima compara la rotación actual de un productor con hasta tres rotaciones alternativas. Para cada plan ejecuta una simulación diaria del balance hídrico del suelo y de la respuesta del cultivo sobre **20 campañas de evaluación** (2005/06–2024/25), usando datos diarios de NASA POWER de **34 campañas agrícolas válidas** (1991/92–2024/25). Reporta el rendimiento relativo, el riesgo climático en lenguaje directo ("campaña mala en 1 de cada 20 años") y un puntaje de salud del suelo de 0 a 100. Cada cifra de una ficha de recomendación está vinculada al conjunto de datos NASA, los parámetros y el periodo de los que se calculó.

**No hay machine learning ni chatbot.** El motor es determinista: las mismas entradas producen siempre las mismas salidas.

## Contenido

1. Propiedades clave
2. Inicio rápido
3. Arquitectura
4. API
5. Fuentes de datos
6. Modelo científico
7. Catálogo de cultivos
8. Resultados del sitio de demostración
9. Frontend
10. Validación y pruebas
11. Supuestos y limitaciones
12. Estructura del repositorio
13. Problemas conocidos
14. Documentación y traducciones
15. Glosario
16. Referencias

---

## 1. Propiedades clave

- **Determinista.** Sin aleatoriedad sin semilla, sin reloj en el motor, desempates definidos en [PLAN.md](../../../PLAN.md) §5. El requisito de determinismo (respuestas idénticas byte a byte para solicitudes idénticas) está especificado como la prueba P2 en PLAN §6.
- **Trazable.** Cada afirmación lleva su evidencia: conjunto de datos, nombres exactos de parámetros POWER, valor, unidad y periodo.
- **Honesto con la incertidumbre.** Se reportan los valores p. Las tendencias con `p ≥ 0.10` se etiquetan como "no significativo". Los resultados desfavorables se muestran tal como se calcularon.
- **Sin relleno silencioso de huecos.** El valor de relleno `-999` de POWER se convierte en `NaN` en un único lugar ([backend/app/nasa/power.py](../../../backend/app/nasa/power.py)). Una campaña con entradas faltantes falla explícitamente.
- **Agronomía con fuente.** Los coeficientes provienen de FAO-56, USDA SCS-CN (TR-55), FAO EcoCrop y Teixeira et al. (2013). Cada campo agronómico de [crops.json](../../../backend/app/data/crops.json) tiene una `fuente` y una marca `verificar`. Los 130 campos tienen actualmente `verificar: false`, es decir, ninguno está pendiente.

---

## 2. Inicio rápido

**Requisitos:** Python ≥ 3.11, Node.js ≥ 20 (npm ≥ 10).

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                       # 159 pruebas, sin red; unos 3 minutos en la máquina de desarrollo
uvicorn app.main:app --reload --port 8000
```

Endpoints: `GET /health`, `GET /crops`, `POST /analyze`. Documentación interactiva OpenAPI: `GET /docs`.

```bash
# Frontend (segunda terminal)
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # verificación de tipos (tsc) + build de producción
```

El servidor de desarrollo de Vite redirige `/analyze` y `/crops` a `http://localhost:8000`. Si el backend no responde, la interfaz recurre a la demo precacheada de Santa Cruz y la etiqueta como datos de demostración.

Scripts de datos (ejecutar desde `backend/`):

```bash
python scripts/precache_demo.py         # genera frontend/public/demo_santa_cruz.json (4 perfiles + backtest MODIS)
python scripts/fetch_fixture.py         # descarga el fixture de NASA POWER para pruebas (requiere internet)
python scripts/fetch_modis_fixture.py   # descarga MOD13Q1 para 20 campañas (requiere internet; tarda varios minutos)
```

---

## 3. Arquitectura

```
Navegador: React 19 + TypeScript (Vite)
  MapForm · ClimateShift · Compare (+ RotationEditor, CalendarChart, ModisBacktestCard, …)
        │  POST /analyze   (respaldo: frontend/public/demo_santa_cruz.json)
        ▼
FastAPI  backend/app/main.py      CORS: allow_origins=["*"]; caché en proceso indexada por SHA-256 de la solicitud
        │
pipeline.py  analyze(request)     orquestación
   ├── nasa/power.py     cliente POWER: redondeo de coordenadas, caché en disco, reintentos, -999 → NaN
   ├── nasa/modis.py     backtest MOD13Q1, solo offline (offline_only=True)
   └── engine/           funciones puras: sin red, sin E/S, sin estado global
         calendar · et0 · crop · slot · table · rotation · soil · climate · alternatives · cards
config.py               todas las constantes numéricas del motor (fuente única de verdad)
```

| Módulo | Responsabilidad |
|---|---|
| `app/main.py` | Aplicación FastAPI, CORS, manejadores de error (422, 503), `/health`, `/crops`, `/analyze` |
| `app/pipeline.py` | Construye campañas, evalúa rotaciones, perfil climático, backtest MODIS, fichas |
| `app/schemas.py` | Contratos Pydantic v2 (solicitud y respuesta) |
| `app/config.py` | Todas las constantes del motor, con referencias a secciones de PLAN |
| `app/data/crops.json`, `crops.py` | Catálogo de cultivos y cargador con validación |
| `app/nasa/power.py` | Análisis, renombrado, caché y reintentos de POWER |
| `app/nasa/modis.py` | Análisis de subconjuntos MODIS, escalado de NDVI, backtest de Spearman |
| `engine/calendar.py` | Campañas agrícolas, rejilla de siembra, elegibilidad de campañas |
| `engine/et0.py` | Radiación extraterrestre, Penman–Monteith, respaldo Hargreaves |
| `engine/crop.py` | Curva de Kc en cuatro etapas, ventana sensible de floración |
| `engine/slot.py` | Escorrentía SCS-CN, balance hídrico diario, factores térmicos y de helada, rendimiento |
| `engine/table.py` | Tabla de slots memoizada; suavizado circular usado solo para elegir fechas de siembra |
| `engine/rotation.py` | Validez de la rotación, modos de cultivo, índices P e I, campañas malas, métricas |
| `engine/soil.py` | Puntaje de salud del suelo (nitrógeno, diversidad, protección contra erosión, materia orgánica) |
| `engine/climate.py` | Perfil climático, comparación antes/reciente, Mann–Whitney U |
| `engine/alternatives.py` | Enumeración de planes y selección de perfiles con relajaciones documentadas |
| `engine/cards.py` | Fichas de recomendación generadas por plantillas |

Convenciones del motor ([AGENTS.md](../../../AGENTS.md)): vectorizado con numpy a lo largo de las campañas, bucles explícitos sobre los días, sin literales mágicos en `engine/`.

---

## 4. API

### `POST /analyze`

Solicitud (`AnalyzeRequest`), con el caso de demostración:

```json
{
  "lat": -17.30,
  "lon": -62.25,
  "soil_texture": "franco",
  "current_rotation": {
    "years": [
      { "slots": [
          { "crop_id": "soya", "sow_date": "11-16" },
          { "crop_id": "soya", "sow_date": "05-01" }
      ] }
    ]
  },
  "include_diversified": false
}
```

| Campo | Regla |
|---|---|
| `lat` / `lon` | `-60 … 60` / `-180 … 180`. Las coordenadas se redondean a 2 decimales para acceder a los datos. |
| `soil_texture` | `arenoso` \| `franco` (por defecto) \| `arcilloso` |
| `sow_date` | `"MM-DD"`, el día debe ser `01` o `16` (quincenas) |
| `years` | De 1 a 3 años; de 1 a 2 slots por año, en orden cronológico dentro de la campaña |
| `crop_id` | Debe existir en el catálogo (minúsculas, sin tildes: `soya`, `maiz`, …) |
| `include_diversified` | **Valor por defecto de la API: `false`.** La interfaz web envía `true`. |

Errores:
- **422** con `detail` (mensaje en español): cultivo inexistente, slots solapados, menos de 10 días entre cosecha y siguiente siembra, rotación sin cultivo cosechable.
- **503** con `detail`: POWER no responde y no hay datos en caché para la coordenada.

Respuesta (`AnalyzeResponse`):

| Clave | Contenido |
|---|---|
| `meta` | Ubicación, elevación, hemisferio, inicio de campaña (`07-01` S / `01-01` N), lista de campañas, periodos, fracción de días Hargreaves, nota de resolución, supuestos S1–S12 |
| `climate` | 14 métricas climáticas: antes, reciente, delta, valor p, significancia, serie por campaña, fuente |
| `climatology` | 24 quincenas desde el inicio de campaña, para `before` y `recent` (lluvia, ET0, Tmax, Tmin) |
| `rotations` | Orden fijo: `actual`, `adaptada`, `regenerativa` y, si se solicita, `diversificada`. Cada una tiene slots, métricas, resultados por campaña y una ficha. |
| `modis_backtest` | Objeto, o `null` cuando no existe caché MODIS local para la coordenada |

`GET /crops` devuelve el resumen del catálogo (ID, nombre, familia, indicador de cosechable, cantidad de verificaciones pendientes).

Caché: las series de POWER se guardan en disco por punto; las respuestas completas de `/analyze` se guardan en memoria por proceso, indexadas por el SHA-256 del cuerpo de la solicitud.

---

## 5. Fuentes de datos

### 5.1 NASA POWER (diario, API de punto)

- Endpoint: `https://power.larc.nasa.gov/api/temporal/daily/point`, comunidad `AG` (agroclimatología). No requiere credenciales.
- Ventana: `19910101`–`20251231` (`DATA_START`, `DATA_END`). El fixture de demostración contiene **12,784 días consecutivos** (del 1 de enero de 1991 al 31 de diciembre de 2025).
- Caché en disco: `backend/cache/power/{lat:.2f}_{lon:.2f}_{start}_{end}.json` (respuesta cruda).
- Cliente: timeout de 60 s; 3 intentos en total (una solicitud más dos reintentos), con esperas de 2 s y luego 4 s entre ellos; el fallo final lanza `PowerUnavailable`. La tupla de reintentos por defecto del código también contiene 8 s, pero con 3 intentos nunca se alcanza (ver §13).
- Elevación: `geometry.coordinates[2]`.

| Parámetro POWER | Columna interna | Unidad | Papel en el modelo |
|---|---|---|---|
| `PRECTOTCORR` | `prec` | mm/día | Lluvia; escorrentía SCS-CN, balance hídrico, perfil climático |
| `T2M_MAX` | `tmax` | °C | ET0, estrés por calor, conteo de días calurosos |
| `T2M_MIN` | `tmin` | °C | ET0, estrés por helada, GDD |
| `T2M` | `t2m` | °C | Se ingiere; la ET0 usa `(tmax + tmin)/2` por diseño (FAO-56 ec. 6) |
| `RH2M` | `rh` | % | Presión de vapor en Penman–Monteith |
| `ALLSKY_SFC_SW_DWN` | `rs` | MJ/m²/día | Radiación neta (CERES SYN1deg) |
| `WS2M` | `ws` | m/s | Término de viento en Penman–Monteith |
| `PS` | `ps` | kPa | Constante psicrométrica |
| `GWETTOP` | `gwettop` | 0–1 | Se ingiere; humedad superficial del suelo (0–5 cm) |
| `GWETROOT` | `gwetroot` | 0–1 | Referencia para la verificación de cordura de humedad del suelo (§10) |

Los nombres de parámetros POWER aparecen solo en `nasa/power.py` y en `Source.parameters` de la salida.

### 5.2 NASA MODIS MOD13Q1 v061 (solo validación)

- Producto: MOD13Q1 v061, 250 m, compuestos de 16 días, banda `250m_16_days_NDVI`, factor de escala 0.0001, accedido mediante la API de subconjuntos de ORNL DAAC.
- Se usa solo en un **backtest offline** para el punto de demostración. La ruta `/analyze` nunca consulta MODIS en red (`offline_only=True`).
- Muestreo: cuatro compuestos por campaña en la ventana estival (`A{y+1}017` … `A{y+1}065`), 20 campañas → 80 compuestos.
- Límites del servicio: como máximo 10 fechas por solicitud (con más fechas responde HTTP 400). El proyecto midió de 33 a 42 s por solicitud.
- Caché: `backend/cache/modis/{lat:.2f}_{lon:.2f}_MOD13Q1.json`. Fixture de pruebas: `backend/tests/fixtures/modis_demo.json`.

---

## 6. Modelo científico

La especificación normativa completa está en [PLAN.md](../../../PLAN.md) §4. Esta sección la resume. Las fórmulas se reproducen en los bloques de código; las constantes están en `config.py`.

### 6.1 Campaña agrícola (unidad de análisis)

- Hemisferio `S` si `lat < 0`, en otro caso `N`. Una campaña `y` comienza el **1 de julio** (S) o el **1 de enero** (N). Nunca se agrupa por año calendario.
- Campañas válidas: `inicio(y) − 180 d ≥ DATA_START` y `inicio(y) + 365 + 183 d ≤ DATA_END` → **S: 1991–2024 (34 campañas)**, **N: 1992–2024 (33)**.
- `before` = primeras 15 campañas (1991/92–2005/06). `recent` = últimas 15 (2010/11–2024/25). `eval` = últimas 20 (2005/06–2024/25). Por construcción, `before` y `eval` comparten la campaña 2005/06.
- En el hemisferio S, una fecha de siembra con mes ≥ 07 cae en el año calendario `y` de la campaña `y`; con mes < 07, cae en `y+1`. Así un cultivo que cruza el 31 de diciembre se mantiene en una sola pieza.

### 6.2 Evapotranspiración de referencia (ET0)

Penman–Monteith (FAO-56 ec. 6) con `T = (tmax + tmin)/2`. Hargreaves (FAO-56 ec. 52) se usa **por día** cuando faltan HR, radiación o viento; la fracción de días con Hargreaves se reporta en `meta.et0_hargreaves_share` (0.0 en la demo).

```
Ra     = (24·60/π)·0.0820·dr·(ωs·sin φ·sin δ + cos φ·cos δ·sin ωs)   MJ m⁻² d⁻¹   (φ en radianes, negativa en el sur)
ET0_PM = (0.408·Δ·Rn + γ·900/(T+273)·ws·(es − ea)) / (Δ + γ·(1 + 0.34·ws))
ET0_HG = 0.0023·(T + 17.8)·√(tmax − tmin)·Ra·0.408                         (respaldo; Ra se convierte con 0.408)
```

### 6.3 Coeficiente de cultivo y ventana de floración

- Kc es lineal por tramos en cuatro etapas (inicial, desarrollo, media, maduración), según FAO-56 tablas 11–12. Sin ajuste climático de Kc (supuesto S3).
- Ventana sensible (floración): `[t_mid − 5, t_mid + 25)` días, donde `t_mid = L_ini + L_dev`.

### 6.4 Balance hídrico diario de un solo balde

- **Escorrentía (SCS-CN):** `S = 25400/CN − 254`; `RO = (P − 0.2S)² / (P + 0.8S)` si `P > 0.2S`, en otro caso 0.
- **Lluvia efectiva:** la lluvia menor que `0.2 × ET0` se ignora (`Pe = 0`). La lluvia entra al balde **antes** de evaluar el factor de estrés de ese día.
- **Balde:** capacidad `TAW = AWC × Zr`; `AWC` es 80 / 155 / 160 mm/m y `CN` es 67 / 78 / 85 para arenoso / franco / arcilloso.
- **Estrés:** `RAW = p·TAW`, con `p = clip(p_tab + 0.04·(5 − ETc), 0.1, 0.8)`; `Ks = 1` si `D ≤ RAW`, en otro caso `(TAW − D)/(TAW − RAW)`.
- **Spin-up:** 180 días antes de la siembra, partiendo de `Dr = 0.5·TAW`. Durante los últimos 120 días, `Kc = 0.90` si el slot anterior se cosechó dentro de los 30 días (`mode = "crop"`); en otro caso `Kc = 0.20` (`mode = "fallow"`).
- **Factor hídrico:** `f_agua = clip(1 − Ky·(1 − ΣETa/ΣETc), 0, 1)`. El cociente se calcula sobre sumas, nunca como promedio de cocientes diarios (FAO-56 ec. 90).

### 6.5 Factores térmicos, helada y rendimiento relativo

```
Y_rel = f_agua · f_calor · f_helada · f_temp         ∈ [0, 1]
```

- **f_temp:** media a lo largo del ciclo de una respuesta trapezoidal de EcoCrop sobre la temperatura media diaria.
- **f_calor:** `1 − media_{ventana sensible}( clip((tmax − Tcrit)/(Tlim − Tcrit), 0, 1) )`.
- **f_helada:** `0.3` si `tmin < t_helada` (0 °C) en algún día de la ventana de floración; en otro caso `0.7` si `tmin < −3 °C` en algún día del ciclo; en otro caso `1`. Supuesto S6.
- **Factor limitante:** el factor más bajo si está por debajo de 0.95; si no, `ninguno`. Los empates se resuelven en el orden agua, calor, helada, temperatura.

### 6.6 Índices de rotación y campañas malas

- Los slots forman una secuencia cíclica de 1 a 3 años. Validez: cada intervalo entre una cosecha y la siguiente siembra es ≥ 10 días; `sow_offset + duración ≤ 365 + 183`; al menos un cultivo cosechable.
- Para cada campaña `y`, el clima de `y` se aplica a **cada fase** `k = 1..L` de la rotación:

```
P_y = (1/L) · Σ_k Σ_{s ∈ año k, cosechable} w_s · Y_rel(s, y)
Pot = (1/L) · Σ_k Σ_{s ∈ año k, cosechable} w_s
I_y = P_y / Pot                  campaña mala ⇔ I_y < 0.60
```

- Los cultivos de cobertura (`cosechable = false`) no cuentan en `P` ni en `Pot`. Sí cuentan para el suelo, el modo de cultivo y la validez.
- Métricas sobre las 20 campañas de evaluación: `mean_index`, `p10_index` (percentil lineal), `mean_productivity`, `bad_seasons` (de 20), `bad_before` y `bad_recent` (de 15 cada una), y `productivity_vs_current = 100 · mean_P / mean_P(actual)`.
- Un slot "falla" en una campaña cuando `Y_rel < 0.50`.

### 6.7 Puntaje de salud del suelo (0–100)

```
total = 0.25 · (nitrogen + diversity + erosion + organic_matter)
```

- **Nitrógeno:** `clip(60 + 20 · N_año, 0, 100)`, con `N_año = (1/L) · Σ_s N_POINTS[clase_n(s)]`. Puntos: `cobertura_leguminosa` +2.0, `leguminosa_grano` +0.5, `cobertura_no_leguminosa` +0.5, `extractiva` −1.0, `muy_extractiva` −1.5.
- **Diversidad:** `DIVERSITY_BASE[familias] · (1 − 0.5 · fracción_repetida)`, con base 30 / 65 / 85 para 1 / 2 / 3 familias botánicas, y 100 para cuatro o más. `fracción_repetida` es la proporción de pares cíclicos adyacentes con la misma familia.
- **Materia orgánica:** `clip(100 · ((1/L) · Σ_s pts(s)) / 6, 0, 100)`, con `pts = RESIDUE_POINTS[clase]` (bajo 1, medio 2, alto 3), más `COVER_CROP_BONUS = 1` para los cultivos de cobertura no cosechables.
- **Protección contra erosión:** la escorrentía diaria SCS-CN (campañas de evaluación, promediada por día de la campaña) ponderada por una curva de cobertura, expresada en porcentaje. La cobertura es el rastrojo tras la cosecha (`RESIDUE_COVER`: bajo 0.3, medio 0.5, alto 0.8), que crece linealmente durante el desarrollo del cultivo y vale 1.0 después. Supone siembra directa (S5). Si la escorrentía total es 0, el puntaje es 100.
- El puntaje de suelo **no** retroalimenta el rendimiento (supuesto S4).

### 6.8 Perfil climático y prueba de significancia

Se calculan catorce métricas por campaña (definiciones en [PLAN.md](../../../PLAN.md) §4.8):

- **Lluvia:** total, y por trimestre de la campaña (días 0–90, 91–181, 182–272, 273–fin).
- **Inicio de lluvias (onset):** primer desfase ≥ 62 donde la lluvia de 3 días es ≥ 20 mm y no hay una racha de ≥ 10 días secos (< 1 mm/día) en los 30 días siguientes.
- **Fin de lluvias (cessation):** primer desfase ≥ inicio + 60 donde la lluvia de 20 días es < 10 mm.
- **Duración de la temporada de lluvias**, **días calurosos** (Tmax > 35 °C), **rachas secas** y **racha seca más larga** dentro del periodo húmedo, **GDD** (base 10 °C), **ET0 total**, **déficit hídrico**.

Para cada métrica: medias de `before` y `recent` (ignorando NaN), `delta = recent − before`, valor p de **Mann–Whitney U** bilateral (`None` si alguna muestra tiene menos de 5 valores) y `significant = p < 0.10`.

### 6.9 Perfiles alternativos

La selección es determinista y sigue [PLAN.md](../../../PLAN.md) §5. Las relajaciones se registran en `relaxed_constraints`.

| Perfil | Objetivo | Restricciones (antes de relajar) | Orden de preferencia |
|---|---|---|---|
| `actual` | Línea base: la rotación tal como se ingresó, sin reoptimizar | — | — |
| `adaptada` (adaptada al clima) | Cambio mínimo | Mismo número de años y slots, como máximo un cultivo cambiado, fechas de siembra reoptimizadas, `mean_P ≥ 95%` de la actual | Menos campañas malas → mayor `p10_index` → mayor `mean_P` → menos cambios |
| `regenerativa` | Mejor suelo con pérdida de rendimiento acotada | Ganancia de suelo ≥ 10 puntos, `mean_P ≥ 80%` de la actual, campañas malas no superiores a la actual | Mayor total de suelo → mayor `mean_P` |
| `diversificada` (opcional) | Ciclo diversificado de dos años | ≥ 3 familias botánicas, ≥ 3 cultivos cosechables, suelo no inferior al actual | Mayor `mean_P` entre planes con campañas malas no superiores a la actual |

Orden de relajación: pérdida del 20% → 30% en `regenerativa`; se quita el límite de campañas malas; ganancia de suelo 10 → 1 punto. `adaptada` quita su filtro de productividad si ningún candidato lo cumple.

### 6.10 Fichas de recomendación

Las fichas se generan a partir de plantillas fijas, no de texto libre. Cada plantilla se activa solo si se cumple su condición y cita los parámetros de los que provienen sus cifras. Una prueba verifica que cada número del texto de una afirmación aparezca en su `evidence[].value` (PLAN §2.5). Las fichas tienen tres secciones: **por qué**, **beneficios** y **riesgos**.

---

## 7. Catálogo de cultivos

El catálogo ([backend/app/data/crops.json](../../../backend/app/data/crops.json)) tiene 13 cultivos. Los valores siguientes se leen del archivo.

| ID | Nombre | Familia | Cosechable | Etapas ini/dev/mid/late (d) | Kc ini/mid/end | Zr (m) | p | Ky | EcoCrop Tmin/Topt-min/Topt-max/Tmax (°C) | Calor Tcrit/Tlim (°C) | Clase N | Rastrojo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `soya` | Soya | Fabaceae | sí | 20/30/60/25 | 0.40/1.15/0.50 | 1.0 | 0.50 | 0.85 | 10/20/33/38 | 35/40 | leguminosa_grano | bajo |
| `maiz` | Maíz | Poaceae | sí | 25/40/45/30 | 0.30/1.20/0.35 | 1.3 | 0.55 | 1.25 | 10/18/33/47 | 35/45 | muy_extractiva | alto |
| `sorgo` | Sorgo | Poaceae | sí | 20/35/40/30 | 0.30/1.05/0.55 | 1.5 | 0.55 | 0.90 | 8/22/35/40 | 35/40 | extractiva | alto |
| `trigo` | Trigo | Poaceae | sí | 15/25/50/30 | 0.30/1.15/0.30 | 1.2 | 0.55 | 1.15 | 5/15/23/27 | 27/40 | extractiva | medio |
| `girasol` | Girasol | Asteraceae | sí | 25/35/45/25 | 0.35/1.10/0.35 | 1.2 | 0.45 | 0.95 | 5/17/34/45 | 34/45 | muy_extractiva | medio |
| `frijol` | Frijol | Fabaceae | sí | 20/30/40/20 | 0.40/1.15/0.35 | 0.7 | 0.45 | 1.15 | 7/16/25/32 | 25/32 | leguminosa_grano | bajo |
| `mani` | Maní | Fabaceae | sí | 25/35/45/25 | 0.40/1.15/0.60 | 0.8 | 0.50 | 0.70 | 10/22/32/45 | 32/45 | leguminosa_grano | bajo |
| `algodon` | Algodón | Malvaceae | sí | 30/50/55/45 | 0.35/1.15/0.60 | 1.4 | 0.65 | 0.85 | 15/22/36/42 | 36/42 | muy_extractiva | bajo |
| `cebada` | Cebada | Poaceae | sí | 15/25/50/30 | 0.30/1.15/0.25 | 1.2 | 0.55 | 1.15 | 2/15/20/40 | 20/40 | extractiva | medio |
| `papa` | Papa | Solanaceae | sí | 25/30/45/30 | 0.50/1.15/0.75 | 0.5 | 0.35 | 1.10 | 7/15/25/30 | 25/30 | extractiva | bajo |
| `mijo` | Mijo | Poaceae | sí | 15/25/40/25 | 0.30/1.00/0.30 | 1.5 | 0.55 | 0.90 | 12/25/35/40 | 35/40 | extractiva | alto |
| `avena_cob` | Avena (cobertura) | Poaceae | **no** | 15/25/45/5 | 0.30/1.15/1.15 | 1.2 | 0.55 | 1.00 | 5/16/20/30 | 20/30 | cobertura_no_leguminosa | alto |
| `crotalaria` | Crotalaria (cobertura) | Fabaceae | **no** | 15/25/45/5 | 0.40/1.10/1.10 | 1.0 | 0.50 | 1.00 | 15/23/30/37 | 30/37 | cobertura_leguminosa | alto |

Los cultivos de cobertura se truncan a un ciclo de 90 días con Kc_end = Kc_mid (supuesto S9). Los umbrales de calor de los cultivos fuera de Teixeira et al. (2013) se derivan de EcoCrop (S7). El umbral de helada `t_helada` es 0 °C para todos los cultivos (S6).

---

## 8. Resultados del sitio de demostración

Punto de demostración: **Santa Cruz, Bolivia (−17.30, −62.25), elevación 280.15 m**, textura `franco` (AWC 155 mm/m, CN 78). Rotación actual: soya 11-16 + soya 05-01. Todos los valores siguientes se leen de [frontend/public/demo_santa_cruz.json](../../../frontend/public/demo_santa_cruz.json).

### 8.1 Cambio climático (antes 1991/92–2005/06 vs reciente 2010/11–2024/25)

| Métrica | Unidad | Antes | Reciente | Delta | Valor p | Significativo (p < 0.10) |
|---|---|---|---|---|---|---|
| Lluvia total | mm/campaña | 1342.0 | 1146.0 | −195.9 | 0.0114 | sí |
| Lluvia, trimestre 1 | mm | 145.4 | 142.7 | −2.73 | 0.9669 | no |
| Lluvia, trimestre 2 | mm | 466.2 | 287.9 | −178.3 | 0.0006 | sí |
| Lluvia, trimestre 3 | mm | 493.3 | 436.6 | −56.64 | 0.2290 | no |
| Lluvia, trimestre 4 | mm | 237.3 | 279.1 | +41.79 | 0.2455 | no |
| Inicio de lluvias | desfase en días | 82.6 | 110.2 | +27.6 | 0.0016 | sí |
| Fin de lluvias | desfase en días | 312.9 | 274.8 | −38.12 | 0.0723 | sí |
| Duración de la temporada de lluvias | días | 232.1 | 168.0 | −64.1 | 0.0055 | sí |
| Días calurosos (Tmax > 35 °C) | días/campaña | 52.73 | 80.47 | +27.73 | 0.0084 | sí |
| Rachas secas (≥ 10 d) | conteo | 1.00 | 1.73 | +0.73 | 0.0791 | sí |
| Racha seca más larga | días | 11.00 | 13.47 | +2.47 | 0.0828 | sí |
| GDD (base 10 °C) | °C·día | 5694 | 5934 | +240.4 | 0.0202 | sí |
| ET0 total | mm/campaña | 1522 | 1587 | +65.02 | 0.1057 | **no** |
| Déficit hídrico | mm/campaña | 470.7 | 659.0 | +188.3 | 0.0101 | sí |

Diez de las 14 métricas son significativas. Las cuatro que no lo son (lluvia de los trimestres 1, 3 y 4, y ET0 total) se reportan como tales.

### 8.2 Perfiles de rotación (ventana de evaluación, 20 campañas)

| Perfil | Rotación (año 1 · año 2) | I medio | I P10 | Productividad vs actual | Campañas malas | Suelo total | N | Diversidad | Protección contra erosión | Materia orgánica |
|---|---|---|---|---|---|---|---|---|---|---|
| `actual` | soya@11-16 + soya@05-01 | 0.7644 | 0.6812 | 100.00 % | 1 / 20 | 47.90 | 80.0 | 15.0 | 63.26 % | 33.33 |
| `adaptada` | mijo@11-16 + soya@03-16 | 0.8589 | 0.7779 | 112.36 % | 0 / 20 | 63.82 | 50.0 | 65.0 | 73.60 % | 66.67 |
| `regenerativa` | crotalaria@10-16 + sorgo@02-16 · girasol@11-01 + mijo@04-16 | 0.8795 | 0.8277 | 86.30 % | 0 / 20 | 79.03 | 45.0 | 85.0 | 86.12 % | 100.00 |
| `diversificada` | algodon@09-16 + sorgo@04-01 · mijo@11-16 + girasol@03-16 | 0.8819 | 0.7958 | 115.37 % | 0 / 20 | 60.56 | 10.0 | 74.38 | 82.88 % | 75.00 |

Las peores campañas de la rotación actual: **2016/17** (I = 0.5541, factor limitante: calor), **2023/24** (I = 0.6796, agua) y **2015/16** (I = 0.6814, agua).

`adaptada` reemplaza un cultivo (soya → mijo) y reoptimiza las fechas de siembra dentro de la misma estructura de un año. `regenerativa` y `diversificada` son ciclos de dos años. `regenerativa` tiene el mayor puntaje de suelo; `diversificada` tiene la mayor productividad, pero el menor puntaje de nitrógeno (10.0), porque no incluye leguminosas.

### 8.3 Validación satelital (MODIS MOD13Q1, offline)

- Correlación de rangos de Spearman entre el máximo de NDVI estival y el índice simulado `I` de la rotación actual: **ρ = −0.0617, p = 0.7962** (n = 20). No hay correlación significativa. Se reporta tal como se calculó.
- Umbral del tercil inferior de NDVI: **0.7260**. La única campaña mala, 2016/17, tiene un NDVI máximo de **0.7160**, por lo que cae en el tercil inferior (**1 de 1** campañas malas).

Interpretación: un píxel de 250 m refleja los cultivos realmente sembrados en ese lote cada año, mientras que el modelo simula una rotación fija impulsada por un clima regional de unos 50 km. No cabe esperar una correlación estrecha entre ambos en años normales.

---

## 9. Frontend

Stack: Vite, React 19, TypeScript en modo estricto, Leaflet (`react-leaflet`), Recharts. **Las etiquetas de la interfaz están en español.** Los identificadores y el código están en inglés.

| Área | Componentes | Qué hace |
|---|---|---|
| Parcela y rotación (a) | `views/MapForm.tsx`, `components/RotationEditor.tsx` | Mapa Leaflet con captura de coordenadas por clic, selector de textura, editor de rotación por quincenas con validación de solapamientos y de intervalos, botón de demo de Santa Cruz |
| Cambio climático (b) | `views/ClimateShift.tsx`, `components/MetricDelta.tsx` | Una tarjeta por métrica climática (antes → reciente, delta, "No significativo" cuando p ≥ 0.10), serie por campaña, fuente NASA |
| Calendario | `components/CalendarChart.tsx` | Gráfico de lluvia y ET0 por 24 quincenas, líneas de Tmax/Tmin, barras de etapas del cultivo con la ventana de floración resaltada |
| Comparación (c) | `views/Compare.tsx`, `components/CompareTable.tsx`, `components/RotationCard.tsx`, `components/ModisBacktestCard.tsx` | Perfiles lado a lado, tira de campañas malas de las 20 campañas, fichas con por qué/beneficios/riesgos, chips de evidencia por afirmación, tarjeta MODIS |
| Cliente de API | `src/api.ts`, `src/types.ts` | Llama a `/analyze` y `/crops`; recurre a la demo precacheada y a la lista estática de cultivos; `types.ts` replica `schemas.py` a mano |

La barra superior muestra un aviso de **demo offline** cuando los datos provienen del archivo precacheado.

---

## 10. Validación y pruebas

- **Suite del backend:** `pytest -q` → **159 passed, 1 warning**, unos 3 minutos en la máquina de desarrollo. Las pruebas corren sin red: usan fixtures en `backend/tests/fixtures/` o `httpx.MockTransport`.
- **Frontend:** `npm run build` ejecuta `tsc` en modo estricto y luego el build de Vite.
- **Criterios go/no-go** ([PLAN.md](../../../PLAN.md) §3, N1–N2), en [notebooks/01_validacion_motor.ipynb](../../../notebooks/01_validacion_motor.ipynb):
  1. ET0 anual entre 1,100 y 2,000 mm, y lluvia anual entre 700 y 1,800 mm.
  2. La soya de verano rinde más que la soya de invierno.
  3. La rotación actual tiene entre 1 y 15 campañas malas de 20.
  4. Las tres peores campañas se contrastan con sequías reportadas.
  5. Correlación entre `1 − Dr/TAW` simulado y `gwetroot` superior a 0.5. Es una **verificación de cordura, no una validación independiente**, porque ambos usan la misma lluvia.

  El notebook **no se volvió a ejecutar** para esta documentación. Los resultados reportados en los documentos previos del proyecto, incluido r = 0.5501 para el criterio 5, no se recalcularon aquí.

---

## 11. Supuestos y limitaciones

Estos son los supuestos S1–S12 de [PLAN.md](../../../PLAN.md) §4.10. También se devuelven en `meta.assumptions`.

- **S1** POWER es reanálisis a ≈ 50 km (MERRA-2), con radiación de 1° (CERES). Describe el clima regional, no una parcela específica. La Tmax modelada tiende a ser menor que la de las estaciones, así que los conteos de días por encima de 35 °C son conservadores.
- **S2** Agua inicial: spin-up de 180 días con Kc fijo de 0.20 (barbecho) o 0.90 (cultivo previo). No se simula el cultivo anterior real.
- **S3** La fenología usa días calendario. Kc no se ajusta por humedad ni viento. Sin fotoperiodo.
- **S4** El puntaje de suelo no cambia el rendimiento simulado.
- **S5** Se supone manejo sin labranza.
- **S6** La helada es una regla escalonada: factor 0.3 durante la floración, 0.7 en la fase vegetativa.
- **S7** Los umbrales de calor que no están en Teixeira et al. (2013) se derivan de EcoCrop.
- **S8** Las clases de nitrógeno y de rastrojo son conocimiento agronómico general, no mediciones.
- **S9** Los cultivos de cobertura usan parámetros por analogía, un ciclo truncado de 90 días y no producen grano.
- **S10** El rendimiento es relativo al potencial agroecológico. No hay precios ni márgenes. `value_weight = 1` para todos los cultivos por defecto.
- **S11** Modelo de un solo balde. No se modelan: anegamiento, plagas, malezas, fallas de emergencia, aguas subterráneas, ascenso capilar, dinámica de nutrientes ni cambios de la estructura del suelo en el tiempo.
- **S12** Las tendencias de lluvia en los reanálisis pueden contener artefactos del sistema de observación. De ahí los valores p y la etiqueta "no significativo" cuando `p ≥ 0.10`.

Límites de alcance que se derivan de estos supuestos:
- El motor evalúa un punto por solicitud. Una comparación regional requiere una solicitud por coordenada.
- La salida es un ranking relativo bajo una plantilla de rotación fija. No es un pronóstico de rendimiento ni un pronóstico estacional.
- El puntaje de suelo y el rendimiento son independientes: un puntaje de suelo más alto no eleva el rendimiento simulado.

---

## 12. Estructura del repositorio

```
.
├── README.md                     # este archivo (versión maestra en inglés)
├── AGENTS.md                     # reglas de ingeniería para colaboradores y agentes
├── PLAN.md                       # plan normativo: contratos (§2), fórmulas (§4), pruebas (§6)
├── docs/i18n/
│   ├── es/README.md              # Español
│   ├── pt-BR/README.md           # Português (Brasil)
│   └── zh-CN/README.md           # 中文（简体）
├── backend/
│   ├── pyproject.toml            # dependencias y el extra de desarrollo (pytest)
│   ├── app/
│   │   ├── main.py               # endpoints de FastAPI, CORS, manejadores de error
│   │   ├── pipeline.py           # analyze(): orquestación y caché en memoria
│   │   ├── schemas.py            # contratos Pydantic v2
│   │   ├── config.py             # todas las constantes del motor
│   │   ├── data/                 # crops.json y su cargador
│   │   ├── nasa/                 # power.py (cliente POWER), modis.py (backtest MODIS)
│   │   └── engine/               # funciones puras: calendar, et0, crop, slot, table,
│   │                             #   rotation, soil, climate, alternatives, cards
│   ├── scripts/                  # scripts de datos canónicos (ver §13)
│   └── tests/                    # test_*.py y fixtures/
├── frontend/
│   ├── package.json · vite.config.ts · tsconfig.json · index.html
│   ├── public/demo_santa_cruz.json   # demo offline precacheada
│   └── src/                      # App.tsx, api.ts, types.ts, views/, components/
├── notebooks/01_validacion_motor.ipynb
└── contracts/analyze_response.example.json
```

Generado e ignorado por git: `backend/cache/`, `backend/.venv/`, `frontend/node_modules/`, `frontend/dist/`.

---

## 13. Problemas conocidos

- **Scripts duplicados.** Existen `scripts/` en la raíz del repositorio y `backend/scripts/`, y su contenido difiere. Los comandos de este documento usan `backend/scripts/`, que se toma como canónico. Las copias de la raíz están desactualizadas hasta que se reconcilien.
- **Archivo faltante.** [AGENTS.md](../../../AGENTS.md) y [PLAN.md](../../../PLAN.md) mencionan `QUESTIONS.md` como lugar para las dudas abiertas. No está en el repositorio.
- **Sin archivo de licencia.** El repositorio no declara una licencia; por tanto, no hay términos de reutilización definidos.
- **El valor por defecto de diversificada difiere según el cliente.** El valor por defecto de la API es `include_diversified: false`; la interfaz web envía `true`.
- **Caché vacía.** Sin `backend/cache/`, el primer `/analyze` de una coordenada nueva necesita red para consultar POWER. La demo precacheada en `frontend/public/` funciona sin conexión. La interfaz advierte que una primera consulta puede tardar unos 20 segundos.
- **Cobertura del proxy de desarrollo.** El proxy de Vite solo redirige `/analyze` y `/crops`, no `/health`. Define `VITE_API_URL` para llamar al backend desde otro origen.
- **Alcance de MODIS.** El backtest MODIS está precacheado y es offline por diseño. No puede ejecutarse para coordenadas sin caché MODIS local; en ese caso el campo `modis_backtest` es `null`.
- **Reintentos de POWER distintos del plan.** [PLAN.md](../../../PLAN.md) §2.3 especifica tres reintentos con esperas de 2, 4 y 8 s. [backend/app/nasa/power.py](../../../backend/app/nasa/power.py) hace 3 intentos en total (2 reintentos) con esperas de 2 s y 4 s. El código es el comportamiento de referencia; el plan no se ha actualizado.

---

## 14. Documentación y traducciones

- La **versión en inglés de este archivo es la maestra.** Las versiones en español, portugués brasileño y chino simplificado de [docs/i18n/](../../) son traducciones de ella.
- Las fórmulas, los bloques de código, los identificadores, los IDs de cultivos, los nombres de parámetros POWER y MODIS, las rutas de archivos y los nombres de campos de la API son idénticos en las cuatro versiones.
- Las traducciones se mantienen a mano. Cuando cambie este archivo, actualiza las traducciones en el mismo cambio.

---

## 15. Glosario

| Término | Significado |
|---|---|
| Campaña | Año agrícola desde el 1 de julio (S) o el 1 de enero (N). Es la unidad de análisis. |
| Slot | Un cultivo con su fecha de siembra y su modo de cultivo: (cultivo, fecha de siembra, `crop` \| `fallow`) |
| Modo | `crop` si la cosecha previa fue dentro de los 30 días anteriores a la siembra; en otro caso `fallow` |
| TAW | Agua total disponible en la zona radicular (mm) |
| RAW | Agua fácilmente disponible, `p · TAW` (mm) |
| Dr | Agotamiento de la zona radicular (mm) |
| Y_rel | Rendimiento relativo de un slot en una campaña, 0–1 |
| P, Pot, I | Productividad, potencial e índice de una rotación en una campaña |
| Campaña mala | Campaña con `I < 0.60` |
| Ventana de evaluación | Las últimas 20 campañas, usadas para todas las métricas principales |

---

## 16. Referencias

- Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop water requirements.* FAO Irrigation and Drainage Paper 56.
- Doorenbos, J., & Kassam, A. H. (1979). *Yield response to water.* FAO Irrigation and Drainage Paper 33 (fuente del factor de respuesta de rendimiento Ky).
- USDA Soil Conservation Service. *National Engineering Handbook, Section 4 (Hydrology)*, y TR-55 (método del número de curva).
- Teixeira, E. I., et al. (2013). *Global and Planetary Change* (umbrales de estrés por calor).
- Base de datos FAO ECOCROP (rangos de idoneidad térmica).
- NASA POWER (Prediction Of Worldwide Energy Resources), Langley Research Center. Conjuntos de datos MERRA-2 y CERES SYN1deg.
- MODIS MOD13Q1 v061, 250 m, NDVI de 16 días, accedido mediante la API de subconjuntos de ORNL DAAC.
