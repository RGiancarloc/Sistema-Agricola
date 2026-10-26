"""Utilidades geoespaciales y tipo SQLAlchemy portable para geometrias.

- En PostgreSQL/PostGIS la columna se crea como ``geometry(...,4326)``.
- En SQLite (desarrollo/pruebas) se almacena el WKT como texto.

El resto del sistema trabaja con WKT (str) y, cuando se necesita geometria,
con objetos Shapely, de modo que la capa de calculo es independiente del motor.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Optional

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

try:  # Shapely es una dependencia geoespacial; el nucleo puede funcionar sin ella.
    from shapely import wkt as shapely_wkt
    from shapely.geometry import mapping, shape
    from shapely.geometry.base import BaseGeometry

    HAS_SHAPELY = True
except Exception:  # pragma: no cover
    HAS_SHAPELY = False

EARTH_RADIUS_M = 6_371_000.0


# ---------------------------------------------------------------------------
# Conversion de geometrias
# ---------------------------------------------------------------------------
def to_wkt(value: Any) -> Optional[str]:
    """Normaliza cualquier representacion de geometria a WKT (str)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    data = getattr(value, "data", None)
    if isinstance(data, str):
        return data
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8")
    if HAS_SHAPELY and isinstance(value, BaseGeometry):
        return shapely_wkt.dumps(value)
    wkt_attr = getattr(value, "wkt", None)
    if isinstance(wkt_attr, str):
        return wkt_attr
    return str(value)


def from_geom(value: Any) -> Optional[str]:
    """Normaliza el valor devuelto por la BD a WKT (str)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8")
    data = getattr(value, "data", None)
    if isinstance(data, str):
        return data
    if isinstance(data, (bytes, bytearray)):
        return data.decode("utf-8")
    return str(value)


class WKTGeometry(TypeDecorator):
    """Tipo portatil: almacena geometrias como WKT (TEXT) en cualquier motor.

    En PostgreSQL/PostGIS las columnas espaciales nativas (``geometry``) y sus
    indices GIST se crean/ sincronizan aparte (ver ``app/core/postgis.py``), de
    modo que el esquema ORM es identico en SQLite y PostGIS.
    """

    impl = Text
    cache_ok = True

    def __init__(self, geometry_type: str = "GEOMETRY", srid: int = 4326) -> None:
        self.geometry_type = geometry_type
        self.srid = srid
        super().__init__()

    def process_bind_param(self, value, dialect):
        return to_wkt(value)

    def process_result_value(self, value, dialect):
        return from_geom(value)


# ---------------------------------------------------------------------------
# Geometria y metrica
# ---------------------------------------------------------------------------
def load_geom(wkt: str):
    """Carga un WKT a un objeto Shapely (requiere Shapely)."""
    if not HAS_SHAPELY:  # pragma: no cover
        raise RuntimeError("Shapely no esta disponible para operaciones geometricas")
    return shapely_wkt.loads(wkt)


def geom_to_geojson(wkt: str) -> Optional[dict]:
    if not wkt:
        return None
    return mapping(load_geom(wkt))


def geojson_to_wkt(geojson: dict) -> str:
    return shapely_wkt.dumps(shape(geojson))


def centroid_xy(wkt: str) -> tuple[float, float]:
    """Centroide (lon, lat) de una geometria en WGS84."""
    c = load_geom(wkt).centroid
    return float(c.x), float(c.y)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia great-circle en metros entre dos puntos WGS84."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def polygon_area_ha(wkt: str) -> float:
    """Area aproximada en hectareas usando proyeccion equirectangular local."""
    geom = load_geom(wkt)
    lon, lat = geom.centroid.x, geom.centroid.y
    # Metros por grado en el centroide.
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat))
    # Escalar la geometria a metros y calcular area.
    from shapely.affinity import scale

    scaled = scale(geom, xfact=m_per_deg_lon, yfact=m_per_deg_lat, origin=(lon, lat))
    return float(scaled.area) / 10_000.0


def bbox_polygon(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    """WKT de un rectangulo (para pruebas y recortes)."""
    return (
        f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, "
        f"{max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    )


def make_rectangle(cx: float, cy: float, width_deg: float, height_deg: float,
                   angle_deg: float = 0.0) -> str:
    """WKT de un rectangulo rotado centrado en (cx, cy)."""
    w, h = width_deg / 2, height_deg / 2
    corners = [(-w, -h), (w, -h), (w, h), (-w, h)]
    theta = math.radians(angle_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    pts = []
    for x, y in corners:
        xr = x * cos_t - y * sin_t + cx
        yr = x * sin_t + y * cos_t + cy
        pts.append(f"{xr:.6f} {yr:.6f}")
    pts.append(pts[0])
    return f"POLYGON(({', '.join(pts)}))"


def point_wkt(lon: float, lat: float) -> str:
    return f"POINT({lon:.6f} {lat:.6f})"


def feature_collection(features: Iterable[dict]) -> dict:
    return {"type": "FeatureCollection", "features": list(features)}
