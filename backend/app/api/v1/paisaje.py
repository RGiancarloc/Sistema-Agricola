"""Endpoints del modelo de paisaje."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.services import pipelines

router = APIRouter(prefix="/paisaje", tags=["paisaje"])


@router.get("", summary="Conectividad, habitat y contexto espacial por parcela")
def paisaje(session: SessionDep) -> dict:
    return pipelines.landscape_report(session)
