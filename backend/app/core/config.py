"""Configuracion tipada, carga de YAML y utilidades transversales.

Toda la aleatoriedad del sistema deriva de ``settings.seed`` para garantizar
reproducibilidad (semillas fijas + parametros en YAML).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

# .../backend/app/core/config.py -> backend -> repo root
BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Configuracion de la aplicacion (override via entorno con prefijo SA_)."""

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env"),
        env_prefix="SA_",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = (
        "Gemelo digital de paisajes agricolas y redes de polinizadores"
    )
    version: str = "1.0.0"
    description: str = (
        "Plataforma para modelar el paisaje agricola y la red planta-polinizador, "
        "simular escenarios climaticos y optimizar intervenciones. "
        "Zona de estudio: Valle de Moche y Chavimochic (La Libertad, Peru)."
    )

    host: str = "0.0.0.0"
    port: int = 8000

    # Persistencia: por defecto SQLite local; en Docker es PostGIS.
    database_url: str = f"sqlite:///{(ROOT_DIR / 'data' / 'agricola.db').as_posix()}"

    seed: int = 42
    config_dir: str = str(ROOT_DIR / "config")

    cors_origins: str = "http://localhost:3000"

    @property
    def db_backend(self) -> str:
        """``postgres`` si la URL es PostgreSQL/PostGIS, si no ``sqlite``."""
        return "postgres" if self.database_url.startswith("postgresql") else "sqlite"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def config_path(self) -> Path:
        p = Path(self.config_dir)
        return p if p.is_absolute() else (ROOT_DIR / p)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


@lru_cache
def _load_yaml_cached(name: str, mtime: float) -> Dict[str, Any]:
    path = settings.config_path / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No se encontro el archivo de configuracion: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"El YAML {path} debe contener un diccionario raiz")
    return data


def load_config(name: str) -> Dict[str, Any]:
    """Carga ``config/<name>.yaml`` con cache invalidado por mtime."""
    path = settings.config_path / f"{name}.yaml"
    mtime = path.stat().st_mtime if path.exists() else 0.0
    return _load_yaml_cached(name, mtime)


def params() -> Dict[str, Any]:
    return load_config("params")


def crops() -> Dict[str, Any]:
    return load_config("crops").get("cultivos", {})


def scenarios() -> Dict[str, Any]:
    return load_config("scenarios")
