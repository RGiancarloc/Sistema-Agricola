"""Pruebas de optimizacion (MIQCP y GA-ABC)."""
from __future__ import annotations

from app.optimization.common import Intervention, Parcel, evaluate
from app.optimization.ga_abc import solve_ga_abc
from app.optimization.miqcp import solve_miqcp

PARCELS = [Parcel(id=i, area_ha=2.0 + i, cultivo="palto", deficit=0.5) for i in range(1, 11)]
IVS = [
    Intervention("habitat_floral", "HF", 1200, 0, 0.12, 0.20, 0.05),
    Intervention("colmena_manejo", "CM", 0, 600, 0.15, 0.02, 0.08),
    Intervention("riego_eficiente", "RE", 800, 0, 0.0, 0.05, 0.10),
]


def test_evaluate_budget_infeasible():
    assignment = {p.id: "habitat_floral" for p in PARCELS}
    m = evaluate(assignment, PARCELS, {i.codigo: i for i in IVS},
                 budget=1000, max_area_ha=1000)
    assert not m["factible"]
    assert m["costo"] > 1000


def test_miqcp_feasible_and_within_budget():
    res = solve_miqcp(PARCELS, IVS, budget=20000, max_area_ha=20)
    if res["status"] == "sin_solver":
        return  # entorno sin solver: se omite
    assert res["costo"] <= 20000 + 1e-6
    assert res["area_ha"] <= 20 + 1e-6


def test_ga_abc_improves_over_no_intervention():
    iv_map = {i.codigo: i for i in IVS}
    baseline = evaluate({p.id: None for p in PARCELS}, PARCELS, iv_map, 20000, 20)
    res = solve_ga_abc(PARCELS, IVS, budget=20000, max_area_ha=20, seed=1)
    assert res.factible
    assert res.beneficio >= baseline["beneficio"] - 1e-9
    assert res.costo <= 20000 + 1e-6
