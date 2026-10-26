"""Pruebas de las metricas de red bipartita."""
from __future__ import annotations

import numpy as np

from app.network.analysis import (
    BipartiteNetwork,
    connectance,
    degree_distribution,
    from_observations,
    modularity,
    nodf,
    robustness,
    summarize,
)


def _perfect_nested() -> BipartiteNetwork:
    m = np.array([
        [1, 1, 1, 1],
        [1, 1, 1, 0],
        [1, 1, 0, 0],
        [1, 0, 0, 0],
    ], dtype=float)
    return BipartiteNetwork(m, [f"P{i}" for i in range(4)], [f"Q{j}" for j in range(4)])


def test_connectance_unit():
    net = BipartiteNetwork(np.ones((3, 3)), ["a", "b", "c"], ["x", "y", "z"])
    assert connectance(net) == 1.0


def test_nodf_perfect_nested_high():
    net = _perfect_nested()
    assert nodf(net) > 85.0


def test_nodf_bounds():
    net = from_observations([("p1", "q1", 2), ("p1", "q2", 1), ("p2", "q1", 1)])
    val = nodf(net)
    assert 0.0 <= val <= 100.0


def test_robustness_bounds():
    net = from_observations([
        ("p1", "q1", 1), ("p1", "q2", 1), ("p2", "q1", 1), ("p3", "q1", 1),
    ])
    r = robustness(net)
    assert 0.0 <= r["robustez"] <= 1.0


def test_degree_distribution():
    net = _perfect_nested()
    dd = degree_distribution(net)
    assert dd["plantas"]["max"] == 4
    assert dd["polinizadores"]["max"] == 4


def test_summarize_keys():
    net = from_observations([("p1", "q1", 3), ("p2", "q1", 1), ("p2", "q2", 1)])
    s = summarize(net)
    for key in ["connectance", "anidamiento_nodf", "modularidad", "robustez"]:
        assert key in s
    assert s["n_plantas"] == 2
