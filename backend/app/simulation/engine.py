"""Motor de simulacion mensual bajo escenarios climaticos.

Modelo (parametrizo, no mecanistico de cultivo):

    rendimiento(t) = rendimiento_base *
        f_clima(t) * f_polinizacion(t) * (1 + efecto_aleatorio_parcela)

con:

- ``f_clima``: penalizacion gaussiana por desviacion de la temperatura
  proyectada respecto a la optima del cultivo, modulada por GDD.
- ``f_polinizacion``: servicio de polinizacion saturante que combina visitas,
  riqueza, contexto de habitat e intervenciones aplicadas.

La temperatura y precipitacion proyectadas se obtienen de la climatologia
historica observada + deltas por escenario (interpolacion lineal por anio).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import crops, params, scenarios
from app.core.logging import get_logger
from app.domain import models as M
from app.ecosystem.indicators import aggregate_score, biodiversity_score, pollination_service

logger = get_logger(__name__)

ANCHORS = [2025, 2030, 2035, 2040, 2045, 2050]


def scenario_delta(escenario_codigo: str, anio: int) -> tuple[float, float]:
    """(delta_temp_c, delta_precip_pct) interpolado para un anio dado."""
    cfg = scenarios()["escenarios"].get(escenario_codigo)
    if cfg is None or anio < ANCHORS[0]:
        return 0.0, 0.0
    tvals = cfg["delta_temp_anual"]
    pvals = cfg["delta_precip_anual_pct"]
    if anio >= ANCHORS[-1]:
        return float(tvals[-1]), float(pvals[-1])
    for i in range(len(ANCHORS) - 1):
        a, b = ANCHORS[i], ANCHORS[i + 1]
        if a <= anio <= b:
            w = (anio - a) / (b - a)
            return (
                float(tvals[i] + w * (tvals[i + 1] - tvals[i])),
                float(pvals[i] + w * (pvals[i + 1] - pvals[i])),
            )
    return 0.0, 0.0


def _month_shares(peak_month: int) -> np.ndarray:
    """Reparto de la produccion anual en 12 meses (pico en ``peak_month``)."""
    raw = np.array([max(0.05, 0.5 + 0.5 * math.cos(2 * math.pi * (m - peak_month) / 12))
                    for m in range(1, 13)])
    return raw / raw.sum()


def _climate_factor(tmean_proj: float, c: dict) -> float:
    """Penalizacion gaussiana por temperatura (0.4 - 1.1)."""
    z = (tmean_proj - c["temp_optima_c"]) / max(1e-6, c["tolerancia_termica_c"])
    return float(np.clip(math.exp(-0.5 * z * z) * 1.05, 0.4, 1.1))


def _load_context(session: Session):
    parcelas = session.scalars(select(M.Parcela)).all()
    habitats = session.scalars(select(M.Habitat)).all()
    colmenas = session.scalars(select(M.Colmena)).all()
    plantas = {p.id: p for p in session.scalars(select(M.EspeciePlanta)).all()}
    clima = session.scalars(select(M.ObservacionClima)).all()
    red = session.scalars(select(M.ObservacionRed)).all()
    return parcelas, habitats, colmenas, plantas, clima, red


def _annual_climatology(clima: Sequence[M.ObservacionClima]) -> Dict[int, dict]:
    acc: Dict[int, list] = {}
    for o in clima:
        acc.setdefault(o.anio, []).append((o.tmean_c, o.gdd, o.precip_mm))
    out = {}
    for a, rows in acc.items():
        arr = np.array(rows, dtype=float)
        out[a] = {
            "tmean": float(np.nanmean(arr[:, 0])),
            "gdd": float(np.nansum(arr[:, 1])),
            "precip": float(np.nanmean(arr[:, 2])),
        }
    return out


def _network_by_parcel(red: Sequence[M.ObservacionRed], years: int) -> Dict[int, dict]:
    visits: Dict[int, float] = {}
    rich: Dict[int, set] = {}
    for o in red:
        if o.parcela_id is None:
            continue
        visits[o.parcela_id] = visits.get(o.parcela_id, 0.0) + o.visitas
        rich.setdefault(o.parcela_id, set()).add(o.polinizador_id)
    return {
        pid: {
            "visitas_tasa": visits.get(pid, 0.0) / max(1.0, years * 12.0),
            "riqueza": float(len(rich.get(pid, set()))),
        }
        for pid in set(list(visits.keys()) + list(rich.keys()))
    }


def simulate_scenario(
    session: Session,
    escenario_codigo: str,
    interventions: Optional[Dict[int, List[dict]]] = None,
    years: Optional[Sequence[int]] = None,
    persist: bool = False,
    seed: Optional[int] = None,
) -> Dict[str, object]:
    """Simula un escenario para todas las parcelas.

    ``interventions``: {parcela_id: [{"codigo":..,"efecto_polinizacion":..,
    "efecto_biodiversidad":..,"efecto_productividad":..}, ...]}.
    """
    cfg = params()["simulation"]
    rng = np.random.default_rng(params()["seed"] if seed is None else seed)
    y0, y1 = cfg["year_start"], cfg["projection_end"]
    year_list = list(years) if years else list(range(y0, y1 + 1))

    parcelas, habitats, colmenas, plantas, clima, red = _load_context(session)
    clim = _annual_climatology(clima)
    net = _network_by_parcel(red, years=max(1, cfg["year_end"] - cfg["year_start"] + 1))
    habitat_area = sum(h.area_ha for h in habitats)

    esc = next((e for e in session.scalars(select(M.Escenario)).all()
                if e.codigo == escenario_codigo), None)
    base_atm = np.array([clim[a]["tmean"] if a in clim else np.nan for a in sorted(clim)])
    hist_mean_t = float(np.nanmean(base_atm)) if base_atm.size else 21.0
    hist_mean_p = float(np.nanmean([clim[a]["precip"] for a in clim])) if clim else 2.0
    hist_mean_gdd = float(np.nanmean([clim[a]["gdd"] for a in clim])) if clim else 2000.0

    # Efectos latentes por parcela (aleatorio pero reproducible).
    par_random = {p.id: float(rng.normal(0, 0.05)) for p in parcelas}

    results: List[dict] = []
    annual_series: Dict[int, list] = {}

    for anio in year_list:
        dT, dP = scenario_delta(escenario_codigo, anio)
        if anio in clim:
            tmean = clim[anio]["tmean"] + dT
            precip = clim[anio]["precip"] * (1 + dP / 100.0)
            gdd = clim[anio]["gdd"] + dT * 365 * 0.5
        else:
            tmean = hist_mean_t + dT
            precip = hist_mean_p * (1 + dP / 100.0)
            gdd = hist_mean_gdd + dT * 365 * 0.5

        for p in parcelas:
            c = crops()[p.cultivo]
            shares = _month_shares(c["ndvi_pico_mes"])
            iv = net.get(p.id, {"visitas_tasa": 0.0, "riqueza": 0.0})
            applied = (interventions or {}).get(p.id, [])
            eff_pol = sum(a.get("efecto_polinizacion", 0.0) for a in applied)
            eff_bio = sum(a.get("efecto_biodiversidad", 0.0) for a in applied)
            eff_prod = sum(a.get("efecto_productividad", 0.0) for a in applied)

            # contexto de habitat: numero de parches cercanos (proxy sin geo pesada)
            near_hab = sum(
                1 for h in habitats
                if _approx_near(p, h, params()["landscape"]["habitat_search_radius_m"])
            )
            near_col = sum(nc.n_colmenas for nc in colmenas
                           if _approx_near(p, nc, params()["landscape"]["habitat_search_radius_m"]))

            f_clima = _climate_factor(tmean, c)
            # estres termico de polinizadores: por encima de 30 C reduce actividad
            heat_pen = float(np.clip(1.0 - max(0.0, tmean - 30.0) * 0.05, 0.5, 1.0))
            visits = iv["visitas_tasa"] * heat_pen * (1 + eff_pol) * (1 + 0.02 * near_hab + 0.005 * near_col)
            richness = iv["riqueza"] * (1 + 0.15 * eff_pol + 0.1 * eff_bio)
            service = pollination_service(visits, richness)
            dep = c["dependencia_polinizadores_silvestres"] + c["dependencia_abeja_mielifera"]
            f_pol = 1.0 - dep * c["sensibilidad_deficit_polinizacion"] * (1.0 - service)
            f_pol = float(np.clip(f_pol + eff_prod * 0.1, 0.5, 1.2))

            rend_anual = c["rendimiento_base_t_ha"] * f_clima * f_pol * (1 + par_random[p.id])
            rend_anual = max(0.05, rend_anual)

            biod = biodiversity_score(richness, 30.0, habitat_area, 50.0,
                                      conectividad=float(np.clip(near_hab / 6.0, 0, 1)))
            pol_score = service
            prod_score = float(np.clip(rend_anual / c["rendimiento_base_t_ha"], 0, 1))
            score = aggregate_score(prod_score, pol_score, biod)

            deficit = float(np.clip(1.0 - service, 0, 1))
            annual_series.setdefault(anio, []).append(
                (rend_anual, visits, richness, score, deficit)
            )

            if persist:
                for mes in range(1, 13):
                    results.append(
                        dict(
                            escenario_id=esc.id if esc else None,
                            parcela_id=p.id, anio=anio, mes=mes,
                            productividad_t_ha=rend_anual * float(shares[mes - 1]),
                            produccion_total_t=rend_anual * float(shares[mes - 1]) * p.area_ha,
                            visitas_polinizadores=visits, riqueza_polinizadores=richness,
                            deficit_polinizacion=deficit, score_ecosistema=score,
                        )
                    )

    if persist and esc is not None:
        session.execute(delete(M.ResultadoSimulacion).where(
            M.ResultadoSimulacion.escenario_id == esc.id))
        if results:
            session.bulk_insert_mappings(M.ResultadoSimulacion, results)
        session.commit()

    series = []
    for anio in sorted(annual_series):
        arr = np.array(annual_series[anio], dtype=float)
        series.append({
            "anio": anio,
            "productividad_media_t_ha": float(arr[:, 0].mean()),
            "visitas_medias": float(arr[:, 1].mean()),
            "riqueza_media": float(arr[:, 2].mean()),
            "deficit_polinizacion_medio": float(arr[:, 4].mean()),
            "score_medio": float(arr[:, 3].mean()),
        })

    return {
        "escenario": escenario_codigo,
        "nombre": esc.nombre if esc else escenario_codigo,
        "anios": [s["anio"] for s in series],
        "serie": series,
        "resumen": _summarize(series),
        "n_parcelas": len(parcelas),
        "persistido": bool(persist and esc is not None),
    }


def _approx_near(a, b, radius_m: float) -> bool:
    """Aproximacion rapida por bbox en grados (0.01 deg ~ 1.1 km)."""
    from app.core.geo import centroid_xy, haversine_m

    ax, ay = centroid_xy(a.geom)
    bx, by = centroid_xy(b.geom)
    return haversine_m(ay, ax, by, bx) <= radius_m


def _summarize(series: List[dict]) -> dict:
    if not series:
        return {}
    first, last = series[0], series[-1]
    return {
        "productividad_inicial": first["productividad_media_t_ha"],
        "productividad_final": last["productividad_media_t_ha"],
        "cambio_productividad_pct": (
            (last["productividad_media_t_ha"] - first["productividad_media_t_ha"])
            / first["productividad_media_t_ha"] * 100.0
            if first["productividad_media_t_ha"] else 0.0
        ),
        "score_inicial": first["score_medio"],
        "score_final": last["score_medio"],
        "deficit_final": last["deficit_polinizacion_medio"],
    }
