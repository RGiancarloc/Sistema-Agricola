"""Endpoints de estado y metadatos del sistema."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.core.config import settings
from app.services import repository as repo

router = APIRouter(tags=["estado"])


@router.get("/health", summary="Estado del servicio y conteos de datos")
def health(session: SessionDep) -> dict:
    return {
        "status": "ok",
        "version": settings.version,
        "region": "Valle de Moche y Chavimochic (La Libertad, Peru)",
        "backend_bd": settings.db_backend,
        "counts": repo.counts(session),
    }


@router.get("/config", summary="Parametros de configuracion activos")
def config() -> dict:
    from app.core.config import crops, params, scenarios

    return {
        "params": params(),
        "cultivos": crops(),
        "escenarios": scenarios()["escenarios"],
    }
