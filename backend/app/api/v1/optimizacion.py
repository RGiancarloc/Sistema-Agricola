"""Endpoints de optimizacion de intervenciones (MIQCP y GA-ABC)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import SessionDep
from app.services import pipelines

router = APIRouter(prefix="/optimizacion", tags=["optimizacion"])


class OptimizarIn(BaseModel):
    metodo: str = Field("comparar", pattern="^(miqcp|ga_abc|comparar)$")
    escenario: str = "linea_base"
    persist: bool = False
    budget: float | None = None
    max_area_ha: float | None = None


@router.post("", summary="Ejecuta la optimizacion y compara MIQCP vs GA-ABC")
def optimizar(payload: OptimizarIn, session: SessionDep) -> dict:
    try:
        return pipelines.optimization_report(
            session, metodo=payload.metodo, escenario=payload.escenario,
            persist=payload.persist, budget=payload.budget,
            max_area_ha=payload.max_area_ha,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/recomendaciones", summary="Lista de recomendaciones almacenadas")
def recomendaciones(session: SessionDep, escenario: str | None = None,
                    metodo: str | None = None) -> list[dict]:
    return pipelines.list_recommendations(session, escenario, metodo)
