"""Pipelines de alto nivel usados por la API (orquestan datos + modelos)."""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import params
from app.domain import models as M
from app.ecosystem.indicators import (
    aggregate_score,
    biodiversity_score,
    ecosystem_summary,
    pollination_service,
)
from app.landscape.analysis import global_landscape_summary, landscape_metrics
from app.network.analysis import from_observations, graph_json, summarize
from app.optimization.ga_abc import solve_ga_abc
from app.optimization.miqcp import available_solver, solve_miqcp
from app.services import repository as repo
from app.simulation.engine import simulate_scenario
from app.stats.mixed_effects import fit_mixed_effects


# ---------------------------------------------------------------------------
# Red
# ---------------------------------------------------------------------------
def network_report(session: Session, min_weight: float = 1.0) -> dict:
    rows = repo.network_rows(session)
    net = from_observations(rows)
    metrics = summarize(net, seed=params()["seed"])
    return {"metricas": metrics, "grafo": graph_json(net, min_weight=min_weight)}


# ---------------------------------------------------------------------------
# Paisaje
# ---------------------------------------------------------------------------
def landscape_report(session: Session) -> dict:
    p = params()["landscape"]
    parcelas = repo.parcelas_entities(session)
    habitats = repo.habitats_entities(session)
    colmenas = repo.colmenas_entities(session)
    per_parcel = landscape_metrics(
        parcelas, habitats, colmenas,
        radius_m=p["habitat_search_radius_m"],
        threshold_m=p["connectivity_threshold_m"],
    )
    summary = global_landscape_summary(habitats, p["connectivity_threshold_m"])
    return {"resumen_global": summary, "por_parcela": per_parcel}


# ---------------------------------------------------------------------------
# Estadistico
# ---------------------------------------------------------------------------
def stats_report(session: Session, include_crop: bool = True) -> dict:
    landscape = landscape_report(session)["por_parcela"]
    df = repo.rendimiento_dataframe(session, landscape)
    if df.empty:
        return {"error": "No hay observaciones de rendimiento. Ejecute el seed."}
    return fit_mixed_effects(df, include_crop=include_crop)


# ---------------------------------------------------------------------------
# Simulacion
# ---------------------------------------------------------------------------
def simulation_report(
    session: Session,
    escenario: str,
    persist: bool = False,
    interventions: Optional[Dict[int, List[dict]]] = None,
) -> dict:
    return simulate_scenario(session, escenario, interventions=interventions,
                             persist=persist)


def compare_scenarios(session: Session, codigos: Optional[List[str]] = None) -> dict:
    all_esc = session.scalars(select(M.Escenario)).all()
    codigos = codigos or [e.codigo for e in all_esc]
    out = {}
    for cod in codigos:
        out[cod] = simulate_scenario(session, cod, persist=False)
    return out


# ---------------------------------------------------------------------------
# Optimizacion
# ---------------------------------------------------------------------------
def _persist_recommendations(session: Session, escenario_codigo: str, method: str,
                             assignment: dict, interventions: Dict[str, object]) -> int:
    session.execute(delete(M.Recomendacion).where(
        M.Recomendacion.escenario_codigo == escenario_codigo,
        M.Recomendacion.metodo == method,
    ))
    parcels = {p.id: p for p in session.scalars(select(M.Parcela)).all()}
    n = 0
    for pid, code in assignment.items():
        if not code or code not in interventions:
            continue
        p = parcels.get(pid)
        if p is None:
            continue
        iv = interventions[code]
        costo = iv.costo_usd_fijo + iv.costo_usd_ha * p.area_ha
        beneficio = (iv.efecto_productividad + iv.efecto_polinizacion
                     + iv.efecto_biodiversidad) * p.area_ha
        prioridad = 1 if p.area_ha >= 10 else (2 if p.area_ha >= 3 else 3)
        session.add(M.Recomendacion(
            escenario_codigo=escenario_codigo, parcela_id=pid,
            intervencion_codigo=code, area_ha=p.area_ha, costo_usd=costo,
            beneficio_relativo=beneficio, prioridad=prioridad, metodo=method,
            justificacion=f"Intervencion {iv.nombre} en parcela {p.codigo}",
        ))
        n += 1
    session.commit()
    return n


def optimization_report(
    session: Session,
    metodo: str = "comparar",
    escenario: str = "linea_base",
    persist: bool = False,
    budget: Optional[float] = None,
    max_area_ha: Optional[float] = None,
) -> dict:
    cfg = params()["optimization"]
    weights = params()["ecosystem"]["weights"]
    parcels = repo.parcels_for_optimization(session)
    iv_map = repo.interventions_objects(session)
    iv_list = list(iv_map.values())
    budget = cfg["budget_usd"] if budget is None else budget
    max_area_ha = cfg["max_intervention_area_ha"] if max_area_ha is None else max_area_ha

    out: Dict[str, object] = {
        "n_parcelas": len(parcels),
        "n_intervenciones": len(iv_list),
        "presupuesto": budget,
        "area_max_ha": max_area_ha,
        "solver_disponible": available_solver(),
    }

    miqcp_res = gaabc_res = None
    if metodo in ("miqcp", "comparar"):
        miqcp_res = solve_miqcp(parcels, iv_list, budget, max_area_ha, weights)
        out["miqcp"] = miqcp_res
    if metodo in ("ga_abc", "comparar"):
        ga = solve_ga_abc(parcels, iv_list, budget, max_area_ha, weights,
                          seed=params()["seed"])
        gaabc_res = {
            "beneficio": ga.beneficio, "costo": ga.costo, "area_ha": ga.area_ha,
            "factible": ga.factible, "tiempo_s": ga.tiempo_s,
            "generaciones": ga.generaciones, "historial": ga.historial,
            "asignacion": [{"parcela_id": pid, "intervencion": code}
                           for pid, code in ga.mejor_asignacion.items() if code],
        }
        out["ga_abc"] = gaabc_res

    if metodo == "comparar" and miqcp_res and gaabc_res:
        bm, bg = miqcp_res.get("beneficio_recomputado", miqcp_res["beneficio"]), gaabc_res["beneficio"]
        out["comparacion"] = {
            "mejor_beneficio": "miqcp" if bm >= bg else "ga_abc",
            "brecha_pct": (abs(bm - bg) / max(1e-9, max(bm, bg))) * 100.0,
            "miqcp_tiempo_s": miqcp_res.get("tiempo_s"),
            "ga_abc_tiempo_s": gaabc_res["tiempo_s"],
            "miqcp_n": len(miqcp_res.get("asignacion", [])),
            "ga_abc_n": len(gaabc_res["asignacion"]),
        }

    if persist:
        if miqcp_res and miqcp_res.get("asignacion"):
            out["recomendaciones_guardadas"] = _persist_recommendations(
                session, escenario, "miqcp",
                {a["parcela_id"]: a["intervencion"] for a in miqcp_res["asignacion"]},
                iv_map)
        if gaabc_res:
            out["recomendaciones_guardadas_ga"] = _persist_recommendations(
                session, escenario, "ga_abc",
                {a["parcela_id"]: a["intervencion"] for a in gaabc_res["asignacion"]},
                iv_map)
    return out


# ---------------------------------------------------------------------------
# Ecosistema agregado
# ---------------------------------------------------------------------------
def ecosystem_report(session: Session) -> dict:
    net = repo.network_by_parcel(session)
    parcels = repo.parcels_for_optimization(session)
    landscape = landscape_report(session)["por_parcela"]
    from app.core.config import crops

    riqueza_max = max((n["riqueza"] for n in net.values()), default=1.0) or 1.0
    habitat_area_ref = max(
        (v.get("habitat_area_ha", 0.0) for v in landscape.values()), default=1.0
    ) or 1.0

    por_parcela = []
    agg = {"productividad": [], "polinizacion": [], "biodiversidad": [], "score": []}
    for p in parcels:
        n = net.get(p.id, {"visitas_tasa": 0.0, "riqueza": 0.0})
        ctx = landscape.get(str(p.id), {})
        c = crops()[p.cultivo]
        # rendimiento estimado = base * servicio de polinizacion
        service = pollination_service(n["visitas_tasa"], n["riqueza"])
        dep = c["dependencia_polinizadores_silvestres"] + c["dependencia_abeja_mielifera"]
        rend = c["rendimiento_base_t_ha"] * (1 - dep * c["sensibilidad_deficit_polinizacion"] * (1 - service))
        idx = ecosystem_summary(
            rend, c["rendimiento_base_t_ha"], n["visitas_tasa"], n["riqueza"],
            ctx.get("habitat_area_ha", 0.0), riqueza_max=riqueza_max,
            habitat_area_ref=habitat_area_ref,
            conectividad=min(1.0, ctx.get("habitat_parches", 0) / 6.0),
        )
        idx["parcela_id"] = p.id
        idx["cultivo"] = p.cultivo
        por_parcela.append(idx)
        for k in agg:
            agg[k].append(idx[k])

    import numpy as np

    resumen = {k: float(np.mean(v)) if v else 0.0 for k, v in agg.items()}
    return {"resumen": resumen, "por_parcela": por_parcela}


def list_recommendations(session: Session, escenario: Optional[str] = None,
                         metodo: Optional[str] = None) -> List[dict]:
    stmt = select(M.Recomendacion)
    if escenario:
        stmt = stmt.where(M.Recomendacion.escenario_codigo == escenario)
    if metodo:
        stmt = stmt.where(M.Recomendacion.metodo == metodo)
    rows = session.scalars(stmt.order_by(M.Recomendacion.prioridad)).all()
    return [
        {"id": r.id, "escenario": r.escenario_codigo, "parcela_id": r.parcela_id,
         "intervencion": r.intervencion_codigo, "area_ha": r.area_ha,
         "costo_usd": r.costo_usd, "beneficio_relativo": r.beneficio_relativo,
         "prioridad": r.prioridad, "metodo": r.metodo, "justificacion": r.justificacion}
        for r in rows
    ]
