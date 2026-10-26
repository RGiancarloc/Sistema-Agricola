"""Formulacion MIQCP (Mixed-Integer Quadratically Constrained Program) con Pyomo.

Variables:
    x[i,k] in {0,1}   : parcela i recibe intervencion k
    a[i,k] in [0, A_i]: area intervenida de la parcela i con la intervencion k

Restricciones:
    a[i,k] <= A_i * x[i,k]                                   (acoplamiento)
    sum_{i,k} a[i,k]  <= area_max                            (area)
    sum_{i,k} costo(i,k) * x[i,k] + costo_ha * a[i,k] <= P   (presupuesto)
    sum_k x[i,k] <= 1                                        (a lo sumo una)

Objetivo: maximizar beneficio. Se incluye, opcionalmente, un termino convexo
cuadratico (rendimientos decrecientes al concentrar una intervencion) que
convierte el problema en MIQCP. Si el solver disponible no soporta MIQP, se
resuelve la version lineal (MILP) y se reporta explicitamente.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Sequence

import pyomo.environ as pyo

from app.core.config import params
from app.core.logging import get_logger
from app.optimization.common import (
    Intervention,
    Parcel,
    default_weights,
    intervention_benefit,
    intervention_cost,
)

logger = get_logger(__name__)
# Silencia el log verboso del solver HiGHS.
import logging as _logging

_logging.getLogger("pyomo.contrib.appsi.solvers.highs").setLevel(_logging.WARNING)

_SOLVER_PRIORITY = ["appsi_highs", "cbc", "glpk", "appsi_glpk"]


def available_solver(prefer: Optional[str] = None) -> Optional[str]:
    candidates = [prefer] if prefer else []
    candidates += [s for s in _SOLVER_PRIORITY if s not in candidates]
    for name in candidates:
        if not name:
            continue
        try:
            if pyo.SolverFactory(name).available(exception_flag=False):
                return name
        except Exception:  # pragma: no cover
            continue
    return None


def solve_miqcp(
    parcels: Sequence[Parcel],
    interventions: Sequence[Intervention],
    budget: Optional[float] = None,
    max_area_ha: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
    time_limit: Optional[int] = None,
    quadratic: bool = True,
) -> Dict[str, object]:
    cfg = params()["optimization"]
    budget = cfg["budget_usd"] if budget is None else budget
    max_area_ha = cfg["max_intervention_area_ha"] if max_area_ha is None else max_area_ha
    time_limit = cfg["time_limit_s"] if time_limit is None else time_limit
    w = weights or default_weights()

    solver_name = available_solver()
    # HiGHS no resuelve MIQP: se usa la relajacion lineal del objetivo.
    use_quadratic = quadratic and solver_name not in ("appsi_highs", None)

    model = pyo.ConcreteModel("miqcp_intervenciones")
    P = list(parcels)
    I = list(interventions)
    model.i = pyo.Set(initialize=[p.id for p in P])
    model.k = pyo.Set(initialize=[iv.codigo for iv in I])
    parea = {p.id: p.area_ha for p in P}
    pdef = {p.id: p.deficit for p in P}
    imap = {iv.codigo: iv for iv in I}

    model.x = pyo.Var(model.i, model.k, domain=pyo.Binary)
    model.a = pyo.Var(model.i, model.k, domain=pyo.NonNegativeReals)

    def area_coupling(m, i, k):
        return m.a[i, k] <= parea[i] * m.x[i, k]

    model.area_coupling = pyo.Constraint(model.i, model.k, rule=area_coupling)
    model.at_most_one = pyo.Constraint(
        model.i, rule=lambda m, i: sum(m.x[i, k] for k in m.k) <= 1
    )
    model.area_budget = pyo.Constraint(
        expr=sum(model.a[i, k] for i in model.i for k in model.k) <= max_area_ha
    )

    def budget_rule(m):
        return sum(
            (imap[k].costo_usd_ha * m.a[i, k] + imap[k].costo_usd_fijo * m.x[i, k])
            for i in m.i for k in m.k
        ) <= budget

    model.budget = pyo.Constraint(rule=budget_rule)

    ben_map = {
        (p.id, iv.codigo): intervention_benefit(iv, p.area_ha, p.deficit, w) / max(1e-9, p.area_ha)
        for p in P for iv in I
    }

    def obj_rule(m):
        linear = sum(ben_map[(i, k)] * m.a[i, k] for i in m.i for k in m.k)
        if use_quadratic:
            # Termino convexo: penaliza concentracion excesiva (diversificacion).
            quad = -0.0005 * sum(m.a[i, k] ** 2 for i in m.i for k in m.k)
            return linear + quad
        return linear

    model.obj = pyo.Objective(rule=obj_rule, sense=pyo.maximize)

    result = {
        "solver": solver_name or "ninguno",
        "cuadratico": use_quadratic,
        "nota": (
            "MIQCP resuelto con termino cuadratico" if use_quadratic
            else "MILP: objetivo linealizado (solver sin soporte MIQP)"
        ),
    }

    if solver_name is None:
        result.update({"status": "sin_solver", "asignacion": [], "beneficio": 0.0,
                       "costo": 0.0, "area_ha": 0.0})
        return result

    opt = pyo.SolverFactory(solver_name)
    try:
        opt.options["time_limit"] = int(time_limit)
        if solver_name == "appsi_highs":
            opt.options["mip_rel_gap"] = 0.01
    except Exception:  # pragma: no cover
        pass

    t0 = time.perf_counter()
    try:
        res = opt.solve(model, tee=False)
    except Exception as exc:  # pragma: no cover
        logger.warning("Fallo del solver %s: %s", solver_name, exc)
        result.update({"status": "error", "detalle": str(exc), "asignacion": [],
                       "beneficio": 0.0, "costo": 0.0, "area_ha": 0.0})
        return result
    elapsed = time.perf_counter() - t0

    assignment = []
    benefit = cost = area = 0.0
    for i in model.i:
        for k in model.k:
            if pyo.value(model.x[i, k]) > 0.5:
                a = float(pyo.value(model.a[i, k]))
                if a <= 1e-6:
                    continue
                iv = imap[k]
                assignment.append({
                    "parcela_id": i, "intervencion": k, "area_ha": a,
                    "costo_usd": iv.costo_usd_fijo + iv.costo_usd_ha * a,
                })
                benefit += intervention_benefit(iv, a, pdef[i], w)
                cost += iv.costo_usd_fijo + iv.costo_usd_ha * a
                area += a

    term = str(res.solver.termination_condition) if hasattr(res, "solver") else "ok"
    result.update({
        "status": term,
        "tiempo_s": round(elapsed, 4),
        "beneficio": float(pyo.value(model.obj)),
        "beneficio_recomputado": float(benefit),
        "costo": float(cost),
        "area_ha": float(area),
        "presupuesto": budget,
        "area_max_ha": max_area_ha,
        "asignacion": assignment,
        "n_intervenciones": len(assignment),
    })
    return result
