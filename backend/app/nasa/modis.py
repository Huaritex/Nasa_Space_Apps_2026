"""PLAN §3 F7 E1 — Cliente offline/incremental y backtest satelital NASA MODIS (MOD13Q1 ORNL DAAC)."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
from pathlib import Path
import threading
import time
from typing import Any, Literal

import httpx
import numpy as np
import pandas as pd
from scipy import stats

from app.config import (
    MODIS_API_BASE_URL,
    MODIS_BAND_NDVI,
    MODIS_COORD_DECIMALS,
    MODIS_DATASET_LABEL,
    MODIS_DEMO_LAT,
    MODIS_DEMO_LON,
    MODIS_FILL_THRESHOLD,
    MODIS_MAX_DATES_PER_REQUEST,
    MODIS_MAX_WORKERS,
    MODIS_MIN_PAIRED_SEASONS,
    MODIS_NDVI_SCALE,
    MODIS_NORTH_PEAK_DOYS,
    MODIS_REQUEST_TIMEOUT,
    MODIS_RETRY_DELAYS,
    MODIS_SAFE_CHUNK_SIZE,
    MODIS_SOUTH_PEAK_DOYS,
    MODIS_TERTILE_QUANTILE,
    MODIS_YEAR_PREFIX_LEN,
)
from app.engine.calendar import get_season_start_date
from app.schemas import ModisBacktestOut, ModisSeasonPoint, SeasonOut, Source

logger = logging.getLogger(__name__)


class ModisUnavailable(Exception):
    """Levantada cuando la API ORNL DAAC MODIS no responde tras agotar reintentos."""

    pass


def chunk_modis_dates(
    modis_dates: list[str],
    max_chunk: int = MODIS_MAX_DATES_PER_REQUEST,
) -> list[tuple[str, str]]:
    """PLAN §3 F7 E1 — Agrupa fechas AYYYYDDD en bloques <= max_chunk (<= 10) sin cruzar año."""
    effective_max = min(int(max_chunk), MODIS_MAX_DATES_PER_REQUEST)
    if effective_max < 1:
        raise ValueError("max_chunk debe ser >= 1")

    if not modis_dates:
        return []

    sorted_dates = sorted(set(modis_dates))
    chunks: list[tuple[str, str]] = []
    current_chunk: list[str] = []

    for d in sorted_dates:
        if not current_chunk:
            current_chunk.append(d)
            continue

        same_year = d[:MODIS_YEAR_PREFIX_LEN] == current_chunk[0][:MODIS_YEAR_PREFIX_LEN]
        if same_year and len(current_chunk) < effective_max:
            current_chunk.append(d)
        else:
            chunks.append((current_chunk[0], current_chunk[-1]))
            current_chunk = [d]

    if current_chunk:
        chunks.append((current_chunk[0], current_chunk[-1]))

    return chunks


def parse_modis_subset_items(items: list[dict[str, Any]]) -> pd.DataFrame:
    """PLAN §3 F7 E1 — Convierte lista de items subset de ORNL DAAC en DataFrame diario ordenado."""
    records: list[tuple[pd.Timestamp, float]] = []

    for item in items:
        band = item.get("band")
        if band is not None and band != MODIS_BAND_NDVI:
            continue

        if "calendar_date" in item and item["calendar_date"]:
            dt = pd.Timestamp(item["calendar_date"])
        elif "modis_date" in item and item["modis_date"]:
            dt = pd.to_datetime(str(item["modis_date"])[1:], format="%Y%j")
        else:
            continue

        raw_data = item.get("data")
        if not raw_data or raw_data[0] is None:
            ndvi_val = float(np.nan)
        else:
            raw_num = float(raw_data[0])
            if raw_num <= MODIS_FILL_THRESHOLD:
                ndvi_val = float(np.nan)
            else:
                ndvi_val = raw_num * MODIS_NDVI_SCALE

        records.append((dt, ndvi_val))

    if not records:
        df = pd.DataFrame({"ndvi": pd.Series(dtype="float64")})
        df.index = pd.DatetimeIndex([], name="date")
        return df

    dates = pd.DatetimeIndex([r[0] for r in records], name="date")
    values = np.array([r[1] for r in records], dtype="float64")
    df = pd.DataFrame({"ndvi": values}, index=dates)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df["ndvi"] = df["ndvi"].astype("float64")
    return df


def _season_peak_dates(season: int, hemisphere: Literal["N", "S"]) -> list[str]:
    """Genera las fechas MODIS AYYYYDDD del pico estival para una campaña agrícola."""
    if hemisphere == "S":
        target_year = season + 1
        doys = MODIS_SOUTH_PEAK_DOYS
    else:
        target_year = season
        doys = MODIS_NORTH_PEAK_DOYS
    return [f"A{target_year}{doy}" for doy in doys]


def _fetch_chunk_with_retries(
    http_client: httpx.Client,
    lat_r: float,
    lon_r: float,
    start_date: str,
    end_date: str,
    retry_delays: tuple[float, ...],
) -> list[dict[str, Any]]:
    """Consulta un bloque de fechas MODIS a ORNL DAAC con reintentos exponenciales."""
    url = f"{MODIS_API_BASE_URL}/subset"
    params = {
        "latitude": f"{lat_r:.{MODIS_COORD_DECIMALS}f}",
        "longitude": f"{lon_r:.{MODIS_COORD_DECIMALS}f}",
        "startDate": start_date,
        "endDate": end_date,
        "kmAboveBelow": 0,
        "kmLeftRight": 0,
        "band": MODIS_BAND_NDVI,
    }
    headers = {"Accept": "application/json"}
    max_attempts = len(retry_delays) + 1
    last_error: Exception | None = None

    for attempt in range(max_attempts):
        try:
            resp = http_client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                payload = resp.json()
                return list(payload.get("subset", []))
            last_error = httpx.HTTPStatusError(
                f"HTTP {resp.status_code} desde MODIS ORNL DAAC ({start_date}..{end_date})",
                request=resp.request,
                response=resp,
            )
        except Exception as exc:
            last_error = exc

        if attempt < max_attempts - 1:
            delay = retry_delays[attempt]
            if delay > 0:
                time.sleep(delay)

    raise ModisUnavailable(
        f"MODIS ORNL DAAC no disponible tras {max_attempts} intentos "
        f"({lat_r:.2f}, {lon_r:.2f}, {start_date}..{end_date}): {last_error}"
    ) from last_error


def _save_cache_atomic(
    cache_file: Path,
    lat_r: float,
    lon_r: float,
    seasons_fetched: set[int],
    items_by_key: dict[str, dict[str, Any]],
) -> None:
    """Guarda en disco de forma atómica el progreso incremental de MODIS."""
    sorted_items = sorted(
        items_by_key.values(),
        key=lambda it: (str(it.get("modis_date", "")), str(it.get("calendar_date", ""))),
    )
    payload = {
        "lat": lat_r,
        "lon": lon_r,
        "band": MODIS_BAND_NDVI,
        "dataset": MODIS_DATASET_LABEL,
        "seasons_fetched": sorted(seasons_fetched),
        "subset": sorted_items,
    }
    tmp_file = cache_file.with_suffix(".json.tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    tmp_file.replace(cache_file)


def _item_key(item: dict[str, Any]) -> str:
    """Clave determinista para deduplicar items de subset."""
    return f"{item.get('modis_date', '')}_{item.get('calendar_date', '')}_{item.get('band', '')}"


def fetch_modis_ndvi(
    lat: float,
    lon: float,
    seasons: list[int],
    cache_dir: Path | str | None = None,
    client: httpx.Client | None = None,
    offline_only: bool = False,
    retry_delays: tuple[float, ...] = MODIS_RETRY_DELAYS,
) -> pd.DataFrame | None:
    """PLAN §3 F7 E1 — Carga o descarga incremental de MODIS MOD13Q1 NDVI con caché en disco."""
    lat_r = round(float(lat), MODIS_COORD_DECIMALS)
    lon_r = round(float(lon), MODIS_COORD_DECIMALS)

    backend_dir = Path(__file__).resolve().parent.parent.parent
    if cache_dir is None:
        resolved_cache_dir = backend_dir / "cache" / "modis"
    else:
        resolved_cache_dir = Path(cache_dir)

    cache_file = resolved_cache_dir / f"{lat_r:.2f}_{lon_r:.2f}_MOD13Q1.json"
    demo_fixture_file = backend_dir / "tests" / "fixtures" / "modis_demo.json"

    local_source: Path | None = None
    if cache_file.exists():
        local_source = cache_file
    elif (
        cache_dir is None
        and (lat_r, lon_r) == (MODIS_DEMO_LAT, MODIS_DEMO_LON)
        and demo_fixture_file.exists()
    ):
        local_source = demo_fixture_file

    if offline_only:
        if local_source is None:
            return None
        with open(local_source, "r", encoding="utf-8") as f:
            raw_json = json.load(f)
        df = parse_modis_subset_items(list(raw_json.get("subset", [])))
        return None if df.empty else df

    resolved_cache_dir.mkdir(parents=True, exist_ok=True)
    hemisphere: Literal["N", "S"] = "S" if lat_r < 0 else "N"

    items_by_key: dict[str, dict[str, Any]] = {}
    seasons_fetched: set[int] = set()

    if local_source is not None:
        with open(local_source, "r", encoding="utf-8") as f:
            raw_json = json.load(f)
        for item in raw_json.get("subset", []):
            items_by_key[_item_key(item)] = item
        for s in raw_json.get("seasons_fetched", []):
            seasons_fetched.add(int(s))

        # Si el archivo no tenía seasons_fetched explícito, inferir por fechas presentes
        if not seasons_fetched and items_by_key:
            existing_df = parse_modis_subset_items(list(items_by_key.values()))
            for s in seasons:
                s_start = pd.Timestamp(get_season_start_date(s, hemisphere))
                s_end = pd.Timestamp(get_season_start_date(s + 1, hemisphere))
                if not existing_df.loc[(existing_df.index >= s_start) & (existing_df.index < s_end)].empty:
                    seasons_fetched.add(s)

    missing_seasons = [s for s in seasons if s not in seasons_fetched]
    if not missing_seasons:
        df = parse_modis_subset_items(list(items_by_key.values()))
        return None if df.empty else df

    lock = threading.Lock()

    def _fetch_one_season(http_client: httpx.Client, season: int) -> tuple[int, list[dict[str, Any]]]:
        dates = _season_peak_dates(season, hemisphere)
        chunks = chunk_modis_dates(dates, max_chunk=MODIS_SAFE_CHUNK_SIZE)
        season_items: list[dict[str, Any]] = []
        for start_d, end_d in chunks:
            chunk_items = _fetch_chunk_with_retries(
                http_client=http_client,
                lat_r=lat_r,
                lon_r=lon_r,
                start_date=start_d,
                end_date=end_d,
                retry_delays=retry_delays,
            )
            season_items.extend(chunk_items)
        return season, season_items

    def _run_with_client(http_client: httpx.Client) -> None:
        with ThreadPoolExecutor(max_workers=MODIS_MAX_WORKERS) as executor:
            futures = {
                executor.submit(_fetch_one_season, http_client, season): season
                for season in missing_seasons
            }
            for fut in as_completed(futures):
                season, season_items = fut.result()
                with lock:
                    for item in season_items:
                        items_by_key[_item_key(item)] = item
                    seasons_fetched.add(season)
                    _save_cache_atomic(
                        cache_file=cache_file,
                        lat_r=lat_r,
                        lon_r=lon_r,
                        seasons_fetched=seasons_fetched,
                        items_by_key=items_by_key,
                    )

    if client is not None:
        _run_with_client(client)
    else:
        with httpx.Client(timeout=MODIS_REQUEST_TIMEOUT) as default_client:
            _run_with_client(default_client)

    df = parse_modis_subset_items(list(items_by_key.values()))
    return None if df.empty else df


def compute_modis_backtest(
    modis_df: pd.DataFrame | None,
    baseline_seasons_out: list[SeasonOut],
    eval_seasons: list[int],
    hemisphere: Literal["N", "S"],
) -> ModisBacktestOut | None:
    """PLAN §3 F7 E1 — Calcula correlación Spearman y tercil inferior de NDVI máximo vs índice simulado."""
    if modis_df is None or modis_df.empty or not eval_seasons:
        return None

    season_map: dict[int, SeasonOut] = {s.season: s for s in baseline_seasons_out}
    paired: list[tuple[int, SeasonOut, float]] = []

    for season in eval_seasons:
        if season not in season_map:
            continue
        start_dt = pd.Timestamp(get_season_start_date(season, hemisphere))
        end_dt = pd.Timestamp(get_season_start_date(season + 1, hemisphere))
        sub = modis_df.loc[(modis_df.index >= start_dt) & (modis_df.index < end_dt)]
        valid_ndvi = sub["ndvi"].dropna()
        if valid_ndvi.empty:
            continue
        max_ndvi = float(valid_ndvi.max())
        paired.append((season, season_map[season], max_ndvi))

    if len(paired) < MODIS_MIN_PAIRED_SEASONS:
        return None

    ndvi_vals = np.array([p[2] for p in paired], dtype="float64")
    sim_indices = np.array([float(p[1].index) for p in paired], dtype="float64")

    spearman_res = stats.spearmanr(ndvi_vals, sim_indices, nan_policy="omit")
    rho = float(spearman_res[0])
    p_value = float(spearman_res[1])
    if np.isnan(rho) or np.isnan(p_value):
        return None

    tertile_threshold = float(np.quantile(ndvi_vals, MODIS_TERTILE_QUANTILE))

    series: list[ModisSeasonPoint] = []
    bad_in_low = 0
    total_bad = 0

    for season, s_out, max_ndvi in paired:
        in_low = bool(max_ndvi <= tertile_threshold)
        is_bad = bool(s_out.bad)
        if is_bad:
            total_bad += 1
            if in_low:
                bad_in_low += 1
        series.append(
            ModisSeasonPoint(
                season=season,
                label=s_out.label,
                max_ndvi=max_ndvi,
                sim_index=float(s_out.index),
                bad=is_bad,
                in_low_tertile=in_low,
            )
        )

    period_str = f"campañas {series[0].label}–{series[-1].label}"
    source = Source(
        dataset=MODIS_DATASET_LABEL,
        parameters=[MODIS_BAND_NDVI],
        period=period_str,
    )

    return ModisBacktestOut(
        spearman_rho=rho,
        p_value=p_value,
        tertile_threshold=tertile_threshold,
        bad_in_low_ndvi_tertile=bad_in_low,
        total_bad_seasons=total_bad,
        n_seasons=len(series),
        series=series,
        source=source,
    )
