"""Punto de entrada de la API FastAPI del gemelo digital agricola."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app import __version__
from app.api.v1 import api_router
from app.core.config import settings
from app.core.db import SessionLocal, init_db
from app.core.logging import get_logger

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa esquema y, si esta vacio, siembra datos sinteticos."""
    init_db()
    try:
        from app.domain import models as M
        with SessionLocal() as session:
            n = session.scalar(select(func.count()).select_from(M.Parcela)) or 0
        if n == 0:
            logger.info("Base vacia: generando datos sinteticos (seed)...")
            from app.seeds.generate import seed_all
            with SessionLocal() as session:
                seed_all(session, reset=False)
    except Exception as exc:  # pragma: no cover
        logger.warning("No se pudo verificar/sembrar la base: %s", exc)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=settings.description,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "estado", "description": "Salud y configuracion."},
        {"name": "datos", "description": "Ingesta y consulta de datos espaciales/tabulares."},
        {"name": "paisaje", "description": "Modelo de paisaje y conectividad."},
        {"name": "red de polinizadores", "description": "Red bipartita planta-polinizador."},
        {"name": "modelo estadistico", "description": "Modelos de efectos mixtos."},
        {"name": "simulacion", "description": "Evolucion temporal y escenarios climaticos."},
        {"name": "optimizacion", "description": "MIQCP y metaheuristica GA-ABC."},
        {"name": "servicios ecosistemicos", "description": "Indicadores y score agregado."},
        {"name": "exportacion", "description": "Exportacion CSV/PDF."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "nombre": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "api": "/api/v1",
    }
