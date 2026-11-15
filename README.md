# RotaClima

**Language:** English · [Español](docs/i18n/es/README.md) · [Português (Brasil)](docs/i18n/pt-BR/README.md) · [中文（简体）](docs/i18n/zh-CN/README.md)

**Live Demo:** [https://nasaspaceapps2026-ivory.vercel.app](https://nasaspaceapps2026-ivory.vercel.app)

> Agronomic decision-support tool for crop-rotation planning under climate change.
> Built for the NASA Space Apps Challenge 2026, challenge **"Field Shift"**.

RotaClima compares a farmer's current crop rotation with up to three alternative rotations. For each plan it runs a daily soil water-balance and crop-response simulation over **20 evaluation seasons** (2005/06–2024/25), using NASA POWER daily data from **34 valid agricultural seasons** (1991/92–2024/25). It reports relative yield, climate risk in plain language ("bad season in 1 of 20 years"), and a 0–100 soil-health score. Every number in a recommendation card is linked to the NASA dataset, parameters, and period it was computed from.

**There is no machine learning and no chatbot.** The engine is deterministic: the same inputs always produce the same outputs.

## Contents

1. [Key properties](#1-key-properties)
2. [Quick start](#2-quick-start)
3. [Architecture](#3-architecture)
4. [API](#4-api)
5. [Data sources](#5-data-sources)
6. [Scientific model](#6-scientific-model)
7. [Crop catalog](#7-crop-catalog)
8. [Results for the demo site](#8-results-for-the-demo-site)
9. [Frontend](#9-frontend)
10. [Validation and tests](#10-validation-and-tests)
11. [Assumptions and limitations](#11-assumptions-and-limitations)
12. [Repository layout](#12-repository-layout)
13. [Known issues](#13-known-issues)
14. [Documentation and translations](#14-documentation-and-translations)
15. [Glossary](#15-glossary)
16. [References](#16-references)
17. [Target audience and users](#17-target-audience-and-users)
18. [Sustainability, business model, and scaling](#18-sustainability-business-model-and-scaling)

---

## 1. Key properties

- **Deterministic.** No unseeded randomness, no clock in the engine, tie-breaks defined in [PLAN.md](PLAN.md) §5. The determinism requirement (byte-identical responses for identical requests) is specified as test P2 in PLAN §6.
- **Traceable.** Each claim carries evidence: dataset, exact POWER parameter names, value, unit, and period.
- **Honest about uncertainty.** p-values are reported. Trends with `p ≥ 0.10` are labeled "not significant". Unfavorable results are shown as computed.
- **No silent gap-filling.** POWER fill value `-999` becomes `NaN` in one place only ([backend/app/nasa/power.py](backend/app/nasa/power.py)). A season with missing inputs fails explicitly.
- **Sourced agronomy.** Coefficients come from FAO-56, USDA SCS-CN (TR-55), FAO EcoCrop and Teixeira et al. (2013). Every agronomic field in [crops.json](backend/app/data/crops.json) has a `fuente` (source) and a `verificar` flag. All 130 fields currently have `verificar: false`, so none are pending.

---

## 2. Quick start

**Requirements:** Python ≥ 3.11, Node.js ≥ 20 (npm ≥ 10).

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                       # 159 tests, offline; about 3 minutes on the development machine
uvicorn app.main:app --reload --port 8000
```

Endpoints: `GET /health`, `GET /crops`, `POST /analyze`. Interactive OpenAPI docs: `GET /docs`.

```bash
# Frontend (second terminal)
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # type-check (tsc) + production build
```

The Vite dev server proxies `/analyze` and `/crops` to `http://localhost:8000`. If the backend is unreachable, the UI falls back to the precached Santa Cruz demo and labels the data as demo data.

Data scripts (run from `backend/`):

```bash
python scripts/precache_demo.py         # builds frontend/public/demo_santa_cruz.json (4 profiles + MODIS backtest)
python scripts/fetch_fixture.py         # downloads the NASA POWER test fixture (needs internet)
python scripts/fetch_modis_fixture.py   # downloads MOD13Q1 for 20 seasons (needs internet; takes several minutes)
```

---

## 3. Architecture

```
Browser: React 19 + TypeScript (Vite)
  MapForm · ClimateShift · Compare (+ RotationEditor, CalendarChart, ModisBacktestCard, …)
        │  POST /analyze   (fallback: frontend/public/demo_santa_cruz.json)
        ▼
FastAPI  backend/app/main.py      CORS: allow_origins=["*"]; in-process cache keyed by SHA-256 of the request
        │
pipeline.py  analyze(request)     orchestration
   ├── nasa/power.py     POWER client: coordinate rounding, disk cache, retries, -999 → NaN
   ├── nasa/modis.py     MOD13Q1 backtest, offline only (offline_only=True)
   └── engine/           pure functions: no network, no I/O, no global state
         calendar · et0 · crop · slot · table · rotation · soil · climate · alternatives · cards
config.py               every numeric constant of the engine (single source of truth)
```

| Module | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, CORS, error handlers (422, 503), `/health`, `/crops`, `/analyze` |
| `app/pipeline.py` | Builds seasons, evaluates rotations, climate profile, MODIS backtest, cards |
| `app/schemas.py` | Pydantic v2 contracts (request and response) |
| `app/config.py` | All engine constants, with PLAN section references |
| `app/data/crops.json`, `crops.py` | Crop catalog and loader with validation |
| `app/nasa/power.py` | POWER parsing, renaming, caching, retries |
| `app/nasa/modis.py` | MODIS subset parsing, NDVI scaling, Spearman backtest |
| `engine/calendar.py` | Agricultural seasons, sowing grid, season eligibility |
| `engine/et0.py` | Extraterrestrial radiation, Penman–Monteith, Hargreaves fallback |
| `engine/crop.py` | Kc curve over four stages, flowering sensitive window |
| `engine/slot.py` | SCS-CN runoff, daily water balance, thermal and frost factors, yield |
| `engine/table.py` | Memoized slot table; circular smoothing used only to choose sowing dates |
| `engine/rotation.py` | Rotation validity, cropping modes, P and I indices, bad seasons, metrics |
| `engine/soil.py` | Soil-health score (nitrogen, diversity, erosion protection, organic matter) |
| `engine/climate.py` | Climate profile, before/recent comparison, Mann–Whitney U |
| `engine/alternatives.py` | Plan enumeration and profile selection with documented relaxations |
| `engine/cards.py` | Template-based recommendation cards |

Engine conventions ([AGENTS.md](AGENTS.md)): numpy-vectorized across seasons, explicit loops over days, no magic literals in `engine/`.

---

## 4. API

### `POST /analyze`

Request (`AnalyzeRequest`), using the demo case:

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

| Field | Rule |
|---|---|
| `lat` / `lon` | `-60 … 60` / `-180 … 180`. Coordinates are rounded to 2 decimals for data access. |
| `soil_texture` | `arenoso` \| `franco` (default) \| `arcilloso` |
| `sow_date` | `"MM-DD"`, day must be `01` or `16` (fortnights) |
| `years` | 1 to 3 years; 1 to 2 slots per year, in chronological order within the season |
| `crop_id` | Must exist in the catalog (lowercase, no accents: `soya`, `maiz`, …) |
| `include_diversified` | **API default: `false`.** The web UI sends `true`. |

Errors:
- **422** with `detail` (Spanish message): unknown crop, overlapping slots, less than 10 days between harvest and next sowing, no harvestable crop.
- **503** with `detail`: POWER unreachable and no cached data for the coordinate.

Response (`AnalyzeResponse`):

| Key | Content |
|---|---|
| `meta` | Location, elevation, hemisphere, season start (`07-01` S / `01-01` N), season list, periods, Hargreaves share, resolution note, assumptions S1–S12 |
| `climate` | 14 climate metrics: before, recent, delta, p-value, significance, per-season series, source |
| `climatology` | 24 fortnightly bins from season start, for `before` and `recent` (rain, ET0, Tmax, Tmin) |
| `rotations` | Fixed order: `actual`, `adaptada`, `regenerativa`, then `diversificada` if requested. Each has slots, metrics, per-season results, and a card. |
| `modis_backtest` | Object, or `null` when no local MODIS cache exists for the coordinate |

`GET /crops` returns the catalog summary (ID, name, family, harvestable flag, pending-verification count).

Caching: POWER series are cached on disk per point; complete `/analyze` responses are cached in memory per process, keyed by the SHA-256 of the request body.

---

## 5. Data sources

### 5.1 NASA POWER (daily, point API)

- Endpoint: `https://power.larc.nasa.gov/api/temporal/daily/point`, community `AG` (agroclimatology). No credentials required.
- Window: `19910101`–`20251231` (`DATA_START`, `DATA_END`). The demo fixture holds **12,784 consecutive days** (1991-01-01 to 2025-12-31).
- Disk cache: `backend/cache/power/{lat:.2f}_{lon:.2f}_{start}_{end}.json` (raw response).
- Client: 60 s timeout; 3 attempts in total (one request plus two retries), waiting 2 s and then 4 s between them; final failure raises `PowerUnavailable`. The code's default retry tuple also contains 8 s, but it is never reached with 3 attempts (see §13).
- Elevation: `geometry.coordinates[2]`.

| POWER parameter | Internal column | Unit | Role in the model |
|---|---|---|---|
| `PRECTOTCORR` | `prec` | mm/day | Rainfall; SCS-CN runoff, water balance, climate profile |
| `T2M_MAX` | `tmax` | °C | ET0, heat stress, hot-day count |
| `T2M_MIN` | `tmin` | °C | ET0, frost stress, GDD |
| `T2M` | `t2m` | °C | Ingested; ET0 uses `(tmax + tmin)/2` by design (FAO-56 eq. 6) |
| `RH2M` | `rh` | % | Penman–Monteith vapour pressure |
| `ALLSKY_SFC_SW_DWN` | `rs` | MJ/m²/day | Net radiation (CERES SYN1deg) |
| `WS2M` | `ws` | m/s | Penman–Monteith wind term |
| `PS` | `ps` | kPa | Psychrometric constant |
| `GWETTOP` | `gwettop` | 0–1 | Ingested; surface soil wetness (0–5 cm) |
| `GWETROOT` | `gwetroot` | 0–1 | Reference for the soil-moisture sanity check (§10) |

Parameter names appear only in `nasa/power.py` and in `Source.parameters` of the output.

### 5.2 NASA MODIS MOD13Q1 v061 (validation only)

- Product: MOD13Q1 v061, 250 m, 16-day composites, band `250m_16_days_NDVI`, scale factor 0.0001, distributed by ORNL DAAC.
- Used only in an **offline backtest** for the demo point. The `/analyze` path never calls the network for MODIS (`offline_only=True`).
- Sampling: four composites per season in the summer window (`A{y+1}017` … `A{y+1}065`), 20 seasons → 80 composites.
- Service limits: at most 10 dates per request (more returns HTTP 400). The project measured 33–42 s per request.
- Cache: `backend/cache/modis/{lat:.2f}_{lon:.2f}_MOD13Q1.json`. Test fixture: `backend/tests/fixtures/modis_demo.json`.

---

## 6. Scientific model

The full normative specification is in [PLAN.md](PLAN.md) §4. This section summarizes it. Formulas are reproduced in the code blocks; the constants live in `config.py`.

### 6.1 Agricultural season (unit of analysis)

- Hemisphere `S` if `lat < 0`, else `N`. A season `y` starts on **1 July** (S) or **1 January** (N). Calendar years are never used for aggregation.
- Valid seasons: `inicio(y) − 180 d ≥ DATA_START` and `inicio(y) + 365 + 183 d ≤ DATA_END` → **S: 1991–2024 (34 seasons)**, **N: 1992–2024 (33)**.
- `before` = first 15 seasons (1991/92–2005/06). `recent` = last 15 (2010/11–2024/25). `eval` = last 20 (2005/06–2024/25). By construction, `before` and `eval` share the 2005/06 season.
- In the S hemisphere, a sowing date with month ≥ 07 falls in calendar year `y` of season `y`; a month < 07 falls in `y+1`. This keeps a crop that crosses 31 December in one piece.

### 6.2 Reference evapotranspiration (ET0)

Penman–Monteith (FAO-56 eq. 6) with `T = (tmax + tmin)/2`. Hargreaves (FAO-56 eq. 52) is used **per day** when RH, radiation or wind is missing; the share of Hargreaves days is reported in `meta.et0_hargreaves_share` (0.0 for the demo).

```
Ra     = (24·60/π)·0.0820·dr·(ωs·sin φ·sin δ + cos φ·cos δ·sin ωs)   MJ m⁻² d⁻¹   (φ in radians, negative in the south)
ET0_PM = (0.408·Δ·Rn + γ·900/(T+273)·ws·(es − ea)) / (Δ + γ·(1 + 0.34·ws))
ET0_HG = 0.0023·(T + 17.8)·√(tmax − tmin)·Ra·0.408                         (fallback; Ra converted by 0.408)
```

### 6.3 Crop coefficient and flowering window

- Kc is piecewise linear over four stages (initial, development, mid, late), per FAO-56 Tables 11–12. No climate adjustment of Kc (assumption S3).
- Sensitive window (flowering): `[t_mid − 5, t_mid + 25)` days, where `t_mid = L_ini + L_dev`.

### 6.4 Daily one-bucket water balance

- **Runoff (SCS-CN):** `S = 25400/CN − 254`; `RO = (P − 0.2S)² / (P + 0.8S)` if `P > 0.2S`, else 0.
- **Effective rain:** rain below `0.2 × ET0` is ignored (`Pe = 0`). Rain enters the bucket **before** the stress factor is evaluated that day.
- **Bucket:** capacity `TAW = AWC × Zr`; `AWC` is 80 / 155 / 160 mm/m and `CN` is 67 / 78 / 85 for arenoso / franco / arcilloso.
- **Stress:** `RAW = p·TAW`, with `p = clip(p_tab + 0.04·(5 − ETc), 0.1, 0.8)`; `Ks = 1` if `D ≤ RAW`, else `(TAW − D)/(TAW − RAW)`.
- **Spin-up:** 180 days before sowing, starting from `Dr = 0.5·TAW`. During the last 120 days, `Kc = 0.90` if the previous slot is harvested within 30 days (`mode = "crop"`); otherwise `Kc = 0.20` (`mode = "fallow"`).
- **Water factor:** `f_agua = clip(1 − Ky·(1 − ΣETa/ΣETc), 0, 1)`. The ratio is taken over sums, never as an average of daily ratios (FAO-56 eq. 90).

### 6.5 Thermal factors, frost, and relative yield

```
Y_rel = f_agua · f_calor · f_helada · f_temp         ∈ [0, 1]
```

- **f_temp:** mean over the cycle of a trapezoidal EcoCrop response to daily mean temperature.
- **f_calor:** `1 − mean_{sensitive window}( clip((tmax − Tcrit)/(Tlim − Tcrit), 0, 1) )`.
- **f_helada:** `0.3` if `tmin < t_helada` (0 °C) on any day of the flowering window; else `0.7` if `tmin < −3 °C` on any day of the cycle; else `1`. Assumption S6.
- **Limiting factor:** the smallest factor if it is below 0.95; otherwise `ninguno`. Ties are broken in the order agua, calor, helada, temperatura.

### 6.6 Rotation indices and bad seasons

- Slots form a cyclic sequence over 1–3 years. Validity: every gap between a harvest and the next sowing is ≥ 10 days; `sow_offset + duration ≤ 365 + 183`; at least one harvestable crop.
- For each season `y`, the climate of `y` is applied to **every phase** `k = 1..L` of the rotation:

```
P_y = (1/L) · Σ_k Σ_{s ∈ year k, harvestable} w_s · Y_rel(s, y)
Pot = (1/L) · Σ_k Σ_{s ∈ year k, harvestable} w_s
I_y = P_y / Pot                  bad season ⇔ I_y < 0.60
```

- Cover crops (`cosechable = false`) do not count in `P` or `Pot`. They do count for soil, cropping mode and validity.
- Metrics over the 20 evaluation seasons: `mean_index`, `p10_index` (linear percentile), `mean_productivity`, `bad_seasons` (of 20), `bad_before` and `bad_recent` (of 15 each), and `productivity_vs_current = 100 · mean_P / mean_P(actual)`.
- A slot "fails" in a season when `Y_rel < 0.50`.

### 6.7 Soil-health score (0–100)

```
total = 0.25 · (nitrogen + diversity + erosion + organic_matter)
```

- **Nitrogen:** `clip(60 + 20 · N_yr, 0, 100)`, where `N_yr = (1/L) · Σ_s N_POINTS[class_n(s)]`. Points: `cobertura_leguminosa` +2.0, `leguminosa_grano` +0.5, `cobertura_no_leguminosa` +0.5, `extractiva` −1.0, `muy_extractiva` −1.5.
- **Diversity:** `DIVERSITY_BASE[families] · (1 − 0.5 · repeat_fraction)`, with base 30 / 65 / 85 for 1 / 2 / 3 botanical families and 100 for four or more. `repeat_fraction` is the share of cyclic adjacent pairs with the same family.
- **Organic matter:** `clip(100 · ((1/L) · Σ_s pts(s)) / 6, 0, 100)`, where `pts = RESIDUE_POINTS[class]` (bajo 1, medio 2, alto 3), plus `COVER_CROP_BONUS = 1` for non-harvestable cover crops.
- **Erosion protection:** the daily SCS-CN runoff (eval seasons, averaged by day of season) weighted by a cover curve, expressed as a percentage. Cover is residue after harvest (`RESIDUE_COVER`: bajo 0.3, medio 0.5, alto 0.8), rising linearly during crop development and equal to 1.0 afterwards. Assumes no-till (S5). If total runoff is 0, the score is 100.
- The soil score does **not** feed back into yield (assumption S4).

### 6.8 Climate profile and significance test

Fourteen metrics per season are computed (definitions in [PLAN.md](PLAN.md) §4.8):

- **Rain:** total, and by quarter of the season (days 0–90, 91–181, 182–272, 273–end).
- **Onset:** first offset ≥ 62 where 3-day rain ≥ 20 mm and no ≥ 10-day dry spell (< 1 mm/day) follows within 30 days.
- **Cessation:** first offset ≥ onset + 60 where 20-day rain < 10 mm.
- **Season length**, **hot days** (Tmax > 35 °C), **dry spells** and **longest dry spell** within the wet period, **GDD** (base 10 °C), **ET0 total**, **water deficit**.

For each metric: `before` and `recent` means (NaN ignored), `delta = recent − before`, two-sided **Mann–Whitney U** p-value (`None` if any sample has fewer than 5 values), and `significant = p < 0.10`.

### 6.9 Alternative profiles

Selection is deterministic and follows [PLAN.md](PLAN.md) §5. Relaxations are recorded in `relaxed_constraints`.

| Profile | Goal | Constraints (before relaxation) | Ranking |
|---|---|---|---|
| `actual` | Baseline: the rotation as entered, no re-optimization | — | — |
| `adaptada` | Minimum change | Same number of years and slots, at most one crop changed, sowing dates re-optimized, `mean_P ≥ 95%` of current | Fewest bad seasons → highest `p10_index` → highest `mean_P` → fewest changes |
| `regenerativa` | Best soil with bounded yield loss | Soil gain ≥ 10 points, `mean_P ≥ 80%` of current, bad seasons not above current | Highest soil total → highest `mean_P` |
| `diversificada` (optional) | Two-year diversified cycle | ≥ 3 botanical families, ≥ 3 harvestable crops, soil not below current | Highest `mean_P` among plans with bad seasons not above current |

Relaxation order: loss 20% → 30% for `regenerativa`; drop the bad-season limit; soil gain 10 → 1 point. Adaptada drops its productivity filter if nothing qualifies.

### 6.10 Recommendation cards

Cards are generated from fixed templates, not from free text. Each template fires only when its condition holds and cites the parameters behind its numbers. A test asserts that every number in a claim's text appears in its `evidence[].value` (PLAN §2.5). Cards have three sections: **why**, **benefits**, and **risks**.

---

## 7. Crop catalog

The catalog ([backend/app/data/crops.json](backend/app/data/crops.json)) has 13 crops. Values below are read from the file.

| ID | Name | Family | Harvestable | Stages ini/dev/mid/late (d) | Kc ini/mid/end | Zr (m) | p | Ky | EcoCrop Tmin/Topt-min/Topt-max/Tmax (°C) | Heat Tcrit/Tlim (°C) | N class | Residue |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `soya` | Soya | Fabaceae | yes | 20/30/60/25 | 0.40/1.15/0.50 | 1.0 | 0.50 | 0.85 | 10/20/33/38 | 35/40 | leguminosa_grano | bajo |
| `maiz` | Maíz | Poaceae | yes | 25/40/45/30 | 0.30/1.20/0.35 | 1.3 | 0.55 | 1.25 | 10/18/33/47 | 35/45 | muy_extractiva | alto |
| `sorgo` | Sorgo | Poaceae | yes | 20/35/40/30 | 0.30/1.05/0.55 | 1.5 | 0.55 | 0.90 | 8/22/35/40 | 35/40 | extractiva | alto |
| `trigo` | Trigo | Poaceae | yes | 15/25/50/30 | 0.30/1.15/0.30 | 1.2 | 0.55 | 1.15 | 5/15/23/27 | 27/40 | extractiva | medio |
| `girasol` | Girasol | Asteraceae | yes | 25/35/45/25 | 0.35/1.10/0.35 | 1.2 | 0.45 | 0.95 | 5/17/34/45 | 34/45 | muy_extractiva | medio |
| `frijol` | Frijol | Fabaceae | yes | 20/30/40/20 | 0.40/1.15/0.35 | 0.7 | 0.45 | 1.15 | 7/16/25/32 | 25/32 | leguminosa_grano | bajo |
| `mani` | Maní | Fabaceae | yes | 25/35/45/25 | 0.40/1.15/0.60 | 0.8 | 0.50 | 0.70 | 10/22/32/45 | 32/45 | leguminosa_grano | bajo |
| `algodon` | Algodón | Malvaceae | yes | 30/50/55/45 | 0.35/1.15/0.60 | 1.4 | 0.65 | 0.85 | 15/22/36/42 | 36/42 | muy_extractiva | bajo |
| `cebada` | Cebada | Poaceae | yes | 15/25/50/30 | 0.30/1.15/0.25 | 1.2 | 0.55 | 1.15 | 2/15/20/40 | 20/40 | extractiva | medio |
| `papa` | Papa | Solanaceae | yes | 25/30/45/30 | 0.50/1.15/0.75 | 0.5 | 0.35 | 1.10 | 7/15/25/30 | 25/30 | extractiva | bajo |
| `mijo` | Mijo | Poaceae | yes | 15/25/40/25 | 0.30/1.00/0.30 | 1.5 | 0.55 | 0.90 | 12/25/35/40 | 35/40 | extractiva | alto |
| `avena_cob` | Avena (cover) | Poaceae | **no** | 15/25/45/5 | 0.30/1.15/1.15 | 1.2 | 0.55 | 1.00 | 5/16/20/30 | 20/30 | cobertura_no_leguminosa | alto |
| `crotalaria` | Crotalaria (cover) | Fabaceae | **no** | 15/25/45/5 | 0.40/1.10/1.10 | 1.0 | 0.50 | 1.00 | 15/23/30/37 | 30/37 | cobertura_leguminosa | alto |

Cover crops are truncated to a 90-day cycle with Kc_end = Kc_mid (assumption S9). Heat thresholds for crops outside Teixeira et al. (2013) are derived from EcoCrop (S7). Frost threshold `t_helada` is 0 °C for all crops (S6).

---

## 8. Results for the demo site

Demo point: **Santa Cruz, Bolivia (−17.30, −62.25), elevation 280.15 m**, texture `franco` (AWC 155 mm/m, CN 78). Current rotation: soya 11-16 + soya 05-01. All values below are read from [frontend/public/demo_santa_cruz.json](frontend/public/demo_santa_cruz.json).

### 8.1 Climate change (before 1991/92–2005/06 vs recent 2010/11–2024/25)

| Metric | Unit | Before | Recent | Delta | p-value | Significant (p < 0.10) |
|---|---|---|---|---|---|---|
| Total rain | mm/season | 1342.0 | 1146.0 | −195.9 | 0.0114 | yes |
| Rain, quarter 1 | mm | 145.4 | 142.7 | −2.73 | 0.9669 | no |
| Rain, quarter 2 | mm | 466.2 | 287.9 | −178.3 | 0.0006 | yes |
| Rain, quarter 3 | mm | 493.3 | 436.6 | −56.64 | 0.2290 | no |
| Rain, quarter 4 | mm | 237.3 | 279.1 | +41.79 | 0.2455 | no |
| Onset of rains | day offset | 82.6 | 110.2 | +27.6 | 0.0016 | yes |
| Cessation of rains | day offset | 312.9 | 274.8 | −38.12 | 0.0723 | yes |
| Season length | days | 232.1 | 168.0 | −64.1 | 0.0055 | yes |
| Hot days (Tmax > 35 °C) | days/season | 52.73 | 80.47 | +27.73 | 0.0084 | yes |
| Dry spells (≥ 10 d) | count | 1.00 | 1.73 | +0.73 | 0.0791 | yes |
| Longest dry spell | days | 11.00 | 13.47 | +2.47 | 0.0828 | yes |
| GDD (base 10 °C) | °C·day | 5694 | 5934 | +240.4 | 0.0202 | yes |
| ET0 total | mm/season | 1522 | 1587 | +65.02 | 0.1057 | **no** |
| Water deficit | mm/season | 470.7 | 659.0 | +188.3 | 0.0101 | yes |

Ten of 14 metrics are significant. The four that are not (rain quarters 1, 3 and 4, and ET0 total) are reported as such.

### 8.2 Rotation profiles (evaluation window, 20 seasons)

| Profile | Rotation (year 1 · year 2) | Mean I | P10 I | Productivity vs current | Bad seasons | Soil total | N | Diversity | Erosion protection | Organic matter |
|---|---|---|---|---|---|---|---|---|---|---|
| `actual` | soya@11-16 + soya@05-01 | 0.7644 | 0.6812 | 100.00 % | 1 / 20 | 47.90 | 80.0 | 15.0 | 63.26 % | 33.33 |
| `adaptada` | mijo@11-16 + soya@03-16 | 0.8589 | 0.7779 | 112.36 % | 0 / 20 | 63.82 | 50.0 | 65.0 | 73.60 % | 66.67 |
| `regenerativa` | crotalaria@10-16 + sorgo@02-16 · girasol@11-01 + mijo@04-16 | 0.8795 | 0.8277 | 86.30 % | 0 / 20 | 79.03 | 45.0 | 85.0 | 86.12 % | 100.00 |
| `diversificada` | algodon@09-16 + sorgo@04-01 · mijo@11-16 + girasol@03-16 | 0.8819 | 0.7958 | 115.37 % | 0 / 20 | 60.56 | 10.0 | 74.38 | 82.88 % | 75.00 |

Worst seasons of the current rotation: **2016/17** (I = 0.5541, limiting factor: heat), **2023/24** (I = 0.6796, water), **2015/16** (I = 0.6814, water).

Adaptada replaces one crop (soya → mijo) and re-optimizes sowing dates within the same one-year structure. Regenerativa and Diversificada are two-year cycles. Regenerativa has the highest soil score; Diversificada has the highest productivity but the lowest nitrogen score (10.0), because it includes no legumes.

### 8.3 Satellite cross-check (MODIS MOD13Q1, offline)

- Spearman rank correlation between the summer NDVI maximum and the simulated index `I` of the current rotation: **ρ = −0.0617, p = 0.7962** (n = 20). No significant correlation. Reported as computed.
- Lower NDVI tertile threshold: **0.7260**. The only bad season, 2016/17, has max NDVI **0.7160**, so it falls in the lowest tertile (**1 of 1** bad seasons).

Interpretation: one 250 m pixel reflects the actual crops planted on that field in each year, while the model simulates a fixed rotation driven by ~50 km regional climate. The two are not expected to correlate closely in normal years.

---

## 9. Frontend

Stack: Vite, React 19, TypeScript in strict mode, Leaflet (`react-leaflet`), Recharts. **The UI labels are in Spanish.** Identifiers and code are in English.

| Area | Components | What it does |
|---|---|---|
| Plot and rotation (a) | `views/MapForm.tsx`, `components/RotationEditor.tsx` | Leaflet map with click-to-coordinate, texture selector, fortnightly rotation editor with overlap and turnaround checks, Santa Cruz demo button |
| Climate change (b) | `views/ClimateShift.tsx`, `components/MetricDelta.tsx` | One card per climate metric (before → recent, delta, "No significativo" when p ≥ 0.10), per-season series, NASA source |
| Calendar | `components/CalendarChart.tsx` | 24-fortnight rain and ET0 chart, Tmax/Tmin lines, crop stage bars with the flowering window highlighted |
| Comparison (c) | `views/Compare.tsx`, `components/CompareTable.tsx`, `components/RotationCard.tsx`, `components/ModisBacktestCard.tsx` | Side-by-side profiles, bad-season strip for the 20 seasons, cards with why/benefits/risks, evidence chips per claim, MODIS card |
| API client | `src/api.ts`, `src/types.ts` | Calls `/analyze` and `/crops`; falls back to the precached demo and static crop list; `types.ts` mirrors `schemas.py` by hand |

The top bar shows an **offline demo** banner when the data come from the precached file.

---

## 10. Validation and tests

- **Backend suite:** `pytest -q` → **159 passed, 1 warning**, about 3 minutes on the development machine. Tests run offline: they use fixtures in `backend/tests/fixtures/` or `httpx.MockTransport`.
- **Frontend:** `npm run build` runs `tsc` in strict mode and then the Vite build.
- **Go/no-go checks** ([PLAN.md](PLAN.md) §3, N1–N2), in [notebooks/01_validacion_motor.ipynb](notebooks/01_validacion_motor.ipynb):
  1. Annual ET0 between 1,100 and 2,000 mm, and annual rain between 700 and 1,800 mm.
  2. Summer soya yield above winter soya yield.
  3. Current rotation has between 1 and 15 bad seasons out of 20.
  4. The three worst seasons are compared with reported droughts.
  5. Correlation between simulated `1 − Dr/TAW` and `gwetroot` above 0.5. This is a **sanity check, not an independent validation**, because both use the same rainfall.

  The notebook was **not re-executed** for this documentation. Results reported in the project's earlier documents, including r = 0.5501 for check 5, were not re-derived here.

---

## 11. Assumptions and limitations

These are the S1–S12 assumptions from [PLAN.md](PLAN.md) §4.10. They are also returned in `meta.assumptions`.

- **S1** POWER is reanalysis at ≈ 50 km (MERRA-2), with 1° radiation (CERES). It describes regional climate, not a specific plot. Modeled Tmax tends to be lower than station readings, so counts of days above 35 °C are conservative.
- **S2** Initial water: 180-day spin-up with fixed Kc of 0.20 (fallow) or 0.90 (previous crop). The real previous crop is not simulated.
- **S3** Phenology uses calendar days. Kc is not adjusted for humidity or wind. No photoperiod.
- **S4** The soil score does not change simulated yield.
- **S5** No-till management is assumed.
- **S6** Frost is a step rule: factor 0.3 during flowering, 0.7 in the vegetative phase.
- **S7** Heat thresholds not in Teixeira et al. (2013) are derived from EcoCrop.
- **S8** Nitrogen and residue classes are general agronomic knowledge, not measurement.
- **S9** Cover crops use analogous parameters, a 90-day truncated cycle, and no grain yield.
- **S10** Yield is relative to the agroecological potential. There are no prices and no margins. `value_weight = 1` for all crops by default.
- **S11** Single-layer bucket model. Not modeled: waterlogging, pests, weeds, emergence failures, groundwater, capillary rise, nutrient dynamics, and soil structure change over time.
- **S12** Rainfall trends in reanalysis can contain observation-system artifacts. Hence the p-values, and the label "not significant" when `p ≥ 0.10`.

Scope limits that follow from these assumptions:
- The engine evaluates one point per request. Regional comparison requires one request per coordinate.
- The output is a relative ranking under a fixed rotation template. It is not a yield forecast and not a seasonal forecast.
- Soil score and yield are separate; a higher soil score does not raise simulated yield.

---

## 12. Repository layout

```
.
├── README.md                     # this file (English master)
├── AGENTS.md                     # engineering rules for contributors and agents
├── PLAN.md                       # normative plan: contracts (§2), formulas (§4), tests (§6)
├── docs/i18n/
│   ├── es/README.md              # Español
│   ├── pt-BR/README.md           # Português (Brasil)
│   └── zh-CN/README.md           # 中文（简体）
├── backend/
│   ├── pyproject.toml            # dependencies and the dev extra (pytest)
│   ├── app/
│   │   ├── main.py               # FastAPI endpoints, CORS, error handlers
│   │   ├── pipeline.py           # analyze(): orchestration and in-memory cache
│   │   ├── schemas.py            # Pydantic v2 contracts
│   │   ├── config.py             # all engine constants
│   │   ├── data/                 # crops.json and its loader
│   │   ├── nasa/                 # power.py (POWER client), modis.py (MODIS backtest)
│   │   └── engine/               # pure functions: calendar, et0, crop, slot, table,
│   │                             #   rotation, soil, climate, alternatives, cards
│   ├── scripts/                  # canonical data scripts (see §13)
│   └── tests/                    # test_*.py and fixtures/
├── frontend/
│   ├── package.json · vite.config.ts · tsconfig.json · index.html
│   ├── public/demo_santa_cruz.json   # precached offline demo
│   └── src/                      # App.tsx, api.ts, types.ts, views/, components/
├── notebooks/01_validacion_motor.ipynb
└── contracts/analyze_response.example.json
```

Generated and ignored by git: `backend/cache/`, `backend/.venv/`, `frontend/node_modules/`, `frontend/dist/`.

---

## 13. Known issues

- **Root `scripts/` wrappers.** `scripts/` at the repository root holds two wrappers (`fetch_fixture.py`, `precache_demo.py`) that delegate to the same-named files in `backend/scripts/`. The commands in this document run from `backend/`; the root wrappers are an alternative entry point. `fetch_modis_fixture.py` has no root wrapper.
- **Missing file.** [AGENTS.md](AGENTS.md) and [PLAN.md](PLAN.md) refer to `QUESTIONS.md` as the place for open questions. It is not in the repository.
- **No license file.** The repository does not declare a license. Reuse terms are therefore not defined.
- **Diversified default differs by client.** The API default is `include_diversified: false`; the web UI sends `true`.
- **Cold cache.** Without `backend/cache/`, the first `/analyze` for a new coordinate needs network access to POWER. The precached demo in `frontend/public/` works offline. The UI warns that a first query can take about 20 seconds.
- **Dev proxy coverage.** The Vite proxy forwards only `/analyze` and `/crops`, not `/health`. Set `VITE_API_URL` to call the backend from another origin.
- **MODIS scope.** The MODIS backtest is precached and offline by design. It cannot run for coordinates without a local MODIS cache. The field `modis_backtest` is then `null`.
- **POWER retries differ from the plan.** [PLAN.md](PLAN.md) §2.3 specifies three retries with waits of 2, 4 and 8 s. [backend/app/nasa/power.py](backend/app/nasa/power.py) makes 3 attempts in total (2 retries) with waits of 2 s and 4 s. The code is the behavior of record; the plan has not been updated.

---

## 14. Documentation and translations

- The **English version of this file is the master.** The Spanish, Brazilian Portuguese and Simplified Chinese versions in [docs/i18n/](docs/i18n/) are translations of it.
- Formulas, code blocks, identifiers, crop IDs, POWER and MODIS parameter names, file paths, and API field names are identical in all four versions.
- The translations are maintained by hand. When this file changes, update the translations in the same change.

---

## 15. Glossary

| Term | Meaning |
|---|---|
| Season (*campaña*) | Agricultural year from 1 July (S) or 1 January (N). The unit of analysis. |
| Slot | One crop with its sowing date and cropping mode: (crop, sowing date, `crop` \| `fallow`) |
| Mode | `crop` if the previous harvest was within 30 days of sowing, otherwise `fallow` |
| TAW | Total available water in the root zone (mm) |
| RAW | Readily available water, `p · TAW` (mm) |
| Dr | Root-zone depletion (mm) |
| Y_rel | Relative yield of one slot in one season, 0–1 |
| P, Pot, I | Productivity, potential, and index of a rotation in one season |
| Bad season | A season with `I < 0.60` |
| Eval window | The last 20 seasons, used for all headline metrics |

---

## 16. References

- Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop water requirements.* FAO Irrigation and Drainage Paper 56.
- Doorenbos, J., & Kassam, A. H. (1979). *Yield response to water.* FAO Irrigation and Drainage Paper 33 (source of the Ky yield-response factor).
- USDA Soil Conservation Service. *National Engineering Handbook, Section 4 (Hydrology)*, and TR-55 (curve-number method).
- Teixeira, E. I., et al. (2013). *Global and Planetary Change* (heat-stress thresholds).
- FAO ECOCROP database (temperature suitability ranges).
- NASA POWER (Prediction Of Worldwide Energy Resources), Langley Research Center. Datasets MERRA-2 and CERES SYN1deg.
- MODIS MOD13Q1 v061, 250 m, 16-day NDVI, accessed through the ORNL DAAC subset API.

---

## 17. Target audience and users

RotaClima separates **who benefits from the decision** from **who operates the interface today**, avoiding the common mistake of assuming every smallholder farmer reads statistical output directly:

1. **Primary operators today (current MVP):**
   - **Field agronomists, cooperative technical advisors, and rural extensionists (e.g., INIAF, NGOs):** They already understand `ET0`, flowering heat stress, relative yield indices (`I`), and soil-health trade-offs. They use RotaClima in 3 clicks as a climate-auditing dashboard to sit alongside the farmer and back up rotation changes with 35 years of NASA evidence.
   - **Agricultural risk & credit analysts (rural banks, parametric/crop insurers):** They need transparent, auditable historical risk metrics (`bad seasons in X of 20`, limiting factor `water` vs `heat`, Mann-Whitney `p`-values) without black-box ML.
   - **Tech-enabled commercial farmers:** Medium and large producers who already work with agronomic advisors and want to verify how rainfall onset and extreme heat have shifted in their zone.

2. **End beneficiary:**
   - **The farmer / agricultural producer:** Always has free, anonymous, zero-paywall access to public NASA climate diagnostics and rotation comparisons.

3. **Institutional & public-sector users (roadmap):**
   - **Ministries of Agriculture, municipalities, and multilateral adaptation programs:** For dynamic agro-ecological zoning, climate-adaptation diagnostics, and extension planning.
   - **Seed companies and grain cooperatives:** For regional variety positioning under shifting rainfall windows.

4. **Future direct-to-farmer UX ("Producer Mode"):**
   - Today's UI exposes scientific terminology (`I = 0.5541`, `P10`, Mann-Whitney `p`, Spearman `ρ`) and biophysical relative yield without local crop prices (`S10`). A dedicated simplified mode is planned to hide statistical notation and pair risk counts (*"bad season in X of 10 years"*) with local market prices and gross margins (`$/ha`).

---

## 18. Sustainability, business model, and scaling

RotaClima follows a **two-layer Open Science + B2B model** that keeps public NASA data free for individual producers while monetizing institutional risk and scale.

### 1. How it sustains itself (Open Science + B2B)

| Layer | Status | Who it serves | What it includes |
|---|---|---|---|
| **Layer 1: Open Science (Public Good)** | **Live today** (`GET /health`, `GET /crops`, `POST /analyze`) | Individual farmers, extensionists, students, researchers | 100% free, anonymous, no login, no paywall; full `p`-values, evidence trails, and declared limits (`S1–S12`); low-cost static frontend + stateless API. |
| **Layer 2: Institutional B2B** | **Planned roadmap** *(not yet in `main.py`)* | Crop insurers, rural banks, cooperatives, seed companies, public agencies | Polygon-scale climate/NDVI, seasonal ENSO weighting, private yield/margin calibration, and multi-parcel batch API. |

**Why institutions pay:**
- **Crop & parametric insurers** need historical drought/heat risk pricing across thousands of insured parcels without manual agronomic calibration.
- **Rural banks & microfinance** need climate-adjusted credit scoring (e.g., differentiating a monoculture exposed to heat stress from a diversified rotation with `0/20` bad seasons).
- **Cooperatives & grain originators** need to plan seed inventory, credit lines, and technical assistance across whole districts.

### 2. How it scales (technical, agronomic, and geographic)

1. **Geographic scaling (already supported by data source):**
   - NASA POWER provides global daily coverage (`-90..90`, `-180..180`), and the engine automatically adapts agricultural season start dates by hemisphere (`1 July` for `lat < 0`, `1 January` for `lat >= 0`).
   - Coordinate rounding (`0.01°`) with disk caching (`power.py`) plus SHA-256 request caching (`pipeline.py`) prevents redundant NASA POWER downloads as user volume grows.
2. **Spatial & seasonal scaling (B2B roadmap):**
   - **Higher spatial resolution:** Move from the `~50 km` regional POWER grid (`S1`) to parcel/polygon scale using `CHIRPS (~5 km)` / `IMERG (~10 km)` precipitation and `MODIS` / `Sentinel-2` vegetation layers.
   - **Prospective seasonal weighting:** Add `ENSO (ONI)` phase and `NMME` seasonal forecast weighting on top of the 20-season deterministic backtest.
   - **Batch infrastructure:** Expose a thin `POST /analyze/batch` endpoint with `X-API-Key` authentication over the existing deterministic `engine/` to score thousands of polygons per request.
3. **Agronomic & local-market scaling:**
   - **Private & local calibration:** Allow cooperatives and research stations (e.g., INIAF) to calibrate local cultivar `GDD`, `Ky`, photoperiod sensitivity (`S3`), and regional `$/ha` gross margins (`S10`) so alternatives reflect commercial viability as well as biophysical resilience.
   - **Dynamic MODIS windows & low-connectivity field use:** Anchor satellite backtest windows dynamically to simulated rainfall `onset`, and export lightweight offline/PDF extension briefs for rural areas with intermittent connectivity.
