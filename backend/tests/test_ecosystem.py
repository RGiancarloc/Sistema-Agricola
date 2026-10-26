"""Pruebas de indicadores de servicios ecosistemicos."""
from __future__ import annotations

from app.ecosystem.indicators import (
    aggregate_score,
    biodiversity_score,
    ecosystem_summary,
    pollination_service,
    productivity_score,
)


def test_pollination_service_bounds():
    assert 0.0 <= pollination_service(0, 0) < 0.01
    assert pollination_service(50, 20) <= 1.0
    assert pollination_service(50, 20) > pollination_service(2, 1)


def test_productivity_score_clamped():
    assert productivity_score(5, 10) == 0.5
    assert productivity_score(20, 10) == 1.0


def test_biodiversity_score_bounds():
    v = biodiversity_score(10, 30, 20, 50, 0.5)
    assert 0.0 <= v <= 1.0


def test_aggregate_score_weights():
    s = aggregate_score(1.0, 1.0, 1.0)
    assert abs(s - 1.0) < 1e-9
    s0 = aggregate_score(0.0, 0.0, 0.0)
    assert s0 == 0.0


def test_ecosystem_summary_keys():
    out = ecosystem_summary(8, 10, 5, 6, 20)
    assert set(out) == {"productividad", "polinizacion", "biodiversidad", "score"}
