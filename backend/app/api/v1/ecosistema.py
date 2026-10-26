"""Endpoints de servicios ecosistemicos e indicadores agregados."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.services import pipelines

router = APIRouter(prefix="/ecosistema", tags=["servicios ecosistemicos"])


@router.get("", summary="Indicadores (productividad, polinizacion, biodiversidad) y score")
def ecosistema(session: SessionDep) -> dict:
    return pipelines.ecosystem_report(session)
