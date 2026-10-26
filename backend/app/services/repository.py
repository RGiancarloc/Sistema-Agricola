"""Repositorio: consultas y adaptadores ORM -> estructuras ligeras de calculo."""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain import models as M
from app.optimization.common import Intervention, Parcel


def parcelas_entities(session: Session) -> List[dict]:
    rows = session.scalars(select(M.Parcela)).all()
    return [
        {"id": p.id, "wkt": p.geom,
         "attrs": {"codigo": p.codigo, "cultivo": p.cultivo, "area_ha": p.area_ha}}
        for p in rows
    ]


def habitats_entities(session: Session) -> List[dict]:
    rows = session.scalars(select(M.Habitat)).all()
    return [
        {"id": h.id, "wkt": h.geom,
         "attrs": {"codigo": h.codigo, "tipo": h.tipo, "area_ha": h.area_ha,
                   "calidad": h.calidad}}
        for h in rows
    ]


def colmenas_entities(session: Session) -> List[dict]:
    rows = session.scalars(select(M.Colmena)).all()
    return [
        {"id": c.id, "wkt": c.geom,
         "attrs": {"codigo": c.codigo, "n_colmenas": c.n_colmenas}}
        for c in rows
    ]


def network_rows(session: Session) -> List[Tuple[str, str, float]]:
    """Tuplas (planta, polinizador, visitas) agregadas de toda la red."""
    stmt = (
        select(
            M.EspeciePlanta.nombre,
            M.Polinizador.nombre,
            func.sum(M.ObservacionRed.visitas),
        )
        .join(M.EspeciePlanta, M.ObservacionRed.planta_id == M.EspeciePlanta.id)
        .join(M.Polinizador, M.ObservacionRed.polinizador_id == M.Polinizador.id)
        .group_by(M.EspeciePlanta.nombre, M.Polinizador.nombre)
    )
    return [(r[0], r[1], float(r[2])) for r in session.execute(stmt).all()]


def network_by_parcel(session: Session, n_years: int = 1) -> Dict[int, dict]:
    stmt = (
        select(
            M.ObservacionRed.parcela_id,
            func.sum(M.ObservacionRed.visitas),
            func.count(func.distinct(M.ObservacionRed.polinizador_id)),
        )
        .where(M.ObservacionRed.parcela_id.is_not(None))
        .group_by(M.ObservacionRed.parcela_id)
    )
    out: Dict[int, dict] = {}
    for pid, visits, rich in session.execute(stmt).all():
        out[int(pid)] = {
            "visitas_tasa": float(visits) / max(1.0, n_years * 12.0),
            "riqueza": float(rich),
        }
    return out


def network_by_parcel_year(session: Session) -> Dict[tuple, dict]:
    """Metricas de red por (parcela, anio): tasa mensual de visitas y riqueza."""
    stmt = (
        select(
            M.ObservacionRed.parcela_id,
            M.ObservacionRed.anio,
            func.sum(M.ObservacionRed.visitas),
            func.count(func.distinct(M.ObservacionRed.polinizador_id)),
        )
        .where(M.ObservacionRed.parcela_id.is_not(None))
        .group_by(M.ObservacionRed.parcela_id, M.ObservacionRed.anio)
    )
    out: Dict[tuple, dict] = {}
    for pid, anio, visits, rich in session.execute(stmt).all():
        out[(int(pid), int(anio))] = {
            "visitas_tasa": float(visits) / 12.0,
            "riqueza": float(rich),
        }
    return out


def interventions_objects(session: Session) -> Dict[str, Intervention]:
    rows = session.scalars(select(M.Intervencion)).all()
    return {
        i.codigo: Intervention(
            codigo=i.codigo, nombre=i.nombre, costo_usd_ha=i.costo_usd_ha,
            costo_usd_fijo=i.costo_usd_fijo, efecto_polinizacion=i.efecto_polinizacion,
            efecto_biodiversidad=i.efecto_biodiversidad,
            efecto_productividad=i.efecto_productividad,
        )
        for i in rows
    }


def parcels_for_optimization(session: Session) -> List[Parcel]:
    net = network_by_parcel(session)
    from app.ecosystem.indicators import pollination_service

    out: List[Parcel] = []
    for p in session.scalars(select(M.Parcela)).all():
        s = net.get(p.id, {"visitas_tasa": 0.0, "riqueza": 0.0})
        service = pollination_service(s["visitas_tasa"], s["riqueza"])
        out.append(Parcel(id=p.id, area_ha=p.area_ha, cultivo=p.cultivo,
                          deficit=float(1.0 - service)))
    return out


def rendimiento_dataframe(session: Session, landscape: Dict[str, dict]) -> pd.DataFrame:
    """Ensambla el data frame para el modelo de efectos mixtos."""
    net_year = network_by_parcel_year(session)
    net_avg = network_by_parcel(session)
    parcelas = {p.id: p for p in session.scalars(select(M.Parcela)).all()}
    rows = session.scalars(select(M.ObservacionRendimiento)).all()
    records = []
    for r in rows:
        p = parcelas.get(r.parcela_id)
        if p is None:
            continue
        ctx = landscape.get(str(p.id), {})
        # Se prioriza la metrica de red del mismo anio; si no existe, el promedio.
        n = net_year.get((p.id, r.anio)) or net_avg.get(p.id, {"visitas_tasa": 0.0, "riqueza": 0.0})
        records.append({
            "parcela": p.codigo,
            "cultivo": p.cultivo,
            "rendimiento_t_ha": r.rendimiento_t_ha,
            "anio": r.anio,
            "visitas_tasa": n["visitas_tasa"],
            "riqueza_polinizadores": n["riqueza"],
            "t_mean_anual_c": r.t_mean_anual_c,
            "gdd_anual": r.gdd_anual,
            "precipitacion_anual_mm": r.precipitacion_anual_mm,
            "habitat_area_ha": ctx.get("habitat_area_ha", 0.0),
            "dist_habitat_m": ctx.get("dist_habitat_m", 0.0),
            "colmenas_cerca": ctx.get("colmenas_cerca", 0.0),
        })
    return pd.DataFrame.from_records(records)


def climate_dataframe(session: Session) -> pd.DataFrame:
    rows = session.scalars(select(M.ObservacionClima)).all()
    return pd.DataFrame([
        {"estacion_id": o.estacion_id, "anio": o.anio, "mes": o.mes,
         "tmean_c": o.tmean_c, "precip_mm": o.precip_mm, "gdd": o.gdd}
        for o in rows
    ])


def counts(session: Session) -> Dict[str, int]:
    tables = {
        "parcelas": M.Parcela, "habitats": M.Habitat, "colmenas": M.Colmena,
        "estaciones": M.EstacionClima, "observaciones_clima": M.ObservacionClima,
        "plantas": M.EspeciePlanta, "polinizadores": M.Polinizador,
        "interacciones": M.ObservacionRed, "ndvi": M.IndiceVegetacion,
        "rendimientos": M.ObservacionRendimiento, "intervenciones": M.Intervencion,
        "escenarios": M.Escenario, "resultados": M.ResultadoSimulacion,
    }
    out = {}
    for name, model in tables.items():
        out[name] = int(session.scalar(select(func.count()).select_from(model)) or 0)
    return out
