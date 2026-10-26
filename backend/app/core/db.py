"""Motor y sesion de base de datos, Base declarativa e inicializacion."""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Clase base declarativa de todas las entidades ORM."""


def _build_engine():
    url = settings.database_url
    kwargs: dict = {"future": True, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Crea todas las tablas y, en PostGIS, columnas espaciales nativas."""
    # Importa los modelos para registrarlos en el metadata.
    from app.domain import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if settings.db_backend == "postgres":
        from app.core.postgis import ensure_postgis_geometry

        ensure_postgis_geometry(engine)
    logger.info("Esquema inicializado (%s)", settings.db_backend)


def get_session() -> Generator[Session, None, None]:
    """Dependencia FastAPI: entrega una sesion y la cierra al finalizar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def session_scope() -> Session:
    """Sesion para uso programatico (scripts, seeds)."""
    return SessionLocal()
