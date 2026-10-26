"""Modelo de efectos mixtos para productividad.

Especificacion:

    productividad ~ visitas_tasa + riqueza + clima + paisaje + (1 | parcela)

Implementado con ``statsmodels`` (``MixedLM``). El ensamblado de predictores
(clima anual, contexto de paisaje y red) se realiza en el servicio que llama a
``fit_mixed_effects``.
"""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


FEATURES = [
    "visitas_tasa",
    "riqueza_polinizadores",
    "t_mean_anual_c",
    "gdd_anual",
    "precipitacion_anual_mm",
    "habitat_area_ha",
    "dist_habitat_m",
    "colmenas_cerca",
]

TARGET = "rendimiento_t_ha"
GROUP = "parcela"


def _formula(include_crop: bool = True) -> str:
    regressors = " + ".join(f"{f}" for f in FEATURES)
    crop = " + C(cultivo)" if include_crop else ""
    return f"{TARGET} ~ {regressors}{crop}"


def fit_mixed_effects(
    df: pd.DataFrame,
    include_crop: bool = True,
    reml: bool = True,
) -> Dict[str, object]:
    """Ajusta el modelo de efectos mixtos y devuelve un resumen serializable.

    ``df`` debe contener las columnas de ``FEATURES``, ``TARGET`` y ``GROUP``.
    """
    data = df.dropna(subset=[TARGET, GROUP] + FEATURES).copy()
    if data[GROUP].nunique() < 2:
        raise ValueError("Se requieren al menos 2 parcelas (grupos) para el modelo mixto")

    # Estandarizacion de predictores continuos para interpretabilidad y estabilidad.
    scaled = data.copy()
    scalers = {}
    for f in FEATURES:
        mu, sd = float(data[f].mean()), float(data[f].std(ddof=1) or 1.0)
        scalers[f] = {"media": mu, "sd": sd}
        scaled[f] = (data[f] - mu) / sd

    model = smf.mixedlm(_formula(include_crop), scaled, groups=scaled[GROUP],
                        re_formula="1")
    result = None
    last_err = None
    for method in ["bfgs", "lbfgs", "cg"]:
        try:
            result = model.fit(reml=reml, method=method)
            break
        except Exception as err:
            last_err = err
            continue

    if result is None:
        # Intento adicional con ML (reml=False) si REML falló
        for method in ["bfgs", "cg"]:
            try:
                result = model.fit(reml=False, method=method)
                break
            except Exception:
                pass

    if result is None:
        raise last_err or RuntimeError("No fue posible ajustar el modelo de efectos mixtos")

    ci = result.conf_int()
    coefs = []
    for name in result.params.index:
        coefs.append(
            {
                "variable": str(name),
                "coef": float(result.params[name]),
                "std_err": float(result.bse[name]) if name in result.bse else None,
                "p_value": float(result.pvalues[name]) if name in result.pvalues else None,
                "ci_low": float(ci.loc[name, 0]) if name in ci.index else None,
                "ci_high": float(ci.loc[name, 1]) if name in ci.index else None,
            }
        )

    random_var = float(result.cov_re.iloc[0, 0]) if result.cov_re.size else 0.0
    resid_var = float(result.scale)
    icc = random_var / (random_var + resid_var) if (random_var + resid_var) else 0.0

    # AIC/BIC: MixedLM con REML devuelve nan; se calculan con el numero de
    # parametros estimados (efectos fijos + varianza aleatoria + residual).
    llf = float(result.llf)
    k_params = len(result.params) + int(result.cov_re.size) + 1
    aic = float(result.aic) if np.isfinite(result.aic) else (-2.0 * llf + 2.0 * k_params)
    bic = float(result.bic) if np.isfinite(result.bic) else (
        -2.0 * llf + k_params * np.log(max(1, int(result.nobs)))
    )

    return {
        "formula": _formula(include_crop),
        "n_observaciones": int(result.nobs),
        "n_grupos": int(data[GROUP].nunique()),
        "coeficientes": coefs,
        "varianza_efecto_aleatorio": random_var,
        "varianza_residual": resid_var,
        "icc": icc,
        "log_likelihood": llf,
        "aic": aic,
        "bic": bic,
        "r2_condicional_aprox": _pseudo_r2(df, scaled, result),
        "escalado": scalers,
    }


def _pseudo_r2(original: pd.DataFrame, scaled: pd.DataFrame, result) -> Optional[float]:
    """R2 marginal aproximado sobre la escala estandarizada."""
    try:
        fitted = result.fittedvalues
        y = scaled[TARGET]
        ss_res = float(((y - fitted) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        return 1.0 - ss_res / ss_tot if ss_tot else 0.0
    except Exception:  # pragma: no cover
        return None


def predict_productivity(
    base_df: pd.DataFrame,
    coefs: Dict[str, float],
) -> np.ndarray:
    """Prediccion lineal simple a partir de coeficientes ya ajustados."""
    pred = np.full(len(base_df), coefs.get("Intercept", 0.0), dtype=float)
    for f, w in coefs.items():
        if f in base_df.columns:
            pred += w * base_df[f].to_numpy(dtype=float)
    return pred
