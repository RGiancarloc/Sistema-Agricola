"""Indicadores de servicios ecosistemicos y score agregado.

Todos los indicadores se normalizan a [0, 1] para poder combinarlos en un
score ponderado (pesos configurables en ``params.yaml -> ecosystem.weights``).
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np

from app.core.config import params


def pollination_service(
    visitas_tasa: float,
    riqueza: float,
    k_visitas: float = 0.06,
    k_riqueza: float = 0.12,
) -> float:
    """Servicio de polinizacion (0-1) con saturacion."""
    raw = 1.0 - math.exp(-(k_visitas * max(0.0, visitas_tasa) + k_riqueza * max(0.0, riqueza)))
    return float(np.clip(raw, 0.0, 1.0))


def productivity_score(rendimiento_t_ha: float, rendimiento_potencial_t_ha: float) -> float:
    """Productividad relativa al potencial agronomico (0-1, cap 1)."""
    if rendimiento_potencial_t_ha <= 0:
        return 0.0
    return float(np.clip(rendimiento_t_ha / rendimiento_potencial_t_ha, 0.0, 1.0))


def biodiversity_score(
    riqueza: float,
    riqueza_max: float,
    habitat_area_ha: float,
    habitat_area_ref: float,
    conectividad: float,
) -> float:
    """Biodiversidad en funcion de riqueza, habitat y conectividad."""
    r = (riqueza / riqueza_max) if riqueza_max > 0 else 0.0
    h = (habitat_area_ha / habitat_area_ref) if habitat_area_ref > 0 else 0.0
    return float(np.clip(0.5 * r + 0.3 * min(1.0, h) + 0.2 * conectividad, 0.0, 1.0))


def aggregate_score(
    productividad: float,
    polinizacion: float,
    biodiversidad: float,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    w = weights or params()["ecosystem"]["weights"]
    total = sum(w.values()) or 1.0
    return float(
        (w.get("productividad", 0) * productividad
         + w.get("polinizacion", 0) * polinizacion
         + w.get("biodiversidad", 0) * biodiversidad) / total
    )


def ecosystem_summary(
    rendimiento_t_ha: float,
    rendimiento_potencial_t_ha: float,
    visitas_tasa: float,
    riqueza: float,
    habitat_area_ha: float,
    riqueza_max: float = 30.0,
    habitat_area_ref: float = 50.0,
    conectividad: float = 0.5,
) -> Dict[str, float]:
    """Resumen de indicadores + score agregado para una unidad."""
    prod = productivity_score(rendimiento_t_ha, rendimiento_potencial_t_ha)
    pol = pollination_service(visitas_tasa, riqueza)
    biod = biodiversity_score(riqueza, riqueza_max, habitat_area_ha, habitat_area_ref, conectividad)
    return {
        "productividad": prod,
        "polinizacion": pol,
        "biodiversidad": biod,
        "score": aggregate_score(prod, pol, biod),
    }
