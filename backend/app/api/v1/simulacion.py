"""Endpoints del motor de simulacion de escenarios climaticos."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.services import pipelines
from app.simulation.engine import scenario_delta

router = APIRouter(prefix="/simulacion", tags=["simulacion"])


class CompararIn(BaseModel):
    escenarios: list[str] | None = None


@router.get("/{escenario}", summary="Simula un escenario climatico (paso mensual)")
def simular(
    escenario: str,
    session: SessionDep,
    persist: bool = Query(False, description="Guardar resultados mensuales en la BD"),
) -> dict:
    try:
        return pipelines.simulation_report(session, escenario, persist=persist)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/comparar", summary="Compara varios escenarios (linea base vs SSP)")
def comparar(payload: CompararIn, session: SessionDep) -> dict:
    return pipelines.compare_scenarios(session, payload.escenarios)


@router.get("/detalle/delta", summary="Delta climatico interpolado de un escenario")
def delta(escenario: str, anio: int) -> dict:
    dT, dP = scenario_delta(escenario, anio)
    return {"escenario": escenario, "anio": anio,
            "delta_temp_c": dT, "delta_precip_pct": dP}
