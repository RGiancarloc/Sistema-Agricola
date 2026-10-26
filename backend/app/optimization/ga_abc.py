"""Metaheuristica hibrida GA-ABC (Algoritmo Genetico + Colonia Artificial de Abejas).

Representacion: vector de enteros de longitud ``n_parcelas``; el valor 0 indica
"sin intervencion" y ``1..K`` indexa la intervencion aplicada.

Ciclo hibrido por generacion:

1. Fase de abejas empleadas (ABC): cada fuente genera un vecino por cambio de un
   gen y se queda con el mejor (busqueda local codiciosa).
2. Fase genetica: seleccion por torneo, cruce uniforme y mutacion para generar
   descendencia (diversificacion global).
3. Fase de abejas observadoras: seleccion proporcional a la aptitud + fase de
   exploradoras (scout) que reinician fuentes estancadas tras ``limit`` intentos.
4. Elitismo: los mejores individuos se preservan.

Es reproducible: recibe un ``numpy.random.Generator``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import numpy as np

from app.core.config import params
from app.optimization.common import (
    Intervention,
    Parcel,
    default_weights,
    evaluate,
    penalty_objective,
)


@dataclass
class GAABCResult:
    mejor_asignacion: Dict[int, str]
    beneficio: float
    costo: float
    area_ha: float
    factible: bool
    historial: List[float]
    generaciones: int
    tiempo_s: float


def _decode(vec: np.ndarray, parcels: Sequence[Parcel],
            codes: Sequence[str]) -> Dict[int, str]:
    return {p.id: (codes[int(v) - 1] if v > 0 else None)  # type: ignore[dict-item]
            for p, v in zip(parcels, vec)}


def _fitness(vec, parcels, interventions, codes, budget, max_area, weights):
    metrics = evaluate(_decode(vec, parcels, codes), parcels, interventions,
                       budget, max_area, weights)
    return penalty_objective(metrics, budget, max_area), metrics


def solve_ga_abc(
    parcels: Sequence[Parcel],
    interventions: Sequence[Intervention],
    budget: Optional[float] = None,
    max_area_ha: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
    seed: int = 42,
) -> GAABCResult:
    cfg = params()["optimization"]
    gcfg = cfg["ga_abc"]
    budget = cfg["budget_usd"] if budget is None else budget
    max_area_ha = cfg["max_intervention_area_ha"] if max_area_ha is None else max_area_ha
    w = weights or default_weights()

    rng = np.random.default_rng(seed)
    P = list(parcels)
    I = list(interventions)
    n = len(P)
    K = len(I)
    codes = [iv.codigo for iv in I]
    iv_map = {iv.codigo: iv for iv in I}

    pop_size = min(gcfg["population"], max(4, n))
    food_sources = min(gcfg["food_sources"], pop_size)
    limit = gcfg["limit"]
    pc = gcfg["crossover_rate"]
    pm = gcfg["mutation_rate"]
    elite = gcfg["elite"]

    # Inicializacion sesgada: preferir "sin intervencion" y baja densidad de 1s.
    pop = np.zeros((pop_size, n), dtype=int)
    for r in range(pop_size):
        ndens = rng.uniform(0.05, 0.4)
        mask = rng.random(n) < ndens
        pop[r, mask] = rng.integers(1, K + 1, size=int(mask.sum()))
    # Fila 0: sin intervenciones (linea base de comparacion).
    pop[0, :] = 0

    fitness = np.array([
        _fitness(pop[r], P, iv_map, codes, budget, max_area_ha, w)[0]
        for r in range(pop_size)
    ])
    trials = np.zeros(pop_size, dtype=int)
    history: List[float] = []

    def _tournament() -> np.ndarray:
        idx = rng.integers(0, pop_size, size=3)
        best = idx[np.argmax(fitness[idx])]
        return pop[best].copy()

    t0 = time.perf_counter()
    gen = 0
    for gen in range(1, gcfg["generations"] + 1):
        # --- 1. Abejas empleadas ---
        for r in range(food_sources):
            cand = pop[r].copy()
            js = rng.integers(0, n)
            cand[js] = rng.integers(0, K + 1)
            f_cand, _ = _fitness(cand, P, iv_map, codes, budget, max_area_ha, w)
            if f_cand > fitness[r]:
                pop[r], fitness[r], trials[r] = cand, f_cand, 0
            else:
                trials[r] += 1

        # --- 2. Fase genetica: descendencia ---
        offspring = []
        while len(offspring) < pop_size:
            pa, pb = _tournament(), _tournament()
            if rng.random() < pc:
                mask = rng.random(n) < 0.5
                child = np.where(mask, pa, pb)
            else:
                child = pa.copy()
            mut = rng.random(n) < pm
            child[mut] = rng.integers(0, K + 1, size=int(mut.sum()))
            offspring.append(child)
        offspring = np.array(offspring)
        off_fit = np.array([
            _fitness(offspring[r], P, iv_map, codes, budget, max_area_ha, w)[0]
            for r in range(len(offspring))
        ])

        # --- 3. Abejas observadoras (proporcional a la aptitud) ---
        fit_shift = fitness - fitness.min() + 1e-6
        probs = fit_shift / fit_shift.sum()
        for _ in range(food_sources):
            r = int(rng.choice(food_sources, p=probs[:food_sources] / probs[:food_sources].sum()))
            cand = pop[r].copy()
            js = rng.integers(0, n)
            cand[js] = rng.integers(0, K + 1)
            f_cand, _ = _fitness(cand, P, iv_map, codes, budget, max_area_ha, w)
            if f_cand > fitness[r]:
                pop[r], fitness[r], trials[r] = cand, f_cand, 0
            else:
                trials[r] += 1

        # --- Scout: reinicia fuentes estancadas ---
        for r in range(food_sources):
            if trials[r] >= limit:
                ndens = rng.uniform(0.05, 0.4)
                m = rng.random(n) < ndens
                pop[r] = 0
                pop[r, m] = rng.integers(1, K + 1, size=int(m.sum()))
                fitness[r], trials[r] = _fitness(
                    pop[r], P, iv_map, codes, budget, max_area_ha, w)[0], 0

        # --- Seleccion: elitismo + mejores entre poblacion y descendencia ---
        combined = np.vstack([pop, offspring])
        combined_fit = np.concatenate([fitness, off_fit])
        order = np.argsort(-combined_fit)
        new_pop = combined[order[:pop_size]].copy()
        new_fit = combined_fit[order[:pop_size]].copy()
        # preserva elites exactos y rotacion de trials
        for e in range(elite):
            new_pop[e] = combined[order[e]]
            new_fit[e] = combined_fit[order[e]]
        pop, fitness = new_pop, new_fit
        trials = np.zeros(pop_size, dtype=int)
        history.append(float(fitness.max()))

    best_idx = int(np.argmax(fitness))
    best_vec = pop[best_idx]
    best_assign = _decode(best_vec, P, codes)
    metrics = evaluate(best_assign, P, iv_map, budget, max_area_ha, w)
    elapsed = time.perf_counter() - t0

    return GAABCResult(
        mejor_asignacion=best_assign,
        beneficio=metrics["beneficio"],
        costo=metrics["costo"],
        area_ha=metrics["area_ha"],
        factible=metrics["factible"],
        historial=history,
        generaciones=gen,
        tiempo_s=round(elapsed, 4),
    )
