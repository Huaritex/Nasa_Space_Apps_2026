"""PLAN §3 F7 E1 y E2 — Tests 100% offline para MODIS ORNL DAAC backtest y perfil diversificada."""

import json
import math
from pathlib import Path
import re

from fastapi.testclient import TestClient
import httpx
import numpy as np
import pandas as pd
import pytest

from app.config import (
    DATA_END,
    DATA_START,
    MODIS_BAND_NDVI,
    MODIS_DATASET_LABEL,
    MODIS_DEMO_LAT,
    MODIS_DEMO_LON,
    MODIS_MAX_DATES_PER_REQUEST,
    MODIS_TERTILE_QUANTILE,
)
from app.engine.calendar import get_season_partitions, get_valid_seasons
from app.engine.cards import POWER_CANONICAL_PARAMS
from app.engine.et0 import add_et0
from app.engine.rotation import evaluate_rotation
from app.engine.soil import calc_soil_score
from app.engine.table import SlotTable
from app.main import app
from app.nasa.modis import (
    chunk_modis_dates,
    compute_modis_backtest,
    fetch_modis_ndvi,
    parse_modis_subset_items,
)
from app.nasa.power import parse_power_response
from app.pipeline import clear_analyze_cache
from app.schemas import Rotation, RotationCard, RotationYear, SlotIn


def _check_card_invariants_f1_f2_f3(card: RotationCard, profile_name: str) -> None:
    """Verifica invariantes F1, F2 y F3 sobre una RotationCard."""
    assert len(card.why) >= 1, f"{profile_name}: len(why) < 1"
    assert len(card.benefits) >= 1, f"{profile_name}: len(benefits) < 1"
    assert len(card.risks) >= 2, f"{profile_name}: len(risks) < 2"
    assert any("Resolución ≈50 km" in r.text for r in card.risks), (
        f"{profile_name}: falta advertencia de resolución regional"
    )

    for claim in card.why + card.benefits + card.risks:
        nums_in_text = re.findall(r"-?\d+(?:[.,]\d+)?", claim.text)
        ev_values_str = [str(e.value).replace(",", ".") for e in claim.evidence]
        for num in nums_in_text:
            num_clean = num.replace(",", ".")
            matched = False
            for ev_str in ev_values_str:
                if num_clean == ev_str:
                    matched = True
                    break
                try:
                    if float(num_clean) == float(ev_str):
                        matched = True
                        break
                except ValueError:
                    pass
            assert matched, (
                f"F1 violado en {profile_name}: '{num}' en '{claim.text}' "
                f"no está en {ev_values_str}"
            )

        for ev in claim.evidence:
            src = ev.source
            if src.dataset == "Regla agronómica":
                assert src.parameters == []
            else:
                assert set(src.parameters).issubset(POWER_CANONICAL_PARAMS)


def test_e1_modis_chunking_max_10_dates():
    """PLAN §3 F7 E1 — Bloques <= 10 fechas (y <= max_chunk) sin cruzar año calendario."""
    assert chunk_modis_dates([]) == []

    # 12 fechas dentro del mismo año -> 2 bloques (10 + 2)
    same_year_dates = [f"A2015{1 + 16 * i:03d}" for i in range(12)]
    chunks = chunk_modis_dates(same_year_dates, max_chunk=15)
    assert len(chunks) == 2
    assert chunks[0] == (same_year_dates[0], same_year_dates[MODIS_MAX_DATES_PER_REQUEST - 1])
    assert chunks[1] == (same_year_dates[MODIS_MAX_DATES_PER_REQUEST], same_year_dates[-1])

    # Cruce de año calendario -> nunca junta A2015 y A2016
    cross_year = ["A2015337", "A2015353", "A2016001", "A2016017", "A2016033"]
    chunks_cross = chunk_modis_dates(cross_year, max_chunk=10)
    assert chunks_cross == [("A2015337", "A2015353"), ("A2016001", "A2016033")]
    for start_d, end_d in chunks_cross:
        assert start_d[:5] == end_d[:5]


def test_e1_modis_parse_scaling_and_fill():
    """PLAN §3 F7 E1 — Escala 0.0001, fill <= -3000 a NaN y DatetimeIndex ordenado."""
    items = [
        {
            "modis_date": "A2020033",
            "calendar_date": "2020-02-02",
            "band": MODIS_BAND_NDVI,
            "data": [-3000],
        },
        {
            "modis_date": "A2020017",
            "calendar_date": "2020-01-17",
            "band": MODIS_BAND_NDVI,
            "data": [7850],
        },
        {
            "modis_date": "A2020049",
            "calendar_date": "2020-02-18",
            "band": MODIS_BAND_NDVI,
            "data": [-3500],
        },
        {
            "modis_date": "A2020065",
            "calendar_date": "2020-03-06",
            "band": "250m_16_days_EVI",
            "data": [6000],
        },
    ]

    df = parse_modis_subset_items(items)
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.is_monotonic_increasing
    assert list(df.columns) == ["ndvi"]
    assert df["ndvi"].dtype == np.float64
    assert len(df) == 3  # ignora banda EVI
    assert df.loc[pd.Timestamp("2020-01-17"), "ndvi"] == pytest.approx(0.7850)
    assert np.isnan(df.loc[pd.Timestamp("2020-02-02"), "ndvi"])
    assert np.isnan(df.loc[pd.Timestamp("2020-02-18"), "ndvi"])


def test_e1_modis_fetch_incremental_and_offline(tmp_path):
    """PLAN §3 F7 E1 — fetch_modis_ndvi offline_only=True sin red y caché incremental mockeado."""
    # Offline miss -> None inmediato sin red
    assert (
        fetch_modis_ndvi(
            lat=10.123,
            lon=20.456,
            seasons=[2020, 2021],
            cache_dir=tmp_path,
            offline_only=True,
        )
        is None
    )

    calls: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        calls.append(params)
        start_d = params["startDate"]
        year = int(start_d[1:5])
        return httpx.Response(
            200,
            json={
                "subset": [
                    {
                        "modis_date": f"A{year}017",
                        "calendar_date": f"{year}-01-17",
                        "band": MODIS_BAND_NDVI,
                        "data": [6500],
                    },
                    {
                        "modis_date": f"A{year}033",
                        "calendar_date": f"{year}-02-02",
                        "band": MODIS_BAND_NDVI,
                        "data": [7200],
                    },
                ]
            },
        )

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    df = fetch_modis_ndvi(
        lat=-17.304,
        lon=-62.249,
        seasons=[2020, 2021],
        cache_dir=tmp_path,
        client=mock_client,
        offline_only=False,
    )
    assert df is not None
    assert len(calls) == 2
    cache_file = tmp_path / "-17.30_-62.25_MOD13Q1.json"
    assert cache_file.exists()

    # Segunda llamada offline_only=True lee caché sin tocar red
    df_offline = fetch_modis_ndvi(
        lat=-17.30,
        lon=-62.25,
        seasons=[2020, 2021],
        cache_dir=tmp_path,
        offline_only=True,
    )
    assert df_offline is not None
    assert len(df_offline) == 4
    assert len(calls) == 2


def test_e1_modis_backtest_computation_demo():
    """PLAN §3 F7 E1 — Backtest MODIS usando fixtures locales modis_demo.json + power_demo.json."""
    fixtures_dir = Path(__file__).resolve().parent / "fixtures"
    power_path = fixtures_dir / "power_demo.json"
    modis_path = fixtures_dir / "modis_demo.json"
    assert modis_path.exists(), "Falta backend/tests/fixtures/modis_demo.json"

    with open(power_path, "r", encoding="utf-8") as f:
        power_data = parse_power_response(json.load(f))
    with open(modis_path, "r", encoding="utf-8") as f:
        modis_df = parse_modis_subset_items(json.load(f)["subset"])

    hemisphere = "S"
    seasons = get_valid_seasons(hemisphere)
    eval_seasons = get_season_partitions(seasons)["eval"]

    weather_df = add_et0(
        power_data.df, lat=MODIS_DEMO_LAT, elevation_m=power_data.elevation_m
    )
    slot_table = SlotTable(weather_df, MODIS_DEMO_LAT, "franco", seasons=seasons)
    baseline_rot = Rotation(
        years=[
            RotationYear(
                slots=[
                    SlotIn(crop_id="soya", sow_date="11-16"),
                    SlotIn(crop_id="soya", sow_date="05-01"),
                ]
            )
        ]
    )
    soil = calc_soil_score(baseline_rot, hemisphere, soil_texture="franco", eval_seasons=eval_seasons)
    _, seasons_out, _ = evaluate_rotation(
        baseline_rot, slot_table, seasons, hemisphere, soil_score=soil
    )

    backtest = compute_modis_backtest(
        modis_df=modis_df,
        baseline_seasons_out=seasons_out,
        eval_seasons=eval_seasons,
        hemisphere=hemisphere,
    )
    assert backtest is not None
    assert backtest.n_seasons == 20
    assert len(backtest.series) == 20
    assert math.isfinite(backtest.spearman_rho)
    assert math.isfinite(backtest.p_value)
    assert 0.0 <= backtest.p_value <= 1.0
    assert math.isfinite(backtest.tertile_threshold)
    assert backtest.bad_in_low_ndvi_tertile <= backtest.total_bad_seasons
    assert backtest.source.dataset == MODIS_DATASET_LABEL
    assert backtest.source.parameters == [MODIS_BAND_NDVI]

    # Verificar consistencia exacta del umbral de tercil
    ndvis = [pt.max_ndvi for pt in backtest.series]
    expected_thr = float(np.quantile(ndvis, MODIS_TERTILE_QUANTILE))
    assert backtest.tertile_threshold == pytest.approx(expected_thr)


def test_e2_analyze_with_diversified_returns_4_profiles(monkeypatch):
    """PLAN §3 F7 E2 — POST /analyze con include_diversified=True devuelve 4 perfiles e invariantes F1/F2/F3."""
    clear_analyze_cache()
    power_path = Path(__file__).resolve().parent / "fixtures" / "power_demo.json"
    with open(power_path, "r", encoding="utf-8") as f:
        mock_power_data = parse_power_response(json.load(f))

    monkeypatch.setattr(
        "app.pipeline.fetch_power",
        lambda lat, lon, start=DATA_START, end=DATA_END, client=None: mock_power_data,
    )

    payload = {
        "lat": -17.30,
        "lon": -62.25,
        "soil_texture": "franco",
        "current_rotation": {
            "years": [
                {
                    "slots": [
                        {"crop_id": "soya", "sow_date": "11-16"},
                        {"crop_id": "soya", "sow_date": "05-01"},
                    ]
                }
            ]
        },
        "include_diversified": True,
    }

    client = TestClient(app)
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    profiles = [r["profile"] for r in data["rotations"]]
    assert profiles == ["actual", "adaptada", "regenerativa", "diversificada"]

    for rot in data["rotations"]:
        card = RotationCard.model_validate(rot["card"])
        _check_card_invariants_f1_f2_f3(card, rot["profile"])

    assert data["modis_backtest"] is not None
    assert data["modis_backtest"]["n_seasons"] == 20
    assert data["modis_backtest"]["source"]["parameters"] == [MODIS_BAND_NDVI]
