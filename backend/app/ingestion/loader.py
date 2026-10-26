"""Cargadores de archivos (GeoJSON, Shapefile, CSV).

El cargador de Shapefile requiere GeoPandas (dependencia geoespacial opcional);
GeoJSON y CSV funcionan sin dependencias pesadas.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

from app.core.geo import geojson_to_wkt
from app.core.logging import get_logger

logger = get_logger(__name__)


def load_geojson_parcelas(path: str | Path) -> List[dict]:
    """Lee un GeoJSON de parcelas y devuelve registros validables."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    feats = data["features"] if data.get("type") == "FeatureCollection" else [data]
    out: List[dict] = []
    for f in feats:
        props: Dict = f.get("properties", {}) or {}
        geom = f.get("geometry")
        if geom is None:
            continue
        out.append({
            "codigo": props.get("codigo") or props.get("id") or f"PAR-{len(out)+1}",
            "cultivo": props.get("cultivo", "palto"),
            "area_ha": float(props.get("area_ha", 0.0)),
            "geom_wkt": geojson_to_wkt(geom),
            "tipo_suelo": props.get("tipo_suelo"),
            "sistema_riego": props.get("sistema_riego"),
        })
    return out


def load_shapefile_parcelas(path: str | Path) -> List[dict]:
    """Lee un Shapefile con GeoPandas (opcional)."""
    try:
        import geopandas as gpd
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("GeoPandas es necesario para leer Shapefiles") from exc
    gdf = gpd.read_file(path)
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)
    out: List[dict] = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        props = {k: row[k] for k in gdf.columns if k != "geometry"}
        out.append({
            "codigo": props.get("codigo") or f"PAR-{len(out)+1}",
            "cultivo": props.get("cultivo", "palto"),
            "area_ha": float(props.get("area_ha", geom.area if geom else 0.0)),
            "geom_wkt": geom.wkt if geom is not None else None,
            "tipo_suelo": props.get("tipo_suelo"),
            "sistema_riego": props.get("sistema_riego"),
        })
    return [r for r in out if r["geom_wkt"]]


def load_clima_csv(path: str | Path) -> List[dict]:
    out: List[dict] = []
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            out.append({
                "estacion_codigo": row["estacion_codigo"],
                "anio": int(row["anio"]),
                "mes": int(row["mes"]),
                "tmax_c": float(row["tmax_c"]),
                "tmin_c": float(row["tmin_c"]),
                "precip_mm": float(row["precip_mm"]),
                "humedad_pct": float(row["humedad_pct"]) if row.get("humedad_pct") else None,
            })
    return out
