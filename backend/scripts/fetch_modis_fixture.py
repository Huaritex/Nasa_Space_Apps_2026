#!/usr/bin/env python3
"""PLAN §3 F7 E1 — Descarga del fixture demo real de NASA MODIS (MOD13Q1) para Santa Cruz.

Descarga los 4 compuestos de pico estival (A{y+1}017..A{y+1}065) para las 20 campañas
eval (2005..2024) en Santa Cruz (-17.30, -62.25) desde ORNL DAAC de forma incremental,
guardando en backend/cache/modis/-17.30_-62.25_MOD13Q1.json y backend/tests/fixtures/modis_demo.json.
"""

import json
from pathlib import Path
import shutil
import sys

# Asegurar backend/ en sys.path para importaciones de app.*
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pandas as pd

from app.config import MODIS_DEMO_LAT, MODIS_DEMO_LON
from app.engine.calendar import (
    get_hemisphere,
    get_season_partitions,
    get_season_start_date,
    get_valid_seasons,
)
from app.nasa.modis import fetch_modis_ndvi


def main() -> int:
    lat = MODIS_DEMO_LAT
    lon = MODIS_DEMO_LON
    hemisphere = get_hemisphere(lat)
    valid_seasons = get_valid_seasons(hemisphere)
    eval_seasons = get_season_partitions(valid_seasons)["eval"]

    print(
        f"=== Descarga de fixture demo NASA MODIS (MOD13Q1): Santa Cruz ({lat:.2f}, {lon:.2f}) ==="
    )
    print(f"Campañas eval ({len(eval_seasons)}): {eval_seasons[0]}..{eval_seasons[-1]}")

    cache_dir = backend_dir / "cache" / "modis"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{lat:.2f}_{lon:.2f}_MOD13Q1.json"

    fixtures_dir = backend_dir / "tests" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture_file = fixtures_dir / "modis_demo.json"

    modis_df = fetch_modis_ndvi(
        lat=lat,
        lon=lon,
        seasons=eval_seasons,
        cache_dir=cache_dir,
        offline_only=False,
    )

    if modis_df is None or modis_df.empty:
        print("ERROR: No se obtuvieron datos MODIS.", file=sys.stderr)
        return 1

    if not cache_file.exists():
        print(f"ERROR: No se encontró el archivo de caché: {cache_file}", file=sys.stderr)
        return 1

    with open(cache_file, "r", encoding="utf-8") as f:
        raw_json = json.load(f)

    seasons_fetched = raw_json.get("seasons_fetched", [])
    subset_items = raw_json.get("subset", [])
    print(
        f"Caché actualizado: {cache_file} "
        f"({len(seasons_fetched)} campañas en seasons_fetched, {len(subset_items)} items)"
    )

    # Verificar que cada una de las 20 campañas tenga al menos 1 observación válida
    missing_valid: list[int] = []
    for y in eval_seasons:
        start_dt = pd.Timestamp(get_season_start_date(y, hemisphere))
        end_dt = pd.Timestamp(get_season_start_date(y + 1, hemisphere))
        sub = modis_df.loc[(modis_df.index >= start_dt) & (modis_df.index < end_dt)]
        valid = sub["ndvi"].dropna()
        if valid.empty:
            missing_valid.append(y)
        else:
            print(
                f"  Campaña {y}/{(y + 1) % 100:02d}: "
                f"n={len(valid)} obs válidas, max_ndvi={valid.max():.4f}"
            )

    if missing_valid:
        print(
            f"ERROR: Faltan observaciones NDVI válidas en campañas: {missing_valid}",
            file=sys.stderr,
        )
        return 1

    shutil.copyfile(cache_file, fixture_file)
    print(f"\n[OK] Fixture guardado en: {fixture_file} ({fixture_file.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
