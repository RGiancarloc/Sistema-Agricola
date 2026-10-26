"""Endpoints de la red bipartita planta-polinizador."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.services import pipelines

router = APIRouter(prefix="/red", tags=["red de polinizadores"])


@router.get("", summary="Metricas de la red (anidamiento, modularidad, robustez)")
def metricas(session: SessionDep) -> dict:
    return pipelines.network_report(session)["metricas"]


@router.get("/grafo", summary="Grafo bipartita (nodos y enlaces) para visualizacion")
def grafo(session: SessionDep, min_weight: float = 1.0) -> dict:
    return pipelines.network_report(session, min_weight=min_weight)["grafo"]
