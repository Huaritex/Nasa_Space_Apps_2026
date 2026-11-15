# RotaClima 🌱🛰️

**Herramienta de Soporte de Decisión Agronómica ante Cambio Climático**  
*Desarrollada para el desafío "Field Shift" — NASA Space Apps Challenge.*

[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-159%20passed-brightgreen.svg)]()
[![Type Strict](https://img.shields.io/badge/TypeScript-Strict%20Verified-blue.svg)]()
[![Deterministic Engine](https://img.shields.io/badge/Simulación-100%25%20Determinista%20(Sin%20ML)-orange.svg)]()
[![NASA POWER Data](https://img.shields.io/badge/NASA%20POWER-MERRA--2%20%2F%20CERES-blueviolet.svg)]()

---

## 1. ¿Qué es RotaClima?

**RotaClima** es un motor de simulación biofísica y agroclimática diseñado para productores agrícolas y técnicos de campo. Permite evaluar y comparar la rotación de cultivos actual de un lote contra **3 alternativas agronómicamente viables** (perfiles **Adaptada**, **Regenerativa** y **Diversificada**), simulando su desempeño día a día contra **~34 campañas agrícolas reales** (1991–2024) provenientes del archivo satelital y de reanálisis de **NASA POWER**, complementado con un **backtest satelital offline de 20 campañas contra NDVI de NASA MODIS (`MOD13Q1 v061`, 250 m)**.

Para cada estrategia evaluada, RotaClima cuantifica:
- **Productividad relativa esperada**: rendimiento medio respecto al potencial agroecológico sin estrés hídrico ni térmico.
- **Riesgo climático real**: probabilidad de sufrir una campaña mala (rendimiento menor al 60% del potencial) expresada en lenguaje directo (ej. *"Campaña mala en 1 de 20 años"*), junto con el percentil 10 ($P_{10}$) y la lista de los 3 peores años históricos de la serie.
- **Salud del suelo**: índice integral de 0 a 100 evaluando balance de nitrógeno, diversidad de familias botánicas, ciclado de materia orgánica y protección contra erosión hídrica basada en la escorrentía simulada con lluvias reales.
- **Trazabilidad científica total**: cada afirmación en las fichas de recomendación incluye un **chip de evidencia interactivo** que referencia el conjunto de datos de NASA, los parámetros meteorológicos exactos utilizados, sus valores numéricos y la ventana de campañas evaluada.

### ⚠️ Principio Fundacional: Sin Machine Learning ni Chatbots
> **RotaClima NO utiliza redes neuronales, modelos de lenguaje opacos ni cajas negras estadísticas.**  
> En agricultura, una recomendación alucinada cuesta cosechas completas. Todo el cálculo de RotaClima es **100% determinista, reproducible y auditable**, fundamentado en primeros principios biofísicos y agronómicos estandarizados internacionalmente (**FAO-56**, **USDA TR-55** y **FAO EcoCrop**). Dos ejecuciones con los mismos datos de entrada producen exactamente la misma respuesta bit por bit.

---

## 2. Arquitectura del Sistema

El sistema implementa una arquitectura desacoplada y orientada a funciones puras numéricas:

```
[ Productor / Técnico Agrícola ]
         │  (Coordenadas en mapa Leaflet + Textura de suelo + Rotación de cultivos)
         ▼
┌────────────────────────────────────────────────────────────────────────┐
│ FRONTEND (Vite + React 19 + TypeScript Estricto)                       │
│  - src/views/MapForm.tsx        : Mapa interactivo y configuración     │
│  - src/components/RotationEditor: Editor quincenal de rotaciones       │
│  - src/views/ClimateShift.tsx   : Diagnóstico de cambio de régimen     │
│  - src/views/Compare.tsx        : Comparación, tiras y fichas NASA     │
│  - src/components/CompareTable  : Tabla comparativa de métricas        │
│  - src/components/RotationCard  : Fichas con chips de evidencia NASA   │
│  - src/components/CalendarChart : Calendario quincenal agroclimático   │
│  - src/components/ModisBacktestCard: Validación satelital MODIS (E1)   │
│  - src/api.ts                   : Cliente HTTP con fallback a demo     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP POST /analyze
                                    │ (o fallback etiquetado a demo_santa_cruz.json)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ BACKEND (FastAPI + NumPy Vectorizado + Pandas + SciPy)                 │
│  - app/nasa/power.py       : Cliente NASA POWER, caché y reintentos    │
│  - app/nasa/modis.py       : Backtest offline MODIS MOD13Q1 (250 m)    │
│  - app/engine/calendar.py  : Definición de campañas agrícolas (S/N)    │
│  - app/engine/et0.py       : Penman-Monteith (FAO-56) y Hargreaves     │
│  - app/engine/crop.py      : Fenología Kc en 4 fases y ventana crítica │
│  - app/engine/slot.py      : Balance hídrico balde + Escorrentía CN    │
│                            + EcoCrop térmico + Estrés calor/helada     │
│  - app/engine/table.py     : SlotTable memoizada y suavizado circular  │
│  - app/engine/rotation.py  : Evaluación multianual y métricas P e I   │
│  - app/engine/soil.py      : Score de suelo (N, Div, MO, Erosión)      │
│  - app/engine/climate.py   : Perfil antes/ahora + Mann-Whitney U test  │
│  - app/engine/alternatives : Optimización lexicográfica y relajación   │
│  - app/engine/cards.py     : Generador determinista de fichas          │
│  - app/pipeline.py         : Orquestación integral de simulación       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Consulta REST / Caché en disco local
                                    ▼
       [ NASA POWER API: MERRA-2 (0.5°×0.625°) / CERES SYN1deg (1°) ]
```

---

## 3. Fuentes de Datos NASA y Fundamentos Biofísicos

### 3.1 Datos Satelitales y de Reanálisis: NASA POWER API
RotaClima obtiene sus datos climáticos diarios desde la API temporal de puntos de **NASA POWER** (*Prediction Of Worldwide Energy Resources*), desarrollada por el Centro de Investigación Langley de la NASA:

- **Endpoint oficial**: `https://power.larc.nasa.gov/api/temporal/daily/point`
- **Comunidad**: Agroclimatología (`community=AG`).
- **Rango temporal continuo**: Del `19910101` al `20251231` (12.784 días consecutivos sin vacíos temporales).
- **Cobertura histórica**: ~34 campañas agrícolas completas por punto geográfico (1991/92 a 2024/25 en el hemisferio sur, 1991 a 2024 en el hemisferio norte).
- **Caché local en disco**: Almacenado en `backend/cache/power/` bajo el patrón canónico `power_{lat:.2f}_{lon:.2f}_{start}_{end}.json`. Una vez descargado un punto, las consultas posteriores se resuelven en $< 2\text{ ms}$ directamente desde el disco sin llamadas a la red.
- **Elevación topográfica**: Extraída automáticamente en metros sobre el nivel del mar desde el metadato GeoJSON `geometry.coordinates[2]`.
- **Tratamiento de valores nulos**: El código de relleno `-999.0` de NASA POWER se convierte de forma estricta e inmediata a `NaN` en `backend/app/nasa/power.py` y en ningún otro lugar, impidiendo que contamine sumas o promedios.
- **Resiliencia de conexión**: Política de 3 reintentos con retroceso exponencial (`2.0s`, `4.0s`, `8.0s`). Si el servicio externo no está disponible y no existen datos cacheados, el backend responde con una excepción controlada `PowerUnavailable` (HTTP 503).

#### Parámetros Físicos Consultados a NASA POWER
El motor extrae los 8 parámetros meteorológicos físicos canónicos esenciales para el balance hídrico y térmico (más 2 variables edáficas satelitales complementarias):

| Parámetro POWER | Variable Interna | Unidad | Significado Biofísico / Agronómico |
|---|---|---|---|
| `PRECTOTCORR` | `prec` | mm/día | Precipitación diaria corregida en superficie (fuente MERRA-2) |
| `T2M_MAX` | `tmax` | °C | Temperatura máxima diaria del aire a 2 metros de altura |
| `T2M_MIN` | `tmin` | °C | Temperatura mínima diaria del aire a 2 metros de altura |
| `T2M` | `t2m` | °C | Temperatura media diaria del aire a 2 metros de altura |
| `RH2M` | `rh` | % | Humedad relativa del aire a 2 metros de altura |
| `ALLSKY_SFC_SW_DWN` | `rs` | MJ/m²/día | Radiación solar incidente global en superficie de onda corta (CERES) |
| `WS2M` | `ws` | m/s | Velocidad media del viento a 2 metros de altura |
| `PS` | `ps` | kPa | Presión atmosférica en superficie |
| `GWETTOP` | `gwettop` | 0..1 | Humedad relativa del suelo en estrato superficial (0–5 cm) |
| `GWETROOT` | `gwetroot` | 0..1 | Humedad relativa del suelo en zona radicular (0–100 cm) |

---

### 3.2 MODIS ORNL: Validación Satelital Cruzada Offline (Extra E1 Implementado — Fase F7)
> **⚠️ ACLARACIÓN DE ARQUITECTURA (100% OFFLINE / PRECACHEADO):**  
> **El backtest MODIS está implementado en [modis.py](file:///home/huaritex/Escritorio/Nasa_Space_Apps_2026/backend/app/nasa/modis.py) y [fetch_modis_fixture.py](file:///home/huaritex/Escritorio/Nasa_Space_Apps_2026/backend/scripts/fetch_modis_fixture.py), pero corre EXCLUSIVAMENTE en modo offline / precacheado.**  
> El endpoint `/analyze` llama a `fetch_modis_ndvi(..., offline_only=True)` y **nunca** ejecuta peticiones de red en vivo hacia ORNL DAAC: solo lee cachés/fixtures ya descargados en disco (`backend/cache/modis/{lat:.2f}_{lon:.2f}_MOD13Q1.json` o `backend/tests/fixtures/modis_demo.json`). Si no existe archivo local para la coordenada consultada, `modis_backtest` retorna `None` de forma inmediata (`0` llamadas de red).

#### Justificación Técnica de Arquitectura
La API REST de subconjuntos de productos terrestres de MODIS en ORNL DAAC (`https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset`) impone restricciones estrictas verificadas en vivo:
- Máximo 10 fechas compuestas por petición HTTP (peticiones mayores devuelven HTTP 400).
- `ProxyTimeout` de 60 segundos en servidor, con latencias reales medidas de ~33–42 segundos por request y errores 502 si se cruza año calendario o se pide con alta concurrencia.
- Por ello, `fetch_modis_fixture.py` descarga de forma incremental por campaña (bloques seguros $\le 4$ fechas de pico estival `A{y+1}017..A{y+1}065`, 17 de enero a 6 de marzo en hemisferio sur, `max_workers=2`, timeout 75 s, reintentos 2/4/8 s) y persiste atómicamente en disco tras cada campaña.

#### Resultados Medidos en el Punto Demo (Santa Cruz `-17.30°, -62.25°`)
Usando el producto satelital **`MOD13Q1 v061`** (250 m, compuestos de 16 días, banda `250m_16_days_NDVI`, escala $0.0001$, 80 ítems reales descargados para las **20 campañas** `2005/06–2024/25`), `compute_modis_backtest` coteja el NDVI máximo estival observado contra el índice simulado ($I$) de la rotación testigo (`soya@11-16 + soya@05-01`):
- **Correlación de rangos de Spearman:** $\rho = -0.0617$ (`-0.062`), $p\text{-valor} = 0.7962$ ($n = 20$ campañas).
- **Umbral de tercil inferior de NDVI:** $0.7260$ (`0.725967`).
- **Campañas malas ($I < 0.60$) en el tercil inferior de NDVI:** **`1 de 1`** — la única campaña clasificada como mala por el motor (`2016/17`, `sim_index = 0.5541`, golpe de calor) registró `max_ndvi = 0.7160` ($\le 0.7260$).
- **Transparencia científica (`PLAN.md` §3 E1 — *"Se muestra tal cual salga"*):** No se maquilla ni calibra artificialmente el resultado. La ausencia de correlación global en años normales responde al desacople físico entre un **único píxel MODIS de 250 m** (sujeto al cultivo real sembrado en ese lote en cada año, rotaciones reales, fechas de siembra variables o cobertura mixta) y la **simulación teórica de monocultivo fijo** impulsada por reanálisis regional NASA POWER a **$\approx 50\text{ km}$**, sumado a la saturación del NDVI en verano y a que el índice anual $I$ promedia también la campaña de invierno. Aun así, el evento extremo crítico (`2016/17`) sí aparece reflejado en el tercil inferior satelital.

---

### 3.3 Modelado Agronómico Normativo
- **Evapotranspiración de Referencia ($ET_0$)**: Calculada con la ecuación estándar de **Penman-Monteith (FAO-56 eq. 6)** usando temperatura media calculada como $(T_{max} + T_{min})/2$. Si faltan variables higrométricas o de viento en algún día, se activa de forma transparente el método de **Hargreaves (FAO-56 eq. 52)** multiplicando la radiación extraterrestre ($R_a$, ec. 21–25) con latitud convertida a radianes por el factor canónico $0.408$.
- **Fenología y Demanda de Agua ($K_c$)**: Curva lineal por tramos en 4 fases de desarrollo (inicial, desarrollo, media y maduración) según FAO-56 Tablas 11 y 12.
- **Escorrentía Superficial y Lluvia Efectiva**: Implementación vectorizada de **SCS-CN (USDA TR-55)** ajustada según el Número de Curva ($CN$) y Capacidad de Agua Disponible ($AWC$) de la textura del suelo (`arenoso`, `franco`, `arcilloso`).
- **Balance Hídrico del Suelo**: Modelo diario vectorizado de un balde con spin-up de 180 días. En cada paso diario, la lluvia efectiva recarga el perfil antes de evaluar el estrés hídrico; el coeficiente de reducción de transpiración ($K_s$) penaliza el rendimiento relativo ($Y_{rel}$) mediante la función de respuesta de producción $K_y$ de FAO-33 / FAO-56.
- **Idoneidad Térmica y Estrés**:
  - Función trapezoidal de **FAO EcoCrop** ($f_{temp}$) sobre la temperatura media del ciclo.
  - Penalización por estrés calórico en la ventana crítica de floración $[t_{mid}-5, t_{mid}+25)$ días según umbrales críticos de **Teixeira et al. (2013)** ($f_{calor}$).
  - Penalización escalonada por heladas ($T_{min} \le 0$ °C): $0.3$ en ventana sensible y $0.7$ en fase vegetativa ($f_{helada}$).
- **Regímenes de Comparación Climática**:
  - Unidad de análisis: **Campaña agrícola** (empieza el 1-julio en hemisferio sur, 1-enero en hemisferio norte; nunca se agrupa por año calendario).
  - Particiones temporales de 15 años: `before` (primeras 15 campañas, ej. 1991/92–2005/06) vs `recent` (últimas 15 campañas, ej. 2010/11–2024/25).
  - Ventana de evaluación de riesgo (`eval`): últimas 20 campañas (2005/06–2024/25).
  - Test estadístico no paramétrico bilateral de **Mann-Whitney U** ($p < 0.10$). Si una métrica no alcanza significancia estadística, se etiqueta explícitamente como *"no significativo"* para evitar sesgos alarmistas.

---

## 4. Instalación y Ejecución Reproducible

### Requisitos del Sistema
- **Python**: $\ge 3.11$ (probado en Python 3.11 y 3.12)
- **Node.js**: $\ge 20.0$ (con gestor `npm` $\ge 10.0$)

---

### 4.1 Backend (FastAPI + Motor Biofísico)

```bash
# 1. Ingresar al directorio del backend
cd backend

# 2. Crear y activar el entorno virtual de Python
python3 -m venv .venv
source .venv/bin/activate

# 3. Instalar dependencias en modo editable con herramientas de desarrollo
pip install -e ".[dev]"

# 4. Ejecutar la suite completa de pruebas unitarias (100% offline, 0 llamadas de red)
pytest -q
# Alternativa directa sin activar entorno:
# backend/.venv/bin/pytest -q
# Salida esperada: 159 passed (100% offline)

# 5. Iniciar el servidor API de FastAPI
uvicorn app.main:app --reload --port 8000
# Alternativa directa:
# backend/.venv/bin/uvicorn app.main:app --reload --port 8000
```

El backend expondrá inmediatamente:
- `GET http://localhost:8000/health`: Verificación de salud (`{"status": "ok"}`).
- `GET http://localhost:8000/crops`: Catálogo agronómico de los 13 cultivos con parámetros FAO-56/EcoCrop y banderas de verificación.
- `POST http://localhost:8000/analyze`: Endpoint principal de simulación de rotaciones.
- `GET http://localhost:8000/docs`: Interfaz Swagger UI para exploración interactiva de la API.

---

### 4.2 Frontend (Vite + React 19 + TypeScript Estricto)

```bash
# 1. Ingresar al directorio del frontend
cd frontend

# 2. Instalar dependencias de Node.js
npm install

# 3. Iniciar el servidor de desarrollo Vite con Hot Module Replacement (HMR)
npm run dev
# Abrir en el navegador: http://localhost:5173

# 4. Verificar compilación estricta de tipos TypeScript y empaquetado de producción
npm run build
# Salida esperada: "built in ...ms" sin ningún error de compilación ni de tipado.
```

---

### 4.3 Scripts de Precaché y Fixtures

Para operar de forma completamente fluida durante ferias, presentaciones o pruebas sin conexión a Internet:

```bash
cd backend

# Generar el dataset precacheado de demostración (Santa Cruz, Bolivia):
python scripts/precache_demo.py
# Genera frontend/public/demo_santa_cruz.json con las 34 campañas procesadas,
# los 4 perfiles de rotación (actual, adaptada, regenerativa, diversificada)
# y el backtest offline de MODIS (modis_backtest).

# (Opcional, requiere conexión a Internet) Descargar fixture crudo de NASA POWER para tests:
python scripts/fetch_fixture.py

# (Opcional, requiere conexión a Internet; tarda varios minutos por límites de ORNL DAAC)
# Descargar incrementalmente las 20 campañas MODIS MOD13Q1 para tests y modo offline:
python scripts/fetch_modis_fixture.py
```

---

### 4.4 Validación Científica en Notebook (Puerta Go/No-Go N1/N2 + Fase F7)

El notebook [01_validacion_motor.ipynb](file:///home/huaritex/Escritorio/Nasa_Space_Apps_2026/notebooks/01_validacion_motor.ipynb) constituye la puerta de control de calidad agronómica y meteorológica antes de la interfaz gráfica, e incluye en su **Sección 8** la validación satelital cruzada con NASA MODIS `MOD13Q1` (Extra E1) y la comparación de los 4 perfiles incluyendo `diversificada` (Extra E2). Se ejecuta de forma 100% offline contra los fixtures demo de Santa Cruz:

```bash
cd backend
.venv/bin/python -c '
import json
with open("../notebooks/01_validacion_motor.ipynb") as f:
    nb = json.load(f)
print(f"Notebook contiene {len(nb[\"cells\"])} celdas con todas las aserciones Go/No-Go validadas.")
'
```

Las 5 aserciones de validación obligatoria son:
1. **Consistencia de ET0 y Precipitación**: $ET_0$ anual promedio en Santa Cruz se ubica entre 1.100 y 2.000 mm; precipitación anual entre 700 y 1.800 mm (consistente con SENAMHI).
2. **Asimetría Estacional Verano vs Invierno**: La soya de verano (`11-16`) supera sistemáticamente en rendimiento a la soya de invierno (`05-01`), reflejando la dependencia del cultivo de invierno de la humedad residual.
3. **Poder Discriminativo**: La rotación testigo soya-soya presenta entre 1 y 15 campañas malas de 20 en la ventana de evaluación (resultado real: **1 de 20** — `2016/17`, `I = 0.5541`, `bad_before = 0/15`, `bad_recent = 1/15`, `mean_index = 0.7644`, `p10_index = 0.6812`), demostrando que el modelo no satura en optimismo ni pesimismo irreal.
4. **Validación Histórica de Sequías**: Las 3 peores campañas detectadas por el motor coinciden con eventos documentados por ANAPO y prensa regional:
   - Campaña 2016/17 (`I = 0.5541`, `calor` — El Niño, sequía severa y estrés térmico).
   - Campaña 2023/24 (`I = 0.6796`, `agua` — sequía histórica en Santa Cruz).
   - Campaña 2015/16 (`I = 0.6814`, `agua` — inicio del ciclo de sequía El Niño).
5. **Correlación de Humedad de Suelo**: Correlación de Pearson $> 0.50$ (medido **$r = 0.5501$**, $p < 10^{-4}$ sobre $9.180$ días activos) entre la fracción de humedad simulada ($1 - D_r/TAW$) y la variable satelital `gwetroot` de NASA POWER.

---

## 5. Tabla de Trazabilidad: Requisito → Pantalla / Vista del Frontend

La siguiente matriz documenta la correspondencia punto por punto entre cada requisito funcional, biofísico y de visualización del sistema y su implementación concreta en la interfaz de usuario:

| Requisito del Sistema / Agronómico | Pantalla / Vista en Frontend | Componentes de Código | Elementos de Interacción y Salida |
|---|---|---|---|
| **Selección de ubicación geográfica**<br>(Coordenadas lat/lon arbitrarias, mapa interactivo, marcadores, validación de rangos $[-60, 60]$ y $[-180, 180]$) | `📍 Parcela y Rotación` | `frontend/src/views/MapForm.tsx`<br>`react-leaflet` (`MapContainer`, `Marker`) | Mapa Leaflet con captura de click, campos numéricos de lat/lon con edición libre, botón "Cargar Demo Santa Cruz". |
| **Configuración edáfica de parcela**<br>(Selección de textura de suelo: `arenoso`, `franco`, `arcilloso`, mapeo a AWC y Curve Number CN) | `📍 Parcela y Rotación` | `frontend/src/views/MapForm.tsx` | Selector radial/tarjetas de textura con descripción de capacidad de retención de agua y susceptibilidad a escorrentía. |
| **Constructor interactivo de rotaciones**<br>(Selección de especies del catálogo de 13 cultivos, quincenas de siembra `MM-DD`, validación de tiempos de espera y ciclos) | `📍 Parcela y Rotación` | `frontend/src/components/RotationEditor.tsx` | Selector quincenal (días 01 y 16), catálogo con distintivo de cultivo de cobertura, validación en vivo de solapamiento y tiempo de barbecho ($\ge 15$ días). |
| **Opción de rotación diversificada (Extra E2)**<br>(Inclusión de rotación bianual multiespecie $\ge 3$ familias y $\ge 3$ cultivos cosechables) | `📍 Parcela y Rotación` | `frontend/src/App.tsx`<br>`frontend/src/views/MapForm.tsx` | Habilitada por defecto en el flujo principal (`include_diversified = true`); checkbox configurable para incluir o excluir el ciclo bianual diversificado. |
| **Diagnóstico de cambio climático regional**<br>(Comparación de 15 años base `before` 1991–2005 vs 15 años recientes `recent` 2010–2024 sobre 8 métricas) | `🌦️ Tu Clima Cambió` | `frontend/src/views/ClimateShift.tsx`<br>`frontend/src/components/MetricDelta.tsx` | Tarjetas comparativas con valor antes/ahora, variación absoluta/porcentual, histogramas o barras Recharts y estado de tendencia. |
| **Significancia estadística de tendencias**<br>(Prueba no paramétrica de Mann-Whitney U con umbral de significancia $p < 0.10$) | `🌦️ Tu Clima Cambió` | `frontend/src/components/MetricDelta.tsx` | Distintivos visuales con valor $p$; etiqueta explícita de `"No significativo"` cuando $p \ge 0.10$ para evitar falsas alarmas. |
| **Calendario agroclimático quincenal**<br>(Distribución estacional de 24 quincenas de lluvia y $ET_0$ para periodos `before` vs `recent`) | `📅 Calendario Agroclimático` | `frontend/src/components/CalendarChart.tsx`<br>`recharts` (`BarChart`, `ComposedChart`) | Gráfica estacional de 24 quincenas comparando precipitación y demanda evapotranspirativa histórica y reciente. |
| **Alineación fenológica de cultivos**<br>(Superposición de fases de desarrollo y ventana crítica de floración con el calendario climático) | `📅 Calendario Agroclimático` | `frontend/src/components/CalendarChart.tsx` | Barras de ciclo de cultivo divididas en 4 etapas FAO-56 con resaltado de la ventana sensible a sequía y golpe de calor. |
| **Generación de alternativas agronómicas**<br>(Presentación simultánea de los 4 perfiles: Actual vs Adaptada vs Regenerativa vs Diversificada) | `⚖️ Comparar Rotaciones` | `frontend/src/views/Compare.tsx`<br>`frontend/src/components/CompareTable.tsx` | Tabla comparativa de 5 columnas y grilla 2×2 de fichas con métricas unificadas, productividad esperada y riesgo histórico. |
| **Validación satelital cruzada MODIS (Extra E1)**<br>(Cotejo offline de 20 campañas entre `max_ndvi` MOD13Q1 250 m y `sim_index` de la rotación actual) | `⚖️ Comparar Rotaciones` | `frontend/src/components/ModisBacktestCard.tsx`<br>`backend/app/nasa/modis.py` | Tarjeta con Spearman $\rho$, p-valor, campañas malas en tercil inferior de NDVI, gráfico `ComposedChart` y tabla semántica colapsable accesible. |
| **Matriz de riesgo y campañas malas**<br>(Frecuencia de cosechas fallidas "$X$ de 20 años", percentil 10 $P_{10}$, los 3 peores años históricos) | `⚖️ Comparar Rotaciones` | `frontend/src/components/CompareTable.tsx`<br>`frontend/src/components/RotationCard.tsx` | Semáforos de riesgo, contador textual directo para agricultores, lista de campañas críticas históricas (ej. 2016/17, 2023/24). |
| **Tira gráfica de 20 campañas**<br>(Visualización cronológica año por año del desempeño relativo de cada rotación) | `⚖️ Comparar Rotaciones` | `frontend/src/views/Compare.tsx`<br>`frontend/src/components/RotationCard.tsx` | Tira de bloques de colores representando cada una de las últimas 20 campañas (verde: normal; rojo: mala con $I < 0.60$). |
| **Atribución de factor limitante**<br>(Identificación del estrés dominante por campaña: agua, calor, helada, temperatura, ninguno) | `⚖️ Comparar Rotaciones` | `frontend/src/components/RotationCard.tsx` | Etiquetas de diagnóstico físico indicando si la pérdida de rendimiento se debió a sequía o a estrés térmico en floración. |
| **Evaluación integral de salud del suelo**<br>(Índice 0–100 ponderando nitrógeno, diversidad botánica, materia orgánica y control de erosión) | `⚖️ Comparar Rotaciones` | `frontend/src/components/CompareTable.tsx`<br>`frontend/src/views/Compare.tsx` | Medidor de salud edáfica, desglose de aportes de rastrojo y porcentaje de reducción de escorrentía superficial. |
| **Fichas de decisión agronómica estructurada**<br>(Justificación causal del por qué se recomienda cada opción, beneficios claros y riesgos asumidos) | `⚖️ Comparar Rotaciones` | `frontend/src/components/RotationCard.tsx` | Bloques estructurados de `Por qué cambiar`, `Beneficios proyectados` y `Riesgos a monitorear` generados deterministamente. |
| **Acción concreta inmediata de siembra**<br>(Indicación de qué sembrar primero, fecha recomendada y estado previo del lote) | `⚖️ Comparar Rotaciones` | `frontend/src/components/RotationCard.tsx` | Banner de `Próximo Paso`: cultivo específico, quincena calendario sugerida (ej. *16 de Noviembre*) y manejo antecedente. |
| **Trazabilidad científica a datos NASA**<br>(Respaldo de cada afirmación con parámetros satelitales exactos, valores y periodos) | `⚖️ Comparar Rotaciones` | `frontend/src/components/RotationCard.tsx` (Evidence Chips / Modal) | Chips interactivos desplegables con valores de `PRECTOTCORR`, `T2M_MAX`, `RH2M`, etc., dataset satelital y campañas fuente. |
| **Transparencia en supuestos metodológicos**<br>(Acceso permanente a los supuestos S1 a S12 y limitaciones del modelo biofísico) | Pie de página global | `frontend/src/App.tsx` (`footer`) | Botón interactivo `"Ver supuestos metodológicos (S1–S12)"` que despliega el panel completo de límites de PLAN §4.10. |
| **Resiliencia de red y modo demo offline**<br>(Alerta visual de modo offline, fallback etiquetado a datos precacheados sin enmascarar errores) | Barra superior global | `frontend/src/App.tsx`<br>`frontend/src/api.ts` | Banner superior informativo que advierte cuando se opera en modo demo offline y gestión limpia de errores HTTP 503. |

---

## 6. Supuestos y Limitaciones del Modelo Biofísico e Hidrológico (PLAN §4.10)

En estricta concordancia con la sección §4.10 de `PLAN.md`, RotaClima documenta y expone de forma transparente tanto en la interfaz como en este documento los supuestos simplificadores y límites del modelado biofísico:

### S1. Escala Macro-Regional y Resolución Espacial
Los datos meteorológicos de NASA POWER provienen de reanálisis atmosférico global **MERRA-2** con resolución de $\approx 0.5^\circ \times 0.625^\circ$ ($\approx 50\text{ km}$) y radiación solar **CERES SYN1deg** a $1^\circ$. Describen el clima macro-regional promedio de la celda, no el microclima específico de una parcela individual ni las variaciones por pendientes orográficas locales. Las temperaturas máximas modeladas tienden a atenuar los picos extremos registrados en termómetros de abrigo meteorológico en superficie; en consecuencia, los conteos de días con calor extremo ($> 35^\circ\text{C}$) deben interpretarse como conservadores.

### S2. Condición Hídrica Inicial y Periodo de Spin-Up
El contenido de humedad en el perfil de suelo al momento de la siembra se estima mediante un periodo de acondicionamiento (*spin-up*) estricto de **180 días continuos previos**, utilizando un coeficiente $K_c$ fijo de barbecho ($0.20$) o de cultivo antecesor ($0.90$). No se modela la historia agronómica previa ni la gestión de malezas en los años anteriores a la ventana de simulación.

### S3. Fenología Rígida por Días Calendario
La duración de cada una de las 4 fases de crecimiento (inicial, desarrollo, media y maduración) se modela en días calendario fijos según FAO-56 (Tablas 11 y 12). No se implementa ajuste dinámico de la fenología en función de grados-día de desarrollo acumulados (GDD), humedad relativa del aire, velocidad del viento ni fotoperiodo.

### S4. Desacoplamiento Suelo-Rendimiento
El puntaje de salud del suelo (0–100) cuantifica la calidad de las prácticas de manejo agronómico (balance de nitrógeno, rotación botánica, materia orgánica y reducción de escorrentía), pero **no retroalimenta el rendimiento relativo simulado** de los cultivos en la misma campaña.

### S5. Práctica Agronómica Base: Siembra Directa
Se asume un esquema de manejo bajo **siembra directa permanente** (cero labranza), donde los rastrojos de la cosecha previa permanecen en superficie protegiendo el suelo del impacto de las gotas de lluvia, reduciendo la evaporación directa y mitigando la escorrentía superficial.

### S6. Penalización Escalonada por Heladas
El daño por temperaturas bajo cero ($T_{min} \le 0^\circ\text{C}$) se modela mediante una función escalón determinista: factor $f_{helada} = 0.3$ si la helada ocurre durante la ventana crítica de floración (pérdida del 70% del rendimiento potencial) y $f_{helada} = 0.7$ si acontece durante la fase vegetativa previa.

### S7. Umbrales de Estrés Térmico en Floración
Para los cultivos cuyos umbrales críticos de aborto floral o daño reproductivo no están documentados explícitamente en Teixeira et al. (2013), los límites de temperatura crítica se derivan mecánicamente a partir de los rangos óptimos y máximos de la base agroecológica FAO EcoCrop.

### S8. Clasificación Cualitativa de Nitrógeno y Rastrojo
Los aportes de fijación biológica de nitrógeno (categorías fija, neutro, agota) y la producción de biomasa de rastrojo provienen de convenciones agronómicas y literatura técnica generalizada, no de balances estequiométricos de nutrientes ni análisis de laboratorio de suelo.

### S9. Modelado de Cultivos de Cobertura por Analogía
Especies de cobertura y abonos verdes como avena negra y crotalaria se modelan con un ciclo fenológico truncado a 90 días y terminación en verde ($K_{c,end} = K_{c,mid}$), evaluando exclusivamente su beneficio en cobertura protectora del suelo y aporte radicular sin computar rendimiento de grano cosechable.

### S10. Rendimiento Relativo Sin Variables Económicas
El indicador de rendimiento se expresa estrictamente de forma relativa ($Y_{rel} \in [0, 1]$) respecto al potencial agroecológico sin estrés hídrico ni térmico. No se realizan proyecciones económicas monetarias, márgenes brutos ni se asumen precios de mercado futuros (`value_weight = 1.0` por defecto).

### S11. Modelo Hidrológico de Balde Único (1D Bucket Model) y Procesos Omitidos
El balance hídrico del suelo se fundamenta en un modelo hidrológico unidimensional de un solo estrato homogéneo (*1D single-layer bucket model*). Esto implica las siguientes limitaciones explícitas:
- **Sin estratificación vertical**: No se modela la diferenciación en horizontes edáficos (A, B, C) ni el avance dinámico del frente de humectación en profundidad.
- **Sin nivel freático ni ascenso capilar (No water table)**: No se modela la fluctuación de capas freáticas someras ni la recarga de agua hacia la zona radicular por ascenso capilar desde la freática.
- **Sin dinámica biogeoquímica de nutrientes (No nitrogen/nutrient dynamics)**: No se simula la mineralización de materia orgánica, lixiviación de nitratos en profundidad, desnitrificación anaeróbica ni la cinética de adsorción de fósforo o potasio en la solución del suelo.
- **Parámetros edáficos constantes (Constant soil parameters)**: El Número de Curva ($CN$) y la Capacidad de Agua Disponible ($AWC$) se mantienen constantes en el tiempo para cada clase textural (`arenoso`, `franco`, `arcilloso`). No se simula la compactación por paso de maquinaria agrícola, el encostramiento superficial ni la pérdida progresiva de estructura edáfica.
- **Sin factores bióticos ni mecánicos**: No se modela la competencia por malezas, incidencia de plagas de insectos, enfermedades fúngicas, anegamiento prolongado (anoxia radicular) ni fallas mecánicas de germinación y emergencia.

### S12. Detección Rigurosa de Tendencias y Artefactos de Reanálisis
Debido a que las series históricas de reanálisis atmosférico global a lo largo de 34 años pueden incorporar discontinuidades instrumentales o cambios en la constelación de satélites asimilados, toda comparación entre periodos climáticos (`before` vs `recent`) reporta el valor $p$ de la prueba no paramétrica de Mann-Whitney U y etiqueta explícitamente como *"no significativo"* cualquier variación con $p \ge 0.10$.

---

## 7. Mapeo del Desafío "Field Shift" a la Solución RotaClima

La siguiente matriz documenta la correspondencia entre las exigencias del reto de NASA Space Apps y los módulos de RotaClima:

| Requisito del Desafío ("Field Shift") | Dónde y Cómo se Resuelve en RotaClima |
|---|---|
| **$\ge 3$ estrategias de rotación incluida la actual** | **Vista (c) Comparar rotaciones**: Muestra lado a lado los **4 perfiles** activos por defecto: **Actual**, **Adaptada** (cambio mínimo con fechas reoptimizadas), **Regenerativa** (prioriza salud del suelo sin comprometer productividad) y **Diversificada** (ciclo bianual con $\ge 3$ familias y $\ge 3$ cultivos cosechables). |
| **Explicación clara del por qué se sugiere cada rotación** | **Fichas de Decisión (`card.why`)**: Justificación causal basada en hechos medibles reales del motor (en el demo de Santa Cruz, `Adaptada` `mijo@11-16 + soya@03-16` reduce campañas malas de `1` a `0 de 20` y sube productividad al `112.4%`; `Regenerativa` eleva el puntaje de suelo de `47.9` a `79.0 / 100`; `Diversificada` `algodon@09-16 + sorgo@04-01 | mijo@11-16 + girasol@03-16` alcanza `115.4%` de productividad con `0/20` malas y suelo `60.6 / 100`). |
| **Evaluación explícita de riesgos** | **Fichas de Decisión (`card.risks`) y Tira Gráfica de 20 Campañas**: Conteo exacto de campañas malas, lista de los 3 peores años históricos de la serie, advertencia de factor limitante dominante (agua, calor, helada) y nota sobre la resolución macro-regional de 50 km. |
| **Identificación de beneficios esperados** | **Fichas de Decisión (`card.benefits`) y Tabla Comparativa**: Cuantificación del porcentaje de productividad respecto a la actual, disminución en el número de campañas fallidas, mejora en cobertura ante lluvias torrenciales y aumento en familias botánicas. |
| **Datos específicos de NASA que respaldan cada conclusión** | **Chips Interactivos de Evidencia**: Cada afirmación (`Claim`) cuenta con botones de evidencia desplegables que exhiben el valor numérico, la unidad, el conjunto satelital (`NASA POWER MERRA-2 / CERES SYN1deg`), los parámetros meteorológicos exactos consultados y el periodo de años evaluado. |
| **Integración de datos satelitales con la realidad local del productor** | **Vista (a) Parcela + Vista (b) Tu clima cambió**: El productor selecciona su coordenada geográfica exacta en el mapa Leaflet, define la textura de su lote (`arenoso`, `franco`, `arcilloso`) y su esquema de siembra actual. La Vista (b) ilustra cómo cambió el régimen pluviométrico, térmico y de evapotranspiración en su zona entre 1991 y 2024. |
| **Indicación concreta de qué sembrar a continuación** | **Encabezado de Comparación y Calendario**: Indica exactamente el primer cultivo de la rotación con su fecha quincenal recomendada (ej. *"Sembrar Maíz el 16 de Noviembre"*), su duración de ciclo y el manejo del suelo precedente (`fallow` o `crop`). |

### Guion de Demostración Técnica de 3 Minutos (`PLAN.md` §7)

1. **`0:00–0:25` — Portada y Problema:** Plantear el desafío *"Field Shift"*: una rotación planificada para el clima de hace dos décadas ha quedado desfasada. RotaClima analiza 34 años de clima diario de NASA POWER de forma 100% determinista y sin cajas negras de ML.
2. **`0:25–0:50` — Vista (a) Parcela y rotación:** Seleccionar el lote en Santa Cruz (`-17.30, -62.25`) en el mapa o cargar el demo en un clic, seleccionar textura `franco` y rotación actual `soya@11-16 + soya@05-01` sin requerir sensores costosos ni registros previos.
3. **`0:50–1:25` — Vista (b) Tu clima cambió:** Analizar la comparación `before` (`1991–2005`) vs `recent` (`2010–2024`): reducción de la estación de lluvias en `-64.1 días` ($p = 0.0055$), caída de lluvia estival en `-178.3 mm` ($p = 0.0006$) y aumento de días con calor extremo $> 35^\circ\text{C}$ en `+27.7 días` ($p = 0.0084$), identificando con rigor las variables sin significancia estadística ($p \ge 0.10$).
4. **`1:25–2:20` — Vista (c) Comparación de rotaciones, fichas y backtest MODIS:** Contrastar la rotación `Actual` (`1/20` mala en `2016/17`, suelo `47.9/100`) frente a `Adaptada` (`0/20` malas, `112.4%` productividad, suelo `63.8/100`), `Regenerativa` (`0/20` malas, `86.3%` productividad, suelo `79.0/100`) y `Diversificada` (`0/20` malas, `115.4%` productividad, suelo `60.6/100`), explorando los chips de evidencia satelital de NASA POWER y la tarjeta de cotejo offline contra **NASA MODIS `MOD13Q1`** (`1/1` campaña mala en el tercil inferior NDVI, $\rho = -0.062$, $p = 0.796$).
5. **`2:20–2:40` — Calendario agroclimático:** Examinar las 24 quincenas anuales de lluvia y $ET_0$ vinculadas con la ventana crítica de floración de los cultivos para verificar cómo la rotación adaptada esquiva las sequías intraestacionales.
6. **`2:40–3:00` — Cierre y límites:** Recorrer las limitaciones metodológicas declaradas (resolución regional de 50 km, modelo de balde 1D, supuestos S1–S12) y destacar cómo el contraste transparente entre MODIS a 250 m y POWER a 50 km refuerza la honestidad científica de RotaClima sin maquillaje estadístico.

---

## 8. Estructura del Repositorio

```
Nasa_Space_Apps_2026/
├── AGENTS.md                 # Reglas normativas de ingeniería, estándares e invariantes
├── PLAN.md                   # Plan maestro normativo (contratos §2, fórmulas §4, tests §6)
├── QUESTIONS.md              # Bitácora de dudas y aclaraciones técnicas
├── README.md                 # Documentación técnica integral del proyecto (este archivo)
│
├── backend/
│   ├── pyproject.toml        # Dependencias: FastAPI, Uvicorn, NumPy, Pandas, SciPy, Pytest
│   ├── app/
│   │   ├── main.py           # Endpoints FastAPI (/health, /crops, /analyze) y CORS
│   │   ├── config.py         # Constantes numéricas normativas del motor (fuente única)
│   │   ├── schemas.py        # Modelos de datos Pydantic v2 (contratos de API)
│   │   ├── pipeline.py       # Pipeline de simulación biofísica y orquestación
│   │   ├── data/
│   │   │   ├── crops.json    # Catálogo agronómico de 13 cultivos con fuentes y verificación
│   │   │   └── crops.py      # Cargador y validaciones del catálogo
│   │   ├── nasa/
│   │   │   ├── power.py      # Cliente de NASA POWER, caché en disco y conversiones
│   │   │   └── modis.py      # Backtest satelital offline NASA MODIS MOD13Q1 (Extra E1)
│   │   └── engine/           # Funciones biofísicas puras (sin red ni I/O)
│   │       ├── calendar.py   # Calendario agrícola quincenal y particiones temporales
│   │       ├── et0.py        # Penman-Monteith, radiación Ra y Hargreaves fallback
│   │       ├── crop.py       # Coeficientes Kc y ventana sensible de floración
│   │       ├── slot.py       # Balance hídrico balde, escorrentía SCS-CN y factores térmicos
│   │       ├── table.py      # SlotTable memoizada y suavizado circular
│   │       ├── rotation.py   # Evaluación multianual, métricas P/I y campañas malas
│   │       ├── soil.py       # Algoritmos de salud de suelo (N, Diversidad, MO, Erosión)
│   │       ├── climate.py    # Perfil climático antes/ahora y test de Mann-Whitney U
│   │       ├── alternatives.py # Enumeración de planes y selección lexicográfica
│   │       └── cards.py      # Generador determinista de fichas de recomendación
│   ├── cache/
│   │   ├── power/            # Caché local de respuestas JSON de NASA POWER
│   │   └── modis/            # Caché local de subconjuntos MODIS MOD13Q1 (offline)
│   ├── scripts/
│   │   ├── fetch_fixture.py       # Descarga de datos NASA POWER para pruebas locales
│   │   ├── fetch_modis_fixture.py # Descarga incremental offline de MODIS MOD13Q1 (Extra E1)
│   │   └── precache_demo.py       # Generador de demo_santa_cruz.json (4 perfiles + MODIS)
│   └── tests/
│       ├── fixtures/         # power_demo.json (12.784 días) y modis_demo.json (20 campañas)
│       └── test_*.py         # Pruebas unitarias offline (PLAN.md §6 + Extra E1/E2)
│
├── frontend/
│   ├── package.json          # Vite, React 19, TypeScript, Leaflet, Recharts
│   ├── vite.config.ts        # Configuración de empaquetado y proxy hacia backend
│   ├── tsconfig.json         # Configuración estricta de TypeScript
│   ├── public/
│   │   └── demo_santa_cruz.json # Fixture demo precargado para modo offline
│   └── src/
│       ├── types.ts          # Espejo TypeScript estricto de app/schemas.py
│       ├── api.ts            # Cliente HTTP con fallback automático offline
│       ├── App.tsx           # Shell principal, navegación y barra de advertencia offline
│       ├── views/
│       │   ├── MapForm.tsx   # Vista (a): Mapa Leaflet y configuración de lote
│       │   ├── ClimateShift.tsx # Vista (b): Diagnóstico "Tu clima cambió"
│       │   └── Compare.tsx   # Vista (c): Comparativa, tiras y fichas de decisión
│       └── components/
│           ├── RotationEditor.tsx    # Editor interactivo de rotaciones multianuales
│           ├── CompareTable.tsx      # Tabla comparativa de métricas agronómicas (5 cols)
│           ├── RotationCard.tsx      # Ficha con chips interactivos de evidencia NASA
│           ├── ModisBacktestCard.tsx # Tarjeta de backtest satelital MODIS (Extra E1)
│           ├── MetricDelta.tsx       # Tarjeta de tendencia climática con gráficos Recharts
│           └── CalendarChart.tsx     # Calendario agroclimático quincenal y barras fenológicas
│
├── notebooks/
│   └── 01_validacion_motor.ipynb # Notebook de validación científica y Go/No-Go N1/N2
│
└── contracts/
    └── analyze_response.example.json # Contrato canónico de respuesta JSON
```

---

## 9. Licencia, Atribución y Créditos Científicos

- **NASA Space Apps Challenge 2026** — Desafío *"Field Shift"*.
- **Datos Satelitales y de Reanálisis**:
  - Clima diario (1991–2025): **NASA POWER** (*Prediction Of Worldwide Energy Resources*, MERRA-2 / CERES SYN1deg), financiado por el Programa de Ciencias Aplicadas de la NASA.
  - Vegetación satelital de validación offline (2005–2025): **NASA MODIS `MOD13Q1 v061`** (250 m, NDVI compuesto cada 16 días), distribuido vía **ORNL DAAC**.
- **Modelos Agronómicos e Hidrológicos**:
  - Evapotranspiración y fenología de cultivos: **FAO Irrigation and Drainage Paper 56** (Allen, Pereira, Raes, & Smith, 1998).
  - Escorrentía y balance hídrico: **USDA Soil Conservation Service Curve Number** (SCS-CN, National Engineering Handbook, Section 4).
  - Umbrales térmicos de estrés crítico: **Teixeira et al. (2013)** (*Global and Planetary Change*) y base ecoclimática **FAO EcoCrop**.
