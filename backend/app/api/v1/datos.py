"""Endpoints de datos espaciales y tabulares."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.geo import geom_to_geojson, feature_collection
from app.domain import models as M
from app.seeds.generate import seed_all
from app.services import repository as repo

router = APIRouter(prefix="/datos", tags=["datos"])


def _features(entities) -> dict:
    feats = []
    for e in entities:
        feats.append({
            "type": "Feature",
            "id": e["id"],
            "geometry": geom_to_geojson(e["wkt"]),
            "properties": e["attrs"],
        })
    return feature_collection(feats)


@router.get("/parcelas", summary="Parcelas como GeoJSON")
def parcelas(session: SessionDep) -> dict:
    return _features(repo.parcelas_entities(session))


@router.get("/habitats", summary="Habitats semi-naturales como GeoJSON")
def habitats(session: SessionDep) -> dict:
    return _features(repo.habitats_entities(session))


@router.get("/colmenas", summary="Colmenas como GeoJSON")
def colmenas(session: SessionDep) -> dict:
    return _features(repo.colmenas_entities(session))


@router.get("/uso-suelo", summary="Uso de suelo como GeoJSON")
def uso_suelo(session: SessionDep) -> dict:
    rows = session.scalars(select(M.UsoSuelo)).all()
    feats = [{
        "type": "Feature", "id": u.id, "geometry": geom_to_geojson(u.geom),
        "properties": {"clase": u.clase, "area_ha": u.area_ha},
    } for u in rows]
    return feature_collection(feats)


@router.get("/clima", summary="Serie climatica mensual")
def clima(session: SessionDep, anio: int | None = None) -> list[dict]:
    stmt = select(M.ObservacionClima)
    if anio:
        stmt = stmt.where(M.ObservacionClima.anio == anio)
    rows = session.scalars(stmt.order_by(M.ObservacionClima.anio, M.ObservacionClima.mes)).all()
    return [
        {"estacion_id": o.estacion_id, "anio": o.anio, "mes": o.mes,
         "tmax_c": o.tmax_c, "tmin_c": o.tmin_c, "tmean_c": o.tmean_c,
         "precip_mm": o.precip_mm, "humedad_pct": o.humedad_pct, "gdd": o.gdd}
        for o in rows
    ]


@router.get("/ndvi", summary="Indice de vegetacion (NDVI) por parcela")
def ndvi(session: SessionDep, limit: int = Query(5000, le=50000)) -> list[dict]:
    rows = session.scalars(select(M.IndiceVegetacion).limit(limit)).all()
    return [{"parcela_id": r.parcela_id, "anio": r.anio, "mes": r.mes, "ndvi": r.ndvi}
            for r in rows]


@router.get("/escenarios", summary="Escenarios climaticos disponibles")
def escenarios(session: SessionDep) -> list[dict]:
    rows = session.scalars(select(M.Escenario)).all()
    return [{"codigo": e.codigo, "nombre": e.nombre, "ssp": e.ssp,
             "anio_inicio": e.anio_inicio, "anio_fin": e.anio_fin,
             "delta_temp_final_c": e.delta_temp_final_c,
             "delta_precip_final_pct": e.delta_precip_final_pct,
             "descripcion": e.descripcion} for e in rows]


@router.get("/intervenciones", summary="Catalogo de intervenciones")
def intervenciones(session: SessionDep) -> list[dict]:
    rows = session.scalars(select(M.Intervencion)).all()
    return [{"codigo": i.codigo, "nombre": i.nombre, "tipo": i.tipo,
             "costo_usd_ha": i.costo_usd_ha, "costo_usd_fijo": i.costo_usd_fijo,
             "efecto_polinizacion": i.efecto_polinizacion,
             "efecto_biodiversidad": i.efecto_biodiversidad,
             "efecto_productividad": i.efecto_productividad,
             "descripcion": i.descripcion} for i in rows]


@router.post("/seed", summary="Regenera los datos sinteticos (idempotente)")
def reseed(session: SessionDep) -> dict:
    try:
        return seed_all(session, reset=True)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ingest-real", summary="Reemplaza datos sinteticos por datos reales (MIDAGRI + ERA5-Land)")
def ingest_real(session: SessionDep) -> dict:
    from app.ingestion.ingest_real import ingest_real_data
    try:
        return ingest_real_data(session)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/rendimientos", summary="Rendimientos observados por parcela y ano (calibrados con MIDAGRI-SIEA)")
def rendimientos(session: SessionDep, anio: int | None = None, cultivo: str | None = None) -> list[dict]:
    stmt = select(M.ObservacionRendimiento, M.Parcela).join(M.Parcela)
    if anio:
        stmt = stmt.where(M.ObservacionRendimiento.anio == anio)
    if cultivo:
        stmt = stmt.where(M.Parcela.cultivo == cultivo)
    rows = session.execute(stmt.order_by(M.ObservacionRendimiento.anio, M.Parcela.codigo)).all()
    return [
        {
            "parcela_codigo": p.codigo,
            "cultivo": p.cultivo,
            "anio": r.anio,
            "rendimiento_t_ha": r.rendimiento_t_ha,
            "precipitacion_anual_mm": r.precipitacion_anual_mm,
            "gdd_anual": r.gdd_anual,
            "t_mean_anual_c": r.t_mean_anual_c,
            "sistema_riego": p.sistema_riego,
            "tipo_suelo": p.tipo_suelo,
        }
        for r, p in rows
    ]

