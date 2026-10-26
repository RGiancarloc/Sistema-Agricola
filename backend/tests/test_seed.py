"""Pruebas del generador de datos sinteticos y del esquema."""
from __future__ import annotations

from sqlalchemy import func, select

from app.core.config import params
from app.domain import models as M


def test_seed_counts(session):
    sd = params()["seed_data"]
    n_parc = session.scalar(select(func.count()).select_from(M.Parcela))
    assert n_parc == sd["n_parcelas"]
    n_hab = session.scalar(select(func.count()).select_from(M.Habitat))
    assert n_hab == sd["n_habitats"]
    n_esc = session.scalar(select(func.count()).select_from(M.Escenario))
    assert n_esc == 3


def test_parcelas_have_valid_geometry(session):
    parcelas = session.scalars(select(M.Parcela)).all()
    assert parcelas, "Debe haber parcelas"
    for p in parcelas:
        assert p.geom.upper().startswith("POLYGON")
        assert p.area_ha > 0
        assert p.cultivo in {"palto", "arandano", "esparrago"}


def test_climate_ranges(session):
    obs = session.scalars(select(M.ObservacionClima)).all()
    assert obs
    for o in obs:
        assert -5 < o.tmin_c < o.tmax_c < 45
        assert o.precip_mm >= 0
        assert 1 <= o.mes <= 12


def test_network_observations_exist(session):
    n = session.scalar(select(func.count()).select_from(M.ObservacionRed))
    assert n > 1000
