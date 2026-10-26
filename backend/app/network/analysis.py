"""Metricas de red bipartita planta-polinizador.

Implementa, sobre una matriz de visitas (filas = plantas, columnas =
polinizadores):

- grado y distribucion de grados,
- connectance,
- anidamiento (NODF),
- modularidad (Louvain sobre el grafo),
- robustez a la extincion secuencial de polinizadores (extinciones secundarias).

Todas las funciones son puras y facilmente verificables con matrices pequenas.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import networkx as nx
import numpy as np


@dataclass
class BipartiteNetwork:
    """Matriz de visitas con etiquetas de plantas y polinizadores."""

    matrix: np.ndarray  # (n_plantas, n_polinizadores), no negativa
    plants: List[str]
    pollinators: List[str]

    @property
    def binary(self) -> np.ndarray:
        return (self.matrix > 0).astype(int)

    @property
    def n_plants(self) -> int:
        return self.matrix.shape[0]

    @property
    def n_pollinators(self) -> int:
        return self.matrix.shape[1]


# ---------------------------------------------------------------------------
# Construccion
# ---------------------------------------------------------------------------
def from_observations(
    rows: Sequence[Tuple[str, str, float]]
) -> BipartiteNetwork:
    """Construye la matriz a partir de tuplas (planta, polinizador, visitas)."""
    plants = sorted({r[0] for r in rows})
    poll = sorted({r[1] for r in rows})
    pi = {p: i for i, p in enumerate(plants)}
    qi = {q: j for j, q in enumerate(poll)}
    m = np.zeros((len(plants), len(poll)), dtype=float)
    for pl, q, v in rows:
        m[pi[pl], qi[q]] += float(v)
    return BipartiteNetwork(matrix=m, plants=plants, pollinators=poll)


def to_graph(net: BipartiteNetwork) -> nx.Graph:
    """Grafo bipartito no dirigido con pesos de visita."""
    g = nx.Graph()
    for p in net.plants:
        g.add_node(f"P::{p}", kind="planta")
    for q in net.pollinators:
        g.add_node(f"Q::{q}", kind="polinizador")
    for i, p in enumerate(net.plants):
        for j, q in enumerate(net.pollinators):
            w = float(net.matrix[i, j])
            if w > 0:
                g.add_edge(f"P::{p}", f"Q::{q}", weight=w)
    return g


# ---------------------------------------------------------------------------
# Metricas
# ---------------------------------------------------------------------------
def connectance(net: BipartiteNetwork) -> float:
    total = net.n_plants * net.n_pollinators
    if total == 0:
        return 0.0
    return float(net.binary.sum()) / total


def degree_distribution(net: BipartiteNetwork) -> Dict[str, Dict[str, float]]:
    b = net.binary
    plant_deg = b.sum(axis=1)
    poll_deg = b.sum(axis=0)

    def _stats(arr: np.ndarray) -> Dict[str, float]:
        if arr.size == 0:
            return {"mean": 0.0, "min": 0.0, "max": 0.0, "sd": 0.0}
        return {
            "mean": float(arr.mean()),
            "min": float(arr.min()),
            "max": float(arr.max()),
            "sd": float(arr.std()),
        }

    return {"plantas": _stats(plant_deg), "polinizadores": _stats(poll_deg)}


def nodf(net: BipartiteNetwork) -> float:
    """Nestedness Overlap and Decreasing Fill (Almeida-Neto et al. 2008).

    Devuelve un porcentaje en [0, 100]; 100 = anidamiento perfecto.
    """
    m = net.binary
    r, c = m.shape
    if r < 2 and c < 2:
        return 0.0
    total = 0.0
    pairs = 0

    def _pairs(mat: np.ndarray, axis: int) -> Tuple[float, int]:
        deg = mat.sum(axis=axis)
        order = np.argsort(-deg)
        n = len(order)
        acc = 0.0
        cnt = 0
        for i in range(n):
            for j in range(i + 1, n):
                hi, lo = order[i], order[j]
                ni, nj = deg[hi], deg[lo]
                if nj == 0:
                    continue
                ov = int(np.sum(mat[hi] & mat[lo])) if axis == 1 else int(
                    np.sum(mat[:, hi] & mat[:, lo])
                )
                acc += ov / nj
                cnt += 1
        return acc, cnt

    a1, c1 = _pairs(m, axis=1)  # pares de filas (plantas)
    a2, c2 = _pairs(m, axis=0)  # pares de columnas (polinizadores)
    total = a1 + a2
    pairs = c1 + c2
    return float(100.0 * total / pairs) if pairs else 0.0


def modularity(net: BipartiteNetwork, seed: int = 0) -> Dict[str, object]:
    """Modularidad y comunidades (Louvain) sobre el grafo bipartito."""
    g = to_graph(net)
    if g.number_of_edges() == 0:
        return {"modularidad": 0.0, "n_comunidades": 0, "comunidades": []}
    communities = nx.algorithms.community.louvain_communities(g, seed=seed)
    mod = nx.algorithms.community.modularity(g, communities, weight="weight")
    return {
        "modularidad": float(mod),
        "n_comunidades": len(communities),
        "comunidades": [sorted(c) for c in communities],
    }


def robustness(net: BipartiteNetwork) -> Dict[str, float]:
    """Robustez a extinciones secundarias removiendo polinizadores por grado.

    Se eliminan polinizadores del mayor al menor grado (peor escenario).
    Se mide la fraccion de plantas que conservan al menos un visitante.
    R=1 implica red totalmente robusta; valores menores implican colapso.
    """
    m = net.binary.copy()
    if m.sum() == 0:
        return {"robustez": 0.0, "supervivencia_plantas_final": 0.0}
    order = np.argsort(-m.sum(axis=0))
    alive = [float((m.sum(axis=1) > 0).mean())]
    for q in order:
        m[:, q] = 0
        alive.append(float((m.sum(axis=1) > 0).mean()))
    x = np.linspace(0.0, 1.0, len(alive))
    _trapz = getattr(np, "trapezoid", None) or getattr(np, "trapz")
    auc = float(_trapz(alive, x))
    return {"robustez": auc, "supervivencia_plantas_final": alive[-1]}


def summarize(net: BipartiteNetwork, seed: int = 0) -> Dict[str, object]:
    """Resumen completo de metricas de la red."""
    return {
        "n_plantas": net.n_plants,
        "n_polinizadores": net.n_pollinators,
        "n_interacciones": int((net.matrix > 0).sum()),
        "visitas_totales": float(net.matrix.sum()),
        "connectance": connectance(net),
        "anidamiento_nodf": nodf(net),
        "modularidad": modularity(net, seed=seed)["modularidad"],
        "robustez": robustness(net)["robustez"],
        "grado": degree_distribution(net),
    }


def graph_json(net: BipartiteNetwork, min_weight: float = 1.0) -> Dict[str, list]:
    """Representacion nodos/enlaces para el frontend (grafo interactivo)."""
    nodes = [
        {"id": f"P::{p}", "label": p, "group": "planta"} for p in net.plants
    ] + [
        {"id": f"Q::{q}", "label": q, "group": "polinizador"} for q in net.pollinators
    ]
    links = []
    for i, p in enumerate(net.plants):
        for j, q in enumerate(net.pollinators):
            w = float(net.matrix[i, j])
            if w >= min_weight:
                links.append({"source": f"P::{p}", "target": f"Q::{q}", "weight": w})
    return {"nodes": nodes, "links": links}
