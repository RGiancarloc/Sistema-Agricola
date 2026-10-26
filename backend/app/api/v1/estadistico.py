"""Endpoints del modelo estadistico (efectos mixtos)."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.services import pipelines

router = APIRouter(prefix="/estadistico", tags=["modelo estadistico"])


@router.get("/mixto", summary="Ajuste del modelo mixto productividad ~ polinizacion + clima + paisaje")
def mixto(session: SessionDep, incluir_cultivo: bool = True) -> dict:
    return pipelines.stats_report(session, include_crop=incluir_cultivo)
