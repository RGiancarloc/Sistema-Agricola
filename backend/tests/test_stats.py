"""Pruebas del modelo de efectos mixtos."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.stats.mixed_effects import FEATURES, fit_mixed_effects


def _toy_df(n_groups: int = 12, n_per: int = 8, beta: float = 2.0) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for g in range(n_groups):
        g_effect = rng.normal(0, 0.5)
        for _ in range(n_per):
            x = rng.normal()
            rows.append({
                "parcela": f"g{g}",
                "cultivo": "palto",
                "rendimiento_t_ha": 10 + beta * x + g_effect + rng.normal(0, 0.3),
                "visitas_tasa": x,
                "riqueza_polinizadores": rng.normal(5, 1),
                "t_mean_anual_c": rng.normal(21, 1),
                "gdd_anual": rng.normal(2000, 50),
                "precipitacion_anual_mm": rng.normal(3, 1),
                "habitat_area_ha": rng.normal(10, 2),
                "dist_habitat_m": rng.normal(500, 50),
                "colmenas_cerca": rng.normal(20, 5),
            })
    return pd.DataFrame(rows)


def test_fit_recovers_positive_effect():
    df = _toy_df()
    res = fit_mixed_effects(df)
    coefs = {c["variable"]: c["coef"] for c in res["coeficientes"]}
    assert "visitas_tasa" in coefs
    assert coefs["visitas_tasa"] > 0
    assert 0.0 <= res["icc"] <= 1.0
    assert res["n_grupos"] == 12


def test_requires_multiple_groups():
    df = _toy_df(n_groups=1)
    try:
        fit_mixed_effects(df)
        raised = False
    except ValueError:
        raised = True
    assert raised
