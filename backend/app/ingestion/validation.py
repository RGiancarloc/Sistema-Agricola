"""Validacion y limpieza de registros de ingesta (contratos Pydantic)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ParcelaIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=32)
    cultivo: str
    area_ha: float = Field(gt=0)
    geom_wkt: str
    tipo_suelo: Optional[str] = None
    sistema_riego: Optional[str] = None

    @field_validator("geom_wkt")
    @classmethod
    def _geom(cls, v: str) -> str:
        if not v or not v.strip().upper().startswith(("POLYGON", "MULTIPOLYGON")):
            raise ValueError("geom_wkt debe ser POLYGON o MULTIPOLYGON")
        return v.strip()


class ObservacionClimaIn(BaseModel):
    estacion_codigo: str
    anio: int = Field(ge=1980, le=2100)
    mes: int = Field(ge=1, le=12)
    tmax_c: float
    tmin_c: float
    precip_mm: float = Field(ge=0)
    humedad_pct: Optional[float] = Field(default=None, ge=0, le=100)

    @field_validator("tmin_c")
    @classmethod
    def _range(cls, v, info):
        tmax = info.data.get("tmax_c")
        if tmax is not None and v > tmax:
            raise ValueError("tmin_c no puede superar tmax_c")
        return v


class ObservacionRedIn(BaseModel):
    parcela_codigo: Optional[str] = None
    planta: str
    polinizador: str
    anio: int
    mes: int = Field(ge=1, le=12)
    visitas: float = Field(ge=0)


def validate_parcelas(records: List[dict]) -> List[ParcelaIn]:
    return [ParcelaIn(**r) for r in records]


def validate_clima(records: List[dict]) -> List[ObservacionClimaIn]:
    return [ObservacionClimaIn(**r) for r in records]


def validate_red(records: List[dict]) -> List[ObservacionRedIn]:
    return [ObservacionRedIn(**r) for r in records]
