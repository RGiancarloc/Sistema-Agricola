"""Entidades ORM (capa de persistencia) del gemelo digital.

Geometrias: se almacenan como tipo portable ``WKTGeometry`` (PostGIS en
PostgreSQL, WKT en SQLite). Cultivos y polinizadores viven en tablas de
referencia; las observaciones en tablas de hechos.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.db import Base
from app.core.geo import WKTGeometry


class EstacionClima(Base):
    __tablename__ = "estacion_clima"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(32), unique=True, nullable=False)
    nombre = Column(String(120), nullable=False)
    elevacion_m = Column(Float, default=0.0)
    geom = Column(WKTGeometry("POINT"))

    observaciones = relationship("ObservacionClima", back_populates="estacion")


class ObservacionClima(Base):
    __tablename__ = "observacion_clima"
    __table_args__ = (
        UniqueConstraint("estacion_id", "anio", "mes", name="uq_clima_est_anio_mes"),
    )

    id = Column(Integer, primary_key=True)
    estacion_id = Column(Integer, ForeignKey("estacion_clima.id"), nullable=False)
    anio = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    tmax_c = Column(Float)
    tmin_c = Column(Float)
    tmean_c = Column(Float)
    precip_mm = Column(Float)
    humedad_pct = Column(Float)
    gdd = Column(Float, default=0.0)  # grados-dia de crecimiento acumulados

    estacion = relationship("EstacionClima", back_populates="observaciones")


class Parcela(Base):
    __tablename__ = "parcela"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(32), unique=True, nullable=False)
    cultivo = Column(String(40), nullable=False, index=True)
    variedad = Column(String(60))
    area_ha = Column(Float, nullable=False, default=0.0)
    tipo_suelo = Column(String(40))
    sistema_riego = Column(String(40))
    edad_plantacion_anios = Column(Float, default=0.0)
    geom = Column(WKTGeometry("POLYGON"))

    ndvi = relationship("IndiceVegetacion", back_populates="parcela")
    resultados = relationship("ResultadoSimulacion", back_populates="parcela")


class UsoSuelo(Base):
    __tablename__ = "uso_suelo"

    id = Column(Integer, primary_key=True)
    clase = Column(String(60), nullable=False, index=True)
    area_ha = Column(Float, default=0.0)
    geom = Column(WKTGeometry("POLYGON"))


class Habitat(Base):
    __tablename__ = "habitat"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(32), unique=True, nullable=False)
    tipo = Column(String(40), nullable=False)  # floral | nesting | mixto
    calidad = Column(Float, default=0.5)  # 0-1
    area_ha = Column(Float, default=0.0)
    geom = Column(WKTGeometry("POLYGON"))


class Colmena(Base):
    __tablename__ = "colmena"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(32), unique=True, nullable=False)
    especie = Column(String(40), default="Apis mellifera")
    n_colmenas = Column(Integer, default=0)
    activa = Column(Boolean, default=True)
    geom = Column(WKTGeometry("POINT"))


class EspeciePlanta(Base):
    __tablename__ = "especie_planta"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(80), unique=True, nullable=False)
    tipo = Column(String(20), default="silvestre")  # cultivo | silvestre
    es_cultivo_ref = Column(Boolean, default=False)
    meses_floracion = Column(String(60), default="1-12")

    visitas = relationship("ObservacionRed", back_populates="planta")


class Polinizador(Base):
    __tablename__ = "polinizador"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(80), unique=True, nullable=False)
    taxon = Column(String(40))  # Apidae, Halictidae, Syrphidae, ...
    gremio = Column(String(40))  # abeja, mosca, escarabajo, mariposa, ave
    anidamiento = Column(String(40))  # suelo, cavidad, tallo
    rango_forrajeo_m = Column(Float, default=500.0)
    meses_actividad = Column(String(40), default="1-12")

    visitas = relationship("ObservacionRed", back_populates="polinizador")


class ObservacionRed(Base):
    """Interaccion planta-polinizador (visitas) por parcela/anio/mes."""

    __tablename__ = "observacion_red"

    id = Column(Integer, primary_key=True)
    parcela_id = Column(Integer, ForeignKey("parcela.id"))
    planta_id = Column(Integer, ForeignKey("especie_planta.id"), nullable=False)
    polinizador_id = Column(Integer, ForeignKey("polinizador.id"), nullable=False)
    anio = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    visitas = Column(Float, default=0.0)

    parcela = relationship("Parcela")
    planta = relationship("EspeciePlanta", back_populates="visitas")
    polinizador = relationship("Polinizador", back_populates="visitas")


class IndiceVegetacion(Base):
    __tablename__ = "indice_vegetacion"
    __table_args__ = (
        UniqueConstraint("parcela_id", "anio", "mes", name="uq_ndvi_parcela_periodo"),
    )

    id = Column(Integer, primary_key=True)
    parcela_id = Column(Integer, ForeignKey("parcela.id"), nullable=False)
    anio = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    ndvi = Column(Float, nullable=False)

    parcela = relationship("Parcela", back_populates="ndvi")


class ObservacionRendimiento(Base):
    """Rendimiento observado por parcela y anio (base para efectos mixtos)."""

    __tablename__ = "observacion_rendimiento"
    __table_args__ = (
        UniqueConstraint("parcela_id", "anio", name="uq_rend_parcela_anio"),
    )

    id = Column(Integer, primary_key=True)
    parcela_id = Column(Integer, ForeignKey("parcela.id"), nullable=False)
    anio = Column(Integer, nullable=False)
    rendimiento_t_ha = Column(Float, nullable=False)
    precipitacion_anual_mm = Column(Float)
    gdd_anual = Column(Float)
    t_mean_anual_c = Column(Float)

    parcela = relationship("Parcela", backref="rendimientos")


class Intervencion(Base):
    """Catalogo de intervenciones recomendables (con costo unitario)."""

    __tablename__ = "intervencion"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(40), unique=True, nullable=False)
    nombre = Column(String(120), nullable=False)
    tipo = Column(String(40), nullable=False)
    costo_usd_ha = Column(Float, default=0.0)
    costo_usd_fijo = Column(Float, default=0.0)
    # Efectos medios (multiplicadores) sobre los indicadores.
    efecto_polinizacion = Column(Float, default=0.0)
    efecto_biodiversidad = Column(Float, default=0.0)
    efecto_productividad = Column(Float, default=0.0)
    vida_util_anios = Column(Integer, default=5)
    descripcion = Column(Text)


class Escenario(Base):
    __tablename__ = "escenario"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(40), unique=True, nullable=False)
    nombre = Column(String(120), nullable=False)
    ssp = Column(String(40))
    anio_inicio = Column(Integer, default=2015)
    anio_fin = Column(Integer, default=2050)
    delta_temp_final_c = Column(Float, default=0.0)
    delta_precip_final_pct = Column(Float, default=0.0)
    descripcion = Column(Text)


class ResultadoSimulacion(Base):
    __tablename__ = "resultado_simulacion"

    id = Column(Integer, primary_key=True)
    escenario_id = Column(Integer, ForeignKey("escenario.id"), nullable=False)
    parcela_id = Column(Integer, ForeignKey("parcela.id"), nullable=False)
    anio = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    productividad_t_ha = Column(Float)
    produccion_total_t = Column(Float)
    visitas_polinizadores = Column(Float)
    riqueza_polinizadores = Column(Float)
    deficit_polinizacion = Column(Float)
    score_ecosistema = Column(Float)

    parcela = relationship("Parcela", back_populates="resultados")


class Recomendacion(Base):
    __tablename__ = "recomendacion"

    id = Column(Integer, primary_key=True)
    escenario_codigo = Column(String(40))
    parcela_id = Column(Integer, ForeignKey("parcela.id"))
    intervencion_codigo = Column(String(40), nullable=False)
    area_ha = Column(Float, default=0.0)
    costo_usd = Column(Float, default=0.0)
    beneficio_relativo = Column(Float, default=0.0)
    prioridad = Column(Integer, default=3)
    metodo = Column(String(20), default="miqcp")  # miqcp | ga_abc
    justificacion = Column(Text)
    creado_en = Column(DateTime, default=datetime.utcnow)
