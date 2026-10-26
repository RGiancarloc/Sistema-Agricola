"""Agregador de routers de la API v1."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    datos,
    ecosistema,
    estadistico,
    export,
    health,
    optimizacion,
    paisaje,
    red,
    simulacion,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(datos.router)
api_router.include_router(paisaje.router)
api_router.include_router(red.router)
api_router.include_router(estadistico.router)
api_router.include_router(simulacion.router)
api_router.include_router(optimizacion.router)
api_router.include_router(ecosistema.router)
api_router.include_router(export.router)
