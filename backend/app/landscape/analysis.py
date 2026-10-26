"""Metricas de paisaje: proximidad a habitat, conectividad y contexto espacial.

Las entidades se pasan como diccionarios ligeros (``id``, ``wkt``, ``attrs``)
para desacoplar el calculo de la persistencia. Todas las distancias son en
metros (great-circle) y las areas en hectareas.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence

import numpy as np

from app.core.geo import centroid_xy, haversine_m


def _centroids(items: Sequence[dict]) -> List[tuple[float, float]]:
    return [centroid_xy(it["wkt"]) for it in items]


def habitat_context(
    parcela_wkt: str,
    habitats: Sequence[dict],
    radius_m: float,
) -> Dict[str, float]:
    """Contexto de habitat semi-natural alrededor de una parcela.

    ``habitats``: lista de dicts con ``wkt`` y ``attrs`` (``area_ha``, ``calidad``).
    """
    px, py = centroid_xy(parcela_wkt)
    area_sum = 0.0
    quality_weighted = 0.0
    count = 0
    nearest = float("inf")
    for h in habitats:
        hx, hy = centroid_xy(h["wkt"])
        d = haversine_m(py, px, hy, hx)
        nearest = min(nearest, d)
        if d <= radius_m:
            a = float(h["attrs"].get("area_ha", 0.0))
            q = float(h["attrs"].get("calidad", 0.5))
            area_sum += a
            quality_weighted += a * q
            count += 1
    return {
        "habitat_area_ha": area_sum,
        "habitat_calidad_media": (quality_weighted / area_sum) if area_sum else 0.0,
        "habitat_parches": float(count),
        "dist_habitat_m": 0.0 if nearest == float("inf") else nearest,
    }


def colony_context(
    parcela_wkt: str,
    colmenas: Sequence[dict],
    radius_m: float,
) -> Dict[str, float]:
    px, py = centroid_xy(parcela_wkt)
    n = 0
    nearest = float("inf")
    for c in colmenas:
        cx, cy = centroid_xy(c["wkt"])
        d = haversine_m(py, px, cy, cx)
        nearest = min(nearest, d)
        if d <= radius_m:
            n += int(c["attrs"].get("n_colmenas", 0))
    return {
        "colmenas_cerca": float(n),
        "dist_colmena_m": 0.0 if nearest == float("inf") else nearest,
    }


def connectivity_index(
    patches: Sequence[dict],
    threshold_m: float,
) -> Dict[str, float]:
    """Indice de conectividad estructural del mosaico de parches.

    Une parches cuya distancia entre centroides sea <= ``threshold_m`` y
    reporta numero de componentes, tamano del mayor componente y densidad
    de enlaces.
    """
    if len(patches) < 2:
        return {"componentes": float(len(patches)), "mayor_componente": float(len(patches)),
                "densidad_enlaces": 0.0, "dist_media_vecino_m": 0.0}
    cents = _centroids(patches)
    n = len(cents)
    adj = [[] for _ in range(n)]
    nn_dist = []
    for i in range(n):
        dists = []
        for j in range(n):
            if i == j:
                continue
            d = haversine_m(cents[i][1], cents[i][0], cents[j][1], cents[j][0])
            dists.append(d)
            if d <= threshold_m:
                adj[i].append(j)
        nn_dist.append(min(dists) if dists else 0.0)

    seen = [False] * n
    comps = []
    for s in range(n):
        if seen[s]:
            continue
        stack, comp = [s], 0
        seen[s] = True
        while stack:
            u = stack.pop()
            comp += 1
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
        comps.append(comp)
    edges = sum(len(a) for a in adj) // 2
    max_edges = n * (n - 1) / 2
    return {
        "componentes": float(len(comps)),
        "mayor_componente": float(max(comps)),
        "densidad_enlaces": (edges / max_edges) if max_edges else 0.0,
        "dist_media_vecino_m": float(np.mean(nn_dist)),
    }


def landscape_metrics(
    parcelas: Sequence[dict],
    habitats: Sequence[dict],
    colmenas: Sequence[dict],
    radius_m: float,
    threshold_m: float,
) -> Dict[str, dict]:
    """Contexto de paisaje por parcela (id -> metricas)."""
    out: Dict[str, dict] = {}
    for p in parcelas:
        ctx = {}
        ctx.update(habitat_context(p["wkt"], habitats, radius_m))
        ctx.update(colony_context(p["wkt"], colmenas, radius_m))
        ctx["area_ha"] = float(p["attrs"].get("area_ha", 0.0))
        ctx["cultivo"] = p["attrs"].get("cultivo")
        out[str(p["id"])] = ctx
    return out


def global_landscape_summary(
    habitats: Sequence[dict],
    threshold_m: float,
) -> Dict[str, float]:
    conn = connectivity_index(habitats, threshold_m)
    area = sum(float(h["attrs"].get("area_ha", 0.0)) for h in habitats)
    quality = np.mean([float(h["attrs"].get("calidad", 0.5)) for h in habitats]) if habitats else 0.0
    return {
        "habitat_total_ha": area,
        "habitat_calidad_media": float(quality),
        **conn,
    }
