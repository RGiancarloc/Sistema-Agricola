"""Estructuras comunes y funcion objetivo compartida por los optimizadores.

Decision: cada parcela elige a lo sumo una intervencion (o ninguna). El
problema es un problema de asignacion con restricciones de presupuesto y area.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from app.core.config import params


@dataclass(frozen=True)
class Parcel:
    id: int
    area_ha: float
    cultivo: str
    deficit: float = 0.5  # deficit de polinizacion (0-1)


@dataclass(frozen=True)
class Intervention:
    codigo: str
    nombre: str
    costo_usd_ha: float
    costo_usd_fijo: float
    efecto_polinizacion: float
    efecto_biodiversidad: float
    efecto_productividad: float


def default_weights() -> Dict[str, float]:
    return params()["ecosystem"]["weights"]


def intervention_cost(iv: Intervention, area_ha: float) -> float:
    return iv.costo_usd_fijo + iv.costo_usd_ha * area_ha


def intervention_benefit(iv: Intervention, area_ha: float, deficit: float,
                         weights: Optional[Dict[str, float]] = None) -> float:
    w = weights or default_weights()
    unit = (
        w.get("productividad", 0.0) * iv.efecto_productividad
        + w.get("polinizacion", 0.0) * iv.efecto_polinizacion
        + w.get("biodiversidad", 0.0) * iv.efecto_biodiversidad
    )
    # Mayor beneficio marginal donde hay mayor deficit de polinizacion.
    return unit * area_ha * (1.0 + deficit)


def evaluate(
    assignment: Dict[int, str],
    parcels: Sequence[Parcel],
    interventions: Dict[str, Intervention],
    budget: float,
    max_area_ha: float,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, object]:
    """Evalua una asignacion {parcela_id: codigo_intervencion}."""
    by_id = {p.id: p for p in parcels}
    benefit = cost = area = 0.0
    detalle: List[dict] = []
    for pid, code in assignment.items():
        if code is None or code not in interventions:
            continue
        p = by_id.get(pid)
        if p is None:
            continue
        iv = interventions[code]
        benefit += intervention_benefit(iv, p.area_ha, p.deficit, weights)
        cost += intervention_cost(iv, p.area_ha)
        area += p.area_ha
        detalle.append({"parcela_id": pid, "intervencion": code, "area_ha": p.area_ha})
    feasible = (cost <= budget + 1e-6) and (area <= max_area_ha + 1e-6)
    return {
        "beneficio": float(benefit),
        "costo": float(cost),
        "area_ha": float(area),
        "factible": bool(feasible),
        "detalle": detalle,
    }


def penalty_objective(metrics: Dict[str, object], budget: float,
                      max_area_ha: float, big: float = 1e6) -> float:
    """Objetivo con penalizacion para busquedas metaheuristicas."""
    fit = float(metrics["beneficio"])
    if float(metrics["costo"]) > budget:
        fit -= big * (float(metrics["costo"]) - budget)
    if float(metrics["area_ha"]) > max_area_ha:
        fit -= big * (float(metrics["area_ha"]) - max_area_ha)
    return fit
