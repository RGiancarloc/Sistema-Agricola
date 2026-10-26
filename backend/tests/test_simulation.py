"""Pruebas del motor de simulacion."""
from __future__ import annotations

from app.simulation.engine import scenario_delta, simulate_scenario


def test_scenario_delta_monotonic():
    d_2024 = scenario_delta("ssp585", 2024)
    d_2050 = scenario_delta("ssp585", 2050)
    assert d_2024 == (0.0, 0.0)
    assert d_2050[0] > 0
    assert d_2050[1] < 0


def test_scenario_delta_baseline_zero():
    assert scenario_delta("linea_base", 2040) == (0.0, 0.0)


def test_simulate_returns_series(session):
    res = simulate_scenario(session, "ssp245", persist=False)
    assert res["n_parcelas"] > 0
    assert len(res["serie"]) > 10
    for row in res["serie"]:
        assert row["productividad_media_t_ha"] >= 0
        assert 0.0 <= row["score_medio"] <= 1.0
        assert 0.0 <= row["deficit_polinizacion_medio"] <= 1.0


def test_more_severe_warming_reduces_productivity(session):
    base = simulate_scenario(session, "linea_base", persist=False)
    severe = simulate_scenario(session, "ssp585", persist=False)
    base_final = base["resumen"]["productividad_final"]
    severe_final = severe["resumen"]["productividad_final"]
    assert severe_final <= base_final + 1e-9
